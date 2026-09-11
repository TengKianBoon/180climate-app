"""Phase 1A Fieldwork critical-path and privacy-boundary tests."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from scripts.fieldwork_db import backup, restore


client = TestClient(app)


@pytest.fixture()
def pilot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "private" / "fieldwork.sqlite3"
    values = {
        "FIELDWORK_ACCEPTING_SUBMISSIONS": "true",
        "FIELDWORK_DB_PATH": str(db_path),
        "FIELDWORK_INVITE_CODE": "synthetic-invite-only",
        "FIELDWORK_OPERATOR_TOKEN": "synthetic-operator-only",
        "FIELDWORK_PUBLIC_ORIGIN": "https://fieldwork.example.invalid",
        "FIELDWORK_CONTROLLER_NAME": "Synthetic Controller Pte Ltd",
        "FIELDWORK_PRIVACY_CONTACT": "privacy@example.invalid",
        "FIELDWORK_PRIVACY_CONTACT_URL": "mailto:privacy@example.invalid",
        "FIELDWORK_HOSTING_REGION": "synthetic-region",
        "FIELDWORK_PILOT_CAP": "10",
        "FIELDWORK_RETENTION_VERSION": "synthetic-retention-v1",
        "FIELDWORK_RETENTION_SUMMARY": "Synthetic records: 30 days",
        "FIELDWORK_PROCESSOR_LIST_VERSION": "synthetic-processors-v1",
        "FIELDWORK_PROCESSOR_SUMMARY": "Synthetic hosting processor",
        "FIELDWORK_TERMS_VERSION": "synthetic-terms-v1",
        "FIELDWORK_PRIVACY_VERSION": "synthetic-privacy-v1",
        "FIELDWORK_PROHIBITED_USE_VERSION": "synthetic-prohibited-use-v1",
        "FIELDWORK_BAHASA_PACK_VERSION": "synthetic-bahasa-v1",
        "FIELDWORK_COUNSEL_APPROVAL_ID": "synthetic-counsel-approval",
        "FIELDWORK_COMPANY_APPROVAL_ID": "synthetic-company-approval",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return db_path


def request_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "invitation_code": "synthetic-invite-only",
        "idempotency_key": "request-idempotency-0001",
        "name": "Synthetic Requester",
        "contact_kind": "email",
        "contact": "requester@example.invalid",
        "locale": "en",
        "organisation": "Synthetic Organisation",
        "preferred_contact": "email",
        "original_text": "I need owner-authorised exterior condition photographs and a dated checklist.",
        "desired_result": "Dated exterior photographs and a completed condition checklist.",
        "category": "property_condition_photos",
        "broad_location": "Bandung, West Java",
        "timing": "Within two weeks",
        "authority_status": "confirmed",
        "expected_evidence": "Dated photographs and a completed checklist",
        "hazard_status": "none_known",
        "permit_status": "not_required",
        "restricted_status": "no",
        "relationship_type": "direct_independent_service",
        "matching_consent": True,
        "contact_process_consent": True,
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "lawful_use_attested": True,
        "no_payment_details": True,
    }
    payload.update(overrides)
    return payload


def provider_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "invitation_code": "synthetic-invite-only",
        "idempotency_key": "provider-idempotency-0001",
        "name": "Synthetic Provider",
        "contact_kind": "email",
        "contact": "provider@example.invalid",
        "locale": "en",
        "invitation_source": "Synthetic pilot invitation",
        "original_text": "I provide authorised property photography and structured condition checklists.",
        "role_title": "Field documentation specialist",
        "services": "Exterior property photographs and non-invasive condition checklists",
        "service_area": "West Java",
        "travel": "Bandung and nearby districts",
        "availability": "Weekdays with three days notice",
        "experience": "Five years documenting property condition for owners and managers.",
        "credentials": "Declared photography experience; no regulated credential claimed",
        "languages": "Bahasa Indonesia, English",
        "equipment": "Camera and timestamped checklist workflow",
        "exclusions": "No roofs, confined spaces, electrical work, drones or unauthorised entry",
        "matching_consent": True,
        "contact_process_consent": True,
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "lawful_use_attested": True,
        "adult_attested": True,
        "competent_scope_attested": True,
        "no_payment_details": True,
    }
    payload.update(overrides)
    return payload


def operator_headers() -> dict[str, str]:
    return {"Authorization": "Bearer synthetic-operator-only"}


def test_public_pages_catalogue_and_security_headers() -> None:
    page = client.get("/fieldwork")
    assert page.status_code == 200
    assert "Fieldwork support, matched privately" in page.text
    assert page.text.count('data-wix-intake href="https://www.180climate.net/fieldwork-pilot-draft"') == 3
    assert 'id="pilot-banner" data-state="loading" data-intake="wix"' in page.text
    assert 'id="request-form" aria-labelledby="request-title" hidden aria-hidden="true"' in page.text
    assert 'id="provider-form" aria-labelledby="provider-title" hidden aria-hidden="true"' in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"
    assert client.get("/fieldwork/status").headers["cache-control"] == "no-store"
    assert client.get("/fieldwork/operator").headers["cache-control"] == "no-store"

    catalogue = client.get("/services.json")
    assert catalogue.status_code == 200
    services = {item["service_id"]: item for item in catalogue.json()["services"]}
    assert set(services) == {"fieldwork.match_intro.v1", "eudr.plot_screen.v1", "carbon.pre_fs.v1"}
    assert services["fieldwork.match_intro.v1"]["status"] == "closed_pending_launch_gate"
    assert client.get("/schemas/fieldwork-request-v1.json").status_code == 200
    assert client.get("/schemas/not-allowed.json").status_code == 404


def test_intake_fails_closed_without_launch_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FIELDWORK_DB_PATH", str(tmp_path / "closed.sqlite3"))
    monkeypatch.setenv("FIELDWORK_ACCEPTING_SUBMISSIONS", "false")
    monkeypatch.delenv("FIELDWORK_INVITE_CODE", raising=False)
    response = client.post("/api/fieldwork/requests", json=request_payload())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "pilot_closed"
    assert not (tmp_path / "closed.sqlite3").exists()


def test_intake_stays_closed_when_an_approved_notice_version_is_missing(
    pilot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FIELDWORK_PRIVACY_VERSION")
    config = client.get("/api/fieldwork/config").json()
    assert config["accepting_submissions"] is False
    assert "approved privacy notice version" in config["launch_gaps"]
    response = client.post("/api/fieldwork/requests", json=request_payload())
    assert response.status_code == 503
    assert not pilot.exists()


def test_initial_pilot_cap_applies_to_distinct_contacts(
    pilot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIELDWORK_PILOT_CAP", "1")
    first = client.post("/api/fieldwork/requests", json=request_payload())
    assert first.status_code == 200
    second = client.post(
        "/api/fieldwork/providers",
        json=provider_payload(contact="second-provider@example.invalid", idempotency_key="provider-cap-test-0001"),
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "pilot_full"


def test_request_submission_is_auditable_and_status_key_is_not_stored(pilot: Path) -> None:
    response = client.post("/api/fieldwork/requests", json=request_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reference"].startswith("FR-")
    assert body["status"] == "submitted"
    assert body["status_key"]
    assert body["status_key"].encode() not in pilot.read_bytes()

    with sqlite3.connect(pilot) as conn:
        assert conn.execute("SELECT COUNT(*) FROM principals").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM work_requests").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM consents").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM terms_acceptances").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM status_history").fetchone()[0] == 1

    status = client.post(
        "/api/fieldwork/status",
        json={"reference": body["reference"], "status_key": body["status_key"]},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "submitted"
    assert "contact" not in json.dumps(status.json()).lower()


def test_duplicate_submission_does_not_create_second_record(pilot: Path) -> None:
    first = client.post("/api/fieldwork/requests", json=request_payload()).json()
    second = client.post("/api/fieldwork/requests", json=request_payload()).json()
    assert second["duplicate"] is True
    assert second["reference"] == first["reference"]
    assert second["status_key"] is None
    with sqlite3.connect(pilot) as conn:
        assert conn.execute("SELECT COUNT(*) FROM work_requests").fetchone()[0] == 1


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"authority_status": "pending"}, "authority"),
        ({"hazard_status": "unsure"}, "hazard"),
        ({"permit_status": "required"}, "permit"),
        ({"restricted_status": "yes"}, "restricted"),
    ],
)
def test_risky_or_unconfirmed_request_is_blocked(pilot: Path, overrides: dict[str, str], reason: str) -> None:
    payload = request_payload(**overrides, idempotency_key=f"blocked-{reason}-0001")
    body = client.post("/api/fieldwork/requests", json=payload).json()
    assert body["status"] == "blocked"
    status = client.post(
        "/api/fieldwork/status",
        json={"reference": body["reference"], "status_key": body["status_key"]},
    ).json()
    assert reason in status["block_reason"].lower()


def test_invitation_consent_spam_and_mass_assignment_are_enforced(pilot: Path) -> None:
    bad_invite = client.post(
        "/api/fieldwork/requests", json=request_payload(invitation_code="wrong-code")
    )
    assert bad_invite.status_code == 403
    missing_consent = client.post(
        "/api/fieldwork/requests",
        json=request_payload(matching_consent=False, idempotency_key="missing-consent-0001"),
    )
    assert missing_consent.status_code == 422
    honeypot = client.post(
        "/api/fieldwork/requests",
        json=request_payload(website="spam.example", idempotency_key="honeypot-test-0001"),
    )
    assert honeypot.status_code == 422
    extra = client.post(
        "/api/fieldwork/requests",
        json=request_payload(is_admin=True, idempotency_key="mass-assignment-0001"),
    )
    assert extra.status_code == 422


def test_operator_queue_hides_contacts_by_default(pilot: Path) -> None:
    client.post("/api/fieldwork/requests", json=request_payload())
    assert client.get("/api/fieldwork/operator/queue").status_code == 401
    queue = client.get("/api/fieldwork/operator/queue", headers=operator_headers())
    assert queue.status_code == 200
    assert queue.json()["requests"][0]["contact"] is None
    revealed = client.get(
        "/api/fieldwork/operator/queue?include_contacts=true", headers=operator_headers()
    ).json()
    assert revealed["requests"][0]["contact"] == "requester@example.invalid"


def test_two_party_consent_is_required_before_contact_disclosure(pilot: Path) -> None:
    request = client.post("/api/fieldwork/requests", json=request_payload()).json()
    provider = client.post("/api/fieldwork/providers", json=provider_payload()).json()

    assert client.post(
        f"/api/fieldwork/operator/records/{request['reference']}/status",
        headers=operator_headers(),
        json={"status": "qualified", "reason": "Synthetic eligible case"},
    ).status_code == 200
    assert client.post(
        f"/api/fieldwork/operator/records/{provider['reference']}/status",
        headers=operator_headers(),
        json={"status": "match_ready", "reason": "Synthetic profile reviewed"},
    ).status_code == 200

    proposal = client.post(
        "/api/fieldwork/operator/introductions",
        headers=operator_headers(),
        json={
            "request_reference": request["reference"],
            "provider_reference": provider["reference"],
            "shared_fields": ["name", "contact", "role_title", "broad_location"],
        },
    )
    assert proposal.status_code == 200, proposal.text
    intro_ref = proposal.json()["reference"]

    early = client.post(
        f"/api/fieldwork/operator/introductions/{intro_ref}/finalize",
        headers=operator_headers(),
        json={"confirm": True},
    )
    assert early.status_code == 409
    assert early.json()["detail"]["code"] == "contact_consent_incomplete"

    requester_consent = client.post(
        "/api/fieldwork/introductions/consent",
        json={
            "reference": request["reference"],
            "status_key": request["status_key"],
            "introduction_reference": intro_ref,
            "confirm": True,
        },
    )
    assert requester_consent.json()["status"] == "consent_required"
    provider_consent = client.post(
        "/api/fieldwork/introductions/consent",
        json={
            "reference": provider["reference"],
            "status_key": provider["status_key"],
            "introduction_reference": intro_ref,
            "confirm": True,
        },
    )
    assert provider_consent.json()["status"] == "ready_for_introduction"

    final = client.post(
        f"/api/fieldwork/operator/introductions/{intro_ref}/finalize",
        headers=operator_headers(),
        json={"confirm": True},
    )
    assert final.status_code == 200
    assert final.json()["status"] == "introduced"
    assert final.json()["disclosure"]["requester"]["contact_value"] == "requester@example.invalid"
    assert final.json()["disclosure"]["provider"]["contact_value"] == "provider@example.invalid"


def test_same_principal_can_hold_both_roles(pilot: Path) -> None:
    client.post("/api/fieldwork/requests", json=request_payload())
    response = client.post(
        "/api/fieldwork/providers",
        json=provider_payload(contact="requester@example.invalid"),
    )
    assert response.status_code == 200, response.text
    with sqlite3.connect(pilot) as conn:
        assert conn.execute("SELECT COUNT(*) FROM principals").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM requester_profiles").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM provider_profiles").fetchone()[0] == 1


def test_backup_restore_rehearsal_uses_synthetic_database(pilot: Path, tmp_path: Path) -> None:
    client.post("/api/fieldwork/requests", json=request_payload())
    copy = tmp_path / "backup" / "fieldwork-backup.sqlite3"
    restored = tmp_path / "restore" / "fieldwork-restored.sqlite3"
    backup(pilot, copy)
    restore(copy, restored, confirmed=True)
    with sqlite3.connect(restored) as conn:
        assert conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0] == "1"
        assert conn.execute("SELECT COUNT(*) FROM work_requests").fetchone()[0] == 1


def test_wrong_or_expired_style_status_access_does_not_enumerate(pilot: Path) -> None:
    body = client.post("/api/fieldwork/requests", json=request_payload()).json()
    wrong = client.post(
        "/api/fieldwork/status",
        json={"reference": body["reference"], "status_key": "x" * 24},
    )
    missing = client.post(
        "/api/fieldwork/status",
        json={"reference": "FR-0000000000", "status_key": "x" * 24},
    )
    assert wrong.status_code == missing.status_code == 404
    assert wrong.json()["detail"]["code"] == missing.json()["detail"]["code"] == "status_not_found"
