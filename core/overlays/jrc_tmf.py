"""core/overlays/jrc_tmf.py — JRC Tropical Moist Forest (TMF) disturbance adapter (ADR-0013).

Source: JRC TMF Annual Change product (free; Landsat-based; 1990–present).
Purpose: Forest disturbance/degradation history for the forest-presence gate.
Env var JRC_TMF_URL: base URL for TMF raster access (unset → CI fixture only).

Disturbance classes (JRC TMF Annual Change):
  1 = Undisturbed tropical moist forest
  2 = Degraded TMF
  3 = Deforested land (after deforestation)
  4 = Forest regrowth
  5 = Permanent or seasonal water
  6 = Other land cover
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from core.contracts import Boundary
from core.overlays._cache import load_fixture

_ADAPTER = "jrc_tmf"
_SOURCE = "JRC Tropical Moist Forest Annual Change"

_DISTURBANCE_LABELS: dict[str, str] = {
    "undisturbed": "Undisturbed tropical moist forest (TMF class 1)",
    "degraded": "Degraded tropical moist forest (TMF class 2)",
    "deforested": "Deforested land (TMF class 3)",
    "regrowth": "Forest regrowth (TMF class 4)",
    "water": "Permanent or seasonal water (TMF class 5)",
    "other": "Other land cover (TMF class 6)",
    "unknown": "Unknown / data unavailable",
}


@dataclass
class JRCTMFResult:
    """JRC TMF disturbance class for the concession centroid (most recent year)."""
    disturbance_class: str       # one of _DISTURBANCE_LABELS keys
    tropical_forest_pct: float   # estimated % of boundary that is/was TMF (0–100)
    deforestation_year: int | None  # year of most recent deforestation event (None if none)
    source: str = _SOURCE
    note: str = ""

    @property
    def label(self) -> str:
        return _DISTURBANCE_LABELS.get(self.disturbance_class, "Unknown")

    @property
    def is_forest(self) -> bool:
        return self.disturbance_class in ("undisturbed", "degraded", "regrowth")


_UNKNOWN = JRCTMFResult(
    disturbance_class="unknown",
    tropical_forest_pct=0.0,
    deforestation_year=None,
    source=_SOURCE,
    note="JRC TMF data unavailable; forest disturbance history unconfirmed",
)


def query_jrc_tmf(boundary: Boundary) -> JRCTMFResult:
    """Return JRC TMF disturbance class for the boundary centroid.

    Loads from CI fixture cache if available.
    Falls back to live raster query if JRC_TMF_URL is set.
    Returns unknown result when data is unavailable.
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        return JRCTMFResult(
            disturbance_class=cached.get("disturbance_class", "unknown"),
            tropical_forest_pct=cached.get("tropical_forest_pct", 0.0),
            deforestation_year=cached.get("deforestation_year"),
            source=_SOURCE,
            note=cached.get("note", ""),
        )

    tmf_url = os.environ.get("JRC_TMF_URL")
    if tmf_url:
        return _query_live(boundary, tmf_url)

    return _UNKNOWN


def _query_live(boundary: Boundary, base_url: str) -> JRCTMFResult:
    """Placeholder for live JRC TMF raster read — implement via rasterio vsicurl."""
    return JRCTMFResult(
        disturbance_class="unknown",
        tropical_forest_pct=0.0,
        deforestation_year=None,
        source=_SOURCE,
        note=f"JRC TMF live query not yet implemented (url={base_url})",
    )
