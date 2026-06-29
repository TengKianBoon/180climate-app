"""core/overlays/jrc_gfc2020.py — JRC Global Forest Cover 2020 baseline adapter (ADR-0018, EUDR E3).

The EU's OWN reference forest map for the EUDR 31-Dec-2020 cutoff — the credibility anchor.
Binary forest / non-forest for the year 2020, 10 m, WGS84. A plot must have a 2020 forest
baseline for `clear_in_screen` or `loss_detected` to be meaningful.

Source (EC JRC open data, no auth) — VERIFIED LIVE during WO-EUDR-TRIAGE-003 build:
  https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FOREST/GFC2020/LATEST/
  ├─ single-cog/JRC_GFC2020_V3_COG.tif   ← DEFAULT (global Cloud-Optimized GeoTIFF; one
  │                                          windowed vsicurl read works anywhere — no tile math)
  ├─ single/JRC_GFC2020_V3.tif            (plain global GeoTIFF + .ovr)
  └─ tiles/JRC_GFC2020_V3_{NS}{lat}_{EW}{lon}.tif   (10° NW-corner tiles, UNPADDED:
                                              e.g. JRC_GFC2020_V3_N0_E110.tif, N10_E110.tif)

  Default is the single global COG — robust and confirmed reachable (the per-tile path that
  the first build guessed, JRC_GFC2020_V3_N00_E110.tif, 404'd; the real names are unpadded and
  the COG avoids the question entirely). Cowork: please confirm the COG is acceptable as the
  standing source (license = copyright.txt alongside; CC-BY-style EC open data).

Env JRC_GFC2020_URL: override. May be:
  • a single COG/VRT/.tif URL covering the AOI (used verbatim), or
  • a template with {tile}, {lat}, {lon} placeholders for the tiles/ path, e.g.
    ".../LATEST/tiles/JRC_GFC2020_V3_{tile}.tif".
Env JRC_GFC2020_DISABLE_LIVE=true: CI kill-switch → forest_2020=None (unavailable).

Returns forest_2020=None on ANY failure — NEVER a negative (None ≠ "no forest"); the triage
engine maps None → `inconclusive` (honesty rule: never clear without a real 2020 baseline).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from core.contracts import Boundary
from core.data.gfw import GFWHTTPAdapter, _GDAL_ENV
from core.overlays._cache import load_fixture

log = logging.getLogger(__name__)

_ADAPTER = "jrc_gfc2020"
_SOURCE = "JRC Global Forest Cover 2020 (EC JRC, 10 m, EUDR reference map)"
_DATASETS_VERSION = "JRC GFC2020 V3 (EC JRC, 10m)"

_LATEST = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FOREST/GFC2020/LATEST"
# DEFAULT: the single global Cloud-Optimized GeoTIFF (one windowed read works anywhere).
_DEFAULT_URL = f"{_LATEST}/single-cog/JRC_GFC2020_V3_COG.tif"
# Per-tile path (opt-in via JRC_GFC2020_URL template); tiles are NW-corner, UNPADDED.
_TILES_BASE = f"{_LATEST}/tiles"

# A plot needs a meaningful 2020 forest baseline; ≥10% forest-pixel cover qualifies.
_FOREST_BASELINE_PCT_THRESHOLD = 10.0

# Reuse the carbon adapter's NW-corner tile helpers + bbox extractor (DRY).
_GFW = GFWHTTPAdapter()


@dataclass
class JRCGFC2020Result:
    """2020 forest baseline for a plot per the EU's JRC GFC2020 reference map.

    forest_2020 is None when the map could not be read (Point/sub-resolution, rasterio
    missing, network/tile error, all-nodata) — NEVER a fabricated False.
    """

    forest_2020: Optional[bool]   # None = unavailable (NOT a confirmed "no forest")
    forest_pct: float = 0.0       # 0–100, forest-pixel fraction of the plot window
    source: str = _SOURCE
    datasets_version: str = _DATASETS_VERSION
    note: str = ""

    @property
    def available(self) -> bool:
        return self.forest_2020 is not None


def _jrc_tile_name(lat: float, lon: float) -> str:
    """NW-corner 10° tile id, UNPADDED, e.g. 'N0_E110' / 'N10_E110' (verified live naming)."""
    lat_deg, lat_hem = _GFW._nw_lat_deg(lat)
    lon_deg, lon_hem = _GFW._nw_lon_deg(lon)
    return f"{lat_hem}{lat_deg}_{lon_hem}{lon_deg}"


def _jrc_url(lat: float, lon: float) -> str:
    """Resolve the JRC GFC2020 URL. Default = the single global COG (robust, no tile math)."""
    override = os.environ.get("JRC_GFC2020_URL", "").strip()
    if not override:
        return _DEFAULT_URL
    if "{" in override:  # caller supplied a tiles/ template
        return override.format(tile=_jrc_tile_name(lat, lon), lat=lat, lon=lon)
    return override  # single COG/VRT/.tif URL — used verbatim


def query_jrc_gfc2020(boundary: Boundary) -> JRCGFC2020Result:
    """Return the 2020 forest baseline for the plot from JRC GFC2020.

    Fixture cache first (CI-safe). Live rasterio/vsicurl read unless disabled.
    Returns forest_2020=None on any failure (→ inconclusive, never clear).
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        return JRCGFC2020Result(
            forest_2020=cached.get("forest_2020"),
            forest_pct=cached.get("forest_pct", 0.0),
            source=_SOURCE,
            datasets_version=cached.get("datasets_version", _DATASETS_VERSION),
            note=cached.get("note", "fixture"),
        )

    if os.environ.get("JRC_GFC2020_DISABLE_LIVE", "").lower() == "true":
        return JRCGFC2020Result(
            forest_2020=None,
            note="JRC GFC2020 live read disabled (JRC_GFC2020_DISABLE_LIVE=true); no fixture",
        )

    return _query_live(boundary)


