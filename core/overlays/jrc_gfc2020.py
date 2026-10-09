"""core/overlays/jrc_gfc2020.py — JRC Global Forest Cover 2020 baseline adapter (ADR-0018, EUDR E3).

The EU's OWN reference forest map for the EUDR 31-Dec-2020 cutoff — the credibility anchor.
Binary forest / non-forest for the year 2020, 10 m, WGS84. A plot must have a 2020 forest
baseline for `clear_in_screen` or `loss_detected` to be meaningful.

Source (EC JRC open data, no auth) — VERIFIED LIVE during WO-EUDR-TRIAGE-003 build:
  https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FOREST/GFC2020/LATEST/
  ├─ single-cog/JRC_GFC2020_V4_COG.tif   ← DEFAULT (V4 published 2026-09-14; V3 was withdrawn
  │                                          from LATEST/, which broke every live read — see below) (global Cloud-Optimized GeoTIFF; one
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
import re
from dataclasses import dataclass
from typing import Optional

from core.contracts import Boundary
from core.data.gfw import GFWHTTPAdapter, _GDAL_ENV
from core.overlays._cache import load_fixture

log = logging.getLogger(__name__)

_ADAPTER = "jrc_gfc2020"
_SOURCE = "JRC Global Forest Cover 2020 (EC JRC, 10 m, EUDR reference map)"
_DATASETS_VERSION = "JRC GFC2020 V4 (EC JRC, 10m)"

_LATEST = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FOREST/GFC2020/LATEST"
# DEFAULT: the single global Cloud-Optimized GeoTIFF (one windowed read works anywhere).
_SINGLE_COG_DIR = f"{_LATEST}/single-cog"
_DEFAULT_URL = f"{_SINGLE_COG_DIR}/JRC_GFC2020_V4_COG.tif"
_COG_NAME_RE = re.compile(r"JRC_GFC2020_V(\d+)_COG\.tif")

# Self-healing: JRC replaces the file under LATEST/ on each release (V3 -> V4 on 2026-09-14
# silently turned every plot "inconclusive"). On a 404 we re-discover the current COG name
# from the directory listing once per process and remember it here.
_discovered_url: Optional[str] = None
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


def version_label(url: str) -> str:
    """Human version stamp derived from the file actually read, e.g. 'JRC GFC2020 V4 (EC JRC, 10m)'."""
    m = _COG_NAME_RE.search(url) or re.search(r"JRC_GFC2020_V(\d+)", url)
    return f"JRC GFC2020 V{m.group(1)} (EC JRC, 10m)" if m else _DATASETS_VERSION


def _discover_latest_cog() -> Optional[str]:
    """Find the current single-COG file name in LATEST/single-cog/ (highest version wins)."""
    try:
        import httpx

        resp = httpx.get(_SINGLE_COG_DIR + "/", timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        versions = sorted({int(v) for v in _COG_NAME_RE.findall(resp.text)})
        if not versions:
            return None
        return f"{_SINGLE_COG_DIR}/JRC_GFC2020_V{versions[-1]}_COG.tif"
    except Exception as exc:  # pragma: no cover — network guard
        log.warning("JRC GFC2020 COG discovery failed: %s", exc)
        return None


def _jrc_url(lat: float, lon: float) -> str:
    """Resolve the JRC GFC2020 URL. Default = the single global COG (robust, no tile math)."""
    override = os.environ.get("JRC_GFC2020_URL", "").strip()
    if not override:
        return _discovered_url or _DEFAULT_URL
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
    """Read the JRC GFC2020 binary forest map over the plot (rasterio vsicurl).

    Forest share is computed from pixels INSIDE the plot polygon (falls back to the bounding
    box only when the polygon covers no pixel centre, i.e. a sub-pixel sliver). On an HTTP 404
    with no explicit override, the current COG name is re-discovered once and the read retried.
    """
    global _discovered_url

    bbox = _GFW._bbox_from_boundary(boundary)
    if bbox is None:
        return JRCGFC2020Result(
            forest_2020=None,
            note="No polygon window (Point/sub-resolution plot); JRC baseline unavailable",
        )

    url = _jrc_url(boundary.centroid_lat, boundary.centroid_lon)
    try:
        return _read_forest_share(boundary, bbox, url)
    except Exception as exc:
        overridden = bool(os.environ.get("JRC_GFC2020_URL", "").strip())
        if "404" in str(exc) and not overridden:
            fresh = _discover_latest_cog()
            if fresh and fresh != url:
                log.error("JRC GFC2020 URL %s returned 404; switching to %s", url, fresh)
                _discovered_url = fresh
                try:
                    return _read_forest_share(boundary, bbox, fresh)
                except Exception as exc2:  # pragma: no cover — network guard
                    exc = exc2
        log.error("JRC GFC2020 live read failed: %s", exc)
        return JRCGFC2020Result(
            forest_2020=None,
            note=(
                f"JRC GFC2020 read error: {type(exc).__name__}: {exc}; unavailable. "
                f"If persistent, verify tile URL/naming (set JRC_GFC2020_URL)."
            ),
        )


def _read_forest_share(boundary: Boundary, bbox: tuple, url: str) -> JRCGFC2020Result:
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds as _from_bounds

    from core.overlays._mask import inside_mask

    west, south, east, north = bbox
    with rasterio.Env(**_GDAL_ENV):
        with rasterio.open(_GFW._vsicurl(url)) as src:
            window = _from_bounds(west, south, east, north, src.transform)
            if window.width * window.height > 12_000_000:
                raise ValueError('Plot window too large; split the plot')
            arr = src.read(1, window=window, masked=True)
            win_transform = src.window_transform(window)
            nodata = src.nodata
    inside = inside_mask(boundary.geojson, arr.shape, win_transform)
    sample = arr[inside]
    valid = sample.compressed()
    if valid.size != sample.size:
        raise ValueError('JRC pixels unavailable inside plot')
    fname = url.rsplit("/", 1)[-1]
    if valid.size == 0:
        return JRCGFC2020Result(
            forest_2020=None,
            datasets_version=version_label(url),
            note=f"JRC GFC2020 all-nodata over plot ({fname})",
        )
    # GFC2020 is binary: forest pixel value >= 1, non-forest = 0.
    forest_pct = float((valid >= 1).sum()) / float(valid.size) * 100.0
    return JRCGFC2020Result(
        forest_2020=forest_pct >= _FOREST_BASELINE_PCT_THRESHOLD,
        forest_pct=round(forest_pct, 1),
        datasets_version=version_label(url),
        note=f"JRC GFC2020 pixel read inside plot polygon ({fname}, {int(valid.size)} px)",
    )
