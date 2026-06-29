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
from unittest.mock import MagicMock, patch
import httpx
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api.email import send_lead_email
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
    # Ensure SMTP / Brevo / Sheets are off (CI mode)
    monkeypatch.delenv("EMAIL_HOST", raising=False)
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
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
        """Outbox must not contain SMTP password, Brevo key, or credential keys."""
        client.post("/api/lead", json=_GOLDEN_LEAD)
        content = (ci_outbox / "outbox_emails.jsonl").read_text(encoding="utf-8")
        assert "EMAIL_PASSWORD" not in content
        assert "BREVO_API_KEY" not in content
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


# ── Brevo HTTP API unit tests ──────────────────────────────────────────────────

class TestBrevoEmail:
    """Unit tests for the Brevo HTTPS API send path in send_lead_email.

    Mocks httpx.post so no network calls are made. ci_outbox fixture (autouse)
    sets OUTBOX_DIR and removes EMAIL_HOST / BREVO_API_KEY / GOOGLE_SHEETS_ID.
    """

    def test_brevo_201_sent_ok(self, ci_outbox, monkeypatch):
        """HTTP 201 from Brevo → returns True, no outbox record written."""
        monkeypatch.setenv("BREVO_API_KEY", "test-key-brevo-abc")

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.text = '{"messageId":"<abc@smtp-relay.mailin.fr>"}'

        with patch("api.email.httpx.post", return_value=mock_resp) as mock_post:
            result = send_lead_email("PT Brevo Test", "2606291200", {"name": "Alice"}, b"docxdata")

        assert result is True
        mock_post.assert_called_once()
        # Key must be in headers, never in the JSON payload body
        call_headers = mock_post.call_args.kwargs.get("headers", {})
        assert call_headers.get("api-key") == "test-key-brevo-abc"
        # No outbox record on success
        outbox = ci_outbox / "outbox_emails.jsonl"
        assert not outbox.exists() or _read_jsonl(outbox) == []

    def test_brevo_4xx_writes_outbox(self, ci_outbox, monkeypatch):
        """Non-201 from Brevo → returns False, outbox record written (lead not lost)."""
        monkeypatch.setenv("BREVO_API_KEY", "test-key-brevo-abc")

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"code":"unauthorized","message":"Key not found"}'

        with patch("api.email.httpx.post", return_value=mock_resp):
            result = send_lead_email("PT Brevo Test", "2606291200", {"name": "Alice"}, b"docxdata")

        assert result is False
        records = _read_jsonl(ci_outbox / "outbox_emails.jsonl")
        assert len(records) == 1
        r = records[0]
        assert r["_brevo_error"] is True
        assert "PT Brevo Test" in r["subject"]

    def test_brevo_network_exception_writes_outbox(self, ci_outbox, monkeypatch):
        """httpx exception (network down) → returns False, outbox record written."""
        monkeypatch.setenv("BREVO_API_KEY", "test-key-brevo-abc")

        with patch("api.email.httpx.post", side_effect=httpx.ConnectError("timeout")):
            result = send_lead_email("PT Brevo Test", "2606291200", {"name": "Alice"})

        assert result is False
        records = _read_jsonl(ci_outbox / "outbox_emails.jsonl")
        assert len(records) == 1
        assert records[0]["_brevo_error"] is True

    def test_no_brevo_key_falls_back_to_outbox(self, ci_outbox, monkeypatch):
        """No BREVO_API_KEY and no EMAIL_HOST → outbox written, returns True."""
        # ci_outbox already removed BREVO_API_KEY and EMAIL_HOST
        result = send_lead_email("PT Fallback Test", "2606291300", {"name": "Bob"})

        assert result is True
        records = _read_jsonl(ci_outbox / "outbox_emails.jsonl")
        assert len(records) == 1
        assert "_brevo_error" not in records[0]

    def test_brevo_key_never_in_outbox(self, ci_outbox, monkeypatch):
        """Brevo API key must never appear in outbox records on error."""
        monkeypatch.setenv("BREVO_API_KEY", "SECRET-brevo-key-xyz")

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("api.email.httpx.post", return_value=mock_resp):
            send_lead_email("PT Secret Test", "2606291400", {"name": "Carol"})

        content = (ci_outbox / "outbox_emails.jsonl").read_text(encoding="utf-8")
        assert "SECRET-brevo-key-xyz" not in content
        assert "BREVO_API_KEY" not in content
