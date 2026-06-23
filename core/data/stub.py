"""core/data/stub.py — deterministic stub adapter (CI / offline fallback).

Preserves the original core/forest.py stub logic, now registered as a
proper DataAdapter so it can be explicitly selected or swapped out.
"""
from __future__ import annotations
import math
from core.contracts import Boundary, ForestData
from core.data.adapter import DataAdapter, register
from core.data.biomass import biomass_tco2_per_ha, citation as biomass_citation


@register("stub")
class StubAdapter:
    """Deterministic stub — same centroid → same ForestData every time.

    Not real satellite data. Used for CI, offline dev, and as the final
    fallback when all real adapters fail.
    """

    def query(self, boundary: Boundary) -> ForestData:
        s = self._seed(boundary.centroid_lat, boundary.centroid_lon)
        baseline_pct = 60.0 + s * 30.0
        area = max(boundary.area_ha, 25_000.0)
        annual_rate = 0.003 + s * 0.012
        annual_loss: dict[int, float] = {}
        cumulative = 0.0
        for year in range(2001, 2024):
            js = self._seed(boundary.centroid_lat + year * 0.01, boundary.centroid_lon)
            loss = area * (annual_rate + (year - 2001) * 0.00005 + js * 0.001)
            annual_loss[year] = round(loss, 2)
            if year >= 2021:
                cumulative += loss
        return ForestData(
            annual_loss_ha=annual_loss,
            baseline_cover_pct=round(baseline_pct, 1),
            loss_after_2020_ha=round(cumulative, 2),
            data_sources=[
                "GFW/Hansen annual loss (stub — offline/CI mode)",
                f"Biomass: {biomass_citation()}",
            ],
            uncertainty_band=(
                "±25 % — deterministic stub; Tier 1 indicative screening "
                "once real satellite data is wired"
            ),
            biomass_tco2_per_ha=biomass_tco2_per_ha("lowland_moist"),
        )

    @staticmethod
    def _seed(lat: float, lon: float) -> float:
        """Deterministic hash in [0, 1). Classic GLSL-style sin hash."""
        x = math.sin(lat * 12.9898 + lon * 78.233) * 43758.5453
        return x - math.floor(x)
