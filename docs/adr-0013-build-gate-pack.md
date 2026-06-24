# ADR-0013 Auto-Routing — Build Gate Pack
**Status:** GATE-AR READY | **Date:** 2026-06-24 | **Scope:** WO-AUTOROUTE-001 through 005

## 1. What was built

The ADR-0013 auto-routing feature adds four legal/methodological guardrails to the 180Climate carbon engine:

### Guardrail 1: Peat parcels surface as a FLAG — never a tonnage
- `project_type = "PEAT"` triggers the peat branch
- Engine runs two independent legal overlay queries (A=KHG fungsi-lindung PP57/2016; B=PIPPIB moratorium Inpres5/2019) and returns `peat_additionality_status`
- `quantity_low_tco2e = None`, `quantity_high_tco2e = None` — enforced at the `Stratum` Pydantic model level (raises `ValueError` at construction if violated)
- Why: avoided-conversion is non-additional on legally protected peat (regulatory surplus); "legal harvest right foregone" basis is invalid on PP57/2016 or Inpres5/2019 protected land

### Guardrail 2: Forest-presence gate blocks a REDD/IFM number on cleared land
- For all non-peat projects, `_evaluate_forest_gate()` evaluates Hansen baseline_cover_pct + JRC TMF disturbance class + ESA WorldCover land type
- `gate_result = "fail"` (cleared land): forces `eligibility = "flagged"`, `quantity_* = None`
- `gate_result = "flag"` (heavy degradation): number computed but flagged
- `gate_result = "pass"` (intact/light): number computed normally
- Existing numbers unchanged (regression tested against frozen golden fixtures)

### Guardrail 3: Intake classifier at the input boundary — number path deterministic
- `project_type = "other"` triggers `classifier/intake.py` (the ONE permitted runtime LLM call)
- Maps free-text to REDD | IFM | PEAT | out_of_scope (default: out_of_scope)
- Out-of-scope routes to a polite apology and a call-to-action (info@180climate.net) + lead always captured
- `engines/carbon/engine.py` never imports from `classifier/` — asserted in `test_number_path_deterministic_classifier_excluded`

### Guardrail 4: Mixed-concession soil-first stratification
- `run_mixed_stratification()` checks KHG peat area; if peat_area ≥ 1,000 ha AND mineral_area ≥ 1,000 ha two strata are created
- Peat stratum: flag, no tonnage (Guardrail 1 applies)
- Mineral stratum: REDD/IFM estimate on `mineral_area` ha only (no double-counting trees-on-peat)
- Combined band: `quantity_low/high = mineral_stratum range`, peat uncertainty visible in combined string
- `sum(stratum.area_ha) == boundary.area_ha` — asserted in test

---

## 2. Worked examples

### Example A: SMPP-style deep peat dome — flag (never excluded)
**Input:** PEAT project, HTI permit, -2.500 deg N / 103.500 deg E, point input (proxy 25,000 ha)
**Overlays:** KHG = intersects (fungsi-lindung dome); PIPPIB = data unavailable
**Status:** "flag — manual methodological review required; one or both overlay datasets unavailable (KHG fungsi-lindung and/or PIPPIB moratorium data not loaded)"
**Output:** `quantity_low = None`, `quantity_high = None`, `verdict = "flagged"` (never "hard_no")
**Why "flagged" not "hard_no":** A valid restoration/WRC (Wetland Restoration and Conservation) pathway (VCS1899 class, e.g. Sumatra Merang) may exist; the engine defers, not rejects. Legal determination is a per-project call.

### Example B: HTI on cleared/scrub land — flagged, no baseline
**Input:** REDD, HTI permit, 20yr, 24,132 ha polygon near (-1.0 deg N / 115.0 deg E)
**Overlays:** Hansen baseline cover 8% (threshold 20%); JRC: deforested 2017; WorldCover: Grassland
**Forest gate:** `condition = "cleared"`, `gate_result = "fail"`
**Output:** `quantity_low = None`, `quantity_high = None`, `verdict = "flagged"`, reason: "No at-risk forest confirmed"
**Why:** A REDD/IFM baseline requires standing at-risk forest. Cleared land has no forest carbon to protect — the avoided-deforestation counterfactual is invalid.

### Example C: Mixed concession (peat + mineral forest) — soil-first stratification
**Input:** "other" (classified REDD), HTI permit, 49,228 ha polygon near (-2.0 deg N / 113.0 deg E)
**KHG overlay:** peat area 15,000 ha (30%); mineral area 34,228 ha (70%)
**Peat stratum (15,000 ha):** flag, no tonnage. `peat_additionality_status: "flag — A+B"` (fungsi-lindung KHG intersects)
**Mineral stratum (34,228 ha):** REDD estimate. Forest gate: light_degradation (50% cover, JRC degraded — pass). Loss rate: 481 ha/yr / 49,228 ha = 0.977%/yr. ESA CCI Biomass (Biomass v3.0 2018): 266.5 tCO2/ha. Project 20yr.
**Combined output:** `quantity_low` and `quantity_high` from mineral stratum only; `verdict = "flagged"` (peat flag contaminates); peat uncertainty visible in combined string.

### Example D: HTI eligible — unaffected (no regression)
**Input:** REDD, HTI permit, 20yr, 73,787 ha polygon (0.9 deg N / 117.15 deg E)
**Forest gate:** light_degradation (70.7% cover, JRC degraded — pass)
**Output (frozen 2026-06-24, re-verified 2026-06-24):** `quantity_low = 5,816,578 tCO2e`, `quantity_high = 8,309,397 tCO2e`, `verdict = "eligible"` — UNCHANGED after WO-002 through 005.

