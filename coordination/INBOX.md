# INBOX — Cowork (planner) · 2026-06-24 · ADR-0013 (auto-routing) — DESIGN phase (advisor review first)

## Builder: HOLD — do NOT build yet.
ADR-0013 (auto land-characterization + methodology routing + IFM + "describe your own") is in DESIGN.
It is a contract change (Gate C) + methodology-sensitive, so the independent advisor reviews it FIRST.

Drafts:
- docs/adr/ADR-0013-auto-routing.md (the decision record, Proposed)
- docs/adr-0013-advisor-pack.md (the self-contained advisor review pack — John sends this to the Claude.ai project)
- docs/feature-autoroute.md (the design)

## Sequence (no build until step 3):
1. John sends docs/adr-0013-advisor-pack.md to the Claude.ai project → independent review.
2. Cowork folds the advisor's input into ADR-0013; John approves; record Gate C (contract change).
3. THEN Cowork dispatches the build WO batch (data adapters + characterization + engine routing + UI + report).

## Status: carbon v1 BUILD complete (Gate P signed). This is pre-launch (Gate L blocker) work.
