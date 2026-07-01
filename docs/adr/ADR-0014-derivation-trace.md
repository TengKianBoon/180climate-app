# ADR-0014 — Calculation derivation trace (report transparency)

**Status:** ACCEPTED — Gate C signed by John, 2026-06-26 · **Deciders:** John (owner), architect
**Type:** contract change (`core/contracts`) → contract-guard hook · number-path-adjacent → **Opus** build + review

## Context
The report and results page state a carbon **range** but only *summarize* how it was derived. John wants the report to
**show the derivation** so a buyer/auditor can follow (and check) the math. The engine (`_estimate_redd`) already
computes a fully transparent formula:

```
avoided emissions = eligible_area[ha] × baseline_loss_rate[/yr] × project_years × carbon_density[tCO2/ha] × (1 − buffer)
  net_low  = area × (loss_rate×0.8) × years × density × (1 − 0.30)
  net_high = area ×  loss_rate       × years × density × (1 − 0.20)
```

…but it does **not expose the intermediate values** it used. A report that *reconstructs* the formula from partial
fields risks not reproducing the exact stated range — which would undercut the very trust we're building.

## Decision
Add an **optional, read-only** `derivation` field to `CarbonEstimate` — a typed **`CalculationTrace`** the engine
populates with the **actual numbers it used**. This **changes no figure**; it only surfaces what is already computed.

`CalculationTrace` (REDD/IFM):
`formula:str` · `eligible_area_ha:float` · `baseline_loss_rate_yr:float` · `loss_rate_low_factor:float` (0.8) ·
`loss_rate_high_factor:float` (1.0) · `project_years:int` · `carbon_density_tco2_ha:float` ·
`carbon_density_source:str` · `loss_data_source:str` · `buffer_low:float` (0.20) · `buffer_high:float` (0.30) ·
`gross_low_tco2e:float` · `gross_high_tco2e:float` · `net_low_tco2e:float` · `net_high_tco2e:float` · `notes:str`.
**PEAT:** `derivation=None` (flag, no tonnage — ADR-0013 unchanged). **Ineligible/flagged-no-number:** `derivation=None`.

## Invariants (must hold; hook + tests enforce)
- **Reproduces the range exactly:** `trace.net_low_tco2e == estimate.quantity_low_tco2e` and `net_high == quantity_high`
  (regression test). Recomputing from the components equals the net (within rounding).
- **No figure changes** anywhere; all existing golden ranges identical. Determinism intact.
- **Peat stays flag/no-tonnage**; the LLM stays out of the number path (the trace is pure-function output).
- `derivation` is `Optional` (backward-compatible; `None` ⇒ not shown).

## Consequences
+ The report can render a faithful, reproducible derivation (the app's core defensibility, made visible).
+ `core/contracts` grows by one optional field + one model — **requires this ADR + Gate C**.
− Opus build + a reproduction test; advisor reads the derivation wording before go-live.

## Gate C evidence to gather (for John/architect sign-off)
Contract diff (additive only), the reproduction test green, all golden ranges unchanged, peat still `None`.
