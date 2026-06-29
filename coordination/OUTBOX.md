# OUTBOX — Builder → Cowork · WO-EUDR-GEOMETRY-002 (E2) · 2026-06-30

## Status: CI GREEN ✅ — STOPPED for Cowork review (325 tests pass, 19 new)

Implements EUDR Art-9 geometry validation engine. Deterministic, no network calls.

---

## New module — `engines/eudr/geometry.py`

| Concern | Implementation |
|---|---|
| **Parse GeoJSON** | FeatureCollection / Feature / raw geometry; `plot_id` from `properties.plot_id\|id\|name`; `area_ha` from `properties.area_ha\|hectares` |
| **Parse KML** | Namespaced (`http://www.opengis.net/kml/2.2`) + bare KML; `<Placemark><name>` as `plot_id`; `<Polygon>` and `<Point>` geometry |
| **Parse SHP** | `pyshp` (added `pyshp>=2.3` to `requirements.txt`); graceful `ImportError` hint if not installed |
| **Art-9: polygon for >4 ha** | `declared_ha > 4.0` with a Point → `geometry_invalid`; declared area extracted from GeoJSON properties / KML ExtendedData |
| **Art-9: ≥6 decimal places** | `repr(float)` shortest-round-trip string; `len(s.split(".")[1]) >= 6` for every coordinate value; scientific-notation → 0 (safe) |
| **Self-intersection** | `shapely.geometry.shape(geom).is_valid` — catches bowtie, figure-8, touching rings |
| **Empty / degenerate** | Ring with < 4 points; missing `geometry` field; unparseable content |
| **Area** | `pyproj.Geod.geometry_area_perimeter` on WGS84 ellipsoid — no projection needed; accurate for Indonesian coordinates |
| **`geometry_ok` invariant** | `geometry_ok == (detection != "geometry_invalid")` enforced by `PlotValidation.__post_init__` → raises `AssertionError` on any violation (resolves **advisor flag #3** from E1 OUTBOX) |
| **Valid output** | `detection="inconclusive"`, `geometry_ok=True` (pending satellite triage, E3) |
| **Invalid output** | `detection="geometry_invalid"`, `geometry_ok=False`, `fix_message=FIX_MESSAGE` |

**FIX_MESSAGE** (verbatim per WO):
> *"EUDR Art 9 needs a polygon for plots over 4 ha and coordinates to at least 6 decimals. Fix it and we'll re-screen."*

---

## New dep — `pyshp>=2.3`

Light pure-Python library (~50 KB). Added to `requirements.txt`. No conflict with existing deps. If not installed at runtime, the SHP parser returns a `geometry_invalid` result with an install hint rather than raising.

---

## Advisor flag #3 resolved

WO-EUDR-CONTRACTS-001 OUTBOX flagged: "`detection=geometry_invalid` vs `geometry_ok: bool` mild redundancy on `PlotVerdict`". Resolution: `geometry_ok` is now **always derived** from `detection`. `PlotValidation.__post_init__` asserts the invariant at construction time — impossible to build an inconsistent object. The E3/E4 pipeline must follow the same rule when constructing `PlotVerdict` from `PlotValidation`.

---

## Tests — `tests/test_eudr_geometry.py` (19 new)

All WO-specified acceptance criteria covered:

| Test | Verdict |
|---|---|
| `test_valid_large_polygon` | valid polygon ≥6 dec, >4 ha → ok ✅ |
| `test_point_for_large_plot_is_invalid` | point + declared area >4 ha → geometry_invalid ✅ |
| `test_point_for_small_plot_is_valid` | point + declared area ≤4 ha → ok ✅ |
| `test_point_no_declared_area_is_valid` | point, no area declared → ok ✅ |
| `test_polygon_low_precision_coords_invalid` | <6 decimal polygon → geometry_invalid ✅ |
| `test_point_low_precision_coords_invalid` | <6 decimal point → geometry_invalid ✅ |
| `test_self_intersecting_polygon_invalid` | bowtie polygon → geometry_invalid ✅ |
| `test_empty_geometry_invalid` | null geometry → geometry_invalid ✅ |
| `test_polygon_too_few_points_invalid` | degenerate ring → geometry_invalid ✅ |
| `test_multi_plot_feature_collection_parses_all` | 3-feature FC → 3 results in order ✅ |
| `test_geometry_ok_and_detection_always_consistent_via_parse` | 5-plot mixed batch, all consistent ✅ |
| `test_plot_validation_invariant_enforced_at_construction` | both violation directions raise AssertionError ✅ |
| `test_kml_valid_polygon_parses_ok` | KML Polygon ≥6 dec → ok, plot_id from `<name>` ✅ |
| `test_kml_valid_point_parses_ok` | KML Point → ok, geometry_type=point ✅ |
| `test_kml_low_precision_coords_invalid` | KML <6 dec → geometry_invalid ✅ |
| `test_shp_without_pyshp_returns_helpful_message` | ImportError mocked → hint returned ✅ |
| `test_decimal_places_unit` | unit test for `_decimal_places` helper ✅ |
| `test_all_have_min_precision` | unit test for `_all_have_min_precision` ✅ |
| `test_valid_polygon_via_feature` | GeoJSON Feature wrapper ✅ |

**325 tests pass** (was 306). Pre-existing `test_khg_live_smoke_mineral_land` excluded — `ReadTimeout` from BIG One Map endpoint, unrelated to this WO.

---

## Commit

`653dd74` — pushed to `main` — `feat(eudr): Art-9 geometry validation engine (WO-EUDR-GEOMETRY-002, E2)`
