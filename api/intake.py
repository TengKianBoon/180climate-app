"""Private, fail-closed intake registry for Carbon and EUDR submissions.

The registry deliberately uses the same SQLite database path as Fieldwork so a
small pilot has one owned data file, one backup target and one retention owner.
Production recording remains disabled until an explicit path, retention period,
geometry-retention choice and operator token are configured.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response


router = APIRouter(prefix="/api/intake", tags=["intake"])

SCHEMA_VERSION = "1"
_DEFAULT_DB = Path(__file__).parent.parent / ".runtime" / "180climate-intake.sqlite3"
_APPLICATIONS = ("carbon", "eudr")


class IntakeStorageError(RuntimeError):
    """Raised when required intake storage is unavailable or incomplete."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def recording_mode() -> str:
    return os.environ.get("INTAKE_RECORDING_MODE", "off").strip().lower() or "off"


def database_path() -> Path:
    raw = (
        os.environ.get("INTAKE_DB_PATH", "").strip()
        or os.environ.get("FIELDWORK_DB_PATH", "").strip()
    )
    return Path(raw) if raw else _DEFAULT_DB


def _retention_days() -> int | None:
    raw = os.environ.get("INTAKE_RETENTION_DAYS", "").strip()
    if not raw.isdigit():
        return None
    value = int(raw)
    return value if 1 <= value <= 3650 else None


def _geometry_choice() -> bool | None:
    raw = os.environ.get("INTAKE_STORE_GEOMETRY", "").strip().lower()
    if raw == "true":
        return True
    if raw == "false":
        return False
    return None


def configuration_gaps() -> list[str]:
    mode = recording_mode()
    if mode == "off":
        return []

    gaps: list[str] = []
    if mode != "required":
        gaps.append("INTAKE_RECORDING_MODE must be off or required")
    configured_path = (
        os.environ.get("INTAKE_DB_PATH", "").strip()
        or os.environ.get("FIELDWORK_DB_PATH", "").strip()
    )
    if not configured_path:
        gaps.append("private persistent intake database path")
    elif not Path(configured_path).is_absolute():
        gaps.append("absolute private intake database path")
    if _retention_days() is None:
        gaps.append("valid intake retention period")
    if _geometry_choice() is None:
        gaps.append("explicit geometry-retention choice")
    if not os.environ.get("INTAKE_OPERATOR_TOKEN", "").strip():
        gaps.append("intake operator access control")
    required_governance = {
        "personal-data controller": "INTAKE_CONTROLLER_NAME",
        "public privacy contact": "INTAKE_PRIVACY_CONTACT",
        "hosting region": "INTAKE_HOSTING_REGION",
        "retention schedule version": "INTAKE_RETENTION_VERSION",
        "processor inventory version": "INTAKE_PROCESSOR_LIST_VERSION",
        "operator access owner": "INTAKE_OPERATOR_OWNER",
        "authorised deployer": "INTAKE_AUTHORISED_DEPLOYER",
        "Bahasa Indonesia publication pack": "INTAKE_BAHASA_PACK_VERSION",
        "Indonesian legal review": "INTAKE_COUNSEL_APPROVAL_ID",
        "company publication approval": "INTAKE_COMPANY_APPROVAL_ID",
    }
    gaps.extend(
        label
        for label, env_name in required_governance.items()
        if not os.environ.get(env_name, "").strip()
    )
    return gaps


