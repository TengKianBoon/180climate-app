"""core/overlays/khg.py — KHG fungsi-lindung adapter (Overlay A, ADR-0013-peatland).

Legal basis: PP 57/2016 + PermenLHK 14/2017. 1:50,000 national map.
Source: BIG One Map (Kebijakan Satu Peta) — public, WGS84, Query+Data capable.
Endpoint: https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/
          SUMBER_DAYA_ALAM_DAN_LINGKUNGAN/MapServer/48
Env KHG_BASE_URL: override the default endpoint (for testing/future migration).
Env KHG_DISABLE_LIVE=true: skip live query (emergency kill-switch — CI uses fixtures).

Failure/timeout → intersects=None → FLAG (ADR-0013: None ≠ negative; never return False on error).
"""
from __future__ import annotations
import json
import os
import logging
from core.contracts import Boundary, OverlayIntersection
from core.overlays._cache import load_fixture

log = logging.getLogger(__name__)

_ADAPTER = "khg"
_SOURCE = "KHG fungsi-lindung (PP57/2016) — BIG One Map"
_DEFAULT_BASE = (
    "https://kspservices.big.go.id/satupeta/rest/services"
    "/PUBLIK/SUMBER_DAYA_ALAM_DAN_LINGKUNGAN/MapServer"
)
_LAYER = "48"
_PROTECTED_VALUE = "Fungsi Lindung E.G."


def query_khg(boundary: Boundary) -> OverlayIntersection:
    """Query Overlay A: KHG peat ecosystem function (fungsi lindung/dome).

    Fixture cache first (CI-safe). Live BIG REST query if no fixture.
    Returns intersects=None on any failure — NOT a negative result.
    """
    cached = load_fixture(_ADAPTER, boundary.centroid_lat, boundary.centroid_lon)
    if cached is not None:
        return OverlayIntersection(source=_SOURCE, **cached)

    if os.environ.get("KHG_DISABLE_LIVE", "").lower() == "true":
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note="KHG live query disabled (KHG_DISABLE_LIVE=true)",
        )

    base = os.environ.get("KHG_BASE_URL", _DEFAULT_BASE)
    return _query_live(boundary, base)


def _geojson_to_esri(geojson: dict) -> dict:
    """Convert GeoJSON Polygon/MultiPolygon to Esri JSON rings format (WGS84)."""
    gtype = geojson.get("type", "")
    if gtype == "Polygon":
        rings = geojson["coordinates"]
    elif gtype == "MultiPolygon":
        rings = [ring for poly in geojson["coordinates"] for ring in poly]
    else:
        raise ValueError(f"Unsupported geometry type for Esri conversion: {gtype}")
    return {"rings": rings, "spatialReference": {"wkid": 4326}}


def _query_live(boundary: Boundary, base: str) -> OverlayIntersection:
    """POST spatial intersect query to BIG ArcGIS REST endpoint."""
    import httpx  # lazy import — not used in CI

    url = f"{base}/{_LAYER}/query"
    try:
        esri_geom = _geojson_to_esri(boundary.geojson)
    except Exception as exc:
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"KHG geometry conversion failed: {exc}",
        )

    params = {
        "where": f"feg_50k='{_PROTECTED_VALUE}'",
        "geometry": json.dumps(esri_geom),
        "geometryType": "esriGeometryPolygon",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "kode_khg,peat_thick,feg_50k",
        "returnGeometry": "false",
        "f": "json",
    }
    try:
        resp = httpx.post(url, data=params, timeout=10.0, verify=False)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("KHG live query failed: %s", exc)
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"KHG data unavailable — BIG endpoint error: {type(exc).__name__}; manual review required",
        )

    if "error" in data:
        log.warning("KHG query returned error: %s", data["error"])
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"KHG query error from BIG server: {data['error'].get('message', 'unknown')}; manual review required",
        )

    features = data.get("features", [])
    if not features:
        return OverlayIntersection(
            intersects=False,
            source=_SOURCE,
            note="KHG: no fungsi-lindung intersection (BIG live query)",
        )

    attrs = features[0].get("attributes", {})
    kode = attrs.get("kode_khg", "")
    thick = attrs.get("peat_thick", "")
    note_parts = ["KHG fungsi-lindung intersection confirmed (BIG 1:50k live query)"]
    if kode:
        note_parts.append(f"kode_khg={kode}")
    if thick:
        note_parts.append(f"peat_thick_class={thick}")
    note_parts.append("Depth ≥3m requires field survey (auger/coring/GPR) — ADR-0013")
    log.info("KHG intersection: %s features, %s", len(features), "; ".join(note_parts))
    return OverlayIntersection(
        intersects=True,
        source=_SOURCE,
        area_ha=None,
        note="; ".join(note_parts),
    )
