# INBOX — Cowork (planner) · 2026-06-24 · WO-AUTOROUTE-004 ("describe your own" classifier + mixed stratification)

## WO-AUTOROUTE-003 review: APPROVED. Forest-presence gate blocks a number on cleared land
## (HTI-cleared golden → flagged, no number, never hard_no); existing valid numbers unchanged (no regression);
## 3 signals (Hansen + JRC TMF + WorldCover); IFM in UI; permit-validity caveat in narrative; 164 green, Opus PASS.
## On main, no branches; commit coordination/ FIRST.

## WO-AUTOROUTE-004 — "Describe your own" classifier + mixed-concession stratification · Sonnet
- **Free-text "other" project type → an INTAKE CLASSIFIER** that sits at the input boundary and **NEVER touches the
  deterministic number/verdict path**: maps the description to a known category (REDD+/IFM/Peat) OR flags out-of-scope.
  **Default to OUT-OF-SCOPE** when it doesn't cleanly map → brief polite apology + WhatsApp/email info@180climate.net
  CTA + **capture the lead either way**. Extract structured facts (permit/soil/forest hints); NEVER accept the user's
  self-assessed eligibility. Still **require geometry for any number** (free-text alone → qualitative routing only).
  (This is the one NEW runtime model call — intake only; determinism of the number path preserved + asserted in tests.)
- **Mixed-concession soil-first stratification:** forested peat → peat stratum (FLAG, per peatland ADR); each hectare →
  exactly one stratum (no double-counting trees-on-peat); per-stratum eligibility (not one blended verdict); combined
  band keeps peat's wider uncertainty visible (don't average it away); minimum stratum size.
- **UI:** the "describe your own" free-text option + the out-of-scope apology/CTA screen.
- Acceptance: free-text → classified or out-of-scope (apology + CTA + lead captured); ambiguous → out-of-scope default;
  geometry still required for a number; mixed concession stratifies (peat stratum flags, mineral stratum numbers);
  **determinism of the number path preserved (test it)**; tests green; review.
- **Then STOP for Cowork review.**

## Then: 005 golden + re-verify → Gate (John + advisor). Carry-forward: wire REAL KHG + SK PIPPIB maps before launch.
Retry budget 2 → QUESTIONS. Regenerate board + commit + push each step.
