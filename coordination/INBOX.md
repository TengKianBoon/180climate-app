# INBOX — the task right now   ·   written by: Cowork (planner)   ·   PHASE 2 STAGED 2026-06-24

## Phase 2 — Carbon Engine batch (WO-CARBON-001 … 005)
Full Work Orders + acceptance + golden-case spec: **docs/wo-carbon-batch.md** (read it).

**Goal:** turn the placeholder slice into the real, defensible carbon engine — real data,
eligibility gates, Verra methodology routing, avoided-emissions RANGE + quality + IPCC tier,
and the Verra-family narrative. Determinism holds: the ONLY LLM call is the narrative.

**How to run (multi-agent showcase + budget):**
- Parallel **git worktrees**, cap ~3 concurrent (this is the portfolio exhibit).
- Tiered models: **Opus** for WO-CARBON-003 + 004 (number/methodology path) + their reviews;
  **Sonnet** for 001 (data), 002 (golden cases), 005 (narrative templates).
- Retry budget 2 → STOP + QUESTIONS.

**Order:**
1. WO-CARBON-001 (real data) ∥ WO-CARBON-002 (golden cases)  → **STOP for Cowork review**
   (data + golden cases are the test oracle — planner checks before the Opus number work).
2. → WO-CARBON-003 (eligibility + routing, Opus)
3. → WO-CARBON-004 (estimate range + quality, Opus)
4. → WO-CARBON-005 (narrative + Verra rationale)
5. → **Gate M** (John + independent advisor: numbers + routing + disclaimers).

**Invariants:** consume contracts only (change = ADR + Gate C); range+band+IPCC tier, never a
single number or "%"; HTI→APD, HA→IFM, Peat→interim; never VM0048 family for foregone-harvest;
never VM0007; additionality = "legal harvest right foregone"; no secrets.

**Start condition:** John pastes the go-ahead to begin WO-CARBON-001 ∥ 002.
