"""core/overlays/pippib.py — PIPPIB moratorium adapter (Overlay B, ADR-0013-peatland).

Legal basis: Inpres 5/2019 (lineage: Inpres 10/2011 → 6/2013 → 8/2015 → 6/2017).
Covers primary natural forest AND peatland; updated ~6-monthly by KLHK.
Source: KLHK PIPPIB published polygons (free).
Env var PIPPIB_URL: base URL for real query (unset → CI fixture only).

Returns OverlayIntersection(intersects=None) when data is unavailable — NOT a negative.
"""
from __future__ import annotations
import os
from core.contracts import Boundary, OverlayIntersection
from core.overlays._cache import load_fixture

_ADAPTER = "pippib"
_SOURCE = "PIPPIB moratorium peatland (Inpres5/2019) — KLHK"


def query_pippib(boundary: Boundary) -> OverlayIntersection:
    """Query Overlay B: PIPPIB moratorium peatland polygon.

    Loads from the CI fixture cache if available.
    Falls back to a real HTTP query if PIPPIB_URL is set.
    Returns intersects=None when data is unavailable (NOT a negative result).
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        return OverlayIntersection(source=_SOURCE, **cached)

    pippib_url = os.environ.get("PIPPIB_URL")
    if pippib_url:
        return _query_live(boundary, pippib_url)

    return OverlayIntersection(
        intersects=None,
        source=_SOURCE,
        note="PIPPIB moratorium data unavailable; manual overlay review required (ADR-0013-peatland)",
    )


def _query_live(boundary: Boundary, base_url: str) -> OverlayIntersection:
    """Placeholder for live PIPPIB query — implement when KLHK API contract is confirmed."""
    return OverlayIntersection(
        intersects=None,
        source=_SOURCE,
        note=f"PIPPIB live query not yet implemented (url={base_url}); manual review required",
    )