def _query_live(boundary: Boundary) -> JRCGFC2020Result:
    """Read the JRC GFC2020 binary forest tile over the plot window (rasterio vsicurl)."""
    bbox = _GFW._bbox_from_boundary(boundary)
    if bbox is None:
        return JRCGFC2020Result(
            forest_2020=None,
            note="No polygon window (Point/sub-resolution plot); JRC baseline unavailable",
        )

    west, south, east, north = bbox
    url = _jrc_url(boundary.centroid_lat, boundary.centroid_lon)

    try:
        import numpy as np
        import rasterio
        from rasterio.windows import from_bounds as _from_bounds

        with rasterio.Env(**_GDAL_ENV):
            with rasterio.open(_GFW._vsicurl(url)) as src:
                window = _from_bounds(west, south, east, north, src.transform)
                arr = src.read(1, window=window).astype("float64")
                nodata = src.nodata
                if nodata is not None:
                    arr[arr == nodata] = np.nan
                valid = arr[~np.isnan(arr)]
                if valid.size == 0:
                    return JRCGFC2020Result(
                        forest_2020=None,
                        note=f"JRC GFC2020 all-nodata over window (tile {url.rsplit('/', 1)[-1]})",
                    )
                # GFC2020 is binary: forest pixel value >= 1, non-forest = 0.
                forest_pct = float((valid >= 1).sum()) / float(valid.size) * 100.0
                return JRCGFC2020Result(
                    forest_2020=forest_pct >= _FOREST_BASELINE_PCT_THRESHOLD,
                    forest_pct=round(forest_pct, 1),
                    note=f"JRC GFC2020 pixel read (tile {url.rsplit('/', 1)[-1]})",
                )
    except Exception as exc:
        log.warning("JRC GFC2020 live read failed: %s", exc)
        return JRCGFC2020Result(
            forest_2020=None,
            note=(
                f"JRC GFC2020 read error: {type(exc).__name__}: {exc}; unavailable. "
                f"If persistent, verify tile URL/naming (set JRC_GFC2020_URL)."
            ),
        )
