# INBOX — Cowork (planner) · 2026-06-24 · ADR-0013 build — WO-AUTOROUTE-001 dispatch

## Gate C signed. Build the ADR-0013 batch (full plan: docs/wo-autoroute-batch.md).
Authoritative: docs/adr/ADR-0013-peatland-routing.md (peat) + ADR-0013-auto-routing.md (non-peat).
**On main, no branches. Commit coordination/ FIRST, then commit+push each step.**

## WO-AUTOROUTE-001 — Contract change + legal/forest data adapters · Opus (contract) + Sonnet (adapters)
- core/contracts: MethodologyRoute → list / new ProjectClassification (per-stratum routes + flags); add IFM +
  "other" to project_type; add peat_additionality_status + legal-overlay + forest-presence flags. Contract-guard
  hook; this is the Gate-C-authorized change.
- Swappable adapters (free, cached for CI): KHG fungsi-lindung/dome (Overlay A), PIPPIB moratorium (Overlay B),
  ESA WorldCover (land cover, NOT peat), JRC TMF (forest disturbance).
- Acceptance: contracts type-check; adapters return cached overlays deterministically; existing 116 tests still green
  (consume-only elsewhere); no secrets.
- **Then STOP and write OUTBOX for Cowork review** (contract is the constitution — high-stakes).

## Then (after Cowork review): 002 peat=FLAG (Opus) → STOP → 003 forest-gate+routing → 004 classifier+mixed →
## 005 golden+re-verify → Gate (John + advisor). See the batch doc.

Retry budget 2 → QUESTIONS. Regenerate board + commit + push each step.
