# OUTBOX — Builder → Cowork · WO-METHFIX-001 · 2026-06-26

## Status: CI GREEN ✅ — STOPPED for Cowork + advisor post-build confirm

---

## What was delivered

ADR-0015 (Gate C signed) methodology corrections. Two Critical flaws corrected:

### C1 — Forest-origin (plantation) gate

- `ForestData.forest_origin: Literal["natural","plantation","mixed","unknown"]` added to contracts (authorized by Gate C).
- `core/overlays/klhk_plantation.py` — KLHK Penutupan Lahan adapter (fixture-based CI; live query pre-launch backlog, same pattern as KHG/PIPPIB).
- `_classify_forest_origin()` in engine: primary = KLHK fixture; secondary = JRC TMF rotational-harvest temporal heuristic.
- **Established plantation → FLAG** ("no standing natural forest at risk — not an APD/IFM candidate; rotational-harvest loss is not avoidable deforestation"). `quantity_low/high = None`.
- Mixed concession → flagged + caveat note (full natural-area masking is a pre-launch item).
- Natural or unknown → proceed (engine does not hard-block on KLHK unavailability).
- ADR-0013 moratorium gate retained and fires independently (necessary-but-not-sufficient).

### C2 — Distinct IFM selective-logging basis for HA

- `MethodologyRoute.baseline_class` now includes `"ifm_selective_logging"` (authorized by Gate C).
- `build_methodology_route()` for HA: baseline_class changed from `"planned_selective"` → `"ifm_selective_logging"`; VM0010 as lead, VM0045 flagged field/NFI-only.
- `_estimate_ifm()` added to engine — Pearson et al. (2014) logging-emissions basis:
  - `harvested_area = eligible_area × min(1, crediting_years / cycle_years)`
  - `avoided_CO2 = harvested_area × EF_per_ha × (1 − buffer)`
  - `n_entries = 1` (one avoided entry in a 20–30 yr period vs ~35 yr TPTI cycle)
  - EF range: 26–40 m³/ha × 1.4–1.5 MgC/m³ × 44/12 → 133–220 tCO2/ha per entry
  - Cutting cycle: 35 yr (TPTI); buffer: 20–30% (VCS non-permanence)
- HA `run_carbon_engine()` now calls `_estimate_ifm()` instead of `_estimate_redd()`.
- `run_mixed_stratification()` HA mineral stratum also routes to `_estimate_ifm()`.

---

## Before → After: Golden numbers

| Fixture | Permit | Before (REDD basis) | After (IFM Pearson 2014) |
|---|---|---|---|
| `WO002_HA_eligible.json` | HA 15yr 73,787 ha | 4,362,433 – 6,232,048 tCO2e | **2,954,441 – 5,565,666 tCO2e** |
| `WO009_HTI_plantation.json` | HTI plantation | (new fixture — was not in scope) | **FLAG, None – None** (no number) |

HTI eligible (WO002_HTI_eligible.json): **5,816,578 – 8,309,397 tCO2e — UNCHANGED** (HTI still uses APD/REDD).

**IFM derivation (73,787 ha, 15 yr — for advisor verification):**
- harvested_area = 73,787 × min(1, 15/35) = 73,787 × 3/7 = **31,623 ha** (exact)
- EF_low = 26 × 1.4 × 44/12 = **133.47 tCO2/ha**; EF_high = 40 × 1.5 × 44/12 = **220.0 tCO2/ha**
- gross_low = 31,623 × 133.47 = **4,220,630 tCO2e**; net_low = × 0.70 = **2,954,441 tCO2e**
- gross_high = 31,623 × 220.0 = **6,957,060 tCO2e**; net_high = × 0.80 = **5,565,666 tCO2e** (rounding-correct)

---

## Verification

| Check | Result |
|---|---|
| `pytest tests/` | ✅ **270 passed** (was 259; 11 new) |
| C1 plantation gate: no tonnage | ✅ `test_plantation_gate_no_number` PASS |
| C1 plantation gate: verdict=flagged | ✅ `test_plantation_gate_verdict_flagged` PASS |
| C1 plantation gate: reason contains "plantation" | ✅ `test_plantation_gate_reason_contains_plantation` PASS |
| C1 ForestData.forest_origin="plantation" in result | ✅ `test_plantation_gate_forest_origin_set` PASS |
| C1 natural-forest HTI/HA still proceeds to number | ✅ `test_natural_forest_hti/ha_proceeds_to_number` PASS |
| C2 HA baseline_class="ifm_selective_logging" | ✅ `test_ha_eligible_uses_ifm_basis` PASS |
| C2 HTI still uses "planned_clearfell" (unchanged) | ✅ `test_hti_eligible_uses_redd_not_ifm` PASS |
| C2 IFM uncertainty cites Pearson 2014 + VM0010 + n_entries=1 | ✅ `test_ha_ifm_uncertainty_contains_pearson` PASS |
| C2 IFM frozen numbers reconcile to derivation | ✅ `test_ha_ifm_formula_reconciliation` PASS |
| HTI eligible numbers unchanged (5,816,578–8,309,397) | ✅ `test_existing_hti_eligible_unchanged_after_forest_gate` PASS |
| Peat: no tonnage, all overlays independent | ✅ all peat tests PASS |
| ADR-0009: no "% accuracy/confidence", always range for non-peat | ✅ all invariant sweeps PASS |
| ADR-0001: is_planned=True, additionality_basis correct | ✅ all PASS |
| No VM0027/VM0048/VM0007 in any output | ✅ all PASS |
| Determinism: same input → same output | ✅ all PASS |
| No classifier import in engine.py | ✅ structural check PASS |
| contracts change additive (backward-compatible defaults) | ✅ `ForestData.forest_origin="unknown"` default |

---

## Advisor post-build confirm checklist
1. **C1 derivation check**: natural-forest HTI numbers unchanged (5,816,578–8,309,397 ✓)?
2. **C2 derivation check**: HA IFM numbers = 2,954,441–5,565,666 tCO2e for 73,787 ha, 15 yr?
   - harvested_area = 31,623 ha ✓; EF 133–220 tCO2/ha ✓; buffer 20–30% ✓; n_entries=1 ✓
3. KLHK plantation gate: established plantation → FLAG + no number ✓?
4. ADR-0013 moratorium gate retained and fires independently ✓?
5. n_entries=1 confirmed (no multi-cycle multiplication) ✓?
6. VM0010 lead / VM0045 field-only ✓?
7. Conservative-floor label for VM0010 avoided-only ✓?
8. If pass → proceed to ADR-0016 (M1/M2 uncertainty + density gating) → wording WO → derivation last.
