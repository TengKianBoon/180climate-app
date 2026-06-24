# GATE-AR READY — ADR-0013 Auto-Routing Build

**Date:** 2026-06-24  
**Work Orders:** WO-AUTOROUTE-001 through WO-AUTOROUTE-005  
**Builder:** Claude Sonnet 4.6 (Opus 4.8 for contract + peat/forest logic reviews)

## What this gate covers
The complete ADR-0013 auto-routing feature:
1. **WO-001** — Contracts + KHG/PIPPIB/WorldCover/JRC-TMF overlay adapters
2. **WO-002** — Peat = FLAG never tonnage; peat-no-tonnage Stratum validator; SMPP fixture
3. **WO-003** — Forest-presence gate; REDD+/IFM routing; HTI-cleared golden
4. **WO-004** — Intake classifier (Haiku, input-boundary-only); mixed-concession soil-first stratification
5. **WO-005** — Golden suite consolidation (all peat overlay combos + forest gate variants); full invariant sweep; this gate pack

## Gate pack
→ `docs/adr-0013-build-gate-pack.md`

## Evidence
- 231 tests green (all invariants, all worked examples, no regressions)
- See `tests/test_golden.py` and `tests/test_classifier.py` for the full invariant suite

## Acceptance criteria status
- [x] peat = FLAG — never a tonnage, by construction and by test
- [x] Two overlays independent (A=KHG, B=PIPPIB) — never collapsed
- [x] Forest-presence gate — cleared land blocks number; intact/light/heavy computed
- [x] Intake classifier out of number path — structural test asserts no import
- [x] Mixed stratification — soil-first, areas sum to boundary, peat stratum = flag
- [x] REDD+/IFM routing correct — HTI→APD, HA→IFM, never VM0048/VM0007/VM0027
- [x] Determinism — run twice → identical output (all fixtures tested)
- [x] Existing non-peat numbers unchanged
- [x] Out-of-scope: leads captured + polite apology CTA

## Sign-off required from
- [ ] **John** — overall approve Gate-AR
- [ ] **Methodology advisor** — confirm peat legal overlay logic + forest gate thresholds + routing correctness

## Carry-forward before Gate L (go-live)
1. Wire REAL KHG + SK PIPPIB shapefiles (overlays are fixtures only)
2. Set ANTHROPIC_API_KEY for classifier in production env
3. Configure EMAIL_FROM, SMTP, GOOGLE_SHEETS creds (Gate P carry-forward)
4. Logo + brand final polish
5. Advisor wording check on peat narrative
