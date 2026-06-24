# OUTBOX — Builder · WO-AUTOROUTE-005 · 2026-06-24

## Status: COMPLETE — GATE-AR READY (stopping for John + advisor sign-off)

WO-AUTOROUTE-005 complete. **231 tests green** (167 existing all pass, +64 new).

---

## What was delivered

### New golden carbon fixtures (5)
- `tests/fixtures/carbon/WO007_PEAT_Aonly.json`: PEAT, HTI, -1.5/112.0 polygon — KHG intersects, PIPPIB no intersection → "flag — A:" status
- `tests/fixtures/carbon/WO007_PEAT_Bonly.json`: PEAT, HTI, -3.5/110.0 polygon — KHG no intersection, PIPPIB intersects → "flag — B:" status
- `tests/fixtures/carbon/WO007_PEAT_neither.json`: PEAT, HTI, -4.0/108.0 polygon — both overlays no intersection → "possibly developable peat" status
- `tests/fixtures/carbon/WO008_forest_intact.json`: REDD, HTI, -0.5/116.0 polygon — 75% cover, JRC undisturbed → intact, pass, number computed
- `tests/fixtures/carbon/WO008_forest_heavy.json`: REDD, HTI, -1.5/115.0 polygon — 30% cover, JRC degraded → heavy_degradation, flag, number still computed

### New data cache fixtures (5)
Cache keys computed from actual UTM-projected area (shapely/pyproj), not nominal:
- `d67cc15689b40193.json`: Peat A-only centroid (-1.5000, 112.0000, 49195.6 ha)
- `e74d7830034b5964.json`: Peat B-only centroid (-3.5000, 110.0000, 49122.6 ha)
- `1d5d7f387cb0c771.json`: Peat neither centroid (-4.0000, 108.0000, 49215.3 ha)
- `cf72ac513d9218d5.json`: Forest intact centroid (-0.5000, 116.0000, 49210.2 ha)
- `e1bd28d27ac80cd1.json`: Forest heavy centroid (-1.5000, 115.0000, 49240.9 ha)

### New overlay fixtures (10)
- `khg_-1.500_112.000.json` + `pippib_-1.500_112.000.json`: Peat A-only (KHG=true, PIPPIB=false)
- `khg_-3.500_110.000.json` + `pippib_-3.500_110.000.json`: Peat B-only (KHG=false, PIPPIB=true)
- `khg_-4.000_108.000.json` + `pippib_-4.000_108.000.json`: Peat neither (both false)
- `worldcover_-0.500_116.000.json` + `jrc_tmf_-0.500_116.000.json`: Forest intact (78% cover, undisturbed)
- `worldcover_-1.500_115.000.json` + `jrc_tmf_-1.500_115.000.json`: Forest heavy (32% cover, degraded)

### Tests/test_golden.py (+57 new parametrized test cases)
New test functions with parametrization:
- `test_peat_overlay_combo_no_tonnage` (3 params): all peat overlay combos produce no tonnage (ADR-0013)
- `test_peat_overlay_combo_status_matches` (3 params): correct peat_additionality_status text per combo
- `test_peat_overlay_combo_overlays_independent` (3 params): A and B stored separately
- `test_peat_overlay_combo_never_hard_no` (3 params): never "hard_no", always "flagged"
- `test_forest_gate_condition_and_result` (2 params): condition and gate_result verified
- `test_forest_gate_variant_has_number` (2 params): pass/flag gates compute number
- `test_forest_gate_variant_eligibility` (2 params): eligibility verdict verified
- `test_all_peat_no_forbidden_phrases` (5 params): full sweep of 5 peat fixtures
- `test_all_redd_no_forbidden_phrases` (8 params): full sweep of 8 REDD fixtures
- `test_all_fixtures_is_planned_and_additionality_correct` (13 params): all 13 fixtures
- `test_all_peat_never_vm0027_vm0048_vm0007` (5 params): methodology invariant sweep
- `test_all_redd_never_vm0048_vm0007` (8 params): methodology invariant sweep

### tests/test_classifier.py (new file, 7 tests)
Unit tests for classifier/intake.py — all deterministic (no real LLM calls):
- Empty/whitespace description → out_of_scope
- No ANTHROPIC_API_KEY → out_of_scope fallback (never raises)
- ClassifierResult accepts all 4 valid category literals
- ClassifierResult rejects invalid categories via Pydantic ValidationError
- ClassifierResult defaults verified
- Classifier never raises on any input (tested with 4 edge-case descriptions)

### Bug fix: test_golden.py _load() encoding
`_load()` updated to use `encoding="utf-8"` — prevents Windows cp1252 misreading of em dash characters in fixture files containing Unicode strings.

### Gate pack documents
- `coordination/GATE.md`: GATE-AR READY pack (replaces previous Gate C content)
- `docs/adr-0013-build-gate-pack.md`: self-contained gate pack for John + advisor

---

## Key decisions

1. **Actual vs nominal area_ha for cache keys**: The WO spec listed nominal area values (49219.8, etc.) but pyproj/shapely UTM computation gives different values (~49195 ha for a 0.2°×0.2° box near -1.5°). Cache keys were computed from actual shapely areas — this is correct behavior (the cache uses real computed boundary.area_ha).

2. **`_load()` encoding fix**: Read fixtures with `encoding='utf-8'` — prevents Windows cp1252 garbling of Unicode em dashes in peat_additionality_status strings. Safe: all fixtures are UTF-8.

3. **`is_tree_cover` excluded from worldcover fixtures**: It is a `@property` on `WorldCoverResult`, not a constructor field. Only `land_class`, `label`, `tree_cover_pct`, `note` are stored in fixtures.

4. **Forest intact condition**: 75% cover + JRC "undisturbed" → `condition="intact"`, `gate_result="pass"` — number computed, verdict="eligible". Confirmed from engine logic (cover >= 60 AND undisturbed).

5. **Forest heavy condition**: 30% cover + JRC "degraded" → falls through to `cover_pct >= 20` branch → `condition="heavy_degradation"`, `gate_result="flag"` — number still computed. Eligibility gates all pass → verdict="eligible".

---

## 231 tests green
```
231 passed, 1 warning in 5.34s
```

---

## Open questions for reviewer
1. The five data cache keys differ from what the WO spec specified (spec used nominal areas). The correct keys are the ones derived from actual shapely UTM computation. Is this understood and accepted?
2. WO008_forest_heavy expects `eligibility_verdict = "eligible"` — this is because forest gate "flag" does not change eligibility (only "fail" does). The existing `test_forest_gate_variant_eligibility` assertion confirms this. Is this the intended behavior?
