# OUTBOX — Builder · WO-AUTOROUTE-004 · 2026-06-24

## Status: COMPLETE — stopping for Cowork review

WO-AUTOROUTE-004 complete. **167 tests green** (164 existing all pass, +3 new).

---

## What was delivered

### classifier/ (new module)
- `classifier/__init__.py`: module init with docstring declaring it as the intake LLM boundary
- `classifier/intake.py`: `classify_project(description, permit_type, model)` → `ClassifierResult`
  - Maps free-text to REDD | IFM | PEAT | out_of_scope
  - Defaults to `out_of_scope` when description is empty, SDK absent, or ANTHROPIC_API_KEY unset
  - Falls back gracefully on any API or parse error
  - NEVER imported by `engines/` — determinism invariant preserved by design + asserted in tests

### engines/carbon/engine.py
- `run_mixed_stratification(inp, boundary, forest, min_stratum_ha=1000.0)` added (after `run_carbon_engine`)
  - Soil-first stratification: queries KHG peat area; if both peat ≥ 1000 ha AND mineral ≥ 1000 ha → 2 strata
  - **Peat stratum**: flag, no tonnage (ADR-0013), KHG/PIPPIB overlays evaluated
  - **Mineral stratum**: REDD/IFM estimate on mineral area only (forest gate + `_estimate_redd`)
  - `combined_eligibility.verdict = "flagged"` always when peat stratum present
  - Falls back to `run_carbon_engine()` if not sufficiently mixed
  - Module docstring updated: references WO-AUTOROUTE-004, intake classifier mention in docstring only (not import)
  - "Only LLM in narrative/" comment updated to reflect both narrative/ and classifier/ boundary

### api/main.py
- `_capture_out_of_scope_lead()`: lead capture for out-of-scope (email + Sheet, best-effort)
- `_handle_other_project_type()`: full handler for project_type="other"
  - Calls `classify_project()` at intake boundary
  - If `out_of_scope`: captures lead + returns JSON with apology, CTA, cta_email, lead_captured
  - If REDD/IFM: calls `run_mixed_stratification()` (soil-first stratification)
  - If PEAT: calls `run_carbon_engine()`
  - Tags `classification.user_project_type_override` with original description
  - Returns `EngineResult` with classifier_category + classifier_confidence in loss_overlay
- `carbon()` endpoint: checks `inp.project_type == "other"` → delegates to `_handle_other_project_type()`

### narrative/narrator.py
- Module docstring updated: "LLM calls: narrative/ (template) and classifier/ (intake only — never in number path)"
- `generate_narrative()`: `is_mixed` derived from `estimate.classification.dominant_soil`
- Carbon estimate block: changed from `if elig.verdict == "eligible"` to `if low is not None`
  - Shows range for ANY non-None quantity (including mixed-concession flagged cases with mineral range)
  - `range_label` is "**Indicative Carbon Range (mineral stratum — peat stratum separately flagged)**" for mixed

### frontend/index.html
- `project_type` select: added "Other / Describe your own" option + `onchange="onProjectTypeChange()"`
- `project_type_desc_row`: textarea "Describe your project" — shown only when "other" selected
- `onProjectTypeChange()`: toggles description row visibility
- `submitCarbon()`: captures `rawDesc`, stores in `_cache.project_type_description`, sends in payload
- `renderResult()`: out-of-scope guard at top — shows apology + CTA + lead_captured confirmation
- Range display: changed from `verdict === 'eligible'` to `quantity_low_tco2e != null` — shows mineral range for mixed-flagged cases

### Fixtures (new)
- `tests/fixtures/carbon/WO006_mixed_concession.json`: HTI 49,228 ha polygon near (-2.0, 113.0), KHG 15,000 ha peat
- `tests/fixtures/data_cache/a6cc657e3aaf8bfe.json`: forest data for mixed concession (cache key for centroid -2.0000,113.0000,49228.1)
- `tests/fixtures/overlays/khg_-2.000_113.000.json`: KHG intersects=true, area_ha=15000
- `tests/fixtures/overlays/pippib_-2.000_113.000.json`: PIPPIB intersects=false
- `tests/fixtures/overlays/worldcover_-2.000_113.000.json`: Tree cover (class 10), 50%
- `tests/fixtures/overlays/jrc_tmf_-2.000_113.000.json`: degraded, 55% TMF

### Tests (+3 new in test_golden.py)
| Test | Assertion |
|------|-----------|
| `test_number_path_deterministic_classifier_excluded` | `from classifier` / `import classifier` not in engine.py source + determinism |
| `test_mixed_stratification_peat_flag_mineral_number` | 2 strata, peat=flag+no-number, mineral has range, overall=flagged |
| `test_mixed_stratum_areas_sum_to_boundary` | peat_area + mineral_area == boundary.area_ha (no double-counting) |

---

## Key decisions
1. **Structural test uses `from classifier` / `import classifier` check** (not bare "classifier") — the word appears in the engine docstring as documentation, which is acceptable.
2. **Cache key for mixed fixture** is `a6cc657e3aaf8bfe` (SHA-256 of "-2.0000,113.0000,49228.1") — actual UTM area 49228.1 ha, not the description's 49,207 ha.
3. **`is_tree_cover` excluded from worldcover fixture** — it's a computed `@property` on `WorldCoverResult`, not a constructor field.
4. **PIPPIB fixture uses `area_ha: null`** — `OverlayIntersection.area_ha: Optional[float] = None` accepts null.
5. **Narrator `if low is not None` change** — shows mineral range for mixed-flagged cases while still suppressing for pure hard_no/flagged-without-range cases.

---

## 167 tests green
```
167 passed, 1 warning in 3.08s
```

---

## Open questions for reviewer
1. Is the `from classifier` / `import classifier` text-search check robust enough, or should it use AST-based import analysis?
2. The out-of-scope lead capture calls `_deliver()` with `b""` (empty bytes) — no DOCX for out-of-scope. Is this acceptable for the Sheet row format?
3. `_handle_other_project_type()` uses `run_mixed_stratification()` for REDD/IFM classified projects. Should it also run `run_mixed_stratification()` for PEAT-classified or fall through to `run_carbon_engine()` as currently coded?
