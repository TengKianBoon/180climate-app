"""core/forest.py — deterministic GFW forest-loss stub for the WO-001 slice.

IMPORTANT: This is a STUB. Real GFW/Hansen + JRC GFC2020 integration is WO-CARBON-001.
The stub produces deterministic outputs based on the boundary centroid so tests pass
reliably. Values are realistic in magnitude but not geographically accurate.

Determinism invariant: same centroid_lat + centroid_lon → same ForestData every time.
"""
from __future__ import annotations
import math
from core.contracts import Boundary, ForestData


def _seed(lat: float, lon: float) -> float:
    """Deterministic pseudo-random seed from coordinates. Range 0–1."""
    x = math.sin(lat * 12.9898 + lon * 78.233) * 43758.5453
    return x - math.floor(x)


def query_forest_data(boundary: Boundary) -> ForestData:
    """Return a deterministic ForestData for the given boundary (stub).

    Real implementation will query GFW Hansen tiles and JRC GFC2020 via
    free-tier COG endpoints. This stub is replaced in WO-CARBON-001.
    """
    s = _seed(boundary.centroid_lat, boundary.centroid_lon)

    # Baseline cover 60–90 % (deterministic from coords)
    baseline_pct = 60.0 + s * 30.0

    # Annual loss: ~0.3–1.5 % of area per year, 2001–2023
    area = max(boundary.area_ha, 25_000.0)  # use floor so points get realistic data
    annual_rate = 0.003 + s * 0.012  # 0.3–1.5 %
    annual_loss: dict[int, float] = {}
    cumulative = 0.0
    for year in range(2001, 2024):
        # Slight upward trend + year-specific jitter (still deterministic)
        jitter_seed = _seed(boundary.centroid_lat + year * 0.01, boundary.centroid_lon)
        loss = area * (annual_rate + (year - 2001) * 0.00005 + jitter_seed * 0.001)
        annual_loss[year] = round(loss, 2)
        if year >= 2021:
            cumulative += loss

    return ForestData(
        annual_loss_ha=annual_loss,
        baseline_cover_pct=round(baseline_pct, 1),
        loss_after_2020_ha=round(cumulative, 2),
        data_sources=["GFW/Hansen (stub — WO-CARBON-001 wires real data)", "JRC GFC2020 (stub)"],
        uncertainty_band="±25 % — deterministic stub; Tier 1 screening once real data wired",
        biomass_tco2_per_ha=round(150.0 + s * 100.0, 1),  # 150–250 tCO₂/ha proxy
    )
