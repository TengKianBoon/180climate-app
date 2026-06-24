"""core/overlays/pippib.py — PIPPIB moratorium adapter (Overlay B, ADR-0013-peatland).

Legal basis: Inpres 5/2019 (lineage: Inpres 10/2011 → 6/2013 → 8/2015 → 6/2017).
Covers primary natural forest AND peatland; updated ~6-monthly by Kementerian Kehutanan.

IMPORTANT — live REST query not available (2026-06-24 probe):
The geoportal.menlhk.go.id PIPPIB MapServer exposes Map capability only — no Query or
FeatureServer. All 16 portal items tested; no public spatial-query endpoint found post
Oct-2024 ministry split (KLHK → Kehutanan + LH). kehutanan.go.id DNS not yet resolving.

Production path (Option B):
  1. Download PIPPIB current-period shapefile from geoportal.menlhk.go.id web UI
     (or formal KLHK/Kemenhut data request — see docs/wo-realmaps-sourcing.md).
  2. Convert to GeoJSON: ogr2ogr -f GeoJSON PIPPIB_2026_I.geojson PIPPIB_2026_I.shp
  3. Set env var: PIPPIB_SNAPSHOT_PATH=/path/to/PIPPIB_2026_I.geojson
  4. The adapter loads it once per process into a shapely STRtree (fast in-memory lookup).

Category field: PIPPIB (string). Values: "PIPPIB GAMBUT", "PIPPIB KAWASAN", "PIPPIB PRIMER".
Failure/no-snapshot → intersects=None → FLAG (ADR-0013: None ≠ negative).
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
_SOURCE = "PIPPIB moratorium (Inpres5/2019) — Kementerian Kehutanan"

# Module-level snapshot cache: path -> (STRtree, list[feature_dict])
_snapshot_cache: dict[str, tuple] = {}


def query_pippib(boundary: Boundary) -> OverlayIntersection:
    """Query Overlay B: PIPPIB moratorium peatland/forest polygon.

    Fixture cache first (CI-safe). Snapshot file if PIPPIB_SNAPSHOT_PATH set.
    Returns intersects=None when no data available — NOT a negative result.
    """
    cached = load_fixture(_ADAPTER, boundary.centroid_lat, boundary.centroid_lon)
    if cached is not None:
        return OverlayIntersection(source=_SOURCE, **cached)

    snapshot_path = os.environ.get("PIPPIB_SNAPSHOT_PATH", "")
    if snapshot_path:
        return _query_snapshot(boundary, snapshot_path)

    return OverlayIntersection(
        intersects=None,
        source=_SOURCE,
        note=(
            "PIPPIB moratorium data unavailable — no snapshot loaded. "
            "Set PIPPIB_SNAPSHOT_PATH to a local GeoJSON file (see docs/wo-realmaps-sourcing.md). "
            "ADR-0013: intersects=None → FLAG (conservative; not a confirmed intersection)."
        ),
    )


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
    # Log the layer name/date if present in the GeoJSON metadata
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
