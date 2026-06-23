# Skill: geospatial

Shared geospatial core patterns for 180climate-app. Use when writing or reviewing code in `core/` that handles geometry, forest queries, or map overlays.

## Key contracts
- `GeoInput` — raw geometry as supplied by the user (coords / geojson / shapefile)
- `Boundary` — parsed, validated geometry (GeoJSON, area_ha, centroid, is_valid, within_indonesia)
- `ForestData` — free-tier satellite outputs (annual_loss_ha, baseline_cover_pct, loss_after_2020_ha, data_sources, uncertainty_band)
- `MapOverlay` — base tiles + boundary + loss overlay + optional plots

## Data sources (free tier, swappable — ADR-0007)
- **Forest loss:** GFW/Hansen annual loss tiles
- **EUDR baseline:** JRC Global Forest Cover 2020 (loss_after_2020_ha)
- **Alerts:** RADD (near-real-time)
- **Biomass proxy:** ESA CCI Biomass / JAXA
- **Land cover:** ESA WorldCover
- **Peat:** CIFOR/Wetlands International peat maps
- **DEM:** SRTM

⚠️ GEE is **non-commercial only** — flag in README and ADR-0007. Prefer self-hosted COGs / free APIs for production.

## Geometry rules
- Carbon: polygon required; minimum 20,000 ha (CarbonGates.min_area_ha).
- EUDR: polygon required if > 4 ha; point allowed if ≤ 4 ha; no minimum size gate.
- Always normalise to EPSG:4326.
- `within_indonesia` must be validated before any engine computation.

## Uncertainty
Always populate `ForestData.uncertainty_band` with a human-readable string (e.g. "±15% — free satellite, Tier 1 screening"). Never leave it empty.
