from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from api.intake import IntakeStorageError, capture_submission, public_storage_status
from api.main import app
from scripts.fieldwork_db import backup


client = TestClient(app)


def _configure(monkeypatch: pytest.MonkeyPatch, tmp_path, *, geometry: str = "true"):
    path = tmp_path / "private" / "180climate-intake.sqlite3"
    monkeypatch.setenv("INTAKE_RECORDING_MODE", "required")
    monkeypatch.setenv("INTAKE_DB_PATH", str(path))
    monkeypatch.setenv("INTAKE_RETENTION_DAYS", "90")
    monkeypatch.setenv("INTAKE_STORE_GEOMETRY", geometry)
    monkeypatch.setenv("INTAKE_OPERATOR_TOKEN", "synthetic-operator-token")
    for name in (
        "INTAKE_CONTROLLER_NAME",
        "INTAKE_PRIVACY_CONTACT",
        "INTAKE_HOSTING_REGION",
        "INTAKE_RETENTION_VERSION",
        "INTAKE_PROCESSOR_LIST_VERSION",
        "INTAKE_OPERATOR_OWNER",
        "INTAKE_AUTHORISED_DEPLOYER",
        "INTAKE_BAHASA_PACK_VERSION",
        "INTAKE_COUNSEL_APPROVAL_ID",
        "INTAKE_COMPANY_APPROVAL_ID",
    ):
        monkeypatch.setenv(name, "synthetic-test-approval")
    monkeypatch.delenv("FIELDWORK_DB_PATH", raising=False)
    return path


def _capture() -> str | None:
    return capture_submission(
        application="carbon",
        source_route="/api/carbon",
        contact={
            "name": "Synthetic User",
            "email": "synthetic@example.invalid",
            "mobile": "+6500000000",
            "company": "Synthetic Co",
        },
        form={"project_type": "REDD", "iup_name": "Synthetic IUP"},
        geometry_geojson={"type": "Point", "coordinates": [103.8, 1.3]},
        result={"verdict": "synthetic_only"},
    )


def test_recording_off_creates_no_database(monkeypatch, tmp_path):
    path = tmp_path / "off.sqlite3"
    monkeypatch.setenv("INTAKE_RECORDING_MODE", "off")
    monkeypatch.setenv("INTAKE_DB_PATH", str(path))
    assert _capture() is None
    assert not path.exists()


def test_required_storage_fails_closed_when_controls_missing(monkeypatch):
    monkeypatch.setenv("INTAKE_RECORDING_MODE", "required")
    for name in (
        "INTAKE_DB_PATH",
        "FIELDWORK_DB_PATH",
        "INTAKE_RETENTION_DAYS",
        "INTAKE_STORE_GEOMETRY",
        "INTAKE_OPERATOR_TOKEN",
        "INTAKE_CONTROLLER_NAME",
        "INTAKE_PRIVACY_CONTACT",
        "INTAKE_HOSTING_REGION",
        "INTAKE_RETENTION_VERSION",
        "INTAKE_PROCESSOR_LIST_VERSION",
        "INTAKE_OPERATOR_OWNER",
        "INTAKE_AUTHORISED_DEPLOYER",
        "INTAKE_BAHASA_PACK_VERSION",
        "INTAKE_COUNSEL_APPROVAL_ID",
        "INTAKE_COMPANY_APPROVAL_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(IntakeStorageError, match="not ready"):
        _capture()


def test_capture_writes_contact_form_geometry_result_and_retention(monkeypatch, tmp_path):
    path = _configure(monkeypatch, tmp_path)
    reference = _capture()
    assert reference and reference.startswith("CAR-")

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM intake_submissions").fetchone()
    assert row is not None
    assert row["reference"] == reference
    assert row["contact_email"] == "synthetic@example.invalid"
    assert json.loads(row["form_json"])["iup_name"] == "Synthetic IUP"
    assert json.loads(row["geometry_geojson"])["coordinates"] == [103.8, 1.3]
    assert len(row["geometry_sha256"]) == 64
    assert json.loads(row["result_json"])["verdict"] == "synthetic_only"
    assert row["retention_due_at"] > row["created_at"]


def test_geometry_can_be_explicitly_excluded_but_digest_is_kept(monkeypatch, tmp_path):
    path = _configure(monkeypatch, tmp_path, geometry="false")
    _capture()
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT geometry_geojson, geometry_sha256 FROM intake_submissions"
        ).fetchone()
    assert row[0] is None
    assert len(row[1]) == 64


