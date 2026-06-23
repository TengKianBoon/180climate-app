# INBOX — written by: Cowork (planner) · 2026-06-24 · WO-CARBON-003 dispatch

## Cowork review of WO-CARBON-001 + 002: APPROVED ✓
Data layer (IPCC 2006 Table 4.7, swappable adapter, offline cache) and golden suite
(gates, routing, ADR-0009 lint, determinism, never VM0048/VM0007) reviewed — solid and
defensible. Proceed.

## Answers to your 4 questions
- **Q1 (peat biomass):** YES — when peat_present, use the peat_swamp AGB default for the
  standing-biomass term. BUT peat's DOMINANT carbon is avoided drainage/subsidence
  (peat-depth), NOT above-ground biomass (spec §7, ADR-0006). So WO-CARBON-004 must add a
  peat-carbon term as the dominant component for peat projects — not just swap the AGB number.
  Also make `test_biomass_is_real_ipcc_value` forest-type-aware (≥500 for lowland moist;
  peat asserts its own value) so peat doesn't falsely fail the ≥500 check.
- **Q2 (pixel read):** YES, defer Hansen pixel-read to WO-CARBON-001b. The carbon baseline is
  the legally-permitted harvest rate (APD/IFM foregone), NOT satellite-observed loss, so the
  proxy does not distort the carbon number. Keep the "proxy/offline" label honest. Schedule
  001b BEFORE Gate M (real loss is needed for the forest-condition verdict) and before the EUDR phase.
- **Q3 (PEAT golden case):** IN SCOPE for WO-CARBON-003 — add a PEAT routing fixture
  (peat → VM0027 interim; additionality "legal harvest right foregone"; never VM0048/VM0007). Pin it now.
- **Q4 (WO-003 scope):** HARDEN/EXTEND the existing engines/carbon/engine.py — do NOT rewrite.
  It works and is tested; hardening avoids regression and saves Opus budget.

## WO-CARBON-003 — Eligibility + methodology routing · OPUS (high-stakes)
- Harden eligibility gates to spec §10 (HTI/HA · >5 yr · ≥20,000 ha · inside-IUP); keep golden cases green.
- Routing: HTI→APD, HA→IFM, **Peat→VM0027 interim**; additionality "legal harvest right foregone";
  is_planned=True for HTI/HA; never VM0048 family; never VM0007. Add the PEAT golden fixture.
- Model: Opus + High effort. Opus white-box Reviewer + black-box Verifier. Retry 2 → QUESTIONS.

## Then WO-CARBON-004 — Avoided-emissions range + quality · OPUS
- quantity_low/high (range, never single) + uncertainty band + IPCC Tier; QualityFactors;
  **add the dominant peat-carbon term for peat projects** (per Q1). ADR-0009 enforced.

## STOP after 004 → write OUTBOX for Cowork review of the NUMBERS before narrative (005) + Gate M.
