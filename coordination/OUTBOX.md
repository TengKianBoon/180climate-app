# OUTBOX — Builder -> Cowork · WO-EUDR-MAP-017 · 2026-07-01

## Status: CI GREEN -- 457 tests pass -- STOPPED for Cowork review

Frontend-only presentation + api number-format nicety. No contract change. No gate.

---

## What shipped (commit 754f6bd)

### 1. Leaflet satellite map on the EUDR result screen

`frontend/index.html` — new `<div id="eudr-map" style="height:340px;border-radius:10px">` panel
under heading "Your plots on the map", placed between the per-plot table and "What to do next".

`initEudrMap(r)` function:
- Destroys prior `_eudrMap` instance on re-run (clean re-render).
- Guards: returns silently if `geolocation_pack_geojson` is absent or has 0 features.
- Basemap: **Esri World Imagery** satellite (`server.arcgisonline.com`), attribution "Imagery © Esri".
- Optional toggle: OSM "Street" layer via `L.control.layers` — user can switch between satellite and street view.
- Draws `geolocation_pack_geojson` with `L.geoJSON`:
  - Polygon plots: filled boundary, colour by detection.
  - Point plots (≤4 ha): `circleMarker` via `pointToLayer`, same detection colour.
  - Detection→colour: `loss_detected`→#C0392B, `inconclusive`→#8A5A00, `clear_in_screen`→#0E7A30, `geometry_invalid`→#8A97A3.
- **Permanent tooltip**: plot name (`bindTooltip`, `permanent: true`, `direction: 'center'`, class `eudr-plot-tooltip`).
- **Click popup**: plot name / status label / finding detail (label+detail looked up from `_eudrResult.plots` by `plot_id` since geolocation pack only carries `detection`).
- `fitBounds` with 30px padding — handles single-plot case.

### 2. Ha/area thousands-separator formatting (`api/main.py`)

`_eudr_finding_detail` now formats numbers as:
| ha value | Format | Example output |
|---|---|---|
| 0 < ha < 0.05 | `"<0.1"` | "We found about <0.1 ha …" |
| 0.05 ≤ ha < 10 | `f"{ha:.1f}"` | "We found about 3.7 ha …" |
| ha ≥ 10 | `f"{ha:,.0f}"` | "We found about 12 ha …" or "~1,101 ha" |

Area: `f"{int(round(area_ha)):,}"` — always 0 dp with thousands separator.
Example: "~98,457 ha" not "98457 ha".

### 3. Test updated

`test_loss_detected_plot_fields`: `"12.4 ha"` → `"12 ha"` (fixture `loss_after_2020_ha=12.4`; at ha≥10 threshold, `f"{12.4:,.0f}"` = `"12"`).

```
mypy core/contracts/__init__.py --ignore-missing-imports -> Success: no issues found
pytest tests/ -> 457 passed, 1 warning
```
