"""core/data/gfw.py — GFW/Hansen HTTP adapter with real pixel-level loss and density reads.

WO-CARBON-001b: Hansen GFC-2022 annual-loss COG pixel read via rasterio/GDAL vsicurl
(public GCS, no auth). Tile-naming fix: tiles labeled by NORTH edge.

WO-CARBON-001c: ESA CCI Biomass v3.0 2018 (CEDA public, no auth) as the default density
source, replacing the blanket IPCC 657.1 tCO2/ha default. DENSITY_COG_URL env var
overrides to a custom ESA CCI / GEDI COG. Falls back to IPCC Tier-1 labeled default
when the COG read fails (network error, tile missing, etc.).

Both Hansen and ESA CCI use the NW-corner tile-naming convention:
  tile "10N_110E" / "N10E110" covers 0-10N, 110-120E (NW corner at 10N, 110E).

Hansen tile format: "{lat_deg:02d}{lat_hem}_{lon_deg:03d}{lon_hem}" e.g. "10N_110E"
ESA CCI tile format: "{lat_hem}{lat_deg:02d}{lon_hem}{lon_deg:03d}" e.g. "N10E110"

Fallback chain (density):
  1. DENSITY_COG_URL env var (point at custom ESA CCI / GEDI COG)
  2. ESA CCI Biomass v3.0 2018 — CEDA public endpoint (auto, no auth)
  3. IPCC 2006 Table 4.7 SE-Asia Tier-1 default (657.1 tCO2/ha, labeled)

Fallback chain (loss):
  1. Hansen GFC-2022 COG (real pixel read)
  2. StubAdapter (Point input, rasterio import error, or any read failure)

GEE caveat (ADR-0007): uses public HTTP endpoints only — GEE not used.
"""
from __future__ import annotations
import math

from core.contracts import Boundary, ForestData
from core.data.adapter import DataAdapter, register
from core.data.biomass import biomass_tco2_per_ha, citation as biomass_citation

_HANSEN_BASE = (
    "https://storage.googleapis.com/earthenginepartners-hansen/"
    "GFC-2022-v1.10"
)

# ESA CCI Biomass v3.0 2018 — CEDA public endpoint, no auth
# Tiles: 10x10 deg, NW-corner naming. Format: N10E110_ESACCI-BIOMASS-...-2018-fv3.0.tif
_ESA_CCI_BASE = (
    "https://dap.ceda.ac.uk/neodc/esacci/biomass/data/agb/maps/"
    "v3.0/geotiff/2018"
)
_ESA_CCI_VERSION = "fv3.0"
_ESA_CCI_YEAR = 2018

# GDAL environment for vsicurl HTTP reads
_GDAL_ENV = {
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_TIMEOUT": "30",
    "GDAL_HTTP_UNSAFESSL": "YES",
    "CPL_VSIL_CURL_CACHE_SIZE": "50000000",
}

# Hansen GFC-2022 covers loss years 1-22 (2001-2022)
_HANSEN_FIRST_YEAR = 2001
_HANSEN_LAST_YEAR = 2022


