# ADR-0012 — Peat methodology routing correction (no VM0027)

**Status:** Proposed (John approves at/before Gate M) · 2026-06-24
**Deciders:** John (owner), Cowork (planner) · **Input:** independent methodology advisor (Claude.ai project), verified against current Verra status June 2026.
**Corrects:** the peat row of ADR-0001's routing table · **Reaffirms:** ADR-0006.

## Context
WO-CARBON-003 routed peat → **"VM0027 interim,"** following ADR-0001's routing table. The independent Gate-M review found this **wrong on two counts**:
1. **Scope:** VM0027 is a peatland **rewetting** methodology (re-wetting already-drained peat by damming drainage channels). Our additionality is **avoided drainage/conversion** ("legal harvest right foregone") — a different activity VM0027 does not cover.
2. **Status:** VM0027 v1.0 was active only **2014-07-10 → 2023-09-11**, then **inactivated**; **no projects were ever registered** under it.

This also contradicted **ADR-0006** ("never branded to VM0027"). VM0009 excludes peat-soil baselines, so it cannot backfill peat either.

## Decision
1. The peat route **does not cite VM0027** (or any inactivated / activity-mismatched method).
2. Peat is labelled: **"No settled active Verra methodology for avoided tropical-peat conversion as of June 2026 — route to be confirmed by a methodology advisor; figure is IPCC Tier-1 indicative only."**
3. The engine **still computes** the transparent avoided-drainage range (IPCC 2013 Wetlands EF) — methodology-agnostic per ADR-0006. **The number is unchanged; only the cited method changes** (to "to be confirmed").
4. Reaffirms ADR-0006 (agnostic + advisor-confirm; never branded to VM0027). ADR-0001's peat row is corrected accordingly.

## Consequences
- **+** Factually correct, defensible, integrity-safe; resolves the ADR-0001 vs ADR-0006 contradiction.
- **+** The engine estimate is unchanged (still IPCC Tier-1 avoided-drainage range) — low-risk fix.
- **−** No named Verra route for peat until a settled method exists; presented honestly as "to be confirmed."
- **Follow-on:** golden PEAT fixture updated to assert *no VM0027* (and no VM0048/VM0007); methodology.md updated.
