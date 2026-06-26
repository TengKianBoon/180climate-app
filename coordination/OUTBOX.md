# OUTBOX — Builder → Cowork · WO-METHFIX-002 · 2026-06-26

## Status: CI GREEN ✅ — STOPPED for Cowork review (281 tests passed)

---

## What was delivered

ADR-0016 (Gate C signed) uncertainty propagation + density-fallback gating. Two corrections:

**M1 — quadrature uncertainty + buffer separation (both REDD and IFM)**
- REDD: `sigma = sqrt(CV_density² + CV_loss²)`; central = `area × loss_rate × years × density`; VCS buffer (20–30%) deducted **after** and labelled separately.
- IFM: `sigma_IFM = sqrt(CV_intensity² + CV_TEF²) ≈ 0.2149` (pre-computed from TPTI band 26–40 m³/ha and Pearson TEF 1.4–1.5 MgC/m³). Buffer deducted separately.
- CV_density source hierarchy: `biomass_uncertainty_pct / 100` if set → 0.20 for ESA CCI Biomass v3.0 → 0.30 for IPCC default.
- CV_loss = `std(annual_loss_ha 2016–2023) / mean(annual_loss_ha 2016–2023)`.
- `ForestData.biomass_uncertainty_pct: Optional[float] = None` added (Gate C authorized change).

**M2 — density-fallback gating**
- No credible biomass source (`biomass_tco2_per_ha is None`) → FLAG, no number (quantity=null). Uncertainty string cites ADR-0016-M2.
- IPCC default density detected → adds "DEFAULT DENSITY — HIGH UNCERTAINTY" to uncertainty + changes verdict to "flagged" if was "eligible".
- ESA CCI density label includes saturation caveat: "underestimates AGB >~150–250 Mg/ha".
- GEDI/ICESat-2 noted in uncertainty string as pre-launch backlog (not built now).

---

## Contract change (Gate C authorized)

`core/contracts/__init__.py` — `ForestData` extended:
```python
# ADR-0016-M1
biomass_uncertainty_pct: Optional[float] = None
```
`core/data/gfw.py` — `_query_density()` now returns 3-tuple `(biomass, source_label, biomass_uncertainty_pct)`. ESA CCI success → `20.0`; IPCC fallback → `None`.

---

## Before → After: golden ranges

| Fixture | Metric | Before (ADR-0015-C2) | After (ADR-0016-M1) | Notes |
|---------|--------|----------------------|---------------------|-------|
| HTI_eligible (73,787 ha, ESA CCI 266.5 tCO2/ha) | low | 5,816,578 | **731,904** | CV_loss≈0.877 dominates; sigma≈0.899 → wide low |
| HTI_eligible | high | 8,309,397 | **15,782,332** | sigma≈0.899 → wide high |
| HTI_flag_years (3yr, same polygon) | low | 872,487 | **109,786** | Same sigma; 3/20 ratio applied |
| HTI_flag_years | high | 1,246,410 | **2,367,350** | |
| HTI_fail_area (1,107 ha, ESA CCI 174.2) | low | 2,098 | **0** | sigma>1 → `max(0, 1−sigma)=0`; clips to 0 |
| HTI_fail_area | high | 2,997 | **10,282** | Valid: 0 < 10,282 (ADR-0009 preserved) |
| HA_eligible (IFM, 73,787 ha, 15yr) | low | 2,954,441 | **3,049,142** | Quadrature over TPTI+TEF; buffer separate |
| HA_eligible | high | 5,565,666 | **5,392,503** | Range narrows slightly (buffer separation removes cross-product inflation) |
| HTI_flag_outside (Point, IPCC 657.1) | low | 2,279,952 | **1,992,050** | CV_density=0.30; LOUD flag added; verdict flagged |
| HTI_flag_outside | high | 3,257,074 | **4,237,520** | |
| WO010_REDD_no_biomass (new) | low | — | **null** | M2 gate: no AGB → FLAG, no number |
| WO010_REDD_no_biomass | high | — | **null** | |

**Central estimates**: HTI large polygon central = `73,787 × 0.02641 × 20 × 266.5 ≈ 10,393,000` tCO2e (before buffer). Buffer deducted separately. HA IFM central = `31,623 × 175.45 ≈ 5,549,000` (before buffer). Range widens for REDD due to real inter-annual loss variability (Hansen 2016–2023). IFM range adjusts slightly — both are now honest.

---

## Tests added (11 new → 281 total, was 270)

- `test_redd_uncertainty_uses_quadrature` — "in quadrature" in REDD uncertainty
- `test_redd_buffer_labelled_separately` — "separately/separate" in REDD uncertainty
- `test_esa_cci_saturation_caveat_in_redd` — "saturation" in ESA CCI uncertainty
- `test_ipcc_default_loud_flag_in_uncertainty` — "DEFAULT DENSITY" in IPCC-default uncertainty
- `test_ipcc_default_verdict_flagged` — IPCC default → verdict=flagged
- `test_no_biomass_no_number` — quantity_low=None, quantity_high=None
- `test_no_biomass_verdict_flagged` — verdict=flagged
- `test_no_biomass_reason_contains` — reason contains "no credible biomass source"
- `test_no_biomass_uncertainty_label` — uncertainty contains "ADR-0016-M2"
- `test_ifm_uncertainty_uses_quadrature` — "in quadrature" in IFM uncertainty
- `test_ifm_buffer_labelled_separately` — "separately/separate" in IFM uncertainty

---

## Peat unchanged ✅ · Routing unchanged ✅ · Determinism intact ✅

No peat fixture touched. HTI→APD, HA→IFM, Peat→interim routing unchanged. All math is pure Python constants + `math.fsum` — no randomness.

---

## Next (not in scope here)
- M3 wording WO (review uncertainty string language with advisor)
- WO-DERIVE-001 (derivation document, last on the corrected engine)
- Deploy items → Gate L
