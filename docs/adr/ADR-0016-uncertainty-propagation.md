# ADR-0016 — Uncertainty propagation (M1) + density-fallback gating (M2)

**Status:** ACCEPTED — Gate C signed by John ("proceed", 2026-06-26) · **Type:** number-path + `core/contracts` change · **Opus** build.
**Origin:** advisor Major findings M1/M2 (Cowork-verified). **Ranges WIDEN — that is the point (honest uncertainty).**

## Context
- **M1:** the range is **buffer-only** — LOW/HIGH differ only by the 0.8 loss-factor / EF band + the 20–30% VCS
  buffer. The buffer is a *non-permanence deduction*, **not estimation uncertainty**. The two genuinely dominant
  uncertainties — **carbon density** and **baseline loss-rate** — are **not propagated**. This quietly undercuts the
  "honest about limits" claim.
- **M2:** when ESA CCI satellite biomass is missing, the engine falls back to the IPCC **657 tCO₂/ha** default and
  still computes a number (labelled, but not gated) — re-opening the over-statement risk. ESA CCI also **saturates**
  above ~150–250 Mg/ha.

## Decision

### M1 — propagate real uncertainty into the range (then buffer separately)
- Build a simple **error budget**: combine **density relative-SE** (from the ESA CCI per-pixel uncertainty layer;
  a wide default CV when only the IPCC value is used) and **loss-rate variability** (the CV of the annual Hansen loss
  series 2016–2023, already on `ForestData.annual_loss_ha`) **in quadrature** → a central estimate ∓ combined band.
- **Then apply the VCS non-permanence buffer (20–30%) as a SEPARATE, explicitly-labelled deduction** — not as the band.
- The `uncertainty` string lists the components separately (density SE, loss CV, buffer). Applies to **REDD (APD) and IFM**.
- Contract: add `ForestData.biomass_uncertainty_pct: Optional[float] = None` (relative SE; the engine consumes it).

### M2 — density-fallback gating + saturation honesty
- ESA CCI available → use it; **state the saturation caveat** (under-estimates dense forest >~150–250 Mg/ha) and
  carry its uncertainty into M1.
- ESA CCI missing, only the IPCC **657 default** → **gate it behind a LOUD "default density — high uncertainty" flag**
  (prominent in the verdict/uncertainty) **and widen the density SE** in the M1 band accordingly. If **no credible
  biomass source at all → FLAG (no number)**.
- **GEDI / ICESat-2** space-LiDAR as a future secondary density source → **pre-launch backlog** (not built here).

## Invariants & tests
- Ranges **widen** to reflect real density + loss uncertainty — **re-baseline the golden ranges (intended); document
  before→after per case.** (The central/point estimate should stay ~stable; the band widens.)
- Buffer is applied **separately and labelled** (not conflated with the uncertainty band).
- Default-density (657) case → **loudly flagged**; no-biomass case → **flag, no number**.
- Peat unchanged (flag/None). Determinism intact. No methodology-routing change (APD/IFM/peat routing untouched).

## Consequences
+ The headline "honest about limits" claim becomes true — the band reflects the real dominant uncertainties.
− REDD + IFM ranges change (wider); goldens re-baselined; `core/contracts` change → **Gate C** (John approved via "proceed").

## Gate C evidence to gather
Contract diff (additive `biomass_uncertainty_pct`); the propagation tests; re-baselined goldens with before→after;
the default-density loud-flag + no-biomass-flag tests.
