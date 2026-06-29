# OUTBOX — Builder → Cowork · WO-EUDR-GEOMETRY-002 (E2, re-scoped) · 2026-06-30

## Status: CI GREEN ✅ — STOPPED for Cowork review (326 tests pass, 21 new across both parts)

---

## Part A — `engines/eudr/geometry.py` (committed `653dd74`, unchanged from prior push)

Art-9 geometry validation engine. Deterministic, no network calls.

| Rule | Implementation |
|---|---|
| Plot >4 ha needs polygon | `declared_ha > 4.0` with Point geometry → `geometry_invalid`; declared area from GeoJSON `properties.area_ha\|hectares` or KML ExtendedData |
| ≥6 decimal places | `repr(float)` shortest-round-trip; count digits after `.`; scientific notation → 0 (safe fallback) |
| Self-intersecting | `shapely.geometry.shape(geom).is_valid` — catches bowtie, figure-8, degenerate rings |
| Empty / degenerate | Ring < 4 points; `None` geometry; parse failure |
| Valid | `detection="inconclusive"`, `geometry_ok=True` (pending satellite triage, E3) |
| Invalid | `detection="geometry_invalid"`, `geometry_ok=False`, `fix_message=FIX_MESSAGE` |

**FIX_MESSAGE (verbatim):** `"EUDR Art 9 needs a polygon for plots over 4 ha and coordinates to at least 6 decimals. Fix it and we'll re-screen."`

Formats: GeoJSON (FeatureCollection/Feature/raw), KML (namespaced + bare), SHP (pyshp, graceful ImportError hint).
Area: `pyproj.Geod.geometry_area_perimeter` (WGS84 ellipsoid). Added `pyshp>=2.3` to `requirements.txt`.

---

## Part B — ADR-0018 micro-amendments to `core/contracts/__init__.py` (committed `dc03316`)

**`detection` is now the single source of truth on `PlotVerdict`. No stored field can drift from it.**

| Change | Before | After |
|---|---|---|
| `geometry_ok` | `bool` stored field (could be set inconsistently) | `@computed_field @property`: `return self.detection != "geometry_invalid"` |
| `plot_satellite_risk` | `Literal["low","high","inconclusive"]` stored field | `@computed_field @property`: `clear_in_screen→low`, `loss_detected→high`, `inconclusive→inconclusive`, `geometry_invalid→inconclusive` |

Both computed fields:
- Are absent from `PlotVerdict.model_fields` (cannot be passed in constructor)
- Appear in `PlotVerdict.model_computed_fields`
- Are serialised by `model_dump()` / `model_dump_json()` (downstream consumers unaffected)
- Appear in `model_json_schema()` (banned-string guard still passes — "low"/"high"/"inconclusive" are not banned)

**Resolves advisor flag #3** from WO-EUDR-CONTRACTS-001 OUTBOX ("`detection=geometry_invalid` vs `geometry_ok: bool` mild redundancy — engine must keep them consistent"). Consistency is now structurally guaranteed; no runtime invariant enforcement needed.

---

## Tests

### New geometry tests — `tests/test_eudr_geometry.py` (19 tests, Part A)
All WO-specified acceptance criteria: valid polygon >4 ha; point >4 ha invalid; ≤4 ha point valid; <6-dec invalid; bowtie invalid; empty/degenerate; multi-plot FC; KML polygon/point; SHP import-guard hint. `PlotValidation.__post_init__` enforces the invariant for the engine-local dataclass (both violation directions raise `AssertionError`).

### New contract tests — `tests/test_contracts.py` (2 new, Part B)
- `test_geometry_ok_is_computed_from_detection` — not in `model_fields`; in `model_computed_fields`; `True` for all 3 non-invalid detections, `False` for `geometry_invalid`
- `test_plot_satellite_risk_is_derived_from_detection` — not in `model_fields`; in `model_computed_fields`; correct mapping for all 4 detection enum values

**326 tests pass** (306 post-E1 + 19 geometry Part A + 2 contracts Part B + rounding from refactors). Pre-existing `test_khg_live_smoke_mineral_land` excluded (BIG One Map `ReadTimeout`, unrelated).

---

## Commits
- `653dd74` — Part A: Art-9 geometry engine + pyshp dep
- `9ec4fdf` — chore: coordination Part A
- `dc03316` — Part B: computed geometry_ok + plot_satellite_risk
