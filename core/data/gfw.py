"""core/data/gfw.py — GFW/Hansen HTTP adapter with real pixel-level loss read.

WO-CARBON-001b: implements Hansen GFC-2022 annual-loss COG pixel read via
rasterio/GDAL vsicurl (public GCS, no auth). Replaces the stub proxy for
loss-year series. Falls back to StubAdapter on rasterio import error or
any network/tile failure.

Biomass density: tries DENSITY_COG_URL env var (point to ESA CCI Biomass
or GEDI L4 COG); falls back to IPCC 2006 Table 4.7 SE-Asia default
(657.1 tCO2/ha) with a labeled source string when unavailable.

Tile-naming fix (WO-CARBON-001b): Hansen tiles are labeled by their NORTH
edge. Tile "10N_110E" has north edge 10°N, covers 0–10°N; "00N_110E" has
north edge 0°N, covers 0°S–10°S. The v1.0 code was returning "00S" for
southern points which does not exist in the Hansen bucket.

⚠️  GEE non-commercial caveat (ADR-0007): uses public Hansen COG HTTP
    endpoints only — Google Earth Engine is NOT used here.
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

# GDAL environment for vsicurl HTTP reads
_GDAL_ENV = {
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_TIMEOUT": "30",
    "GDAL_HTTP_UNSAFESSL": "YES",       # Bypass Windows/corp SSL chain issues
    "CPL_VSIL_CURL_CACHE_SIZE": "50000000",  # 50 MB block cache
}

# Hansen GFC-2022 covers loss years 1-22 (2001-2022)
_HANSEN_FIRST_YEAR = 2001
_HANSEN_LAST_YEAR = 2022


@register("gfw_http")
class GFWHTTPAdapter:
    """GFW/Hansen HTTP adapter.

    WO-CARBON-001b: real rasterio vsicurl pixel read replaces the stub proxy.
    Biomass = IPCC 2006 Table 4.7 default (657.1 tCO2/ha) with DENSITY_COG_URL
    override for ESA CCI Biomass or GEDI L4 COGs.
    """

    # ── Tile helpers ──────────────────────────────────────────────────────────

    def _tile_name(self, lat: float, lon: float) -> str:
        """Hansen 10° tile name from a centroid coordinate.

        Hansen tiles are labeled by their NORTH edge:
          'XN_YYYYYY' → north edge at X°N, tile covers X°N to (X-10)°N
          '00N_YYY'   → north edge at 0°N, tile covers 0°S to 10°S (≡ lat 0 to -10)
          'XS_YYY'    → north edge at X°S, tile covers X°S to (X+10)°S

        Examples:
          lat=0.9°N  → tile '10N_110E' (covers 0–10°N)
          lat=-0.015 → tile '00N_110E' (covers 0 to -10°)
          lat=-10.5  → tile '10S_110E' (covers -10 to -20°)
        """
        lon_deg = int(abs(lon) // 10) * 10
        lon_hem = "E" if lon >= 0 else "W"

        if lat >= 0:
            # Northern hemisphere: north edge = ceil(lat to next 10°)
            lat_deg = (int(lat // 10) + 1) * 10
            lat_hem = "N"
        else:
            # Southern hemisphere / south-of-equator: north edge = floor of abs(lat) to 10°
            lat_deg = int((-lat) // 10) * 10
            lat_hem = "N" if lat_deg == 0 else "S"

        return f"{lat_deg:02d}{lat_hem}_{lon_deg:03d}{lon_hem}"

    def _tile_url(self, lat: float, lon: float) -> str:
        tile = self._tile_name(lat, lon)
        return f"{_HANSEN_BASE}/Hansen_GFC-2022-v1.10_lossyear_{tile}.tif"

    def _vsicurl(self, url: str) -> str:
        return f"/vsicurl/{url}"

    # ── Hansen pixel loss read ────────────────────────────────────────────────

    def _bbox_from_boundary(self, boundary: Boundary) -> tuple[float, float, float, float] | None:
        """Extract (west, south, east, north) bbox from boundary.geojson.

        Returns None for Point geometries — pixel-window reads require a Polygon.
        """
        geojson = boundary.geojson
        if geojson.get("type") == "Point":
            return None
        try:
            coords = geojson["coordinates"][0]  # outer ring of Polygon
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            return min(lons), min(lats), max(lons), max(lats)
        except (KeyError, IndexError, TypeError):
            return None

    def _query_annual_loss(
        self, boundary: Boundary
    ) -> tuple[dict[int, float], list[str], str]:
        """Real Hansen GFC-2022 pixel read or stub fallback.

        Returns (annual_loss_ha, source_labels, uncertainty_string).
        Falls back to StubAdapter when:
          - geojson is a Point (no polygon to clip)
          - rasterio not available
          - tile not reachable / any read error
        """
        bbox = self._bbox_from_boundary(boundary)
        if bbox is None:
            return self._stub_fallback(boundary, "Point input — no pixel window to read")

        west, south, east, north = bbox
        tile = self._tile_name(boundary.centroid_lat, boundary.centroid_lon)
        url = self._vsicurl(self._tile_url(boundary.centroid_lat, boundary.centroid_lon))

        try:
            import rasterio
            from rasterio.windows import from_bounds as _from_bounds
            import numpy as np  # noqa: F401 — ensures numpy available for arr ops

            with rasterio.Env(**_GDAL_ENV):
                with rasterio.open(url) as src:
                    window = _from_bounds(west, south, east, north, src.transform)
                    arr = src.read(1, window=window)
                    win_transform = src.window_transform(window)

                    # Pixel area in ha: x_m × y_m / 10000 with latitude correction
                    x_res = abs(win_transform.a)   # degrees/pixel (x)
                    y_res = abs(win_transform.e)   # degrees/pixel (y)
                    lat_rad = math.radians(boundary.centroid_lat)
                    x_m = x_res * 111320.0 * math.cos(lat_rad)
                    y_m = y_res * 111320.0
                    pixel_area_ha = (x_m * y_m) / 10000.0

                    annual_loss: dict[int, float] = {}
                    for year_val in range(1, _HANSEN_LAST_YEAR - 1999):  # 1-22
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

    # ── Density read (ESA CCI / GEDI → IPCC fallback) ────────────────────────

    def _query_density(self, boundary: Boundary) -> tuple[float, str]:
        """ESA CCI Biomass or GEDI density read; falls back to IPCC 2006 Table 4.7.

        Configure DENSITY_COG_URL to point at an ESA CCI Biomass or GEDI L4B
        COG (HTTP or vsicurl URL). The COG must contain AGB in t/ha dry mass.
        Falls back to IPCC 657.1 tCO2/ha when the env var is unset or the
        read fails.
        """
        import os
        density_url = os.environ.get("DENSITY_COG_URL", "").strip()

        if density_url:
            bbox = self._bbox_from_boundary(boundary)
            if bbox is not None:
                try:
                    import rasterio
                    from rasterio.windows import from_bounds as _from_bounds
                    import numpy as np

                    url = (
                        density_url
                        if density_url.startswith("/vsicurl/")
                        else self._vsicurl(density_url)
                    )
                    west, south, east, north = bbox
                    with rasterio.Env(**_GDAL_ENV):
                        with rasterio.open(url) as src:
                            window = _from_bounds(
                                west, south, east, north, src.transform
                            )
                            arr = src.read(1, window=window).astype("float64")
                            nodata = src.nodata
                            if nodata is not None:
                                arr[arr == nodata] = np.nan
                            agb_mean = float(np.nanmean(arr))
                            if not (agb_mean > 0):
                                raise ValueError(
                                    f"No valid AGB pixels (mean={agb_mean:.2f})"
                                )
                    # AGB t/ha dry mass → tCO2/ha: × CF(0.47) × (44/12)
                    biomass = round(agb_mean * 0.47 * (44.0 / 12.0), 1)
                    source = (
                        f"ESA CCI / GEDI AGB (DENSITY_COG_URL; "
                        f"concession mean {agb_mean:.0f} t/ha → {biomass:.0f} tCO2/ha)"
                    )
                    return biomass, source
                except Exception:
                    pass  # fall through to IPCC default

        # IPCC 2006 Table 4.7 Tier-1 fallback
        value = biomass_tco2_per_ha("lowland_moist")
        source = (
            f"Biomass: {biomass_citation()} "
            f"— Tier-1 fallback (set DENSITY_COG_URL to enable ESA CCI / GEDI read)"
        )
        return value, source

    # ── Main query ────────────────────────────────────────────────────────────

    def query(self, boundary: Boundary) -> ForestData:
        """Query forest data: real Hansen pixel loss + IPCC/ESA density."""
        annual_loss, loss_sources, loss_unc = self._query_annual_loss(boundary)

        # Baseline tree cover from stub (treecover2000 COG read: WO-CARBON-001c)
        from core.data.stub import StubAdapter
        baseline_pct = StubAdapter().query(boundary).baseline_cover_pct

        # Loss after 2020 (for EUDR cutoff verdict)
        loss_after_2020 = sum(v for yr, v in annual_loss.items() if yr >= 2021)

        # Biomass density
        biomass, density_source = self._query_density(boundary)

        return ForestData(
            annual_loss_ha=annual_loss,
            baseline_cover_pct=baseline_pct,
            loss_after_2020_ha=round(loss_after_2020, 2),
            data_sources=loss_sources + [density_source],
            uncertainty_band=loss_unc,
            biomass_tco2_per_ha=biomass,
        )
