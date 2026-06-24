# INBOX — Cowork (planner) · 2026-06-24 · WO-AUTOROUTE-003 (forest-presence gate + REDD+/IFM routing)

## WO-AUTOROUTE-002 review: APPROVED. Peat = FLAG never a tonnage — enforced structurally (Stratum validator),
## at the API (has_range guard), and as a regression fixture (SMPP deep-dome → flag, not exclude). 159 green; Opus
## caught + fixed the eligible-with-None crash. On main, no branches; commit coordination/ FIRST.

## WO-AUTOROUTE-003 — Forest-presence gate + REDD+/IFM routing · Opus (logic) + Sonnet (UI)
- **Forest-presence/condition gate (REQUIRED before any REDD/IFM number):** wire `ForestPresenceGate` into the
  engine — confirm standing forest + condition from Hansen tree-cover + loss + ESA CCI/GEDI + JRC TMF.
  `gate_result` pass/flag/fail. **HTI on cleared/scrub → no at-risk forest → flag likely-ineligible (no number).**
- **REDD+/IFM routing by permit + condition:** HTI on standing natural forest → APD; HA on intact/light-degraded →
  IFM; heavily-degraded → low baseline / flag. Set MethodologyRoute per stratum.
- **UI:** project type **optional** (auto-determined from land; advanced override); show the auto-determined classification + the permit-validity caveat (permits overlap / One-Map → advisor-confirm) in the narrative.
- Acceptance: forest-gate blocks a REDD/IFM number when no at-risk forest (add an HTI-on-cleared golden case → flag);
  routing correct on golden cases; existing non-peat numbers unchanged where forest is confirmed; determinism; tests green; Opus review.
- **Then STOP for Cowork review.**

## Then: 004 free-text classifier (out of number path) + mixed soil-first stratification → 005 golden + re-verify → Gate (John + advisor).
## Carry-forward (before launch): wire REAL KHG + SK PIPPIB maps (overlays are fixtures now).
Retry budget 2 → QUESTIONS. Regenerate board + commit + push each step.
