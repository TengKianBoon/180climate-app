"""core/overlays/hansen_loss.py — Hansen GFC lossyear post-cutoff loss for EUDR triage (ADR-0018, E3).

Reads the CURRENT Hansen/UMD Global Forest Change release (default GFC-2025-v1.13, loss years
2001-2025; 30 m, public GCS, no auth) directly, measuring loss INSIDE the plot polygon.

The EUDR read is separate from the Carbon scenario adapter, so a failed data read is returned
as unavailable rather than a loss-rate proxy. Both adapters now use the 2025 release. The
EUDR release is configurable via HANSEN_GFC_VERSION, with outdated releases rejected. Uses the
carbon-overlay contract: fixture-cache first (CI-safe) + `HANSEN_LOSS_DISABLE_LIVE` kill-switch + version
stamp + an honest "unavailable" (None) signal when the real read fails.

Post-cutoff loss = Hansen lossyear pixels with year > cutoff_year (EUDR cutoff = 2020),
summed to hectares, intersecting the plot.

Env HANSEN_LOSS_DISABLE_LIVE=true: skip the live pixel read (CI kill-switch) — returns
  loss_after_2020_ha=None (unavailable) unless a fixture is present.

Honesty rule (EUDR, value-first): a stub/proxy fallback is NOT a real read — when the real
pixel read fails, loss_after_2020_ha is None (unavailable), which the triage engine maps to
`inconclusive`, NEVER `clear_in_screen`.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from core.contracts import Boundary
from core.overlays._cache import load_fixture

log = logging.getLogger(__name__)

_ADAPTER = "hansen_loss"
_HANSEN_BUCKET = "https://storage.googleapis.com/earthenginepartners-hansen"
# Bump when UMD publishes a new release (annually, ~Apr-May). Override: HANSEN_GFC_VERSION.
_DEFAULT_VERSION = "GFC-2025-v1.13"


def _version() -> str:
    return os.environ.get("HANSEN_GFC_VERSION", "").strip() or _DEFAULT_VERSION


def _last_loss_year(version: str) -> int:
    """'GFC-2025-v1.13' -> 2025 (the final loss year covered by that release)."""
    match = re.fullmatch(r"GFC-(20\d{2})-v\d+\.\d+", version)
    if not match or int(match.group(1)) < 2025:
        raise ValueError("Hansen release must cover at least 2025")
    return int(match.group(1))


def _label(version: str) -> str:
    return f"Hansen {version} lossyear (30m, loss to {_last_loss_year(version)})"


_SOURCE = f"GFW/Hansen {_DEFAULT_VERSION} lossyear (30 m, public GCS, no auth)"
_DATASETS_VERSION = _label(_DEFAULT_VERSION)

# EUDR cutoff: deforestation after 31 Dec 2020 is in scope → lossyear strictly > 2020.
_DEFAULT_CUTOFF_YEAR = 2020


@dataclass
class HansenLossResult:
    """Post-cutoff Hansen forest loss intersecting a plot.

    loss_after_2020_ha is None when the real pixel read is unavailable (Point input,
    rasterio missing, network/tile error, or stub fallback) — NEVER a fabricated zero.
    """

    loss_after_2020_ha: Optional[float]   # None = unavailable (NOT a confirmed zero)
    source: str = _SOURCE
    datasets_version: str = _DATASETS_VERSION
    note: str = ""

    @property
    def available(self) -> bool:
        return self.loss_after_2020_ha is not None

    @property
    def has_post_cutoff_loss(self) -> Optional[bool]:
        """True/False if a real read exists; None if unavailable (cannot assert)."""
        if self.loss_after_2020_ha is None:
            return None
        return self.loss_after_2020_ha > 0.0


def query_hansen_loss(
    boundary: Boundary, cutoff_year: int = _DEFAULT_CUTOFF_YEAR
) -> HansenLossResult:
    """Return post-cutoff Hansen loss (ha) intersecting the plot.

    Fixture cache first (CI-safe). Live pixel read via GFWHTTPAdapter unless disabled.
    Returns loss_after_2020_ha=None on any failure — the triage engine treats None as
    inconclusive (never clear).
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        return HansenLossResult(
            loss_after_2020_ha=cached.get("loss_after_2020_ha"),
            source=_SOURCE,
            datasets_version=cached.get("datasets_version", _DATASETS_VERSION),
            note=cached.get("note", "fixture"),
        )

    if os.environ.get("HANSEN_LOSS_DISABLE_LIVE", "").lower() == "true":
        return HansenLossResult(
            loss_after_2020_ha=None,
            note="Hansen live read disabled (HANSEN_LOSS_DISABLE_LIVE=true); no fixture",
        )

    return _query_live(boundary, cutoff_year)


