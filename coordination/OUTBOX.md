# OUTBOX — Builder → Cowork · WO-EUDR-EXPORT-008 (E6) · 2026-06-30

## Status: CI GREEN ✅ — 438 tests pass (+12 new E6 tests) — STOPPED for Cowork review

Art-9 GeoJSON geolocation pack export added to `POST /api/eudr` response + frontend download button.

---

## What shipped

### `api/main.py` — new helpers + `geolocation_pack_geojson` response field

**`_round_coords()` / `_round_geojson_coords()`**
Recursively round all GeoJSON coordinate values to ≥6 decimal places. Handles nested lists (Polygon, MultiPolygon, etc.). Never rounds below 6.

**`_build_geolocation_pack(validations, plot_verdicts, commodity, producer_name, run_date)`**
Returns an Art-9 GeoJSON FeatureCollection:
- `geometry_invalid` plots **excluded** (Art-9 non-conforming — cannot enter a DDS)
- Area >4 ha → **Polygon** geometry (rounded to ≥6dp)
- Area ≤4 ha → **Point** geometry (centroid, rounded to ≥6dp)
- Properties: `plot_id`, `commodity`, `detection`, `area_ha`, `producer_name`, `run_date`, `pack_note`
- `pack_note`: "Screened against JRC GFC2020 + Hansen + RADD. Not a Due Diligence Statement. Geolocation pack for DDS preparation." (no banned strings)

**`geolocation_pack_geojson`** key added to `POST /api/eudr` response body (dict, not a separate endpoint — avoids re-running triage).

### `frontend/index.html` — download button + JS

New card above the readiness checklist: "Download your geolocation pack (GeoJSON)"

Copy (verbatim — no banned strings):
> "Your plot coordinates formatted for the EU's system — a geolocation pack for **DDS preparation**. The DDS itself is filed in TRACES by the operator placing on the EU market."

**`downloadGeopack()`** JS function:
- Reads `_eudrResult.geolocation_pack_geojson` (cached from the triage response)
- Guards: no result → message; empty features → message (all plots had geometry errors)
- Creates `Blob` → `URL.createObjectURL` → triggers `<a download>` click
- Filename: `180climate_geolocation_pack_{YYMMDDHHMM}.geojson`
- Shows plot count in status line after download

---

## API smoke

```
2-plot batch (1 loss + 1 clear), palm:
  geolocation_pack_geojson.type = FeatureCollection
  features: 2

  plot_loss    det=loss_detected     area=492.29 ha  geom=Polygon
    first coord: lon=112.989999 lat=-1.009999  (6dp ✓)
  plot_clear   det=clear_in_screen   area=492.07 ha  geom=Polygon
    first coord: lon=113.989999 lat=-2.009999  (6dp ✓)
```

---

## Tests — `tests/test_eudr_api.py` (12 new E6 tests)

| Test | Assertion |
|---|---|
| `test_geolocation_pack_field_present` | field present, type=FeatureCollection |
| `test_geolocation_pack_is_valid_feature_collection` | 2-plot batch → 2 features, each Feature+geometry+properties |
| `test_geolocation_pack_properties_present` | plot_id, commodity, detection, area_ha, producer_name |
| `test_geolocation_pack_commodity_matches` | commodity=timber → properties.commodity=timber |
| `test_geolocation_pack_detection_matches_triage` | pack detection == plots[0].detection |
| `test_geolocation_pack_large_plot_is_polygon` | >4 ha plot → Polygon geometry |
| `test_geolocation_pack_small_plot_is_point` | tiny plot (≤4 ha) → Point geometry with [lon, lat] floats |
| `test_geolocation_pack_at_least_6_decimal_places` | all Polygon coord values: round(v, 6) == v |
| `test_geolocation_pack_point_has_6_decimal_places` | centroid coords at 6dp |
| `test_geolocation_pack_excludes_geometry_invalid` | _POLY_BADGEO → 0 features in pack |
| `test_geolocation_pack_mixed_batch_excludes_invalid` | valid + invalid → only valid in pack |
| `test_geolocation_pack_no_banned_strings` | none of the 4 banned substrings in pack JSON |

---

## OPEN ITEM (flagged for John)

**Live TRACES uploader validation** — whether this GeoJSON file loads correctly into the **EU TRACES EUDR module** cannot be tested here. This is a **pre-launch check for John + legal**:
1. Download a sample geolocation pack from the deployed app (using real Indonesian plot coordinates at ≥6dp)
2. Attempt to import it in the TRACES EUDR pilot environment (available to EU operators)
3. Verify that the FeatureCollection → per-plot mapping is accepted
4. If TRACES requires a specific schema (e.g., ISO-19115 metadata, specific property names), adjust `_build_geolocation_pack()` accordingly

The current format follows the Art-9 requirements as published in the regulation: polygon for >4 ha, point for ≤4 ha, WGS84/EPSG:4326, ≥6 decimal coordinates. Schema adjustment is a one-function edit if TRACES expects different property names.

---

## mypy + pytest

```
mypy core/contracts/__init__.py --ignore-missing-imports → Success: no issues found
pytest tests/ → 438 passed, 1 warning (was 426; +12 new E6 tests)
```
