"""core/overlays/khg.py — KHG fungsi-lindung/dome adapter (Overlay A, ADR-0013-peatland).

Legal basis: PP 71/2014 jo PP 57/2016 (ecosystem function, dome protection).
Source: KLHK KHG function maps (published; free).
Env var KHG_URL: base URL for real KHG WFS/REST query (unset → CI fixture only).

Returns OverlayIntersection(intersects=None) when data is unavailable — this
is NOT a "no intersection" result; callers must treat None as "not determined".
"""
from __future__ import annotations
import os
from core.contracts import Boundary, OverlayIntersection
from core.overlays._cache import load_fixture

_ADAPTER = "khg"
_SOURCE = "KHG fungsi-lindung (PP57/2016) — KLHK"


def query_khg(boundary: Boundary) -> OverlayIntersection:
    """Query Overlay A: KHG peat-ecosystem function / fungsi lindung / dome.

    Loads from the CI fixture cache if available.
    Falls back to a real HTTP query if KHG_URL is set.
    Returns intersects=None when data is unavailable (NOT a negative result).
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        return OverlayIntersection(source=_SOURCE, **cached)

    khg_url = os.environ.get("KHG_URL")
    if khg_url:
        return _query_live(boundary, khg_url)

    return OverlayIntersection(
        intersects=None,
        source=_SOURCE,
        note="KHG fungsi-lindung data unavailable; manual overlay review required (ADR-0013-peatland)",
    )


def _query_live(boundary: Boundary, base_url: str) -> OverlayIntersection:
    """Placeholder for live KHG WFS/REST query — implement when data contract is confirmed."""
    return OverlayIntersection(
        intersects=None,
        source=_SOURCE,
        note=f"KHG live query not yet implemented (url={base_url}); manual review required",
    )
