"""api/email.py — Lead email delivery with DOCX attachment.

Reads SMTP credentials from environment variables:
  EMAIL_HOST     (default: unset → CI/dev fallback)
  EMAIL_PORT     (default: 587)
  EMAIL_USE_SSL  (set to "true" for port-465 SMTP_SSL; default auto-detect by port)
  EMAIL_USER     (optional)
  EMAIL_PASSWORD (optional)
  EMAIL_FROM     (default: noreply@180climate.net)
  OUTBOX_DIR     (optional — CI test hook; overrides the outbox write path)

SSL mode selection (Hostinger):
  port 465 → smtplib.SMTP_SSL  (implicit TLS at connect — set EMAIL_USE_SSL=true or port=465)
  port 587 → smtplib.SMTP + starttls()  (STARTTLS — default)

If EMAIL_HOST is not set, falls back to writing the email to
  {OUTBOX_DIR}/outbox_emails.jsonl  (JSONL, one record per email)
  coordination/evidence/outbox_emails.jsonl  (default when OUTBOX_DIR unset)

Secrets MUST NOT appear in the repo (ADR-0004).
"""
from __future__ import annotations
import json
import os
import smtplib
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

_TO = "info@180climate.net"
_COORD_EVIDENCE = Path(__file__).parent.parent / "coordination" / "evidence"


def _outbox_path() -> Path:
    d = os.environ.get("OUTBOX_DIR", "")
    base = Path(d) if d else _COORD_EVIDENCE
    base.mkdir(parents=True, exist_ok=True)
    return base / "outbox_emails.jsonl"


def _build_body(form_data: dict) -> str:
    c = form_data
    lines = [
        f"New lead — {c.get('timestamp', '—')}",
        "",
        "=== Contact ===",
        f"Name:         {c.get('name', '—')}",
        f"Email:        {c.get('email', '—')}",
        f"Mobile (WA):  {c.get('mobile') or '—'}",
        f"Company:      {c.get('company') or '—'}",
        "",
        "=== Concession ===",
        f"Name:         {c.get('iup_name', '—')}",
        f"Region:       {c.get('iup_address') or '—'}",
        f"Permit type:  {c.get('permit_type', '—')}",
        f"Permit yrs:   {c.get('permit_years_remaining', '—')}",
        f"Project type: {c.get('project_type', '—')}",
        f"Area:         {c.get('area_ha', '—')} ha",
        f"Geometry:     {c.get('geometry_summary', '—')}",
        "",
        "=== Carbon result ===",
        c.get('payload_summary', '—'),
    ]
    return "\n".join(lines)


def send_lead_email(
    iup_name: str,
    filename_base: str,
    form_data: dict,
    docx_bytes: Optional[bytes] = None,
) -> bool:
    """Send lead notification to info@180climate.net with DOCX attached.

    Returns True on success (SMTP) or logging (CI/dev fallback).
    """
    subject = f"{iup_name} — {filename_base}"
    body = _build_body(form_data)
    ts = datetime.now(timezone.utc).isoformat()

    host = os.environ.get("EMAIL_HOST", "")
    if not host:
        # CI / dev mode: write structured record to JSONL outbox
        record = {
            "ts": ts,
            "subject": subject,
            "to": _TO,
            "form_data": form_data,
            "attachment_filename": f"{filename_base}.docx" if docx_bytes else None,
            "attachment_size": len(docx_bytes) if docx_bytes else 0,
        }
        path = _outbox_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True

    port      = int(os.environ.get("EMAIL_PORT", "587"))
    use_ssl   = os.environ.get("EMAIL_USE_SSL", "").lower() == "true" or port == 465
    user      = os.environ.get("EMAIL_USER", "")
    password  = os.environ.get("EMAIL_PASSWORD", "")
    from_addr = os.environ.get("EMAIL_FROM", "noreply@180climate.net")

    try:
        msg = MIMEMultipart()
        msg["From"]    = from_addr
        msg["To"]      = _TO
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if docx_bytes:
            part = MIMEBase(
                "application",
                "vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            part.set_payload(docx_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename_base}.docx"',
            )
            msg.attach(part)

        if use_ssl:
            # Port 465 — implicit TLS at connect (Hostinger SMTP_SSL)
            with smtplib.SMTP_SSL(host, port) as server:
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [_TO], msg.as_string())
        else:
            # Port 587 — STARTTLS
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [_TO], msg.as_string())
        return True
    except Exception as exc:
        # Fallback: write failure record to outbox so no lead is silently lost
        record = {
            "ts": ts,
            "subject": subject,
            "to": _TO,
            "form_data": form_data,
            "attachment_filename": f"{filename_base}.docx" if docx_bytes else None,
            "attachment_size": len(docx_bytes) if docx_bytes else 0,
            "_smtp_error": str(exc),
        }
        path = _outbox_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return False