def test_operator_list_and_csv_export_require_bearer_token(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    reference = _capture()
    assert client.get("/api/intake/submissions").status_code == 401

    headers = {"Authorization": "Bearer synthetic-operator-token"}
    response = client.get("/api/intake/submissions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["submissions"][0]["reference"] == reference
    assert "geometry_geojson" not in body["submissions"][0]

    export = client.get("/api/intake/export.csv", headers=headers)
    assert export.status_code == 200
    assert reference in export.text
    assert "geometry_geojson" not in export.text.splitlines()[0]


def test_public_status_never_exposes_database_path_or_token(monkeypatch, tmp_path):
    path = _configure(monkeypatch, tmp_path)
    status = public_storage_status()
    encoded = json.dumps(status)
    assert status["ready"] is True
    assert str(path) not in encoded
    assert "synthetic-operator-token" not in encoded


def test_controller_deferral_is_recorded_without_claiming_counsel_approval(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.delenv("INTAKE_COUNSEL_APPROVAL_ID", raising=False)
    monkeypatch.setenv("INTAKE_LEGAL_REVIEW_STATUS", "deferred_by_controller")
    status = public_storage_status()
    assert status["ready"] is False
    assert status["legal_review_status"] == "not_recorded"

    monkeypatch.setenv("INTAKE_LEGAL_REVIEW_RECORD", "synthetic-owner-decision-2026-09-24")
    status = public_storage_status()
    assert status["ready"] is True
    assert status["legal_review_status"] == "deferred_by_controller"


def test_eudr_route_records_normalised_geometry_without_json_duplication(monkeypatch, tmp_path):
    path = _configure(monkeypatch, tmp_path)
    monkeypatch.setattr("api.main.send_lead_email", lambda **kwargs: True)
    geometry = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"id": "synthetic-plot"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [113.989999, -2.009999],
                    [114.010001, -2.009999],
                    [114.010001, -1.990001],
                    [113.989999, -1.990001],
                    [113.989999, -2.009999],
                ]],
            },
        }],
    }
    response = client.post(
        "/api/eudr",
        data={
            "geojson_text": json.dumps(geometry),
            "commodity": "palm",
            "role": "non_eu_supplier",
            "name": "Synthetic User",
            "email": "synthetic@example.invalid",
        },
    )
    assert response.status_code == 200
    assert response.json()["submission_reference"].startswith("EUD-")

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM intake_submissions").fetchone()
    assert row is not None
    assert row["application"] == "eudr"
    assert row["geometry_geojson"]
    assert '"coordinates":' not in row["form_json"]
    assert '"coordinates":' not in row["result_json"]
    assert "geolocation_pack_geojson" not in row["result_json"]


def test_unified_backup_accepts_an_intake_only_database(monkeypatch, tmp_path):
    path = _configure(monkeypatch, tmp_path)
    reference = _capture()
    output = tmp_path / "backup" / "intake-backup.sqlite3"
    backup(path, output)
    with sqlite3.connect(output) as conn:
        row = conn.execute("SELECT reference FROM intake_submissions").fetchone()
    assert row and row[0] == reference


def test_carbon_lead_form_is_recorded_before_delivery(monkeypatch, tmp_path):
    path = _configure(monkeypatch, tmp_path, geometry="false")
    monkeypatch.setattr("api.main._deliver", lambda *args, **kwargs: None)
    response = client.post(
        "/api/lead",
        json={
            "name": "Synthetic Lead",
            "email": "lead@example.invalid",
            "company": "Synthetic Co",
            "iup_name": "Synthetic IUP",
            "iup_address": "Indonesia",
            "permit_type": "HTI",
            "permit_years_remaining": 10,
            "project_type": "REDD",
            "payload_summary": "Synthetic test only",
        },
    )
    assert response.status_code == 200
    assert response.json()["submission_reference"].startswith("CAR-")
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT source_route, contact_email FROM intake_submissions"
        ).fetchone()
    assert row == ("/api/lead", "lead@example.invalid")
