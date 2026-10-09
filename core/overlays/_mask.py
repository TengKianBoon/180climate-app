"""core/overlays/_mask.py — restrict a raster window to the pixels inside a plot polygon.

Used by the EUDR overlays so that forest share and post-2020 loss are measured INSIDE the
plot, not across its whole bounding box (a bbox over-counts neighbouring land, and for thin
or diagonal plots can be several times the plot area).
"""
from __future__ import annotations

from typing import Any, Optional


def _plain_geometry(geojson: Optional[dict]) -> Optional[dict]:
    if not isinstance(geojson, dict):
        return None
    kind = geojson.get("type")
    if kind == "Feature":
        return _plain_geometry(geojson.get("geometry"))
    if kind in ("Polygon", "MultiPolygon"):
        return geojson
    return None  # Points, collections, unknown → caller falls back to the bbox window


def inside_mask(geojson: Optional[dict], shape: tuple[int, int], transform: Any):
    """Boolean array (True = pixel centre inside the plot). Whole window if no polygon.

    A polygon with no pixel centre returns an empty mask; callers must report unavailable.
    """
    import numpy as np
    from rasterio.features import geometry_mask

    geom = _plain_geometry(geojson)
    if geom is None:
        return np.ones(shape, dtype=bool)
    inside = ~geometry_mask([geom], out_shape=shape, transform=transform, all_touched=False)
    return inside