def _query_live(boundary: Boundary, cutoff_year: int) -> HansenLossResult:
    """Real pixel read of the current Hansen lossyear tile, restricted to the plot polygon."""
    version = _version()
    try:
        last_year = _last_loss_year(version)
        import math

        import numpy as np
        import rasterio
        from rasterio.windows import from_bounds as _from_bounds

        from core.data.gfw import GFWHTTPAdapter, _GDAL_ENV
        from core.overlays._mask import inside_mask

        gfw = GFWHTTPAdapter()
        bbox = gfw._bbox_from_boundary(boundary)
        if bbox is None:
            return HansenLossResult(
                loss_after_2020_ha=None,
                datasets_version=_label(version),
                note="Point input — no pixel window to read; unavailable",
            )
        tile = gfw._hansen_tile_name(boundary.centroid_lat, boundary.centroid_lon)
        url = f"{_HANSEN_BUCKET}/{version}/Hansen_{version}_lossyear_{tile}.tif"
        west, south, east, north = bbox
        with rasterio.Env(**_GDAL_ENV):
            with rasterio.open(gfw._vsicurl(url)) as src:
                window = _from_bounds(west, south, east, north, src.transform)
                if window.width * window.height > 12_000_000:
                    raise ValueError('Plot window too large; split the plot')
                if west < src.bounds.left or east > src.bounds.right or south < src.bounds.bottom or north > src.bounds.top:
                    raise ValueError('Plot crosses a Hansen tile; split the plot')
                arr = src.read(1, window=window, masked=True)
                wt = src.window_transform(window)
        inside = inside_mask(boundary.geojson, arr.shape, wt)
        if not inside.any() or bool(np.ma.getmaskarray(arr)[inside].any()):
            raise ValueError('Plot is below raster resolution or includes unavailable pixels')
        arr = arr.filled(255)
        lat_rad = math.radians(boundary.centroid_lat)
        pixel_area_ha = (abs(wt.a) * 111320.0 * math.cos(lat_rad)) * (abs(wt.e) * 111320.0) / 1e4
        first_code = cutoff_year - 2000 + 1          # 2021 -> 21
        last_code = last_year - 2000                 # 2025 -> 25
        post = inside & (arr >= first_code) & (arr <= last_code)
        loss_ha = float(post.sum()) * pixel_area_ha
        years = sorted({int(v) + 2000 for v in np.unique(arr[post])})
    except Exception as exc:
        log.error("Hansen loss live read failed (%s): %s", version, exc)
        return HansenLossResult(
            loss_after_2020_ha=None,
            datasets_version=f"Hansen {version} unavailable",
            note=f"Hansen read error: {type(exc).__name__}: {exc}; unavailable",
        )

    return HansenLossResult(
        loss_after_2020_ha=round(loss_ha, 2),
        source=f"GFW/Hansen {version} lossyear (tile {tile}, 30 m, public GCS, no auth)",
        datasets_version=_label(version),
        note=(
            f"post-{cutoff_year} loss inside plot, {cutoff_year + 1}-{last_year}"
            + (f"; loss years: {', '.join(map(str, years))}" if years else "; none found")
        ),
    )
