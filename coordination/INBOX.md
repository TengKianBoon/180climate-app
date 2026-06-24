# INBOX — Cowork (planner) · 2026-06-24 · WO-AUTOROUTE-002 dispatch (peat = FLAG, never a tonnage)

## WO-AUTOROUTE-001 review: APPROVED (contract faithful to ADR-0013; two overlays independent;
## intersects=None=unknown; forest-gate defaults to flag; backward-compat; 145 green, Opus PASS).
## On main, no branches. Commit coordination/ FIRST, then commit+push each step.

## WO-AUTOROUTE-002 — Peat = FLAG, never a tonnage (ADR-0013-peatland) · Opus
- Wire `LegalOverlayResult` into the engine's peat branch: evaluate Overlay A (KHG) + Overlay B (PIPPIB)
  INDEPENDENTLY → set `peat_additionality_status` + the two ADR status notes (A or B intersects → "presumed
  non-additional…"; neither but peat present → "developability not determinable from free data…").
- **A peat-dominant concession surfaces as a FLAG at the verdict level — NO headline tonnage.** Decide cleanly
  how the engine represents this (e.g. peat strata `quantity_*=None`; the top-level estimate returns a flag result
  rather than a number for peat-dominant cases). Downgrade the existing PEAT golden number (18–28 M) to a flag.
- **STRUCTURAL invariant (add now):** a Pydantic validator on `Stratum` — if `soil_type=="peat"` then
  `quantity_low_tco2e`/`quantity_high_tco2e` MUST be None, else raise. Make peat-no-tonnage true by construction,
  not just by test. (Contract tweak is Gate-C-covered — same ADR.)
- Add an **SMPP-style fixture** (deep dome → flag, NEVER excluded — proves peat≠exclude; restoration pathway).
- **Report copy:** plain-language rationale next to the peat flag (so the owner sees why no number, not "tool failed").
- Acceptance: peat → flag + status, no tonnage anywhere for peat; validator blocks a peat tonnage; existing
  non-peat numbers unchanged; determinism; tests green; Opus review.
- **Then STOP for Cowork review** (integrity-critical).

## Then: 003 forest-gate + REDD+/IFM routing → 004 classifier + mixed → 005 golden + re-verify → Gate (John+advisor).
## Carry-forward (before launch): wire REAL KHG fungsi-lindung + SK PIPPIB maps (overlays are fixtures now).
Retry budget 2 → QUESTIONS. Regenerate board + commit + push each step.
