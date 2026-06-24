# OUTBOX — Builder (VS Code) · GATE P SIGNED · Carbon v1 build complete · 2026-06-24

## Status: HOLDING — carbon v1 build complete; awaiting Cowork pre-launch scoping

**Gate P signed by John (2026-06-24).** Real SMTP + Sheets creds wired at deploy (Gate L).

---

## Carbon v1 build summary (all on main, 116 tests green)

| WO | Deliverable | Status |
|----|-------------|--------|
| CARBON-001b | Real Hansen GFC-2022 pixel loss (rasterio vsicurl) | MERGED |
| CARBON-001c | Real ESA CCI Biomass v3.0 2018 density (CEDA; 266.5 tCO2/ha) | MERGED |
| CARBON-003/004 | Engine: eligibility, methodology routing, PEAT (ADR-0012), ranges | MERGED |
| CARBON-005 | Narrative: framing corrected, no single number, Engage CTA | MERGED |
| CARBON-007 | Frontend funnel: input → map + loss chart → verdict + range + IPCC Tier | MERGED |
| CARBON-008 | PDF+DOCX report (reportlab + python-docx), /api/report endpoint, UI tweaks | MERGED |
| CARBON-009 | Lead delivery: email (DOCX attached) + Google Sheet; 15 CI-safe tests | MERGED |

## Invariants upheld
- No single carbon number — always a range + band + IPCC Tier label
- No "%" accuracy/confidence strings
- PEAT → "no settled method" (ADR-0012)
- Legal harvest right foregone stated in narrative
- No secrets in repo (SMTP + Sheets creds are host env vars)
- Deterministic engine (no LLM in number path)

## Next: Cowork scopes pre-launch backlog
See docs/pre-launch-backlog.md for mandatory pre-Gate-L items.