@register("gfw_http")
class GFWHTTPAdapter:
    """GFW/Hansen HTTP adapter.

    WO-CARBON-001b: real rasterio vsicurl pixel read replaces the stub proxy.
    WO-CARBON-001c: ESA CCI Biomass v3.0 2018 as default density; IPCC Tier-1 fallback.
    """

    # ── NW-edge tile helpers (shared convention: Hansen + ESA CCI) ────────────

    def _nw_lat_deg(self, lat: float) -> tuple[int, str]:
        """NW-corner latitude component: (degrees, N/S hemisphere char).

        Tiles cover 10 deg bands; labeled by their NORTH (NW-corner) edge.
        lat=0.9N  -> (10, 'N')  — tile covers 0-10N
        lat=-0.01 -> (0,  'N')  — tile covers 0 to -10 (north edge at 0N)
        lat=-10.5 -> (10, 'S')  — tile covers -10 to -20
        """
        if lat >= 0:
            deg = (int(lat // 10) + 1) * 10
            return deg, "N"
        else:
            deg = int((-lat) // 10) * 10
            hem = "N" if deg == 0 else "S"
            return deg, hem

    def _nw_lon_deg(self, lon: float) -> tuple[int, str]:
        deg = int(abs(lon) // 10) * 10
        hem = "E" if lon >= 0 else "W"
        return deg, hem

    def _hansen_tile_name(self, lat: float, lon: float) -> str:
        """Hansen GFC tile name: "{lat_deg:02d}{lat_hem}_{lon_deg:03d}{lon_hem}"."""
        lat_deg, lat_hem = self._nw_lat_deg(lat)
        lon_deg, lon_hem = self._nw_lon_deg(lon)
        return f"{lat_deg:02d}{lat_hem}_{lon_deg:03d}{lon_hem}"

    def _esa_cci_tile_name(self, lat: float, lon: float) -> str:
        """ESA CCI Biomass tile name: "{lat_hem}{lat_deg:02d}{lon_hem}{lon_deg:03d}"."""
        lat_deg, lat_hem = self._nw_lat_deg(lat)
        lon_deg, lon_hem = self._nw_lon_deg(lon)
        return f"{lat_hem}{lat_deg:02d}{lon_hem}{lon_deg:03d}"

    def _vsicurl(self, url: str) -> str:
        return f"/vsicurl/{url}"

    def _hansen_url(self, lat: float, lon: float) -> str:
        tile = self._hansen_tile_name(lat, lon)
        return f"{_HANSEN_BASE}/Hansen_GFC-2022-v1.10_lossyear_{tile}.tif"

    def _esa_cci_url(self, lat: float, lon: float) -> str:
        tile = self._esa_cci_tile_name(lat, lon)
        return (
            f"{_ESA_CCI_BASE}/"
            f"{tile}_ESACCI-BIOMASS-L4-AGB-MERGED-100m-"
            f"{_ESA_CCI_YEAR}-{_ESA_CCI_VERSION}.tif"
        )

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def _bbox_from_boundary(
        self, boundary: Boundary
    ) -> tuple[float, float, float, float] | None:
        """Extract (west, south, east, north) bbox. Returns None for Points."""
        geojson = boundary.geojson
        if geojson.get("type") == "Point":
            return None
        try:
            coords = geojson["coordinates"][0]
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            return min(lons), min(lats), max(lons), max(lats)
        except (KeyError, IndexError, TypeError):
            return None

    # ── AGB COG read (shared for Hansen + ESA CCI paths) ─────────────────────

    def _read_agb_cog(
        self, http_url: str, boundary: Boundary, treat_zero_as_nodata: bool = True
    ) -> float | None:
        """Read concession-mean AGB (t DM/ha) from a vsicurl COG.

        Returns None on:
          - Point input (no polygon bbox)
          - rasterio unavailable
          - network / tile error
          - all pixels masked / nodata
        """
        bbox = self._bbox_from_boundary(boundary)
        if bbox is None:
            return None
        west, south, east, north = bbox
        url = (
            http_url
            if http_url.startswith("/vsicurl/")
            else self._vsicurl(http_url)
        )
        try:
            import rasterio
            from rasterio.windows import from_bounds as _from_bounds
            import numpy as np

            with rasterio.Env(**_GDAL_ENV):
                with rasterio.open(url) as src:
                    window = _from_bounds(west, south, east, north, src.transform)
                    arr = src.read(1, window=window).astype("float64")
                    nodata = src.nodata
                    if nodata is not None:
                        arr[arr == nodata] = np.nan
                    if treat_zero_as_nodata:
                        arr[arr <= 0] = np.nan
                    if np.all(np.isnan(arr)):
                        return None
                    return float(np.nanmean(arr))
        except Exception:
            return None

    # ── Hansen annual-loss pixel read ─────────────────────────────────────────

    def _query_annual_loss(
        self, boundary: Boundary
    ) -> tuple[dict[int, float], list[str], str]:
        """Real Hansen GFC-2022 pixel read or stub fallback.

        Returns (annual_loss_ha, source_labels, uncertainty_string).
        """
        bbox = self._bbox_from_boundary(boundary)
        if bbox is None:
            return self._stub_fallback(boundary, "Point input — no pixel window to read")

        west, south, east, north = bbox
        tile = self._hansen_tile_name(boundary.centroid_lat, boundary.centroid_lon)
        url = self._vsicurl(self._hansen_url(boundary.centroid_lat, boundary.centroid_lon))

        try:
            import rasterio
            from rasterio.windows import from_bounds as _from_bounds
            import numpy as np

            with rasterio.Env(**_GDAL_ENV):
                with rasterio.open(url) as src:
                    window = _from_bounds(west, south, east, north, src.transform)
                    arr = src.read(1, window=window)
                    win_transform = src.window_transform(window)

                    x_res = abs(win_transform.a)
                    y_res = abs(win_transform.e)
                    lat_rad = math.radians(boundary.centroid_lat)
                    x_m = x_res * 111320.0 * math.cos(lat_rad)
                    y_m = y_res * 111320.0
                    pixel_area_ha = (x_m * y_m) / 10000.0

                    annual_loss: dict[int, float] = {}
                    for year_val in range(1, _HANSEN_LAST_YEAR - 1999):
                        count = int((arr == year_val).sum())
                        annual_loss[_HANSEN_FIRST_YEAR + year_val - 1] = round(
                            count * pixel_area_ha, 2
                        )

            sources = [
                f"GFW/Hansen GFC-2022-v1.10 lossyear pixel read "
                f"(tile {tile}, 30 m, public GCS, no auth)"
            ]
            unc = (
                f"Tier 1 indicative screening — Hansen GFC-2022-v1.10 pixel loss rate "
                f"(30 m, tile {tile}); baseline harvest rate from IUP permit not yet "
                f"verified — dominant uncertainty. Not registry-grade."
            )
            return annual_loss, sources, unc

        except Exception as exc:
            return self._stub_fallback(
                boundary, f"{type(exc).__name__}: {exc}"
            )

    def _stub_fallback(
        self, boundary: Boundary, reason: str
    ) -> tuple[dict[int, float], list[str], str]:
        from core.data.stub import StubAdapter
        stub = StubAdapter().query(boundary)
        sources = [
            f"GFW/Hansen annual loss (stub proxy — real pixel read failed: {reason})"
        ]
        return stub.annual_loss_ha, sources, stub.uncertainty_band

    # ── Density: ESA CCI -> IPCC fallback ────────────────────────────────────

    def _query_density(self, boundary: Boundary) -> tuple[float, str]:
        """Concession-mean carbon density in tCO2/ha.

        Fallback chain:
          1. DENSITY_COG_URL env var (custom ESA CCI / GEDI COG override)
          2. ESA CCI Biomass v3.0 2018 — CEDA public, no auth (auto)
          3. IPCC 2006 Table 4.7 SE-Asia Tier-1 default (657.1 tCO2/ha)
        """
        import os

        # 1 — custom override
        density_url = os.environ.get("DENSITY_COG_URL", "").strip()
        if density_url:
            agb = self._read_agb_cog(density_url, boundary)
            if agb is not None and agb > 0:
                biomass = round(agb * 0.47 * (44.0 / 12.0), 1)
                source = (
                    f"ESA CCI / GEDI AGB (DENSITY_COG_URL override; "
                    f"concession mean {agb:.0f} tDM/ha -> {biomass:.0f} tCO2/ha)"
                )
                return biomass, source

        # 2 — ESA CCI Biomass v3.0 2018 (auto, no auth)
        esa_url = self._esa_cci_url(boundary.centroid_lat, boundary.centroid_lon)
        esa_tile = self._esa_cci_tile_name(boundary.centroid_lat, boundary.centroid_lon)
        agb = self._read_agb_cog(esa_url, boundary)
        if agb is not None and agb > 0:
            biomass = round(agb * 0.47 * (44.0 / 12.0), 1)
            source = (
                f"ESA CCI Biomass v3.0 2018 (CEDA public, tile {esa_tile}, "
                f"100 m; concession mean {agb:.0f} tDM/ha -> {biomass:.0f} tCO2/ha)"
            )
            return biomass, source

        # 3 — IPCC Tier-1 fallback
        value = biomass_tco2_per_ha("lowland_moist")
        source = (
            f"Biomass: {biomass_citation()} "
            f"— Tier-1 fallback (ESA CCI read failed; set DENSITY_COG_URL to override)"
        )
        return value, source

    # ── Main query ────────────────────────────────────────────────────────────

    def query(self, boundary: Boundary) -> ForestData:
        """Query forest data: real Hansen pixel loss + ESA CCI / IPCC density."""
        annual_loss, loss_sources, loss_unc = self._query_annual_loss(boundary)

        # Baseline tree cover from stub (treecover2000 COG read: WO-CARBON-001c)
        from core.data.stub import StubAdapter
        baseline_pct = StubAdapter().query(boundary).baseline_cover_pct

        loss_after_2020 = sum(v for yr, v in annual_loss.items() if yr >= 2021)

        biomass, density_source = self._query_density(boundary)

        return ForestData(
            annual_loss_ha=annual_loss,
            baseline_cover_pct=baseline_pct,
            loss_after_2020_ha=round(loss_after_2020, 2),
            data_sources=loss_sources + [density_source],
            uncertainty_band=loss_unc,
            biomass_tco2_per_ha=biomass,
        )
