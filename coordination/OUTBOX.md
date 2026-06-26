# OUTBOX — Builder → Cowork · WO-DERIVE-001 · 2026-06-26

## Status: CI GREEN ✅ — STOPPED for Cowork review (287 tests passed, 6 new ADR-0014 tests)

---

## What was delivered

### Part 1 — ADR-0014 CalculationTrace (Gate C signed, contracts + engine)

`core/contracts/__init__.py`: new `CalculationTrace(BaseModel)` + `CarbonEstimate.derivation: Optional[CalculationTrace] = None`.

Fields:
- **Common**: `formula`, `basis` ("redd"|"ifm"), `eligible_area_ha`, `project_years`, `buffer_low`, `buffer_high`, `central_tco2e`, `gross_low_tco2e`, `gross_high_tco2e`, `net_low_tco2e`, `net_high_tco2e`, `notes`
- **REDD-specific**: `baseline_loss_rate_yr`, `loss_rate_sem_pct`, `carbon_density_tco2_ha`, `carbon_density_source`, `carbon_density_cv_pct`, `sigma_combined_pct`
- **IFM-specific**: `harvested_area_ha`, `ef_central_tco2_ha`, `sigma_ifm_pct`

`engines/carbon/engine.py`:
- `_estimate_redd()` and `_estimate_ifm()` now return 4-tuple `(net_low, net_high, unc, CalculationTrace)`
- `run_carbon_engine()` and `run_mixed_stratification()` unpack 4-tuples; attach `derivation=trace` to `CarbonEstimate`
- Plantation / peat / forest-fail / no-biomass early returns: `derivation=None` (ADR-0013 compliant)

**ADR-0014 invariant confirmed by test**: `trace.net_low_tco2e == estimate.quantity_low_tco2e` — the trace reproduces the headline range exactly (no re-computation, same `round()` call).

---

### Part 2 — Report restructure (docs/report-derivation-spec.md)

New section order (PDF + DOCX):
1. Header
2. Eligibility Verdict
3. Indicative Carbon Estimate (range + dominant uncertainty)
4. **How This Estimate Is Derived** ← NEW main body
   - REDD: formula + area / loss_rate / SEM / density / CV / sigma / central / pre-buffer / buffer / net rows
   - IFM: formula + area / harvested_area / EF_central / sigma / central / pre-buffer / buffer / net rows
   - Peat: flag rationale (no formula, no tonnage)
5. Methodology (Indicative) + **additionality caveat** ← new
6. Quality Factors
7. Engage 180Climate CTA ← moved BEFORE fine print
8. ── Notes & Supporting Detail (fine print) ──
9. Forest Data Summary
10. Assessment Narrative
11. Uncertainty Band
12. Data Sources
13. Disclaimer

`reports/generator.py`:
- `ReportData.derivation: Optional[Any] = field(default=None)` added
- `_derivation_rows(d)` helper converts CalculationTrace to label/value list
- `_ENGAGE_CTA` M3 wording applied (see Part 3)
- `_ADDITIONALITY_CAVEAT` constant added; rendered in Methodology section

---

### Part 3 — M3 wording (drop the overclaims)

| Location | Before | After |
|---|---|---|
| `api/main.py` `_CARROT` | "appropriate accredited Verra methodology" | "the applicable Verra methodology family (subject to advisor confirmation and Verra's evolving rules)" |
| `api/main.py` `_CARROT` | "~SGD 12K" (ambiguous) | "service fee ~SGD 12K; separate from any carbon credit value" |
| `reports/generator.py` `_ENGAGE_CTA` | same old wording | same M3 fix |
| `narrative/narrator.py` `_ENGAGE_CTA` | same old wording | same M3 fix |
| `narrator.py` `_METHODOLOGY_NOTE["planned_clearfell"]` | no additionality caveat | genuine-harvest-intent + PIPPIB caveat appended |
| `narrator.py` `_METHODOLOGY_NOTE["planned_selective"]` | "IFM (VM0045 / VM0010) — advisor-confirm" | VM0010 lead / VM0045 field-only labels; conservative-floor qualification; additionality caveat |

---

## Tests updated / added

| Test | Change |
|---|---|
| `test_new_cta_wording` (test_report.py:184) | Updated: now asserts "applicable Verra methodology" + "subject to advisor confirmation" + "service fee" |
| `test_redd_derivation_reproduces_range` | NEW — ADR-0014 invariant: REDD trace reproduces exact range |
| `test_ifm_derivation_reproduces_range` | NEW — ADR-0014 invariant: IFM trace reproduces exact range |
| `test_peat_derivation_is_none` | NEW — ADR-0013+0014: peat has derivation=None |
| `test_plantation_derivation_is_none` | NEW — plantation flag has derivation=None |
| `test_derivation_basis_matches_permit_type` | NEW — basis='redd' for HTI, 'ifm' for HA |
| `test_derivation_no_single_number_invariant` | NEW — trace always carries a range |

**Total: 287 tests passed (was 281). 6 new ADR-0014 tests added.**

---

## Peat unchanged ✅ · Numbers unchanged ✅ · Determinism intact ✅ · No confidence % ✅

The derivation trace stores the actual values already computed inside the engine — no re-computation, no new logic. The headline range numbers are identical to the post-ADR-0016 SEM baselines (HTI ~4.46M–11.53M, HA/IFM ~3.05M–5.39M).

---

## Next (not in scope here)
- Cowork verifies: derivation reproduces range, fine print last, M3 wording applied, no overclaims
- Deploy-time items → Gate L (PIPPIB snapshot, credentials, Render, DNS, CI secrets)
- EUDR build = post-carbon (Gate E) per docs/eudr-design-v2.md
