# OUTBOX — Builder -> Cowork · WO-EUDR-PRECISION-018 · 2026-07-01

## Status: CI GREEN -- 463 tests pass (6 new) -- STOPPED for Cowork review

Bug fix + email nicety. No contract change. No gate.

---

## What shipped (commit f998f49)

### 1. False-reject fix — count decimals from raw coordinate string

**Root cause confirmed:** `_decimal_places(float)` used `repr()` which drops trailing zeros.
`"117.152340"` (6 dp) → `float(...)` = `117.15234` → `repr(117.15234)` = `"117.15234"` (5 dp) → **falsely rejected**.
A 10-coordinate polygon has ~10 opportunities to hit a trailing-0 value — explains John's "both plots rejected".

**GeoJSON path** ([engines/eudr/geometry.py](engines/eudr/geometry.py)):
- `json.loads(content, parse_float=str)` → coordinate literals arrive as strings, trailing zeros intact.

**KML path** ([engines/eudr/geometry.py](engines/eudr/geometry.py)):
- `_parse_kml_coord_string` now returns `list[list[str]]` (raw token strings); validates parseability with `float()` but keeps the string for the precision check.

**New string-aware helpers:**
| Helper | Behaviour |
|---|---|
| `_decimal_places_str(s)` | Counts dp from raw string; falls back to `_decimal_places(float(s))` for SHP floats |
| `_all_have_min_precision_str(values)` | Replaces `_all_have_min_precision` in validation; accepts str or float |
| `_coerce_coords_to_float(geom)` | Recursively converts string coords to float for shapely — called after precision check |

`_validate_point` and `_validate_polygon` now use `_all_have_min_precision_str` → `_coerce_coords_to_float` → `_shapely_shape`. `PlotValidation.geojson` stores the float-coord dict (unchanged for triage engine).

The old `_decimal_places` / `_all_have_min_precision` remain for SHP fallback and the existing unit tests.

### 2. EUDR lead email header

`api/email.py` `_build_body`: section header is now **`=== EUDR screening ===`** when `form_data["engine"] == "eudr"`, otherwise `=== Carbon screening ===` (unchanged).
`api/main.py` EUDR `form_data`: `"engine": "eudr"` added.

### 3. New tests (6 added to `tests/test_eudr_geometry.py`)

| Test | What it proves |
|---|---|
| `test_decimal_places_str_unit` | `"117.152340"` → 6 dp; `"-1.000000"` → 6 dp; float fallback works |
| `test_all_have_min_precision_str_accepts_trailing_zeros` | String-aware check passes trailing-zero strings |
| `test_geojson_trailing_zero_polygon_accepted` | Raw GeoJSON with `117.152340` / `-1.000000` → `geometry_ok=True` |
| `test_geojson_trailing_zero_point_accepted` | Same for Point geometry |
| `test_geojson_two_decimal_still_rejected` | 2-dp coords still produce `geometry_invalid` (guard intact) |
| `test_kml_trailing_zero_polygon_accepted` | KML coord-text path: `117.152340,-1.000000` tokens → valid |

```
mypy core/contracts/__init__.py --ignore-missing-imports -> Success: no issues found
pytest tests/ -> 463 passed, 1 warning
```
