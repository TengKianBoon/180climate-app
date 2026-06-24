# OUTBOX — Builder · WO-AUTOROUTE-003 · 2026-06-24

## Status: COMPLETE — stopping for Cowork review

WO-AUTOROUTE-003 complete. Opus reviewer: **PASS**. **164 tests green** (5 new + 159 existing all pass).

---

## What was delivered

### Forest-presence gate (engines/carbon/engine.py)
- `_evaluate_forest_gate(boundary, forest) -> ForestPresenceGate`
  - Uses `ForestData.baseline_cover_pct` (Hansen) + `query_jrc_tmf()` + `query_worldcover()`
  - **Condition logic** (top-down):
    - **cleared** (gate_result=**fail**): `baseline_cover_pct < 20` OR `(JRC deforested AND WorldCover non-tree)`
    - **intact** (gate_result=**pass**): `cover >= 60` AND `JRC undisturbed`
    - **light_degradation** (gate_result=**pass**): `cover >= 40` AND JRC in (undisturbed/degraded/regrowth)
    - **heavy_degradation** (gate_result=**flag**): `cover >= 20` (data present but degraded)
    - **unknown** (gate_result=**flag**): data insufficient
  - Permit-validity caveat embedded in `note` for pass results

### Engine integration (run_carbon_engine — non-peat branch)
- Forest gate evaluated for ALL non-peat projects (after eligibility, before estimate)
- If `gate_result == "fail"` AND `eligibility.verdict != "hard_no"`:
  - Forces `eligibility.verdict = "flagged"` + reason "forest gate fail: …"
  - Returns `quantity_*=None` + `classification` with failed stratum
  - `uncertainty` string contains "Tier 1" + "baseline" (invariant tests stay green)
- If `gate_result == "pass"` or `"flag"`: number still computed (unchanged)
- All non-peat results now carry `classification.strata[0].forest_gate`

### Fixtures (3 new files)
- `tests/fixtures/overlays/worldcover_-1.000_115.000.json`: Grassland (class 30, no tree cover)
- `tests/fixtures/overlays/jrc_tmf_-1.000_115.000.json`: deforested 2017
- `tests/fixtures/data_cache/9e3fb836374f3fa9.json`: baseline_cover_pct=8, no annual loss (cleared land)
- Cache key = SHA-256("-1.0000,115.0000,24132.5")[:16] = `9e3fb836374f3fa9` ✓

### Golden fixture
- `tests/fixtures/carbon/WO005_HTI_cleared.json`: HTI 20yr, 24,132 ha polygon near (-1,115) on cleared scrub → gate_result=fail → flagged, no number

### Tests (5 new in test_golden.py)
| Test | Assertion |
|------|-----------|
| `test_forest_gate_fail_no_number` | quantity_*=None for cleared |
| `test_forest_gate_fail_flagged_not_hard_no` | verdict="flagged", not hard_no |
| `test_forest_gate_condition_cleared` | classification.strata[0].forest_gate.condition="cleared" |
| `test_forest_gate_reason_in_eligibility` | "no at-risk forest" in eligibility.reasons |
| `test_existing_hti_eligible_unchanged_after_forest_gate` | forest gate passes for existing fixture; frozen numbers unchanged |

### API (api/main.py)
- `_forest_gate_overlay()`: extracts `forest_condition` + `forest_gate_result` from classification
- Loss overlay now includes these fields for UI display
- `must_state` updated to include permit-validity caveat (narrator must state)

### Frontend (frontend/index.html)
- `IFM — Improved Forest Management` option added to project_type select
- Forest condition badge shown in tier-row (green for pass, amber for flag/fail)
- Label text: "Forest: intact", "Forest: cleared — no baseline", etc.

---

## Opus reviewer highlights (PASS)
- Gate logic is conservative in the right direction — no path lets cleared land slip into pass
- hard_no bypass is semantically correct (area-fail doesn't double-block with forest gate)
- Cache key integrity verified (fixture addresses match computed centroid+area)
- 164 tests all pass including all 159 prior tests

## Non-blocking note from Opus (pre-existing cosmetic issue)
- Uncertainty string says "8-yr avg 2016-2022" but loop is range(2016,2024) = 2016-2023. Pre-existing mislabel, not introduced here. Carry forward.

---

## 164 tests green
```
164 passed, 1 warning in 6.24s
```

---

## Next: WO-AUTOROUTE-004 (when Cowork clears this)
- "Describe your own" free-text classifier (intake only, out of number path)
- Mixed-concession soil-first stratification (forested peat → peat stratum = flag; mineral forest → REDD/IFM)
- Sonnet (+ Opus review)
