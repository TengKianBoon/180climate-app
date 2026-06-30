"""api/email.py — Lead email delivery with PDF attachment.

Sends via (in priority order):
  1. Brevo HTTPS API (port 443) when BREVO_API_KEY is set — works on Render free tier
  2. smtplib SMTP when EMAIL_HOST is set — for non-Render envs
  3. JSONL outbox (CI / dev mode) when neither is set

Env vars:
  BREVO_API_KEY          — Brevo transactional API key
  LEAD_RECIPIENT_EMAIL   — recipient (default: leoniches@gmail.com)
  EMAIL_HOST, EMAIL_PORT, EMAIL_USE_SSL, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM
  OUTBOX_DIR             — CI override for outbox directory

Secrets MUST NOT appear in the repo (ADR-0004).
"""
from __future__ import annotations
import base64
import html
import json
import logging
import os
import smtplib

import httpx

log = logging.getLogger(__name__)
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

_FROM_EMAIL = "john@180climate.net"
_FROM_NAME = "180Climate"
_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_COORD_EVIDENCE = Path(__file__).parent.parent / "coordination" / "evidence"


def _recipient() -> str:
    return os.environ.get("LEAD_RECIPIENT_EMAIL", "leoniches@gmail.com")


def _outbox_path() -> Path:
    d = os.environ.get("OUTBOX_DIR", "")
    base = Path(d) if d else _COORD_EVIDENCE
    base.mkdir(parents=True, exist_ok=True)
    return base / "outbox_emails.jsonl"


def _write_outbox(
    ts: str,
    subject: str,
    form_data: dict,
    filename_base: str,
    pdf_bytes: Optional[bytes],
    extra: Optional[dict] = None,
) -> None:
    record: dict = {
        "ts": ts,
        "subject": subject,
        "to": _recipient(),
        "form_data": form_data,
        "attachment_filename": f"{filename_base}.pdf" if pdf_bytes else None,
        "attachment_size": len(pdf_bytes) if pdf_bytes else 0,
    }
    if extra:
        record.update(extra)
    path = _outbox_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _build_body(form_data: dict) -> str:
    c = form_data
    low  = c.get("quantity_low_tco2e")
    high = c.get("quantity_high_tco2e")
    low_yr  = c.get("quantity_low_per_yr_tco2e")
    high_yr = c.get("quantity_high_per_yr_tco2e")

    if low is not None and high is not None:
        carbon_range = f"{low:,.0f} – {high:,.0f} tCO2e (lifetime)"
        if low_yr is not None and high_yr is not None:
            carbon_range += f" | {low_yr:,.0f} – {high_yr:,.0f} tCO2e/yr"
    else:
        carbon_range = "—"

    lines = [
        f"New 180Climate lead — {c.get('timestamp', '—')}",
        "",
        "=== Contact ===",
        f"Name:         {c.get('name', '—')}",
        f"Email:        {c.get('email', '—')}",
        f"Mobile (WA):  {c.get('mobile') or '—'}",
        f"Company:      {c.get('company') or '—'}",
        "",
        "=== Concession ===",
        f"IUP name:     {c.get('iup_name', '—')}",
        f"Region:       {c.get('iup_address') or '—'}",
        f"Permit type:  {c.get('permit_type', '—')}",
        f"Permit yrs:   {c.get('permit_years_remaining', '—')}",
        f"Project type: {c.get('project_type', '—')}",
        f"Area:         {c.get('area_ha', '—')} ha",
        f"Geometry:     {c.get('geometry_summary', '—')}",
        "",
        "=== Carbon screening ===",
        f"Verdict:      {c.get('verdict', '—')}",
        f"Range:        {carbon_range}",
        f"Summary:      {c.get('payload_summary', '—')}",
    ]
    return "\n".join(lines)


def _build_html_body(form_data: dict) -> str:
    escaped = html.escape(_build_body(form_data))
    return f'<pre style="font-family:monospace;font-size:13px">{escaped}</pre>'


def send_lead_email(
    iup_name: str,
    filename_base: str,
    form_data: dict,
    pdf_bytes: Optional[bytes] = None,
    subject_override: Optional[str] = None,
) -> bool:
    """Send lead notification with PDF attached.

    Returns True on success (Brevo / SMTP) or outbox-write (CI/dev fallback).
    """
    contact_name = form_data.get("name") or iup_name
    subject = subject_override or f"New 180Climate lead — {contact_name} · {iup_name}"
    ts = datetime.now(timezone.utc).isoformat()

    brevo_key = os.environ.get("BREVO_API_KEY", "")
    if brevo_key:
        return _send_via_brevo(brevo_key, subject, form_data, filename_base, pdf_bytes, ts)

    host = os.environ.get("EMAIL_HOST", "")
    if not host:
        log.info("EMAIL: EMAIL_HOST NOT SET -> outbox, NO email sent")
        _write_outbox(ts, subject, form_data, filename_base, pdf_bytes)
        return True

    return _send_via_smtp(host, subject, form_data, filename_base, pdf_bytes, ts)


def _send_via_brevo(
    api_key: str,
    subject: str,
    form_data: dict,
    filename_base: str,
    pdf_bytes: Optional[bytes],
    ts: str,
) -> bool:
    to = _recipient()
    payload: dict = {
        "sender": {"name": _FROM_NAME, "email": _FROM_EMAIL},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": _build_html_body(form_data),
    }
    if pdf_bytes:
        payload["attachment"] = [
            {
                "name": f"{filename_base}.pdf",
                "content": base64.b64encode(pdf_bytes).decode(),
            }
        ]
    headers = {
        "api-key": api_key,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        resp = httpx.post(_BREVO_URL, json=payload, headers=headers, timeout=15.0)
        if resp.status_code == 201:
            log.info('EMAIL: SENT OK (Brevo) -> %s (subject="%s")', to, subject)
            return True
        log.error("EMAIL: BREVO ERROR: %s %s", resp.status_code, resp.text[:500])
    except Exception as exc:
        log.error("EMAIL: BREVO ERROR: %s", exc)
    _write_outbox(ts, subject, form_data, filename_base, pdf_bytes, {"_brevo_error": True})
    return False


def _send_via_smtp(
    host: str,
    subject: str,
    form_data: dict,
    filename_base: str,
    pdf_bytes: Optional[bytes],
    ts: str,
) -> bool:
    to = _recipient()
    body = _build_body(form_data)
    port      = int(os.environ.get("EMAIL_PORT", "587"))
    use_ssl   = os.environ.get("EMAIL_USE_SSL", "").lower() == "true" or port == 465
    user      = os.environ.get("EMAIL_USER", "")
    password  = os.environ.get("EMAIL_PASSWORD", "")
    from_addr = os.environ.get("EMAIL_FROM", "john@180climate.net")

    log.info("EMAIL: connecting %s:%s ssl=%s FROM=%s TO=%s", host, port, use_ssl, from_addr, to)
    try:
        msg = MIMEMultipart()
        msg["From"]    = from_addr
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if pdf_bytes:
            part = MIMEBase("application", "pdf")
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename_base}.pdf"',
            )
            msg.attach(part)

        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as server:
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to], msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to], msg.as_string())
        log.info("EMAIL: SENT OK")
        return True
    except Exception as exc:
        log.error("EMAIL: SMTP ERROR: %s", exc)
        _write_outbox(ts, subject, form_data, filename_base, pdf_bytes, {"_smtp_error": str(exc)})
        return False
