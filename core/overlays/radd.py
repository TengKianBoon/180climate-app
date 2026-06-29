"""core/overlays/radd.py — RADD radar deforestation-alert adapter (ADR-0018, EUDR E3).

RADD (Radar for Detecting Deforestation, WUR) — Sentinel-1 C-band radar alerts that see
through cloud and catch loss the optical Hansen map misses. Used to ENRICH the triage: a
post-cutoff RADD alert on a forest baseline confirms `loss_detected`. RADD is NON-BLOCKING —
its absence/unavailability does NOT prevent `clear_in_screen` when Hansen+JRC are conclusive.

Distribution: GFW Data API (`data-api.globalforestwatch.org`, dataset `wur_radd_alerts`).
  ⚠ The GFW Data API query endpoint requires an `x-api-key`, so there is NO confirmed
  clean *free* HTTP endpoint at build time. Per the WO, RADD is therefore STUBBED by default
  (fixture-cache + unavailable) and flagged in OUTBOX. A best-effort live path is wired but
  OFF unless both RADD_GFW_API_URL and RADD_API_KEY are set.

Env RADD_GFW_API_URL : GFW Data API query URL (enables the best-effort live path).
Env RADD_API_KEY     : GFW Data API key (required for the live path; NEVER logged).
Env RADD_DISABLE_LIVE=true : force-skip live (CI kill-switch).

Returns alert_after_cutoff=None when unavailable — NEVER a fabricated False. The triage
engine treats None as "no enrichment signal" (it relies on Hansen+JRC), never as "clear".
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
_DATASETS_VERSION_STUB = "RADD (stubbed — enriches, not blocking; see OUTBOX flag)"

_EUDR_CUTOFF_DATE = "2020-12-31"


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

    Fixture cache first (CI-safe). Best-effort live only when RADD_GFW_API_URL + RADD_API_KEY
    are set and live is not disabled. Otherwise returns alert_after_cutoff=None (stubbed,
    flagged) — RADD enriches, it never blocks a clear read.
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

    api_url = os.environ.get("RADD_GFW_API_URL", "").strip()
    api_key = os.environ.get("RADD_API_KEY", "").strip()
    live_disabled = os.environ.get("RADD_DISABLE_LIVE", "").lower() == "true"

    if api_url and api_key and not live_disabled:
        return _query_live(boundary, api_url, api_key, cutoff_date)

    return RADDResult(
        alert_after_cutoff=None,
        datasets_version=_DATASETS_VERSION_STUB,
        note=(
            "RADD stubbed (no confirmed free endpoint; set RADD_GFW_API_URL + RADD_API_KEY "
            "to enable). Enriches, not blocking — triage relies on Hansen + JRC."
        ),
    )


def _query_live(
    boundary: Boundary, api_url: str, api_key: str, cutoff_date: str
) -> RADDResult:
    """Best-effort GFW Data API query for RADD alerts after the cutoff. Key is never logged."""
    import json

    import httpx

    geom = boundary.geojson
    sql = (
        "SELECT MAX(alert__date) AS latest, COUNT(*) AS n "
        f"FROM results WHERE alert__date > '{cutoff_date}'"
    )
    payload = {"geometry": geom, "sql": sql}
    headers = {"x-api-key": api_key, "content-type": "application/json"}
    try:
        resp = httpx.post(api_url, content=json.dumps(payload), headers=headers, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("RADD live query failed: %s", exc)  # key not in message
        return RADDResult(
            alert_after_cutoff=None,
            note=f"RADD data unavailable — GFW API error: {type(exc).__name__}; enrichment skipped",
        )

    rows = data.get("data", []) if isinstance(data, dict) else []
    if not rows:
        return RADDResult(
            alert_after_cutoff=False,
            latest_alert_date=None,
            datasets_version=_DATASETS_VERSION,
            note=f"RADD: no alerts after {cutoff_date} (GFW Data API)",
        )

    row = rows[0]
    n = row.get("n") or 0
    latest = row.get("latest")
    return RADDResult(
        alert_after_cutoff=bool(n and n > 0),
        latest_alert_date=latest,
        datasets_version=_DATASETS_VERSION,
        note=f"RADD: {n} alert(s) after {cutoff_date}; latest {latest} (GFW Data API)",
    )
