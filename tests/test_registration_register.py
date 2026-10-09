from __future__ import annotations

import base64
import io
import json
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx
import pytest
from fastapi.testclient import TestClient

from api import register_notifications as notifications
from api.intake import capture_submission
from api.main import app
from reports.submission_register import build_register, register_tables

NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv("INTAKE_RECORDING_MODE", "required")
    path = tmp_path / "private" / "intake.sqlite3"
    monkeypatch.setenv("INTAKE_DB_PATH", str(path))
    monkeypatch.setenv("INTAKE_RETENTION_DAYS", "180")
    monkeypatch.setenv("INTAKE_STORE_GEOMETRY", "true")
    monkeypatch.setenv("INTAKE_OPERATOR_TOKEN", "synthetic-operator-token")
    monkeypatch.setenv("LEAD_RECIPIENT_EMAIL", "operator@example.invalid")
    monkeypatch.setenv("BREVO_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("INTAKE_REGISTER_EMAIL_ENABLED", "true")
    for suffix in ("CONTROLLER_NAME", "PRIVACY_CONTACT", "HOSTING_REGION", "RETENTION_VERSION", "PROCESSOR_LIST_VERSION", "OPERATOR_OWNER", "AUTHORISED_DEPLOYER", "BAHASA_PACK_VERSION", "COUNSEL_APPROVAL_ID", "COMPANY_APPROVAL_ID"):
        monkeypatch.setenv("INTAKE_" + suffix, "synthetic-test-approval")
    return path


def capture(application="carbon"):
    return capture_submission(
        application=application, source_route="/api/" + application,
        contact={"name": "SYNTHETIC REGISTER QA", "email": "synthetic@example.invalid", "company": "Synthetic Co"},
        form={"iup_name": "Synthetic Project", "permit_type": "HTI", "permit_years_remaining": 20, "commodity": "palm"},
        geometry_geojson={"type": "Polygon", "coordinates": [[[113.111111,-1.111111],[113.211111,-1.111111],[113.211111,-1.211111],[113.111111,-1.111111]]]},
        result={"verdict": "Flagged - review required", "map": {"loss_overlay": {"quantity_low_tco2e": 1200, "quantity_high_tco2e": 2400, "quantity_low_per_yr_tco2e": 40, "quantity_high_per_yr_tco2e": 80, "area_ha": 123}}, "overall": "loss_detected", "plot_count": 1, "plots": [{"area_ha": 123,"loss_after_2020_ha":1.25}]},
    )


def workbook_cells(data, index):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        sheet = ET.fromstring(z.read(f"xl/worksheets/sheet{index}.xml"))
        return sheet, {c.get("r"): c for c in sheet.findall(".//x:c", NS)}


def literal(cell):
    return "".join(cell.itertext())


def test_default_off_does_not_queue(configured, monkeypatch):
    monkeypatch.delenv("INTAKE_REGISTER_EMAIL_ENABLED")
    capture()
    with sqlite3.connect(configured) as db:
        assert db.execute("SELECT count(*) FROM intake_register_jobs").fetchone()[0] == 0
    assert notifications.process_one_job() is False


def test_unknown_eudr_metrics_are_blank_and_known_zero_is_numeric(configured):
    reference = capture("eudr")
    with sqlite3.connect(configured) as db:
        db.row_factory = sqlite3.Row
        record = dict(db.execute("SELECT * FROM intake_submissions WHERE reference=?", (reference,)).fetchone())
    record["result_json"] = json.dumps({"overall": "inconclusive", "plots": [
        {"area_ha": 123, "loss_after_2020_ha": 0},
        {"area_ha": None, "loss_after_2020_ha": None},
    ]})
    row = register_tables([record])[0][0]
    assert row[20] is None and row[22] is None
    record["result_json"] = json.dumps({"overall": "clear", "plots": [
        {"area_ha": 123, "loss_after_2020_ha": 0},
    ]})
    row = register_tables([record])[0][0]
    assert row[20] == 123 and row[22] == 0


def test_newest_first_ranges_coords_and_formulas_are_literal(configured):
    carbon, eudr = capture(), capture("eudr")
    with sqlite3.connect(configured) as db:
        db.execute("UPDATE intake_submissions SET contact_name=? WHERE reference=?", ('=WEBSERVICE("https://example.invalid")', carbon))
    data, records = notifications.refresh_snapshot()
    sheet, cells = workbook_cells(data, 1)
    assert literal(cells["A2"]) == eudr and literal(cells["A3"]) == carbon
    assert cells["F2"].find("x:v", NS) is None  # EUDR has no carbon estimate
    assert literal(cells["F3"]) == "1200.0" and literal(cells["G3"]) == "2400.0"
    assert literal(cells["J3"]) == "30"
    assert cells["B2"].get("t") == "n" and cells["B2"].get("s")
    assert cells["L3"].get("t") == "inlineStr" and literal(cells["L3"]).startswith("=WEBSERVICE")
    assert not sheet.findall(".//x:f", NS)
    _, coordinates = workbook_cells(data, 2)
    assert literal(coordinates["A2"]) == eudr
    assert literal(coordinates["G2"]) == "113.111111"
    assert literal(coordinates["H2"]) == "-1.111111"
    assert literal(coordinates["A6"]) == carbon
    assert notifications.snapshot_path().read_bytes() == data


def test_multipolygon_holes_altitude_and_empty_ranges(configured):
    ref = capture()
    with sqlite3.connect(configured) as db:
        db.row_factory = sqlite3.Row
        row = dict(db.execute("SELECT * FROM intake_submissions WHERE reference=?", (ref,)).fetchone())
    row["geometry_geojson"] = json.dumps({"type":"MultiPolygon", "coordinates":[[[[1,2,3],[2,2,4],[1,2,3]],[[1.1,2.1],[1.2,2.1],[1.1,2.1]]], [[[3,4],[4,4],[3,4]]]]})
    tables = register_tables([row])
    assert len(tables[1]) == 9
    assert tables[1][0][-1] == 3
    assert tables[1][3][4] == 2 and tables[1][6][3] == 2
    row["result_json"] = json.dumps({"verdict":"inconclusive"})
    assert register_tables([row])[0][0][5:10] == [None]*5
    with zipfile.ZipFile(io.BytesIO(build_register([]))) as z:
        assert z.testzip() is None


def test_one_notification_per_saved_reference_and_persistent_acceptance(configured, monkeypatch):
    first, second = capture(), capture("eudr")
    sent = []
    def fake_post(url, **kwargs):
        sent.append(kwargs["json"])
        return httpx.Response(201, json={"messageId":"synthetic-message"})
    monkeypatch.setattr(notifications.httpx, "post", fake_post)
    assert notifications.process_one_job() and notifications.process_one_job()
    assert notifications.process_one_job() is False
    assert len(sent) == 2
    for payload in sent:
        assert payload["to"] == [{"email":"operator@example.invalid"}]
        assert payload["attachment"][0]["name"].endswith(".xlsx")
        _, cells = workbook_cells(base64.b64decode(payload["attachment"][0]["content"]), 1)
        assert literal(cells["A2"]) == second
    assert sent[0]["headers"]["idempotencyKey"] != sent[1]["headers"]["idempotencyKey"]
    assert notifications.notification_status()["counts"] == {"accepted":2}


def test_failed_email_preserves_submission_and_retries_same_job(configured, monkeypatch):
    ref = capture()
    sent = []
    responses = iter([httpx.Response(429), httpx.Response(201,json={"messageId":"retry-accepted"})])
    def fake_post(url, **kwargs):
        sent.append(kwargs["json"])
        return next(responses)
    monkeypatch.setattr(notifications.httpx,"post",fake_post)
    assert notifications.process_one_job()
    assert notifications.notification_status()["counts"] == {"pending":1}
    with sqlite3.connect(configured) as db:
        assert db.execute("SELECT count(*) FROM intake_submissions").fetchone()[0] == 1
        db.execute("UPDATE intake_register_jobs SET next_attempt_at='2000-01-01' WHERE reference=?", (ref,))
    assert notifications.process_one_job()
    assert sent[0]["headers"] == sent[1]["headers"]
    assert notifications.notification_status()["counts"] == {"accepted":1}


def test_expired_records_excluded_and_job_cancelled(configured, monkeypatch):
    ref = capture()
    with sqlite3.connect(configured) as db:
        db.execute("UPDATE intake_submissions SET retention_due_at='2000-01-01' WHERE reference=?", (ref,))
    monkeypatch.setattr(notifications.httpx,"post",lambda *a,**k: pytest.fail("Expired submission must not email"))
    assert notifications.process_one_job()
    assert notifications.notification_status()["counts"] == {"cancelled":1}
    assert notifications.refresh_snapshot()[1] == []


def test_restart_beyond_idempotency_window_needs_review(configured, monkeypatch):
    ref = capture()
    old = (datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
    with sqlite3.connect(configured) as db:
        db.execute("UPDATE intake_register_jobs SET state='sending',attempts=1,claimed_at=?,first_attempt_at=? WHERE reference=?", (old,old,ref))
    monkeypatch.setattr(notifications.httpx,"post",lambda *a,**k: pytest.fail("Do not resend an ambiguous old attempt"))
    assert notifications.process_one_job()
    assert notifications.notification_status()["recent"][0]["last_error"] == "retry_window_expired_check_delivery"


def test_private_download_status_and_missing_key_no_false_success(configured, monkeypatch):
    capture()
    client = TestClient(app)
    for route in ("/api/intake/register.xlsx", "/api/intake/register/status"):
        assert client.get(route).status_code == 401
    headers = {"Authorization":"Bearer synthetic-operator-token"}
    response = client.get("/api/intake/register.xlsx",headers=headers)
    assert response.status_code == 200 and response.content.startswith(b"PK")
    assert response.headers["cache-control"] == "no-store"
    monkeypatch.delenv("BREVO_API_KEY")
    assert notifications.process_one_job() is False
    response = client.get("/api/intake/register/status",headers=headers)
    assert response.json()["configuration_gaps"] == ["brevo_key_missing"]
    assert response.json()["counts"] == {"pending":1}
