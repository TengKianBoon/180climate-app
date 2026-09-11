"""Invitation-only Fieldwork Phase 1A service layer.

The module deliberately has no outbound messaging or deployment side effects.
Real-user intake is fail-closed until the launch configuration is complete.
Status and operator keys are compared in constant time and only hashes are stored.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator


router = APIRouter(prefix="/api/fieldwork", tags=["fieldwork"])

SERVICE_ID = "fieldwork.match_intro.v1"
TERMS_DRAFT_VERSION = "fieldwork-pilot-terms-draft-2026-09-11"
PRIVACY_DRAFT_VERSION = "fieldwork-privacy-draft-2026-09-11"
PROHIBITED_USE_DRAFT_VERSION = "fieldwork-prohibited-use-draft-2026-09-11"
SCHEMA_VERSION = "1"

_DEFAULT_DB = Path(__file__).parent.parent / ".runtime" / "fieldwork.sqlite3"
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s().-]{6,30}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_id() -> str:
    return secrets.token_hex(16)


def _new_reference(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(5).upper()}"


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() == "true"


def _db_path() -> Path:
    raw = os.environ.get("FIELDWORK_DB_PATH", "").strip()
    return Path(raw) if raw else _DEFAULT_DB


def _notice_version(env_name: str, draft: str) -> str:
    return os.environ.get(env_name, "").strip() or draft


def _pilot_cap() -> int | None:
    raw = os.environ.get("FIELDWORK_PILOT_CAP", "").strip()
    if not raw.isdigit():
        return None
    value = int(raw)
    return value if 1 <= value <= 1000 else None


def _launch_gaps() -> list[str]:
    required = {
        "private persistent datastore": "FIELDWORK_DB_PATH",
        "pilot invitation control": "FIELDWORK_INVITE_CODE",
        "operator access control": "FIELDWORK_OPERATOR_TOKEN",
        "public origin": "FIELDWORK_PUBLIC_ORIGIN",
        "personal-data controller": "FIELDWORK_CONTROLLER_NAME",
        "privacy contact": "FIELDWORK_PRIVACY_CONTACT",
        "privacy contact link": "FIELDWORK_PRIVACY_CONTACT_URL",
        "hosting region": "FIELDWORK_HOSTING_REGION",
        "retention decision": "FIELDWORK_RETENTION_VERSION",
        "published retention summary": "FIELDWORK_RETENTION_SUMMARY",
        "processor disclosure": "FIELDWORK_PROCESSOR_LIST_VERSION",
        "published processor summary": "FIELDWORK_PROCESSOR_SUMMARY",
        "approved pilot terms version": "FIELDWORK_TERMS_VERSION",
        "approved privacy notice version": "FIELDWORK_PRIVACY_VERSION",
        "approved prohibited-use version": "FIELDWORK_PROHIBITED_USE_VERSION",
        "Bahasa publication pack": "FIELDWORK_BAHASA_PACK_VERSION",
        "Indonesian counsel approval": "FIELDWORK_COUNSEL_APPROVAL_ID",
        "company launch approval": "FIELDWORK_COMPANY_APPROVAL_ID",
    }
    gaps = [label for label, env_name in required.items() if not os.environ.get(env_name, "").strip()]
    origin = os.environ.get("FIELDWORK_PUBLIC_ORIGIN", "").strip()
    if origin and not origin.startswith("https://"):
        gaps.append("HTTPS public origin")
    contact_url = os.environ.get("FIELDWORK_PRIVACY_CONTACT_URL", "").strip()
    if contact_url and not (contact_url.startswith("mailto:") or contact_url.startswith("https://wa.me/")):
        gaps.append("approved privacy contact link")
    if _pilot_cap() is None:
        gaps.append("valid pilot participant cap")
    return gaps


def public_config() -> dict[str, Any]:
    accepting_requested = _truthy("FIELDWORK_ACCEPTING_SUBMISSIONS")
    gaps = _launch_gaps()
    return {
        "service_id": SERVICE_ID,
        "pilot_status": "limited_private_pilot",
        "accepting_submissions": accepting_requested and not gaps,
        "launch_gaps": gaps,
        "terms_version": _notice_version("FIELDWORK_TERMS_VERSION", TERMS_DRAFT_VERSION),
        "privacy_version": _notice_version("FIELDWORK_PRIVACY_VERSION", PRIVACY_DRAFT_VERSION),
        "prohibited_use_version": _notice_version(
            "FIELDWORK_PROHIBITED_USE_VERSION", PROHIBITED_USE_DRAFT_VERSION
        ),
        "controller_name": os.environ.get("FIELDWORK_CONTROLLER_NAME", "").strip() or "not_confirmed",
        "privacy_contact": os.environ.get("FIELDWORK_PRIVACY_CONTACT", "").strip() or "not_confirmed",
        "privacy_contact_url": os.environ.get("FIELDWORK_PRIVACY_CONTACT_URL", "").strip() or "not_confirmed",
        "hosting_region": os.environ.get("FIELDWORK_HOSTING_REGION", "").strip() or "not_confirmed",
        "retention_version": os.environ.get("FIELDWORK_RETENTION_VERSION", "").strip() or "not_confirmed",
        "retention_summary": os.environ.get("FIELDWORK_RETENTION_SUMMARY", "").strip() or "not_confirmed",
        "processor_list_version": os.environ.get("FIELDWORK_PROCESSOR_LIST_VERSION", "").strip() or "not_confirmed",
        "processor_summary": os.environ.get("FIELDWORK_PROCESSOR_SUMMARY", "").strip() or "not_confirmed",
        "pilot_cap": _pilot_cap(),
        "status_route": "/fieldwork/status",
        "price_status": "free_private_pilot",
    }


def _require_open_pilot() -> None:
    cfg = public_config()
    if not cfg["accepting_submissions"]:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "pilot_closed",
                "message": "Invited-pilot intake is not open yet. No information was saved.",
            },
        )


def _require_invite(code: str) -> None:
    expected = os.environ.get("FIELDWORK_INVITE_CODE", "")
    if not expected or not hmac.compare_digest(code, expected):
        raise HTTPException(
            status_code=403,
            detail={"code": "invalid_invitation", "message": "This invitation code is not valid."},
        )


def _require_operator(authorization: str | None) -> None:
    expected = os.environ.get("FIELDWORK_OPERATOR_TOKEN", "")
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail={"code": "operator_unauthorised"})


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    _init_schema(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS principals (
            id TEXT PRIMARY KEY,
            contact_kind TEXT NOT NULL,
            contact_value TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            locale TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requester_profiles (
            id TEXT PRIMARY KEY,
            principal_id TEXT NOT NULL UNIQUE REFERENCES principals(id),
            organisation TEXT,
            preferred_contact TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS provider_profiles (
            id TEXT PRIMARY KEY,
            reference TEXT NOT NULL UNIQUE,
            principal_id TEXT NOT NULL UNIQUE REFERENCES principals(id),
            invitation_source TEXT NOT NULL,
            original_text TEXT NOT NULL,
            role_title TEXT NOT NULL,
            services TEXT NOT NULL,
            service_area TEXT NOT NULL,
            travel TEXT NOT NULL,
            availability TEXT NOT NULL,
            experience TEXT NOT NULL,
            credentials TEXT NOT NULL,
            languages TEXT NOT NULL,
            equipment TEXT NOT NULL,
            exclusions TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS work_requests (
            id TEXT PRIMARY KEY,
            reference TEXT NOT NULL UNIQUE,
            principal_id TEXT NOT NULL REFERENCES principals(id),
            original_text TEXT NOT NULL,
            desired_result TEXT NOT NULL,
            category TEXT NOT NULL,
            broad_location TEXT NOT NULL,
            timing TEXT NOT NULL,
            authority_status TEXT NOT NULL,
            expected_evidence TEXT NOT NULL,
            hazard_status TEXT NOT NULL,
            permit_status TEXT NOT NULL,
            restricted_status TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            status TEXT NOT NULL,
            block_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS consents (
            id TEXT PRIMARY KEY,
            principal_id TEXT NOT NULL REFERENCES principals(id),
            purpose TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            notice_version TEXT NOT NULL,
            language TEXT NOT NULL,
            choice INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS terms_acceptances (
            id TEXT PRIMARY KEY,
            principal_id TEXT NOT NULL REFERENCES principals(id),
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            document_name TEXT NOT NULL,
            document_version TEXT NOT NULL,
            language TEXT NOT NULL,
            method TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS status_keys (
            reference TEXT PRIMARY KEY,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS status_history (
            id TEXT PRIMARY KEY,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            actor TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS introductions (
            id TEXT PRIMARY KEY,
            reference TEXT NOT NULL UNIQUE,
            work_request_id TEXT NOT NULL REFERENCES work_requests(id),
            provider_profile_id TEXT NOT NULL REFERENCES provider_profiles(id),
            proposed_shared_fields TEXT NOT NULL,
            requester_consent INTEGER NOT NULL DEFAULT 0,
            provider_consent INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            introduced_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            idempotency_key TEXT PRIMARY KEY,
            object_type TEXT NOT NULL,
            object_reference TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS analytics_daily (
            day TEXT NOT NULL,
            event TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (day, event)
        );
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
        (SCHEMA_VERSION,),
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContactMixin(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    contact_kind: Literal["email", "whatsapp"]
    contact: str = Field(min_length=7, max_length=254)
    locale: Literal["en", "id"] = "en"

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, value: str, info: Any) -> str:
        clean = value.strip()
        kind = info.data.get("contact_kind")
        if kind == "email" and not _EMAIL_RE.match(clean):
            raise ValueError("Enter a valid email address")
        if kind == "whatsapp" and not _PHONE_RE.match(clean):
            raise ValueError("Enter a valid WhatsApp number with country code")
        return clean


class ConsentMixin(StrictModel):
    matching_consent: bool
    contact_process_consent: bool
    terms_accepted: bool
    privacy_acknowledged: bool
    lawful_use_attested: bool

    def require_acceptances(self) -> None:
        if not all(
            [
                self.matching_consent,
                self.contact_process_consent,
                self.terms_accepted,
                self.privacy_acknowledged,
                self.lawful_use_attested,
            ]
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "acceptance_required",
                    "message": "Required matching, contact-process, legal, privacy and lawful-use choices must be confirmed separately.",
                },
            )


class RequestSubmission(ContactMixin, ConsentMixin):
    website: str = Field(default="", max_length=0, exclude=True)
    invitation_code: str = Field(min_length=4, max_length=160)
    idempotency_key: str = Field(min_length=12, max_length=100)
    organisation: str = Field(default="", max_length=160)
    preferred_contact: Literal["email", "whatsapp"]
    original_text: str = Field(min_length=20, max_length=4000)
    desired_result: str = Field(min_length=10, max_length=1000)
    category: Literal[
        "property_condition_photos",
        "non_invasive_land_observation",
        "qualified_desktop_review",
        "mine_authorised_admin_support",
    ]
    broad_location: str = Field(min_length=2, max_length=160)
    timing: str = Field(min_length=2, max_length=160)
    authority_status: Literal["confirmed", "pending", "not_authorised"]
    expected_evidence: str = Field(min_length=2, max_length=1000)
    hazard_status: Literal["none_known", "yes", "unsure"]
    permit_status: Literal["not_required", "required", "unsure"]
    restricted_status: Literal["no", "yes", "unsure"]
    relationship_type: Literal["direct_independent_service", "to_be_confirmed"]
    no_payment_details: bool


class ProviderSubmission(ContactMixin, ConsentMixin):
    website: str = Field(default="", max_length=0, exclude=True)
    invitation_code: str = Field(min_length=4, max_length=160)
    idempotency_key: str = Field(min_length=12, max_length=100)
    invitation_source: str = Field(min_length=2, max_length=200)
    original_text: str = Field(min_length=20, max_length=4000)
    role_title: str = Field(min_length=2, max_length=160)
    services: str = Field(min_length=5, max_length=1200)
    service_area: str = Field(min_length=2, max_length=300)
    travel: str = Field(min_length=2, max_length=300)
    availability: str = Field(min_length=2, max_length=300)
    experience: str = Field(min_length=10, max_length=1600)
    credentials: str = Field(default="None declared", max_length=1200)
    languages: str = Field(min_length=2, max_length=300)
    equipment: str = Field(default="None declared", max_length=800)
    exclusions: str = Field(min_length=2, max_length=1000)
    adult_attested: bool
    competent_scope_attested: bool
    no_payment_details: bool


class StatusAccess(StrictModel):
    reference: str = Field(min_length=8, max_length=40)
    status_key: str = Field(min_length=20, max_length=160)


class AnalyticsEvent(StrictModel):
    event: Literal["visit", "request_form_start", "provider_form_start"]


class OperatorStatusUpdate(StrictModel):
    status: Literal[
        "needs_information",
        "qualified",
        "blocked",
        "matching",
        "no_match",
        "profile_incomplete",
        "match_ready",
        "temporarily_unavailable",
        "restricted",
        "archived",
    ]
    reason: str = Field(default="", max_length=500)


class IntroductionProposal(StrictModel):
    request_reference: str
    provider_reference: str
    shared_fields: list[Literal["name", "contact", "role_title", "broad_location"]]


class IntroductionConsent(StatusAccess):
    introduction_reference: str
    confirm: bool


class IntroductionFinalize(StrictModel):
    confirm: bool


def _normalise_contact(kind: str, value: str) -> str:
    return value.strip().lower() if kind == "email" else re.sub(r"[^0-9+]", "", value)


def _upsert_principal(conn: sqlite3.Connection, data: ContactMixin) -> str:
    now = _utc_now()
    contact = _normalise_contact(data.contact_kind, data.contact)
    row = conn.execute("SELECT id FROM principals WHERE contact_value = ?", (contact,)).fetchone()
    if row:
        conn.execute(
            "UPDATE principals SET display_name=?, locale=?, updated_at=? WHERE id=?",
            (data.name.strip(), data.locale, now, row["id"]),
        )
        return str(row["id"])
    principal_id = _new_id()
    conn.execute(
        "INSERT INTO principals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (principal_id, data.contact_kind, contact, data.name.strip(), data.locale, "invited", now, now),
    )
    return principal_id


def _enforce_pilot_cap(conn: sqlite3.Connection, data: ContactMixin) -> None:
    cap = _pilot_cap()
    if cap is None:
        raise HTTPException(status_code=503, detail={"code": "pilot_closed"})
    contact = _normalise_contact(data.contact_kind, data.contact)
    existing = conn.execute("SELECT 1 FROM principals WHERE contact_value=?", (contact,)).fetchone()
    if existing:
        return
    count = conn.execute("SELECT COUNT(*) AS count FROM principals").fetchone()["count"]
    if count >= cap:
        raise HTTPException(
            status_code=409,
            detail={"code": "pilot_full", "message": "The initial invited-pilot capacity has been reached."},
        )


def _record_consent_bundle(
    conn: sqlite3.Connection,
    principal_id: str,
    object_type: str,
    object_id: str,
    language: str,
) -> None:
    now = _utc_now()
    for purpose, version in [
        ("private_matching", _notice_version("FIELDWORK_PRIVACY_VERSION", PRIVACY_DRAFT_VERSION)),
        ("contact_sharing_process", _notice_version("FIELDWORK_PRIVACY_VERSION", PRIVACY_DRAFT_VERSION)),
        ("lawful_use_attestation", _notice_version("FIELDWORK_PROHIBITED_USE_VERSION", PROHIBITED_USE_DRAFT_VERSION)),
    ]:
        conn.execute(
            "INSERT INTO consents VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (_new_id(), principal_id, purpose, object_type, object_id, version, language, now),
        )
    for name, version in [
        ("pilot_terms", _notice_version("FIELDWORK_TERMS_VERSION", TERMS_DRAFT_VERSION)),
        ("privacy_notice", _notice_version("FIELDWORK_PRIVACY_VERSION", PRIVACY_DRAFT_VERSION)),
        ("prohibited_use", _notice_version("FIELDWORK_PROHIBITED_USE_VERSION", PROHIBITED_USE_DRAFT_VERSION)),
    ]:
        conn.execute(
            "INSERT INTO terms_acceptances VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_new_id(), principal_id, object_type, object_id, name, version, language, "affirmative_checkbox", now),
        )


def _record_status(
    conn: sqlite3.Connection,
    object_type: str,
    object_id: str,
    to_status: str,
    actor: str,
    from_status: str | None = None,
    reason: str = "",
) -> None:
    conn.execute(
        "INSERT INTO status_history VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (_new_id(), object_type, object_id, from_status, to_status, actor, reason or None, _utc_now()),
    )


def _issue_status_key(conn: sqlite3.Connection, reference: str, object_type: str, object_id: str) -> str:
    raw = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).replace(microsecond=0).isoformat()
    conn.execute(
        "INSERT INTO status_keys VALUES (?, ?, ?, ?, ?, NULL)",
        (reference, object_type, object_id, _hash_secret(raw), expires),
    )
    return raw


def _existing_idempotent(conn: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT object_type, object_reference FROM idempotency_keys WHERE idempotency_key=?",
        (key,),
    ).fetchone()
    if not row:
        return None
    return {
        "service_id": SERVICE_ID,
        "reference": row["object_reference"],
        "status": "already_received",
        "duplicate": True,
        "status_route": "/fieldwork/status",
        "status_key": None,
        "message": "This submission was already received. Use the status key shown after the original submission.",
    }


def _submission_response(reference: str, status: str, status_key: str) -> dict[str, Any]:
    message = (
        "This request needs operator review before it can proceed."
        if status == "blocked"
        else "Received for private operator review. This is not a booking, dispatch, endorsement or contract."
    )
    return {
        "service_id": SERVICE_ID,
        "reference": reference,
        "status": status,
        "duplicate": False,
        "status_route": "/fieldwork/status",
        "status_key": status_key,
        "message": message,
    }


@router.get("/config")
def fieldwork_config() -> dict[str, Any]:
    return public_config()


@router.post("/events", status_code=204)
def fieldwork_event(event: AnalyticsEvent) -> None:
    day = datetime.now(timezone.utc).date().isoformat()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO analytics_daily(day, event, count) VALUES (?, ?, 1)
            ON CONFLICT(day, event) DO UPDATE SET count=count+1
            """,
            (day, event.event),
        )