def public_storage_status() -> dict[str, Any]:
    mode = recording_mode()
    gaps = configuration_gaps()
    return {
        "recording_mode": mode,
        "ready": mode == "required" and not gaps,
        "configuration_gaps": gaps,
        "geometry_retention": _geometry_choice(),
        "retention_days": _retention_days(),
        "database_location": "private_runtime_database" if not gaps and mode == "required" else "not_confirmed",
    }


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    path = database_path()
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
        CREATE TABLE IF NOT EXISTS intake_schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS intake_submissions (
            id TEXT PRIMARY KEY,
            reference TEXT NOT NULL UNIQUE,
            application TEXT NOT NULL CHECK (application IN ('carbon', 'eudr')),
            source_route TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            contact_mobile TEXT NOT NULL,
            company TEXT NOT NULL,
            form_json TEXT NOT NULL,
            geometry_geojson TEXT,
            geometry_sha256 TEXT,
            result_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            retention_due_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_intake_application_created
            ON intake_submissions(application, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_intake_contact_email
            ON intake_submissions(contact_email);
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO intake_schema_meta(key, value) VALUES ('schema_version', ?)",
        (SCHEMA_VERSION,),
    )


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def capture_submission(
    *,
    application: Literal["carbon", "eudr"],
    source_route: str,
    contact: dict[str, Any],
    form: dict[str, Any],
    geometry_geojson: dict[str, Any] | None,
    result: dict[str, Any],
) -> str | None:
    """Persist a submission and return its stable reference.

    ``off`` preserves the existing non-recording behaviour. ``required`` is
    intentionally fail-closed: a missing control or write failure aborts the
    request instead of claiming the submission was saved.
    """
    mode = recording_mode()
    if mode == "off":
        return None
    gaps = configuration_gaps()
    if gaps:
        raise IntakeStorageError("Intake storage is not ready: " + "; ".join(gaps))
    if application not in _APPLICATIONS:
        raise IntakeStorageError(f"Unsupported application: {application}")

    created = _utc_now()
    retention_days = _retention_days()
    assert retention_days is not None
    geometry_text = _json_text(geometry_geojson) if geometry_geojson is not None else None
    geometry_digest = hashlib.sha256(geometry_text.encode("utf-8")).hexdigest() if geometry_text else None
    stored_geometry = geometry_text if _geometry_choice() else None
    reference = f"{application[:3].upper()}-{created:%Y%m%d}-{secrets.token_hex(5).upper()}"

    try:
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO intake_submissions (
                    id, reference, application, source_route,
                    contact_name, contact_email, contact_mobile, company,
                    form_json, geometry_geojson, geometry_sha256, result_json,
                    status, created_at, retention_due_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    secrets.token_hex(16),
                    reference,
                    application,
                    source_route,
                    str(contact.get("name", "")).strip(),
                    str(contact.get("email", "")).strip(),
                    str(contact.get("mobile", "") or "").strip(),
                    str(contact.get("company", "") or "").strip(),
                    _json_text(form),
                    stored_geometry,
                    geometry_digest,
                    _json_text(result),
                    "received",
                    created.isoformat(),
                    (created + timedelta(days=retention_days)).isoformat(),
                ),
            )
    except Exception as exc:
        raise IntakeStorageError("Required intake record could not be saved") from exc
    return reference


def _require_operator(authorization: str | None) -> None:
    expected = os.environ.get("INTAKE_OPERATOR_TOKEN", "")
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail={"code": "intake_operator_unauthorised"})


def _require_ready_registry() -> None:
    status = public_storage_status()
    if not status["ready"]:
        raise HTTPException(status_code=503, detail={"code": "intake_registry_not_ready"})


def _serialise_row(row: sqlite3.Row, *, include_geometry: bool) -> dict[str, Any]:
    item = dict(row)
    for key in ("form_json", "result_json"):
        item[key.removesuffix("_json")] = json.loads(item.pop(key))
    geometry_text = item.pop("geometry_geojson")
    if include_geometry:
        item["geometry_geojson"] = json.loads(geometry_text) if geometry_text else None
    return item


@router.get("/config", tags=["discovery"])
def intake_config() -> dict[str, Any]:
    """Return only safe readiness metadata; never reveal paths or secrets."""
    return public_storage_status()


@router.get("/submissions")
def list_submissions(
    application: Literal["carbon", "eudr"] | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    include_geometry: bool = Query(False),
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    _require_operator(authorization)
    _require_ready_registry()
    query = "SELECT * FROM intake_submissions"
    params: list[Any] = []
    if application:
        query += " WHERE application = ?"
        params.append(application)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return {
        "count": len(rows),
        "submissions": [_serialise_row(row, include_geometry=include_geometry) for row in rows],
    }


@router.get("/export.csv")
def export_submissions(
    application: Literal["carbon", "eudr"] | None = Query(None),
    include_geometry: bool = Query(False),
    authorization: str | None = Header(None),
) -> Response:
    _require_operator(authorization)
    _require_ready_registry()
    query = "SELECT * FROM intake_submissions"
    params: list[Any] = []
    if application:
        query += " WHERE application = ?"
        params.append(application)
    query += " ORDER BY created_at DESC"
    with connection() as conn:
        rows = conn.execute(query, params).fetchall()

    columns = [
        "reference", "application", "created_at", "retention_due_at", "status",
        "contact_name", "contact_email", "contact_mobile", "company", "source_route",
        "form_json", "geometry_sha256", "result_json",
    ]
    if include_geometry:
        columns.append("geometry_geojson")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="180climate-intake.csv"'},
    )
