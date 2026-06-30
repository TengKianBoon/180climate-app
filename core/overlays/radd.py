"""core/overlays/radd.py — RADD radar deforestation-alert adapter (ADR-0018, EUDR E3).

RADD (Radar for Detecting Deforestation, WUR) — Sentinel-1 C-band radar alerts that see
through cloud and catch loss the optical Hansen map misses. Used to ENRICH the triage: a
post-cutoff RADD alert on a forest baseline confirms `loss_detected`. RADD is NON-BLOCKING —
its absence/unavailability does NOT prevent `clear_in_screen` when Hansen+JRC are conclusive.

Distribution: GFW Data API (`data-api.globalforestwatch.org`, dataset `wur_radd_alerts`).
  Requires an `x-api-key` header; set RADD_API_KEY in the host environment (Render).
  Default endpoint is _DEFAULT_RADD_URL; override with RADD_GFW_API_URL.

Env RADD_API_KEY          : GFW Data API key (enables live path; NEVER logged).
Env RADD_GFW_API_URL      : override the default GFW Data API query URL.
Env RADD_DISABLE_LIVE=true: force-skip live (CI kill-switch).

Returns alert_after_cutoff:
  True  — at least one confirmed post-cutoff RADD alert intersects the plot geometry.
  False — query succeeded; no post-cutoff alerts found (genuine negative).
  None  — unavailable (API error, key missing, disabled) — NEVER fabricated.

The triage engine treats None as "no enrichment signal" (relies on Hansen+JRC), never as clear.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from core.contracts import Boundary
from core.overlays._cache import load_fixture

log = logging.getLogger(__name__)

_ADAPTER = "radd"
_SOURCE = "RADD radar alerts (WUR / GFW Data API)"
_DATASETS_VERSION = "RADD (WUR Sentinel-1 alerts; via GFW Data API)"
_DATASETS_VERSION_STUB = "RADD (stubbed — enriches, not blocking; RADD_API_KEY not set)"

_EUDR_CUTOFF_DATE = "2020-12-31"

# Default GFW Data API spatial-query endpoint for WUR RADD alerts.
# Override via RADD_GFW_API_URL (e.g. if GFW renames the dataset).
_DEFAULT_RADD_URL = (
    "https://data-api.globalforestwatch.org/dataset/wur_radd_alerts/latest/query"
)


@dataclass
class RADDResult:
    """Post-cutoff RADD radar-alert signal for a plot (enrichment only).

    alert_after_cutoff is None when RADD is unavailable/stubbed — NEVER a fabricated False.
    """

    alert_after_cutoff: Optional[bool]    # None = unavailable (NOT a confirmed "no alert")
    latest_alert_date: Optional[str] = None   # ISO date of most recent post-cutoff alert
    source: str = _SOURCE
    datasets_version: str = _DATASETS_VERSION_STUB
    note: str = ""

    @property
    def available(self) -> bool:
        return self.alert_after_cutoff is not None


def query_radd(boundary: Boundary, cutoff_date: str = _EUDR_CUTOFF_DATE) -> RADDResult:
    """Return post-cutoff RADD alert signal for the plot.

    Order of precedence:
      1. Committed fixture (CI-safe, always checked first).
      2. Live GFW Data API query (when RADD_API_KEY is set and RADD_DISABLE_LIVE != true).
      3. Stub: alert_after_cutoff=None — enriches, never blocks a clear read.
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        return RADDResult(
            alert_after_cutoff=cached.get("alert_after_cutoff"),
            latest_alert_date=cached.get("latest_alert_date"),
            source=_SOURCE,
            datasets_version=cached.get("datasets_version", _DATASETS_VERSION),
            note=cached.get("note", "fixture"),
        )

    api_key = os.environ.get("RADD_API_KEY", "").strip()
    live_disabled = os.environ.get("RADD_DISABLE_LIVE", "").lower() == "true"

    if api_key and not live_disabled:
        api_url = os.environ.get("RADD_GFW_API_URL", _DEFAULT_RADD_URL).strip()
        return _query_live(boundary, api_url, api_key, cutoff_date)

    return RADDResult(
        alert_after_cutoff=None,
        datasets_version=_DATASETS_VERSION_STUB,
        note=(
            "RADD stubbed (RADD_API_KEY not set or RADD_DISABLE_LIVE=true). "
            "Enriches, not blocking — triage relies on Hansen + JRC."
        ),
    )


def _query_live(
    boundary: Boundary, api_url: str, api_key: str, cutoff_date: str
) -> RADDResult:
    """GFW Data API spatial query for post-cutoff RADD alerts. Key is NEVER logged."""
    import json

    import httpx

    geom = boundary.geojson
    sql = (
        "SELECT MAX(alert__date) AS latest, COUNT(*) AS n "
        f"FROM results WHERE alert__date > '{cutoff_date}'"
    )
    payload = {"geometry": geom, "sql": sql}
    # Key passed only in the header — never written to logs or error messages.
    headers = {"x-api-key": api_key, "content-type": "application/json"}

    try:
        resp = httpx.post(api_url, content=json.dumps(payload), headers=headers, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        # Log the exception type only — never the key or headers.
        log.warning("RADD live query failed (%s); enrichment skipped", type(exc).__name__)
        return RADDResult(
            alert_after_cutoff=None,
            datasets_version=_DATASETS_VERSION_STUB,
            note=f"RADD data unavailable — GFW API error: {type(exc).__name__}",
        )

    # Parse the GFW Data API response: {"status": "success", "data": [...]}
    if not isinstance(data, dict):
        log.warning("RADD: unexpected response type %s; treating as unavailable", type(data).__name__)
        return RADDResult(
            alert_after_cutoff=None,
            datasets_version=_DATASETS_VERSION_STUB,
            note="RADD: unexpected response format — treated as unavailable",
        )

    rows = data.get("data")
    if not isinstance(rows, list):
        log.warning("RADD: 'data' field missing or not a list; treating as unavailable")
        return RADDResult(
            alert_after_cutoff=None,
            datasets_version=_DATASETS_VERSION_STUB,
            note="RADD: 'data' field missing or unexpected — treated as unavailable",
        )

    if not rows:
        # Query succeeded; no alerts found after the cutoff date.
        return RADDResult(
            alert_after_cutoff=False,
            latest_alert_date=None,
            datasets_version=_DATASETS_VERSION,
            note=f"RADD: queried OK; no alerts after {cutoff_date} (GFW Data API)",
        )

    row = rows[0]
    n = row.get("n") or 0
    latest = row.get("latest")
    has_alert = bool(n and int(n) > 0)
    return RADDResult(
        alert_after_cutoff=has_alert,
        latest_alert_date=latest if has_alert else None,
        datasets_version=_DATASETS_VERSION,
        note=f"RADD: {n} alert(s) after {cutoff_date}; latest {latest} (GFW Data API)",
    )