@router.post("/requests")
def submit_request(data: RequestSubmission) -> dict[str, Any]:
    _require_open_pilot()
    _require_invite(data.invitation_code)
    data.require_acceptances()
    if not data.no_payment_details:
        raise HTTPException(status_code=422, detail={"code": "payment_details_prohibited"})

    block_reasons: list[str] = []
    if data.authority_status != "confirmed":
        block_reasons.append("Site or request authority is not confirmed")
    if data.hazard_status != "none_known":
        block_reasons.append("Known or uncertain hazards require separate review")
    if data.permit_status != "not_required":
        block_reasons.append("Permit-dependent activity is outside the initial pilot")
    if data.restricted_status != "no":
        block_reasons.append("Restricted activity requires separate review")
    status = "blocked" if block_reasons else "submitted"

    with connection() as conn:
        existing = _existing_idempotent(conn, data.idempotency_key)
        if existing:
            return existing
        _enforce_pilot_cap(conn, data)
        principal_id = _upsert_principal(conn, data)
        now = _utc_now()
        requester = conn.execute(
            "SELECT id FROM requester_profiles WHERE principal_id=?", (principal_id,)
        ).fetchone()
        if requester:
            conn.execute(
                "UPDATE requester_profiles SET organisation=?, preferred_contact=?, updated_at=? WHERE id=?",
                (data.organisation.strip() or None, data.preferred_contact, now, requester["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO requester_profiles VALUES (?, ?, ?, ?, ?, ?)",
                (_new_id(), principal_id, data.organisation.strip() or None, data.preferred_contact, now, now),
            )
        object_id = _new_id()
        reference = _new_reference("FR")
        conn.execute(
            "INSERT INTO work_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                object_id,
                reference,
                principal_id,
                data.original_text.strip(),
                data.desired_result.strip(),
                data.category,
                data.broad_location.strip(),
                data.timing.strip(),
                data.authority_status,
                data.expected_evidence.strip(),
                data.hazard_status,
                data.permit_status,
                data.restricted_status,
                data.relationship_type,
                status,
                "; ".join(block_reasons) or None,
                now,
                now,
            ),
        )
        _record_consent_bundle(conn, principal_id, "work_request", object_id, data.locale)
        _record_status(conn, "work_request", object_id, status, "requester", reason="; ".join(block_reasons))
        status_key = _issue_status_key(conn, reference, "work_request", object_id)
        conn.execute(
            "INSERT INTO idempotency_keys VALUES (?, 'work_request', ?, ?)",
            (data.idempotency_key, reference, now),
        )
        conn.execute(
            "INSERT INTO audit_events VALUES (?, 'requester', 'request_submitted', 'work_request', ?, ?, ?)",
            (_new_id(), object_id, status, now),
        )
        day = datetime.now(timezone.utc).date().isoformat()
        conn.execute(
            "INSERT INTO analytics_daily VALUES (?, 'valid_submission', 1) ON CONFLICT(day,event) DO UPDATE SET count=count+1",
            (day,),
        )
    return _submission_response(reference, status, status_key)


@router.post("/providers")
def submit_provider(data: ProviderSubmission) -> dict[str, Any]:
    _require_open_pilot()
    _require_invite(data.invitation_code)
    data.require_acceptances()
    if not data.no_payment_details:
        raise HTTPException(status_code=422, detail={"code": "payment_details_prohibited"})
    if not data.adult_attested or not data.competent_scope_attested:
        raise HTTPException(status_code=422, detail={"code": "provider_attestation_required"})

    with connection() as conn:
        existing = _existing_idempotent(conn, data.idempotency_key)
        if existing:
            return existing
        _enforce_pilot_cap(conn, data)
        principal_id = _upsert_principal(conn, data)
        if conn.execute("SELECT id FROM provider_profiles WHERE principal_id=?", (principal_id,)).fetchone():
            raise HTTPException(
                status_code=409,
                detail={"code": "provider_exists", "message": "A provider profile already exists for this contact."},
            )
        now = _utc_now()
        object_id = _new_id()
        reference = _new_reference("FP")
        status = "profile_incomplete"
        conn.execute(
            "INSERT INTO provider_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                object_id,
                reference,
                principal_id,
                data.invitation_source.strip(),
                data.original_text.strip(),
                data.role_title.strip(),
                data.services.strip(),
                data.service_area.strip(),
                data.travel.strip(),
                data.availability.strip(),
                data.experience.strip(),
                data.credentials.strip(),
                data.languages.strip(),
                data.equipment.strip(),
                data.exclusions.strip(),
                status,
                now,
                now,
            ),
        )
        _record_consent_bundle(conn, principal_id, "provider_profile", object_id, data.locale)
        _record_status(conn, "provider_profile", object_id, status, "provider")
        status_key = _issue_status_key(conn, reference, "provider_profile", object_id)
        conn.execute(
            "INSERT INTO idempotency_keys VALUES (?, 'provider_profile', ?, ?)",
            (data.idempotency_key, reference, now),
        )
        conn.execute(
            "INSERT INTO audit_events VALUES (?, 'provider', 'provider_enrolled', 'provider_profile', ?, ?, ?)",
            (_new_id(), object_id, status, now),
        )
        day = datetime.now(timezone.utc).date().isoformat()
        conn.execute(
            "INSERT INTO analytics_daily VALUES (?, 'valid_submission', 1) ON CONFLICT(day,event) DO UPDATE SET count=count+1",
            (day,),
        )
    return _submission_response(reference, status, status_key)