---

## 3. The four guardrails — decision table

| Scenario | Guardrail | Output | Test fixture |
|---|---|---|---|
| Peat + KHG + PIPPIB | Guardrail 1: peat FLAG | No tonnage, flagged | WO003_routing_PEAT |
| Peat + KHG only | Guardrail 1: peat FLAG | No tonnage, "flag — A:" | WO007_PEAT_Aonly |
| Peat + PIPPIB only | Guardrail 1: peat FLAG | No tonnage, "flag — B:" | WO007_PEAT_Bonly |
| Peat + neither overlay | Guardrail 1: peat FLAG | No tonnage, "possibly developable" | WO007_PEAT_neither |
| SMPP deep dome (A + unknown B) | Guardrail 1: peat FLAG | No tonnage, data-unavail note | WO004_SMPP_peat_flag |
| HTI on cleared land | Guardrail 2: forest gate fail | No tonnage, "no at-risk forest" | WO005_HTI_cleared |
| HTI intact forest | Guardrail 2: forest gate pass | Number computed | WO008_forest_intact |
| HTI heavy degradation | Guardrail 2: forest gate flag | Number computed, flagged | WO008_forest_heavy |
| Free text "other" → out-of-scope | Guardrail 3: classifier | Out-of-scope JSON + lead | (API test) |
| Mixed peat+mineral | Guardrail 4: stratification | Peat: no tonnage; Mineral: range | WO006_mixed_concession |

---

## 4. Invariants verified (evidence)

All invariants are asserted in the automated test suite (`pytest tests/ -q` must pass, 231 tests green):

1. **Peat no-tonnage by construction:** `Stratum.model_validator` raises `ValueError` if `soil_type=="peat"` and any quantity is not None — `test_peat_stratum_validator_enforced`
2. **Two overlays never collapsed:** A and B are separate fields on `LegalOverlayResult`, not one bool — `test_peat_overlay_combo_overlays_independent`
3. **Peat never hard_no:** All peat fixtures check `verdict != "hard_no"` — `test_peat_overlay_combo_never_hard_no`
4. **Forest gate blocks cleared land:** `quantity_* = None` for WO005 — `test_forest_gate_fail_no_number`
5. **Classifier excluded from number path:** `from classifier` not in `engines/carbon/engine.py` source — `test_number_path_deterministic_classifier_excluded`
6. **Determinism:** Same input yields same output twice — `test_determinism`, `test_carbon_engine_deterministic`
7. **No single number / no percent accuracy:** No forbidden phrases in any estimate — `test_no_forbidden_phrases_in_output`, `test_all_peat_no_forbidden_phrases`, `test_all_redd_no_forbidden_phrases`
8. **is_planned = True, additionality_basis correct:** All 13 fixtures — `test_all_fixtures_is_planned_and_additionality_correct`
9. **Never VM0027/VM0048/VM0007:** All peat fixtures; VM0048/VM0007 from REDD fixtures — `test_all_peat_never_vm0027_vm0048_vm0007`, `test_all_redd_never_vm0048_vm0007`
10. **HTI to APD, HA to IFM routing:** `test_methodology_routing_golden`
11. **Mixed areas sum to boundary:** `test_mixed_stratum_areas_sum_to_boundary`
12. **Existing frozen ranges unchanged:** `test_existing_hti_eligible_unchanged_after_forest_gate`, `test_golden_ranges`

---

## 5. Evidence pointers

- Engine: `engines/carbon/engine.py` — `run_carbon_engine()`, `run_mixed_stratification()`, `_evaluate_peat_overlays()`, `_evaluate_forest_gate()`
- Contracts: `core/contracts/__init__.py` — `Stratum`, `ProjectClassification`, `ForestPresenceGate`, `LegalOverlayResult`
- Classifier: `classifier/intake.py` — `classify_project()`
- Overlay adapters: `core/overlays/khg.py`, `core/overlays/pippib.py`, `core/overlays/worldcover.py`, `core/overlays/jrc_tmf.py`
- API: `api/main.py` — `_handle_other_project_type()`, `_capture_out_of_scope_lead()`
- Tests: `tests/test_golden.py` (231 assertions), `tests/test_classifier.py` (7 tests)
- ADRs: `docs/adr/ADR-0013-peatland-routing.md`, `docs/adr/ADR-0013-auto-routing.md`

---

## 6. Open items (carry-forward to Gate L)

1. **Real KHG + PIPPIB maps:** Overlays currently use CI stubs only. Must wire real KLHK shapefiles before any live deployment.
2. **Classifier API key:** `ANTHROPIC_API_KEY` must be set in production for project_type="other" live classification. Without it, defaults to out-of-scope.
3. **Email/Sheet/SMTP creds:** Carry-forward from Gate P — configure `EMAIL_FROM`, `EMAIL_USER`, `EMAIL_PASSWORD`, `GOOGLE_SHEET_ID`, `GSPREAD_CREDENTIALS` at deploy time.
4. **Cover threshold tuning:** Forest gate thresholds (20/40/60%) are conservative defaults — make config-driven before Gate L (noted by Opus reviewer WO-003).
5. **Cosmetic:** Uncertainty string says "2016-2022" but loop is 2016-2023 (pre-existing carry-forward).
6. **Advisor wording review:** Peat narrative text to be reviewed by qualified methodology advisor before live deployment.
