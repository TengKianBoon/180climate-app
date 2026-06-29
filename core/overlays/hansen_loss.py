"""core/overlays/hansen_loss.py — Hansen GFC lossyear post-cutoff loss for EUDR triage (ADR-0018, E3).

REUSES core/data/gfw.py `GFWHTTPAdapter` for the real rasterio/vsicurl pixel read of the
Hansen GFC-2022 lossyear COG (30 m, public GCS, no auth). Wraps it in the carbon-overlay
contract: fixture-cache first (CI-safe) + `HANSEN_LOSS_DISABLE_LIVE` kill-switch + version
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
from dataclasses import dataclass
from typing import Optional

from core.contracts import Boundary
from core.overlays._cache import load_fixture

log = logging.getLogger(__name__)

_ADAPTER = "hansen_loss"
_SOURCE = "GFW/Hansen GFC-2022-v1.10 lossyear (30 m, public GCS, no auth)"
_DATASETS_VERSION = "Hansen GFC-2022-v1.10 lossyear (30m)"

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
    """Real Hansen pixel read via the carbon GFWHTTPAdapter (reuse, no duplication)."""
    try:
        from core.data.gfw import GFWHTTPAdapter
    except Exception as exc:  # pragma: no cover — import guard
        return HansenLossResult(
            loss_after_2020_ha=None,
            note=f"Hansen adapter import failed: {type(exc).__name__}: {exc}",
        )

    try:
        annual_loss, sources, _unc = GFWHTTPAdapter()._query_annual_loss(boundary)
    except Exception as exc:
        log.warning("Hansen loss live read failed: %s", exc)
        return HansenLossResult(
            loss_after_2020_ha=None,
            note=f"Hansen read error: {type(exc).__name__}: {exc}; unavailable",
        )

    # The carbon adapter falls back to a StubAdapter proxy on read failure — that is NOT a
    # real read and must not be trusted as a confirmed loss/no-loss. Detect and treat as None.
    if any("stub" in s.lower() for s in sources):
        return HansenLossResult(
            loss_after_2020_ha=None,
            note="Hansen real pixel read unavailable (stub fallback); unavailable",
        )

    loss = sum(v for yr, v in annual_loss.items() if yr > cutoff_year)
    return HansenLossResult(
        loss_after_2020_ha=round(float(loss), 2),
        source="; ".join(sources) if sources else _SOURCE,
        note=f"post-{cutoff_year} loss from Hansen lossyear pixel read",
    )
