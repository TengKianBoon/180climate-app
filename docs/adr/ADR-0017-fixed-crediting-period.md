# ADR-0017 — Fixed 30-year crediting period + per-year average

**Status:** ACCEPTED — Gate C signed by John (2026-06-27, with the value-first overhaul). **Advisor confirm waived by John.**
**Type:** number-path + (minor) `core/contracts` change · **Opus** build. **Changes numbers for every concession with permit < 30 yr.**

## Context
John directs: the tCO₂e estimate must use a **fixed 30-year project lifetime / crediting period for ALL projects and
methodologies** — **not** the actual permit duration — and the report/app must also show an **average tCO₂e per-year
range** alongside the whole-lifetime total. ("39" in the request was a typo; confirmed **30**.) Advisor check waived.

## Decision
1. **Fixed crediting period = 30 yr for all methodologies in the CALCULATION.** Replace `project_years =
   min(permit_years_remaining, 30)` with a constant `project_years = _CREDITING_YR (= 30)` in `_estimate_redd` **and**
   `_estimate_ifm` (IFM `harvested_area = eligible_area × min(1, 30 / cycle_years)`). No permit dependence in the number.
2. **Eligibility gate UNCHANGED:** `permit_years_remaining ≥ 5` still gates eligibility (a valid permit is still
   required) — **only the calculation lifetime is fixed at 30.**
3. **Average tCO₂e/year range:** `avg_per_year_low/high = quantity_low/high ÷ 30`, shown **alongside** the whole-lifetime
   total — on the results page and in the PDF/DOCX, **all methodologies**. (Peat = N/A: flag, no tonnage.)
4. **Display:** "Project crediting period: 30 years" consistently; the derivation trace's `project_years` now reads 30.

## ⚠ Caveat — ON RECORD (advisor check waived by John)
A fixed 30-yr period **decoupled from the permit can over-credit short-permit concessions** vs the "legal harvest right
foregone" basis (a concession with a <30-yr permit would show 30 yr of foregone harvest). **Accepted rationale:** a
standard renewable crediting period is reasonable for an *indicative screen* of project potential (permits renew); the
output is explicitly not registry-grade; and the additionality note already states the legal-right + harvest-intent +
PIPPIB dependence. **Action:** flag this for the advisor's standing review and the full-feasibility stage — the permit
duration must be revisited there before any crediting claim.

## Invariants & tests
- `project_years == 30` for all REDD + IFM estimates (no permit dependence in the calc); the **≥5-yr eligibility gate stays**.
- `avg_per_year` range = total ÷ 30, shown all methodologies, screen + report.
- **Numbers change for all non-peat goldens with permit < 30 — re-baseline + document before→after per case.** Peat
  unchanged (flag/None). Determinism intact. Derivation trace reproduces the range at 30 yr.
- No methodology-routing change (APD/IFM/peat untouched). No confidence %. SEM uncertainty + buffer-separate (ADR-0016) intact.

## Consequences
+ Consistent, comparable crediting period across concessions; a per-year figure (more intuitive for users).
− Over-credits short-permit concessions (caveated above); all non-peat goldens re-baselined; contract gains optional
  `avg_per_year_*` (or computed at the report layer) → **Gate C**.

## Gate C evidence to gather
The `project_years=30` change; the avg/year add; re-baselined goldens (before→after); eligibility gate intact; derivation reproduces.