def _verify_status_access(conn: sqlite3.Connection, reference: str, supplied_key: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM status_keys WHERE reference=?", (reference.strip().upper(),)).fetchone()
    if not row or row["revoked_at"] or not hmac.compare_digest(row["key_hash"], _hash_secret(supplied_key)):
        raise HTTPException(status_code=404, detail={"code": "status_not_found"})
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail={"code": "status_key_expired"})
    return row


@router.post("/status")
def read_status(access: StatusAccess) -> dict[str, Any]:
    with connection() as conn:
        key_row = _verify_status_access(conn, access.reference, access.status_key)
        if key_row["object_type"] == "work_request":
            obj = conn.execute(
                "SELECT reference, desired_result AS summary, broad_location, status, block_reason, updated_at FROM work_requests WHERE id=?",
                (key_row["object_id"],),
            ).fetchone()
            principal_id = conn.execute(
                "SELECT principal_id FROM work_requests WHERE id=?", (key_row["object_id"],)
            ).fetchone()["principal_id"]
        else:
            obj = conn.execute(
                "SELECT reference, role_title AS summary, service_area AS broad_location, status, NULL AS block_reason, updated_at FROM provider_profiles WHERE id=?",
                (key_row["object_id"],),
            ).fetchone()
            principal_id = conn.execute(
                "SELECT principal_id FROM provider_profiles WHERE id=?", (key_row["object_id"],)
            ).fetchone()["principal_id"]
        intros = conn.execute(
            """
            SELECT i.reference, i.status, i.proposed_shared_fields,
                   CASE WHEN w.principal_id=? THEN i.requester_consent ELSE i.provider_consent END AS own_consent
            FROM introductions i
            JOIN work_requests w ON w.id=i.work_request_id
            JOIN provider_profiles p ON p.id=i.provider_profile_id
            WHERE w.principal_id=? OR p.principal_id=?
            ORDER BY i.created_at DESC
            """,
            (principal_id, principal_id, principal_id),
        ).fetchall()
        return {
            "service_id": SERVICE_ID,
            "reference": obj["reference"],
            "summary": obj["summary"],
            "broad_location": obj["broad_location"],
            "status": obj["status"],
            "block_reason": obj["block_reason"],
            "updated_at": obj["updated_at"],
            "introductions": [
                {
                    "reference": row["reference"],
                    "status": row["status"],
                    "shared_fields": json.loads(row["proposed_shared_fields"]),
                    "own_consent": bool(row["own_consent"]),
                }
                for row in intros
            ],
        }


