"""core/overlays/worldcover.py — ESA WorldCover 10m land-cover adapter (ADR-0013).

Source: ESA WorldCover 2021 v200 (free; CC-BY 4.0).
Purpose: land-cover classification for the forest-presence gate (ADR-0013-auto-routing).
NOTE: WorldCover identifies LAND COVER (tree cover) — it CANNOT identify peat (substrate).
      Use KHG/PIPPIB overlays for peat legal status (ADR-0013-peatland).
Env var WORLDCOVER_TILE_URL: S3/HTTPS base URL (unset → CI fixture only).

Class codes (WorldCover 2021):
  10 = Tree cover   20 = Shrubland    30 = Grassland    40 = Cropland
  50 = Built-up     60 = Bare/sparse  70 = Snow/ice     80 = Permanent water
  90 = Herbaceous wetland  95 = Mangroves  100 = Moss/lichen
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from core.contracts import Boundary
from core.overlays._cache import load_fixture

_ADAPTER = "worldcover"
_SOURCE = "ESA WorldCover 2021 v200"

_TREE_COVER_CLASS = 10


@dataclass
class WorldCoverResult:
    """Dominant land-cover class for the concession centroid."""
    land_class: int              # ESA WorldCover class code
    label: str                   # Human-readable label
    tree_cover_pct: float        # Estimated canopy cover (0–100); 0 if not tree cover
    source: str = _SOURCE
    note: str = ""

    @property
    def is_tree_cover(self) -> bool:
        return self.land_class == _TREE_COVER_CLASS


_CLASS_LABELS: dict[int, str] = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare/sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

_UNKNOWN = WorldCoverResult(
    land_class=0,
    label="Unknown",
    tree_cover_pct=0.0,
    source=_SOURCE,
    note="WorldCover data unavailable; forest presence unconfirmed",
)


def query_worldcover(boundary: Boundary) -> WorldCoverResult:
    """Return the dominant ESA WorldCover land-cover class for the boundary centroid.

    Loads from CI fixture cache if available.
    Falls back to live tile query if WORLDCOVER_TILE_URL is set.
    Returns unknown result when data is unavailable.
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        land_class = cached.get("land_class", 0)
        return WorldCoverResult(
            land_class=land_class,
            label=cached.get("label", _CLASS_LABELS.get(land_class, "Unknown")),
            tree_cover_pct=cached.get("tree_cover_pct", 100.0 if land_class == _TREE_COVER_CLASS else 0.0),
            source=_SOURCE,
            note=cached.get("note", ""),
        )

    tile_url = os.environ.get("WORLDCOVER_TILE_URL")
    if tile_url:
        return _query_live(boundary, tile_url)

    return _UNKNOWN


def _query_live(boundary: Boundary, base_url: str) -> WorldCoverResult:
    """Placeholder for live WorldCover COG pixel read — implement via rasterio vsicurl."""
    return WorldCoverResult(
        land_class=0,
        label="Unknown",
        tree_cover_pct=0.0,
        source=_SOURCE,
        note=f"WorldCover live query not yet implemented (url={base_url})",
    )
