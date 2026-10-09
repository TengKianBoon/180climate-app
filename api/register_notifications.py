"""Durable private Excel notifications for saved Carbon and EUDR submissions.

Defaults off. Uses the existing operational recipient and Brevo key. No uploads
to Google Drive, no public export, no customer-facing register or extra service.
"""
from __future__ import annotations

import asyncio
import base64
import html
import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from api.email import _BREVO_URL, _FROM_EMAIL, _FROM_NAME, _recipient
from api.intake import connection, database_path, public_storage_status
from reports.submission_register import build_register

log = logging.getLogger(__name__)


def enabled() -> bool:
    return os.environ.get("INTAKE_REGISTER_EMAIL_ENABLED", "").strip().lower() == "true"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def configuration_gaps() -> list[str]:
    gaps = []
    if not public_storage_status()["ready"]:
        gaps.append("intake_registry_not_ready")
    if not _recipient():
        gaps.append("recipient_missing")
    if not os.environ.get("BREVO_API_KEY", "").strip():
        gaps.append("brevo_key_missing")
    return gaps


def snapshot_path() -> Path:
    return database_path().parent / "180Climate-Submission-Register.xlsx"


def refresh_snapshot() -> tuple[bytes, list[dict[str, Any]]]:
    """Rebuild from the authoritative DB and atomically replace the private file."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM intake_submissions WHERE retention_due_at > ? ORDER BY created_at DESC, rowid DESC",
            (_now().isoformat(),),
        ).fetchall()
    records = [dict(row) for row in rows]
    data = build_register(records)
    path = snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix="register-", suffix=".tmp", delete=False) as f:
        temporary = Path(f.name)
        f.write(data)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return data, records


def _send(job: dict[str, Any], workbook: bytes, records: list[dict[str, Any]]) -> tuple[str, str | None, str | None]:
    """Return accepted, retry or attention. Never log API bodies or customer data."""
    if job["recipient"] != _recipient() or not job["recipient"]:
        return "attention", None, "recipient_configuration_changed"
    if job["attempts"] > 1 and _now() - datetime.fromisoformat(job["first_attempt_at"]) > timedelta(minutes=25):
        return "attention", None, "retry_window_expired_check_delivery"
    subject = f"[180Climate register] {job['reference']} - latest submissions first"
    text = (
        f"A new Carbon or EUDR submission was saved: {job['reference']}.\n"
        f"The attached Excel register contains {len(records)} current submissions, newest first.\n"
        "Tabs: Submissions, Coordinates and Form answers.\n"
        "Carbon quantities are indicative estimates in metric tonnes of CO2e. They are not issued VCUs.\n"
        "EUDR screening does not calculate carbon credits.\n"
        "This private register contains contact details and precise plot coordinates."
    )
    payload = {
        "sender": {"name": _FROM_NAME, "email": _FROM_EMAIL},
        "to": [{"email": job["recipient"]}],
        "subject": subject, "textContent": text,
        "htmlContent": f"<pre>{html.escape(text)}</pre>",
        "headers": {"idempotencyKey": str(uuid.uuid5(uuid.NAMESPACE_URL, f"180climate-register:{job['reference']}"))},
        "tags": ["180climate-registration-register"],
        "attachment": [{"name": "180Climate-Submission-Register.xlsx", "content": base64.b64encode(workbook).decode("ascii")}],
    }
    # Leave provider headroom; an oversized register is visible as operator attention.
    if len(workbook) > 10 * 1024 * 1024:
        return "attention", None, "attachment_too_large"
    try:
        response = httpx.post(
            _BREVO_URL, json=payload,
            headers={"api-key": os.environ["BREVO_API_KEY"], "content-type": "application/json", "accept": "application/json"},
            timeout=20.0,
        )
        if response.status_code == 201:
            return "accepted", response.json().get("messageId"), None
        if response.status_code == 400:
            try:
                if response.json().get("code") == "duplicate_parameter":
                    return "attention", None, "provider_duplicate_check_delivery"
            except ValueError:
                pass
        if response.status_code == 429 or response.status_code >= 500:
            return "retry", None, f"provider_http_{response.status_code}"
        return "attention", None, f"provider_http_{response.status_code}"
    except httpx.HTTPError:
        return "retry", None, "provider_connection_error"
    except (ValueError, KeyError):
        return "attention", None, "provider_response_unconfirmed"


def process_one_job() -> bool:
    if not enabled() or configuration_gaps():
        return False
    now = _now()
    with connection() as conn:
        # One atomic claim also works when a deployment briefly overlaps instances.
        row = conn.execute(
            """UPDATE intake_register_jobs SET state='sending', claimed_at=?,
                   first_attempt_at=COALESCE(first_attempt_at,?), attempts=attempts+1
               WHERE reference=(SELECT reference FROM intake_register_jobs
                 WHERE (state='pending' AND next_attempt_at<=?)
                    OR (state='sending' AND claimed_at<?)
                 ORDER BY created_at, reference LIMIT 1) RETURNING *""",
            (now.isoformat(), now.isoformat(), now.isoformat(), (now-timedelta(minutes=5)).isoformat()),
        ).fetchone()
    if row is None:
        return False
    job = dict(row)
    try:
        workbook, records = refresh_snapshot()
        if not any(r["reference"] == job["reference"] for r in records):
            state, message_id, error = "cancelled", None, "submission_removed_or_expired"
        else:
            state, message_id, error = _send(job, workbook, records)
    except Exception:
        state, message_id, error = "retry", None, "register_generation_failed"
        log.warning("Private register generation failed; notification remains queued")
    # Retries fit within Brevo's 30-minute idempotency window. Ambiguous or
    # repeatedly failed notifications remain visible for operator review.
    next_attempt = now + timedelta(seconds=60 * 2 ** min(job["attempts"]-1, 4))
    if state == "retry":
        state = "pending" if job["attempts"] < 5 else "attention"
    with connection() as conn:
        conn.execute(
            "UPDATE intake_register_jobs SET state=?, next_attempt_at=?, accepted_at=?, message_id=?, last_error=? WHERE reference=?",
            (state, next_attempt.isoformat(), now.isoformat() if state == "accepted" else None, message_id, error, job["reference"]),
        )
    if state == "attention":
        log.warning("Private register notification requires operator attention: %s", error)
    return True


def notification_status() -> dict[str, Any]:
    with connection() as conn:
        counts = {r["state"]: r["n"] for r in conn.execute("SELECT state,COUNT(*) AS n FROM intake_register_jobs GROUP BY state")}
        recent = [dict(r) for r in conn.execute(
            "SELECT reference,state,attempts,accepted_at,message_id,last_error FROM intake_register_jobs ORDER BY created_at DESC,rowid DESC LIMIT 20"
        )]
    return {"enabled": enabled(), "configuration_gaps": configuration_gaps(), "recipient": _recipient(),
            "counts": counts, "recent": recent, "provider_acceptance_is_delivery_confirmation": False}


async def _worker(stop: asyncio.Event) -> None:
    last_refresh = 0.0
    while not stop.is_set():
        try:
            handled = await asyncio.to_thread(process_one_job)
            if enabled() and public_storage_status()["ready"]:
                # Refresh idle snapshots hourly so expired records disappear too.
                clock = asyncio.get_running_loop().time()
                if not handled and clock-last_refresh > 3600:
                    await asyncio.to_thread(refresh_snapshot)
                    last_refresh = clock
        except Exception:
            log.warning("Private register worker unavailable; saved jobs remain in the database")
        try:
            await asyncio.wait_for(stop.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass


@asynccontextmanager
async def register_lifespan(app):
    stop = asyncio.Event()
    task = asyncio.create_task(_worker(stop))
    try:
        yield
    finally:
        stop.set()
        await task
