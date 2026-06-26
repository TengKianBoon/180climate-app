# OUTBOX — Builder → Cowork · WO-METHFIX-002 retry 1/2 · 2026-06-26

## Status: CI GREEN ✅ — STOPPED for Cowork review (281 tests passed, retry 1/2 fix applied)

---

## What was delivered

ADR-0016 (Gate C signed) uncertainty propagation + density-fallback gating. Two corrections:

**M1 — quadrature uncertainty + buffer separation (both REDD and IFM)**
- REDD: `sigma = sqrt(CV_density² + SEM_loss²)`; central = `area × loss_rate × years × density`; VCS buffer (20–30%) deducted **after** and labelled separately.
- **Retry 1/2 fix:** loss uncertainty changed from raw CV (`std/mean`) to **standard error of the mean** (`SEM = std / (mean × sqrt(n))`). SEM reflects uncertainty in the estimated baseline mean; raw CV was inflating ranges by penalising natural inter-annual variability that does not affect the mean estimator.
- IFM: `sigma_IFM = sqrt(CV_intensity² + CV_TEF²) ≈ 0.2149` (pre-computed from TPTI band 26–40 m³/ha and Pearson TEF 1.4–1.5 MgC/m³). Buffer deducted separately. **IFM unchanged.**
- CV_density source hierarchy: `biomass_uncertainty_pct / 100` if set → 0.20 for ESA CCI Biomass v3.0 → 0.30 for IPCC default.
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

| Fixture | Metric | Pre-ADR-0016 (ADR-0015-C2) | ADR-0016 raw-CV | **ADR-0016 SEM (final)** | Notes |
|---------|--------|---------------------------|-----------------|--------------------------|-------|
| HTI_eligible (73,787 ha, ESA CCI 266.5 tCO2/ha) | low | 5,816,578 | 731,904 | **4,456,388** | SEM≈33.1%, sigma≈38.5% |
| HTI_eligible | high | 8,309,397 | 15,782,332 | **11,525,779** | |
| HTI_flag_years (3yr) | low | 872,487 | 109,786 | **668,458** | Same sigma; 3-yr crediting |
| HTI_flag_years | high | 1,246,410 | 2,367,350 | **1,728,867** | |
| HTI_fail_area (1,107 ha, ESA CCI 174.2) | low | 2,098 | 0 | **165** | Raw CV: sigma>1→clip. SEM: sigma<1→positive low |
| HTI_fail_area | high | 2,997 | 10,282 | **5,806** | |
| HA_eligible (IFM, 73,787 ha, 15yr) | low | 2,954,441 | 3,049,142 | **3,049,142** | IFM unchanged |
| HA_eligible | high | 5,565,666 | 5,392,503 | **5,392,503** | IFM unchanged |
| HTI_flag_outside (Point, IPCC 657.1) | low | 2,279,952 | 1,992,050 | **1,994,594** | SEM≈0.9% (stable stub); sigma≈30% |
| HTI_flag_outside | high | 3,257,074 | 4,237,520 | **4,234,612** | |
| WO010_REDD_no_biomass (new) | low | — | null | **null** | M2 gate: no AGB → FLAG |
| WO010_REDD_no_biomass | high | — | null | **null** | |

**Key numbers**: HTI large polygon — SEM = 33.1% (7 years, std/mean = 87.7% raw); sigma = sqrt(0.20² + 0.331²) ≈ 38.5%. Central ≈ 10,393k tCO2e (pre-buffer). HA IFM central ≈ 5,549k (pre-buffer; unchanged). HTI_fail_area SEM = 91.5% for this high-variability small polygon (sigma ≈ 93.6%) — still gives a small positive low (165 tCO2e) instead of clipping to 0.

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
