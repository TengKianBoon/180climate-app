"""api/sheets.py — Google Sheets lead appender.

Reads from environment variables:
  GOOGLE_SHEETS_ID         — spreadsheet ID (not the URL, just the ID)
  GOOGLE_CREDENTIALS_JSON  — service account credentials JSON as a string
  OUTBOX_DIR               — optional CI override for outbox directory

If GOOGLE_SHEETS_ID is not set, falls back to writing the row to
  {OUTBOX_DIR}/outbox_leads.jsonl  (JSONL, one record per lead)

Sheet column order (row 1 header expected in the real sheet):
  timestamp | iup_name | name | email | mobile | company | permit_type |
  permit_years_remaining | project_type | area_ha | geometry_summary |
  verdict | quantity_low_tco2e | quantity_high_tco2e | filename_base

Secrets MUST NOT appear in the repo (ADR-0004).
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_COORD_EVIDENCE = Path(__file__).parent.parent / "coordination" / "evidence"

_COLUMNS = [
    "timestamp", "iup_name", "name", "email", "mobile", "company",
    "permit_type", "permit_years_remaining", "project_type",
    "area_ha", "geometry_summary",
    "verdict", "quantity_low_tco2e", "quantity_high_tco2e",
    "filename_base",
]


def _outbox_path() -> Path:
    d = os.environ.get("OUTBOX_DIR", "")
    base = Path(d) if d else _COORD_EVIDENCE
    base.mkdir(parents=True, exist_ok=True)
    return base / "outbox_leads.jsonl"


def append_lead(row: dict) -> bool:
    """Append a lead row to the Google Sheet, or to the JSONL outbox in CI.

    `row` should contain the keys listed in _COLUMNS (extras are ignored in
    real-sheet mode; all are preserved in JSONL mode).

    Returns True on success or CI-fallback write.
    """
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    ts = row.get("timestamp") or datetime.now(timezone.utc).isoformat()

    if not sheets_id:
        log.info("SHEETS: GOOGLE_SHEETS_ID NOT SET -> outbox")
        # CI / dev mode: write to JSONL outbox
        record = {"ts": ts, **row}
        path = _outbox_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
        creds = Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(sheets_id).sheet1
        values = [str(row.get(col, "")) for col in _COLUMNS]
        ws.append_row(values, value_input_option="USER_ENTERED")
        log.info("SHEETS: appended row to %s", sheets_id)
        return True

    except Exception as exc:
        log.error("SHEETS: ERROR: %s", exc)
        # Fallback: write failure record to JSONL so no lead is lost
        record = {"ts": ts, "_sheets_error": str(exc), **row}
        path = _outbox_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return False
