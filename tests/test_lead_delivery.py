"""tests/test_lead_delivery.py — WO-CARBON-009 lead delivery pipeline tests.

All tests are CI-safe: no SMTP credentials, no Google Sheets API.
In CI mode, email and Sheet both fall back to JSONL outbox files in a temp dir.

Acceptance criteria (INBOX.md):
- /api/lead with full carbon input → email outbox has subject, form fields, DOCX
- /api/report → email outbox has DOCX + subject; Sheet outbox has lead row
- No secrets in repo; env vars control real vs CI paths
- End-to-end golden lead: HTI eligible concession
"""
from __future__ import annotations
import json
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# ── Golden lead payload (HTI eligible, large East Kalimantan polygon) ──────────

_HTI_GEO = {
    "fmt": "coords",
    "payload": "0.9, 117.15",
}

_GOLDEN_LEAD = {
    "name":    "Jane Smith",
    "email":   "jane@example.com",
    "mobile":  "+62 811 000 000",
    "company": "Forestry Co.",
    "iup_name": "PT Hutan Lestari Test",
    "iup_address": "Kalimantan Timur",
    "permit_type": "HTI",
    "permit_years_remaining": 20,
    "project_type": "REDD",
    "payload_summary": "Test lead",
    "geo": _HTI_GEO,
}

_GOLDEN_CARBON_INPUT = {
    "contact": {
        "name":    "Jane Smith",
        "email":   "jane@example.com",
        "mobile":  "+62 811 000 000",
        "company": "Forestry Co.",
    },
    "iup_name": "PT Hutan Lestari Test",
    "iup_address": "Kalimantan Timur",
    "permit_type": "HTI",
    "permit_years_remaining": 20,
    "project_type": "REDD",
    "geo": _HTI_GEO,
}


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def ci_outbox(monkeypatch):
    """Redirect all outbox writes to a temp dir so tests are isolated."""
    d = tempfile.mkdtemp(prefix="180c_test_")
    monkeypatch.setenv("OUTBOX_DIR", d)
    # Ensure SMTP / Sheets are off (CI mode)
    monkeypatch.delenv("EMAIL_HOST", raising=False)
    monkeypatch.delenv("GOOGLE_SHEETS_ID", raising=False)
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in lines]


# ── /api/lead tests ────────────────────────────────────────────────────────────

class TestLeadEndpoint:
    def test_returns_emailed_status(self, ci_outbox):
        res = client.post("/api/lead", json=_GOLDEN_LEAD)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "emailed"
        assert "timestamp" in data

    def test_email_outbox_written(self, ci_outbox):
        client.post("/api/lead", json=_GOLDEN_LEAD)
        records = _read_jsonl(ci_outbox / "outbox_emails.jsonl")
        assert len(records) == 1
        r = records[0]
        assert "PT Hutan Lestari Test" in r["subject"]
        assert r["to"] == "info@180climate.net"

    def test_email_subject_format(self, ci_outbox):
        """Subject must be '{concession} — {filename}'."""
        client.post("/api/lead", json=_GOLDEN_LEAD)
        r = _read_jsonl(ci_outbox / "outbox_emails.jsonl")[0]
        # filename_base is YYMMDDHHMM (10 digits)
        parts = r["subject"].split(" — ")
        assert len(parts) == 2
        assert parts[0] == "PT Hutan Lestari Test"
        assert len(parts[1]) == 10 and parts[1].isdigit()

    def test_email_form_fields_present(self, ci_outbox):
        """All required form fields must appear in the outbox record."""
        client.post("/api/lead", json=_GOLDEN_LEAD)
        r = _read_jsonl(ci_outbox / "outbox_emails.jsonl")[0]
        fd = r["form_data"]
        assert fd["name"]    == "Jane Smith"
        assert fd["email"]   == "jane@example.com"
        assert fd["mobile"]  == "+62 811 000 000"
        assert fd["company"] == "Forestry Co."
        assert fd["iup_name"] == "PT Hutan Lestari Test"
        assert fd["permit_type"] == "HTI"
        assert fd["project_type"] == "REDD"

    def test_email_has_docx_attachment(self, ci_outbox):
        """DOCX must be generated and reported in outbox (geo provided)."""
        client.post("/api/lead", json=_GOLDEN_LEAD)
        r = _read_jsonl(ci_outbox / "outbox_emails.jsonl")[0]
        assert r["attachment_filename"] is not None
        assert r["attachment_filename"].endswith(".docx")
        assert r["attachment_size"] > 1000

    def test_sheet_outbox_written(self, ci_outbox):
        client.post("/api/lead", json=_GOLDEN_LEAD)
        records = _read_jsonl(ci_outbox / "outbox_leads.jsonl")
        assert len(records) == 1
        r = records[0]
        assert r["iup_name"] == "PT Hutan Lestari Test"
        assert r["name"]     == "Jane Smith"
        assert r["email"]    == "jane@example.com"
        assert r["mobile"]   == "+62 811 000 000"
        assert r["permit_type"] == "HTI"
        assert r["project_type"] == "REDD"
        assert "filename_base" in r

    def test_lead_without_geo_still_emails(self, ci_outbox):
        """Lead without geo (minimal form) still sends email without DOCX."""
        minimal = {
            "name":  "Bob",
            "email": "bob@example.com",
            "mobile": "+60 12 000 0000",
            "iup_name": "PT Test",
            "permit_type": "HA",
        }
        res = client.post("/api/lead", json=minimal)
        assert res.status_code == 200
        records = _read_jsonl(ci_outbox / "outbox_emails.jsonl")
        assert len(records) == 1
        r = records[0]
        assert r["attachment_filename"] is None  # no DOCX without geo
        assert r["attachment_size"] == 0

    def test_no_secrets_in_payload(self, ci_outbox):
        """Outbox must not contain SMTP password or credential keys."""
        client.post("/api/lead", json=_GOLDEN_LEAD)
        content = (ci_outbox / "outbox_emails.jsonl").read_text()
        assert "EMAIL_PASSWORD" not in content
        assert "GOOGLE_CREDENTIALS_JSON" not in content
        assert "AKIA" not in content  # AWS key pattern


