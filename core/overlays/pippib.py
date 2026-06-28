"""core/overlays/pippib.py — PIPPIB moratorium adapter (Overlay B, ADR-0013-peatland).

Legal basis: Inpres 5/2019 (lineage: Inpres 10/2011 → 6/2013 → 8/2015 → 6/2017).
Covers primary natural forest AND peatland; updated ~6-monthly by Kementerian Kehutanan.

Authoritative version: PIPPIB 2025 Periode II, SK Menteri Kehutanan No. 6156/2025
(BIG-layer currency to be confirmed by the methodology advisor — noted, not blocking).

Live BIG One Map endpoint (primary):
  https://kspservices.big.go.id/satupeta/rest/services/
  PUBLIK/PERIZINAN_DAN_PERTANAHAN/MapServer/8
  Type: Feature Layer · geometryType: esriGeometryPolygon · SR: wkid 4326
  capabilities: Map,Query,Data · supportedQueryFormats: JSON, geoJSON
  Field `pippib`: "PIPPIB GAMBUT" (peat), "PIPPIB KAWASAN" (conservation/protection
  forest), "PIPPIB PRIMER" (primary natural forest).

Env PIPPIB_BASE_URL: override the default endpoint (for testing/future migration).
Env PIPPIB_DISABLE_LIVE=true: skip live query (CI kill-switch); falls back to
  PIPPIB_SNAPSHOT_PATH if set, else returns intersects=None.
Env PIPPIB_SNAPSHOT_PATH: path to a local PIPPIB GeoJSON snapshot (secondary fallback;
  no longer required when live endpoint is reachable).

Failure/timeout/error → intersects=None → FLAG (ADR-0013: None ≠ negative).
"""
from __future__ import annotations
import json
import logging
import os
from typing import Optional
from shapely.geometry import shape
from shapely.strtree import STRtree
from core.contracts import Boundary, OverlayIntersection
from core.overlays._cache import load_fixture

log = logging.getLogger(__name__)

_ADAPTER = "pippib"
_SOURCE = "PIPPIB moratorium (Inpres5/2019) — BIG One Map / Kementerian Kehutanan"
_DEFAULT_BASE = (
    "https://kspservices.big.go.id/satupeta/rest/services"
    "/PUBLIK/PERIZINAN_DAN_PERTANAHAN/MapServer"
)
_LAYER = "8"

# Module-level snapshot cache: path -> (STRtree, list[feature_dict])
_snapshot_cache: dict[str, tuple] = {}


def query_pippib(boundary: Boundary) -> OverlayIntersection:
    """Query Overlay B: PIPPIB moratorium peatland/forest polygon.

    Fixture cache first (CI-safe). Live BIG REST query if no fixture and live
    not disabled. PIPPIB_SNAPSHOT_PATH is a secondary fallback when live is
    disabled — it is no longer the primary path.
    Returns intersects=None on any failure — NOT a negative result.
    """
    cached = load_fixture(_ADAPTER, boundary.centroid_lat, boundary.centroid_lon)
    if cached is not None:
        return OverlayIntersection(source=_SOURCE, **cached)

    if os.environ.get("PIPPIB_DISABLE_LIVE", "").lower() == "true":
        snapshot_path = os.environ.get("PIPPIB_SNAPSHOT_PATH", "")
        if snapshot_path:
            return _query_snapshot(boundary, snapshot_path)
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note="PIPPIB live query disabled (PIPPIB_DISABLE_LIVE=true)",
        )

    base = os.environ.get("PIPPIB_BASE_URL", _DEFAULT_BASE)
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
    """POST spatial intersect query to BIG ArcGIS REST endpoint (MapServer/8)."""
    import httpx

    url = f"{base}/{_LAYER}/query"
    try:
        esri_geom = _geojson_to_esri(boundary.geojson)
    except Exception as exc:
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"PIPPIB geometry conversion failed: {exc}",
        )

    params = {
        "where": "1=1",
        "geometry": json.dumps(esri_geom),
        "geometryType": "esriGeometryPolygon",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "pippib",
        "returnGeometry": "false",
        "f": "json",
    }
    try:
        resp = httpx.post(url, data=params, timeout=10.0, verify=False)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("PIPPIB live query failed: %s", exc)
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"PIPPIB data unavailable — BIG endpoint error: {type(exc).__name__}; manual review required",
        )

    if "error" in data:
        log.warning("PIPPIB query returned error: %s", data["error"])
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"PIPPIB query error from BIG server: {data['error'].get('message', 'unknown')}; manual review required",
        )

    features = data.get("features", [])
    if not features:
        return OverlayIntersection(
            intersects=False,
            source=_SOURCE,
            note="PIPPIB moratorium: no intersection (BIG live query)",
        )

    categories = sorted({
        f.get("attributes", {}).get("pippib", "unknown")
        for f in features
    })
    note_parts = ["PIPPIB moratorium intersection confirmed (BIG live query)"]
    note_parts.append(f"categories: {', '.join(categories)}")
    log.info("PIPPIB intersection: %s features, %s", len(features), "; ".join(note_parts))
    return OverlayIntersection(
        intersects=True,
        source=_SOURCE,
        area_ha=None,
        note="; ".join(note_parts),
    )


# ── Snapshot fallback (secondary — active when PIPPIB_DISABLE_LIVE=true + PIPPIB_SNAPSHOT_PATH set) ──

def _load_snapshot(path: str) -> tuple[STRtree, list]:
    """Load PIPPIB GeoJSON snapshot into a shapely STRtree (cached per path)."""
    if path in _snapshot_cache:
        return _snapshot_cache[path]
    log.info("Loading PIPPIB snapshot: %s", path)
    with open(path, encoding="utf-8") as f:
        fc = json.load(f)
    features = [feat for feat in fc.get("features", []) if feat.get("geometry")]
    geometries = [shape(feat["geometry"]) for feat in features]
    tree = STRtree(geometries)
    _snapshot_cache[path] = (tree, features)
    name = fc.get("name") or fc.get("title") or os.path.basename(path)
    log.info("PIPPIB snapshot loaded: %s (%d features)", name, len(features))
    return tree, features


def _query_snapshot(boundary: Boundary, path: str) -> OverlayIntersection:
    """Query PIPPIB against a local GeoJSON snapshot using shapely STRtree."""
    try:
        tree, features = _load_snapshot(path)
    except Exception as exc:
        log.warning("PIPPIB snapshot load failed: %s", exc)
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"PIPPIB snapshot load failed ({type(exc).__name__}): {exc}; manual review required",
        )

    try:
        concession = shape(boundary.geojson)
        indices = tree.query(concession, predicate="intersects")
    except Exception as exc:
        log.warning("PIPPIB snapshot query failed: %s", exc)
        return OverlayIntersection(
            intersects=None,
            source=_SOURCE,
            note=f"PIPPIB snapshot query failed: {exc}; manual review required",
        )

    if len(indices) == 0:
        return OverlayIntersection(
            intersects=False,
            source=_SOURCE,
            note="PIPPIB moratorium: no intersection (snapshot query)",
        )

    categories = sorted({features[int(i)]["properties"].get("PIPPIB", "unknown") for i in indices})
    return OverlayIntersection(
        intersects=True,
        source=_SOURCE,
        note=f"PIPPIB moratorium intersection: {', '.join(categories)} (snapshot query — {os.path.basename(path)})",
    )
