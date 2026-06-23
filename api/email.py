"""api/email.py — Lead email delivery.

Reads SMTP credentials from environment variables:
  EMAIL_HOST     (default: localhost)
  EMAIL_PORT     (default: 587)
  EMAIL_USER     (optional)
  EMAIL_PASSWORD (optional)
  EMAIL_FROM     (default: noreply@180climate.net)

If EMAIL_HOST is not set or credentials are missing, falls back to writing the email
content to coordination/evidence/email.log — safe for CI and dev without credentials.

Secrets MUST NOT appear in the repo (ADR-0004).
"""
from __future__ import annotations
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from core.contracts import LeadCapture

_TO = "info@180climate.net"
_LOG_PATH = Path(__file__).parent.parent / "coordination" / "evidence" / "email.log"


def _build_body(lead: LeadCapture) -> str:
    c = lead.contact
    lines = [
        f"New lead captured — {lead.timestamp}",
        f"Engine: {lead.engine}",
        "",
        "=== Contact details ===",
        f"Name:    {c.name}",
        f"Email:   {c.email}",
        f"Mobile:  {c.mobile or '—'}",
        f"Company: {c.company or '—'}",
        "",
        "=== Concession summary ===",
        lead.payload_summary,
    ]
    return "\n".join(lines)


def send_lead_email(lead: LeadCapture, subject_prefix: str = "180Climate lead") -> bool:
    """Send lead email to info@180climate.net. Returns True on success.

    Falls back to logging to coordination/evidence/email.log if SMTP not configured.
    """
    host = os.environ.get("EMAIL_HOST", "")
    port = int(os.environ.get("EMAIL_PORT", "587"))
    user = os.environ.get("EMAIL_USER", "")
    password = os.environ.get("EMAIL_PASSWORD", "")
    from_addr = os.environ.get("EMAIL_FROM", "noreply@180climate.net")

    body = _build_body(lead)
    subject = f"{subject_prefix} — {lead.timestamp}"

    if not host:
        # No SMTP configured — write to log (CI / dev mode)
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\nSUBJECT: {subject}\nTO: {_TO}\n{'='*60}\n{body}\n")
        return True  # logged successfully

    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = _TO
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [_TO], msg.as_string())
        return True
    except Exception as exc:
        # Log the failure but don't crash the API
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\nEMAIL SEND FAILED: {exc}\nSUBJECT: {subject}\n{body}\n")
        return False
