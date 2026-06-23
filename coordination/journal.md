# JOURNAL — append-only episodic log (feeds the Dreaming/consolidation pass)

- 2026-06-23 · Cowork stood up coordination/ mailbox + self-contained board
- 2026-06-23 · Orchestration redesigned goal-first (docs/orchestration-v2.md)
- 2026-06-23 · Models: all Opus 4.8; parallel fan-out capped for cost
- 2026-06-23 · WO-000 dispatched to INBOX; ADR-0011 accepted; START-HERE runbook written
- 2026-06-24 · Cowork dispatched Phase 2 carbon batch (WO-CARBON-001..005) → INBOX + docs/wo-carbon-batch.md; tiered models, parallel worktrees, Gate M plan
- 2026-06-24 · Cowork reviewed 001+002 (PASS); answered 4 Qs (peat AGB+drainage, defer pixel read, peat golden case in 003, harden-not-rewrite); dispatched WO-CARBON-003/004 (Opus)
- 2026-06-24 · Cowork number review PASS (003+004); flagged N1 observed-loss-vs-planned-baseline as #1 Gate M item; answered N2-N5; dispatched WO-CARBON-005 (narrative, Sonnet) → then Gate M
- 2026-06-24 · Independent Gate-M review: CONDITIONAL GO. Caught peat/VM0027 error (rewetting method, inactivated 2023 — ADR-0012 to correct). N1 framing tightened (conservative floor; drop "FS=bigger number"). Dispatched WO-CARBON-006 fixes →- 2026-06-24 · Cowork independent code-level verification at Gate M: VM0027 only in negative guards (fixture asserts cited_methods_must_be_empty); N1 framing confirmed verbatim in narrator.py; "bigger number" wording removed; 81 tests green. Recommend GO. John signs off.
tree parallel isolation failed (Workflow runner lacks git context); ran sequentially, branched correctly, merged cleanly. STOPPED for Cowork review before WO-CARBON-003/004 (Opus number path).
- 2026-06-24 · WO-CARBON-003 complete (Opus): PEAT routing (VM0027 interim), eligibility hardening, PEAT golden fixture. Opus Reviewer + Verifier APPROVED. 69 tests. feat/carbon-003.
- 2026-06-24 · WO-CARBON-004 complete (Opus): real avoided-emissions range (REDD: area×loss_rate×years×biomass×buffer; PEAT: drainage EF 9-13 tCO2/ha/yr dominant + AGB secondary). 6 golden ranges frozen. IPCC Tier 1 label. QualityFactors non-placeholder. Opus Reviewer + Verifier APPROVED. 81 tests. STOPPED for Cowork number review before narrative + Gate M.
- 2026-06-24 · WO-CARBON-006 complete (Sonnet + Opus review): ADR-0012 implemented — VM0027 removed from peat route everywhere (inactivated 2023, rewetting method); peat labelled "no settled active Verra method as of 2026." Narrative rewritten (WO-CARBON-005): observed-loss floor ≠ planned baseline, no "FS=bigger number," tonnage suppressed for hard_no/flagged, co-dominant REDD uncertainties, CTA, all framing corrections. Opus APPROVED (after one docstring fix). 81 tests green. GATE M READY — STOPPED for John.
- 2026-06-24 · GATE M SIGNED OFF by John. Carbon engine approved: conservative Tier-1, routing corrected per ADR-0012, narrative framing verified, 81 tests green. Phase 2 complete. Holding for Cowork to scope Phase 3.
