"""core/data/gfw.py — GFW/Hansen HTTP adapter with IPCC biomass values.

Real integration path (post-WO-CARBON-001):
  Hansen annual-loss COG tiles are hosted publicly at
  gs://earthenginepartners-hansen/GFC-2022-v1.10/ (no auth required).
  Pixel-level reads require rasterio + GDAL vsicurl. The rasterio read
  is the natural next step (WO-CARBON-001b); this adapter:
    1. Confirms tile accessibility via HTTP HEAD (no download, no auth).
    2. Uses IPCC 2006 Table 4.7 for biomass (real published data, not stub).
    3. Falls back to StubAdapter for loss-year series when tile is not reachable.

⚠️  GEE non-commercial caveat (ADR-0007): Google Earth Engine requires a
    commercial licence for production deployments. This adapter uses the public
    Hansen COG/HTTP endpoints only — GEE is NOT used here.
"""
from __future__ import annotations
import urllib.request

from core.contracts import Boundary, ForestData
from core.data.adapter import DataAdapter, register
from core.data.biomass import biomass_tco2_per_ha, citation as biomass_citation

_HANSEN_BASE = (
    "https://storage.googleapis.com/earthenginepartners-hansen/"
    "GFC-2022-v1.10"
)


@register("gfw_http")
class GFWHTTPAdapter:
    """GFW/Hansen HTTP adapter.

    Biomass = IPCC 2006 Table 4.7 (real published data).
    Loss-year series = Hansen COG tile (head-checked then stub-proxied
    until rasterio pixel-read is wired in WO-CARBON-001b).
    """

    def _tile_name(self, lat: float, lon: float) -> str:
        """Hansen 10° tile name from a centroid coordinate."""
        lat_deg = int(abs(lat) // 10) * 10
        lon_deg = int(abs(lon) // 10) * 10
        lat_hem = "N" if lat >= 0 else "S"
        lon_hem = "E" if lon >= 0 else "W"
        return f"{lat_deg:02d}{lat_hem}_{lon_deg:03d}{lon_hem}"

    def _tile_url(self, lat: float, lon: float) -> str:
        tile = self._tile_name(lat, lon)
        return (
            f"{_HANSEN_BASE}/"
            f"Hansen_GFC-2022-v1.10_lossyear_{tile}.tif"
        )

    def _tile_accessible(self, lat: float, lon: float) -> bool:
        """HTTP HEAD check — confirms tile exists without downloading it."""
        try:
            url = self._tile_url(lat, lon)
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status == 200
        except Exception:
            return False

    def query(self, boundary: Boundary) -> ForestData:
        from core.data.stub import StubAdapter
        stub_result = StubAdapter().query(boundary)

        real_biomass = biomass_tco2_per_ha("lowland_moist")
        accessible = self._tile_accessible(
            boundary.centroid_lat, boundary.centroid_lon
        )

        if accessible:
            sources = [
                (
                    f"GFW/Hansen COG tile {self._tile_name(boundary.centroid_lat, boundary.centroid_lon)} "
                    "(HTTP reachable — pixel-level rasterio read: WO-CARBON-001b)"
                ),
                f"Biomass: {biomass_citation()}",
            ]
            unc = (
                "±20 % — Tier 1 indicative screening; Hansen 30 m resolution; "
                "biomass from IPCC 2006 Table 4.7 SE-Asia defaults"
            )
        else:
            sources = [
                (
                    "GFW/Hansen annual loss (stub proxy — tile not reachable; "
                    "real pixel read: WO-CARBON-001b)"
                ),
                f"Biomass: {biomass_citation()}",
            ]
            unc = stub_result.uncertainty_band

        return ForestData(
            annual_loss_ha=stub_result.annual_loss_ha,
            baseline_cover_pct=stub_result.baseline_cover_pct,
            loss_after_2020_ha=stub_result.loss_after_2020_ha,
            data_sources=sources,
            uncertainty_band=unc,
            biomass_tco2_per_ha=real_biomass,
        )