@router.get("/operator/queue")
def operator_queue(
    include_contacts: bool = Query(default=False),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_operator(authorization)
    with connection() as conn:
        requests = conn.execute(
            """
            SELECT w.reference, w.desired_result, w.category, w.broad_location, w.timing,
                   w.authority_status, w.hazard_status, w.permit_status, w.restricted_status,
                   w.status, w.block_reason, w.created_at,
                   CASE WHEN ? THEN p.display_name ELSE NULL END AS name,
                   CASE WHEN ? THEN p.contact_value ELSE NULL END AS contact
            FROM work_requests w JOIN principals p ON p.id=w.principal_id
            ORDER BY w.created_at DESC
            """,
            (include_contacts, include_contacts),
        ).fetchall()
        providers = conn.execute(
            """
            SELECT f.reference, f.role_title, f.services, f.service_area, f.availability,
                   f.credentials, f.languages, f.exclusions, f.status, f.created_at,
                   CASE WHEN ? THEN p.display_name ELSE NULL END AS name,
                   CASE WHEN ? THEN p.contact_value ELSE NULL END AS contact
            FROM provider_profiles f JOIN principals p ON p.id=f.principal_id
            ORDER BY f.created_at DESC
            """,
            (include_contacts, include_contacts),
        ).fetchall()
        analytics = conn.execute(
            "SELECT day, event, count FROM analytics_daily ORDER BY day DESC, event"
        ).fetchall()
        action = "queue_contacts_viewed" if include_contacts else "queue_viewed"
        conn.execute(
            "INSERT INTO audit_events VALUES (?, 'operator', ?, 'operator_queue', NULL, 'success', ?)",
            (_new_id(), action, _utc_now()),
        )
        day = datetime.now(timezone.utc).date().isoformat()
        conn.execute(
            "INSERT INTO analytics_daily VALUES (?, 'operator_receipt', 1) ON CONFLICT(day,event) DO UPDATE SET count=count+1",
            (day,),
        )
        return {
            "requests": [dict(row) for row in requests],
            "providers": [dict(row) for row in providers],
            "analytics": [dict(row) for row in analytics],
            "contacts_included": include_contacts,
        }


_REQUEST_TRANSITIONS = {
    "submitted": {"needs_information", "qualified", "blocked"},
    "needs_information": {"qualified", "blocked", "archived"},
    "qualified": {"matching", "blocked", "archived"},
    "matching": {"no_match", "blocked"},
    "blocked": {"needs_information", "archived"},
    "no_match": {"matching", "archived"},
}
_PROVIDER_TRANSITIONS = {
    "profile_incomplete": {"match_ready", "restricted", "archived"},
    "match_ready": {"temporarily_unavailable", "restricted", "archived"},
    "temporarily_unavailable": {"match_ready", "archived"},
    "restricted": {"profile_incomplete", "archived"},
}


@router.post("/operator/records/{reference}/status")
def operator_set_status(
    reference: str,
    update: OperatorStatusUpdate,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    _require_operator(authorization)
    ref = reference.strip().upper()
    with connection() as conn:
        if ref.startswith("FR-"):
            table, object_type, transitions = "work_requests", "work_request", _REQUEST_TRANSITIONS
        elif ref.startswith("FP-"):
            table, object_type, transitions = "provider_profiles", "provider_profile", _PROVIDER_TRANSITIONS
        else:
            raise HTTPException(status_code=404, detail={"code": "record_not_found"})
        row = conn.execute(f"SELECT id, status FROM {table} WHERE reference=?", (ref,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={"code": "record_not_found"})
        if update.status not in transitions.get(row["status"], set()):
            raise HTTPException(
                status_code=409,
                detail={"code": "invalid_transition", "from": row["status"], "to": update.status},
            )
        conn.execute(
            f"UPDATE {table} SET status=?, updated_at=? WHERE id=?",
            (update.status, _utc_now(), row["id"]),
        )
        _record_status(conn, object_type, row["id"], update.status, "operator", row["status"], update.reason)
        return {"reference": ref, "status": update.status}


@router.post("/operator/introductions")
def propose_introduction(
    proposal: IntroductionProposal,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_operator(authorization)
    fields = list(dict.fromkeys(proposal.shared_fields))
    if "contact" not in fields or "name" not in fields:
        raise HTTPException(
            status_code=422,
            detail={"code": "disclosure_preview_incomplete", "message": "Name and contact must be previewed."},
        )
    with connection() as conn:
        request_row = conn.execute(
            "SELECT id, status FROM work_requests WHERE reference=?",
            (proposal.request_reference.strip().upper(),),
        ).fetchone()
        provider_row = conn.execute(
            "SELECT id, status FROM provider_profiles WHERE reference=?",
            (proposal.provider_reference.strip().upper(),),
        ).fetchone()
        if not request_row or not provider_row:
            raise HTTPException(status_code=404, detail={"code": "record_not_found"})
        if request_row["status"] not in {"qualified", "matching"} or provider_row["status"] != "match_ready":
            raise HTTPException(status_code=409, detail={"code": "records_not_match_ready"})
        intro_id = _new_id()
        intro_ref = _new_reference("FI")
        now = _utc_now()
        conn.execute(
            "INSERT INTO introductions VALUES (?, ?, ?, ?, ?, 0, 0, 'consent_required', ?, NULL)",
            (intro_id, intro_ref, request_row["id"], provider_row["id"], json.dumps(fields), now),
        )
        conn.execute(
            "UPDATE work_requests SET status='introduction_proposed', updated_at=? WHERE id=?",
            (now, request_row["id"]),
        )
        _record_status(
            conn,
            "work_request",
            request_row["id"],
            "introduction_proposed",
            "operator",
            request_row["status"],
        )
        return {"reference": intro_ref, "status": "consent_required", "shared_fields": fields}


@router.post("/introductions/consent")
def introduction_consent(data: IntroductionConsent) -> dict[str, Any]:
    with connection() as conn:
        key_row = _verify_status_access(conn, data.reference, data.status_key)
        intro = conn.execute(
            """
            SELECT i.*, w.id AS request_id, w.principal_id AS requester_id,
                   p.id AS provider_id, p.principal_id AS provider_principal_id
            FROM introductions i
            JOIN work_requests w ON w.id=i.work_request_id
            JOIN provider_profiles p ON p.id=i.provider_profile_id
            WHERE i.reference=?
            """,
            (data.introduction_reference.strip().upper(),),
        ).fetchone()
        if not intro:
            raise HTTPException(status_code=404, detail={"code": "introduction_not_found"})
        if key_row["object_id"] == intro["request_id"]:
            column, principal_id, actor = "requester_consent", intro["requester_id"], "requester"
        elif key_row["object_id"] == intro["provider_id"]:
            column, principal_id, actor = "provider_consent", intro["provider_principal_id"], "provider"
        else:
            raise HTTPException(status_code=403, detail={"code": "introduction_not_authorised"})
        if not data.confirm:
            conn.execute("UPDATE introductions SET status='declined' WHERE id=?", (intro["id"],))
            result = "declined"
        else:
            conn.execute(f"UPDATE introductions SET {column}=1 WHERE id=?", (intro["id"],))
            updated = conn.execute(
                "SELECT requester_consent, provider_consent FROM introductions WHERE id=?", (intro["id"],)
            ).fetchone()
            result = "ready_for_introduction" if updated["requester_consent"] and updated["provider_consent"] else "consent_required"
            conn.execute("UPDATE introductions SET status=? WHERE id=?", (result, intro["id"]))
            locale = conn.execute("SELECT locale FROM principals WHERE id=?", (principal_id,)).fetchone()["locale"]
            conn.execute(
                "INSERT INTO consents VALUES (?, ?, 'named_contact_disclosure', 'introduction', ?, ?, ?, 1, ?)",
                (
                    _new_id(),
                    principal_id,
                    intro["id"],
                    _notice_version("FIELDWORK_PRIVACY_VERSION", PRIVACY_DRAFT_VERSION),
                    locale,
                    _utc_now(),
                ),
            )
        conn.execute(
            "INSERT INTO audit_events VALUES (?, ?, 'introduction_consent', 'introduction', ?, ?, ?)",
            (_new_id(), actor, intro["id"], result, _utc_now()),
        )
        return {"reference": intro["reference"], "status": result}


@router.post("/operator/introductions/{reference}/finalize")
def finalize_introduction(
    reference: str,
    action: IntroductionFinalize,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_operator(authorization)
    if not action.confirm:
        raise HTTPException(status_code=422, detail={"code": "operator_confirmation_required"})
    with connection() as conn:
        intro = conn.execute(
            """
            SELECT i.*, w.principal_id AS requester_id, p.principal_id AS provider_id,
                   w.id AS request_id
            FROM introductions i
            JOIN work_requests w ON w.id=i.work_request_id
            JOIN provider_profiles p ON p.id=i.provider_profile_id
            WHERE i.reference=?
            """,
            (reference.strip().upper(),),
        ).fetchone()
        if not intro:
            raise HTTPException(status_code=404, detail={"code": "introduction_not_found"})
        if intro["status"] != "ready_for_introduction" or not intro["requester_consent"] or not intro["provider_consent"]:
            raise HTTPException(status_code=409, detail={"code": "contact_consent_incomplete"})
        requester = conn.execute(
            "SELECT display_name, contact_kind, contact_value FROM principals WHERE id=?", (intro["requester_id"],)
        ).fetchone()
        provider = conn.execute(
            "SELECT display_name, contact_kind, contact_value FROM principals WHERE id=?", (intro["provider_id"],)
        ).fetchone()
        now = _utc_now()
        conn.execute(
            "UPDATE introductions SET status='introduced', introduced_at=? WHERE id=?", (now, intro["id"])
        )
        conn.execute(
            "UPDATE work_requests SET status='introduced', updated_at=? WHERE id=?", (now, intro["request_id"])
        )
        _record_status(
            conn,
            "work_request",
            intro["request_id"],
            "introduced",
            "operator",
            "introduction_proposed",
        )
        conn.execute(
            "INSERT INTO audit_events VALUES (?, 'operator', 'contacts_revealed_for_introduction', 'introduction', ?, 'success', ?)",
            (_new_id(), intro["id"], now),
        )
        return {
            "reference": intro["reference"],
            "status": "introduced",
            "disclosure": {
                "requester": dict(requester),
                "provider": dict(provider),
                "shared_fields": json.loads(intro["proposed_shared_fields"]),
            },
            "message": "Both parties consented. The operator may now make the direct introduction outside the platform.",
        }