# ── /api/report tests ─────────────────────────────────────────────────────────

class TestReportEndpoint:
    def test_pdf_download_triggers_email(self, ci_outbox):
        res = client.post("/api/report?fmt=pdf", json=_GOLDEN_CARBON_INPUT)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        # Email must have been dispatched
        records = _read_jsonl(ci_outbox / "outbox_emails.jsonl")
        assert len(records) == 1

    def test_docx_download_triggers_email(self, ci_outbox):
        res = client.post("/api/report?fmt=docx", json=_GOLDEN_CARBON_INPUT)
        assert res.status_code == 200
        assert res.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument"
        )
        records = _read_jsonl(ci_outbox / "outbox_emails.jsonl")
        assert len(records) == 1

    def test_report_email_has_docx_attachment(self, ci_outbox):
        client.post("/api/report?fmt=pdf", json=_GOLDEN_CARBON_INPUT)
        r = _read_jsonl(ci_outbox / "outbox_emails.jsonl")[0]
        assert r["attachment_filename"].endswith(".docx")
        assert r["attachment_size"] > 1000

    def test_report_email_subject_format(self, ci_outbox):
        client.post("/api/report?fmt=pdf", json=_GOLDEN_CARBON_INPUT)
        r = _read_jsonl(ci_outbox / "outbox_emails.jsonl")[0]
        parts = r["subject"].split(" — ")
        assert len(parts) == 2
        assert "PT Hutan Lestari Test" in parts[0]
        assert len(parts[1]) == 10 and parts[1].isdigit()

    def test_report_sheet_written(self, ci_outbox):
        client.post("/api/report?fmt=pdf", json=_GOLDEN_CARBON_INPUT)
        records = _read_jsonl(ci_outbox / "outbox_leads.jsonl")
        assert len(records) == 1
        r = records[0]
        assert r["iup_name"] == "PT Hutan Lestari Test"
        assert r["permit_type"] == "HTI"

    def test_report_form_has_geometry_summary(self, ci_outbox):
        client.post("/api/report?fmt=pdf", json=_GOLDEN_CARBON_INPUT)
        r = _read_jsonl(ci_outbox / "outbox_emails.jsonl")[0]
        assert r["form_data"]["geometry_summary"] not in ("", "—", None)
        assert r["form_data"]["area_ha"] is not None

    def test_content_disposition_filename(self, ci_outbox):
        res = client.post("/api/report?fmt=pdf", json=_GOLDEN_CARBON_INPUT)
        cd = res.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".pdf" in cd
