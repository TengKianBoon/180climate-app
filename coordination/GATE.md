# GATE C SIGNED — ADR-0013 v2 (Auto-Routing + Legal Guardrails)

**Date:** 2026-06-24
**Signed by:** John
**Gate type:** C — contract change (core/contracts/* modification authorised)
**ADR:** docs/adr/ADR-0013 (auto land-routing + IFM + legal guardrails)

---

## What changed (authorised by this gate)

ADR-0013 v2 — auto-routing restructure with four mandatory guardrails:

| # | Guardrail | Rationale |
|---|-----------|-----------|
| 1 | Legal-overlay gate (PIPPIB + KHG) | PP57/2016 dome/3m peat protection + Inpres5/2019 permanent moratorium make "legal harvest right foregone" INVALID on protected peat. Free data: PIPPIB polygon layer. |
| 2 | Forest-presence gate | Carbon project requires actual forest cover; concession with no canopy cannot assert avoided deforestation. |
| 3 | PEAT leans to FLAG (not a tonnage) | "Legal harvest right foregone" additionality is invalid on moratorium peat; existing peat numbers downgraded to flag with explanation. ADR-0012 peat-no-settled-method retained. |
| 4 | Free-text project classifier out of the number path | "Describe your own" intake option is a routing hint only; it never feeds directly into a carbon calculation. |

Additional scope:
- Mixed-concession stratification (where a single IUP spans HTI + HA zones)
- Permit-validity caveat (IUP tenure check before asserting additionality)
- IFM route formalised in methodology router

## Evidence for Gate C

- Advisor review: VERIFIED (independently confirmed PP57/2016 + Inpres5/2019 + Verra regulatory-surplus rule)
- Cowork legal-additionality review: PASS (peat moratorium trap confirmed; ADR-0013 v2 guardrails sufficient)
- John approval: SIGNED 2026-06-24

## Build scope unlocked by this gate

- `core/contracts/` — allowed to add/extend fields for auto-routing result, legal-overlay verdict, forest-presence gate
- `engines/carbon/` — allowed to implement the four guardrails
- `frontend/index.html` — allowed to add "describe your own" option (out of number path)
- Existing golden fixtures — allowed to re-freeze peat case to FLAG verdict (number removed)

## Constraints (invariants remain in force)

- PEAT tonnage output MUST be removed / suppressed; peat verdict = "flagged" with legal-overlay explanation
- "no settled active Verra method as of 2026" pill retained (ADR-0012)
- Legal-harvest-right-foregone framing MUST NOT appear in peat narrative
- Free-text classifier output is a routing hint; it MUST NOT feed a carbon range

---

## Previous gate

GATE P — Lead delivery pipeline (2026-06-24, also signed)

## Next gate

GATE L — Launch readiness (deploy creds, real end-to-end email/Sheet verify, pre-launch-backlog complete)
