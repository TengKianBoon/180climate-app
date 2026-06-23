# INBOX — the task right now   ·   written by: Cowork (planner)   ·   DISPATCHED 2026-06-23

## WO-000 — Repo scaffold + typed contracts + .claude harness + green CI
**Phase:** P0 → P1 · **Depends on:** none · **Worktree:** feat/scaffold
**Models:** Haiku/Sonnet (plumbing — no Opus needed) · **Retry budget:** 2 → STOP + write QUESTIONS.md

**Objective:** stand up the foundation everything else is built behind — the monorepo
tree, the typed contracts ("the constitution"), the .claude/ harness, and a green CI.

### In scope
- Repo tree per master spec §12: core/, engines/{carbon,eudr}/, narrative/, frontend/, api/, tests/, docs/.
- core/contracts/ exactly as the Planning-Batch-01 contracts (type-checks clean: mypy/pydantic).
- docs/: ensure methodology.md (ADR-0001 routing), spec, application-plan.md, orchestration-v2.md,
  project-instructions.md, and adr/ADR-0001..0011.md are present.
- .claude/: create CLAUDE.md from Block B of docs/project-instructions.md; settings.json with hooks
  (secret-scan, contract-guard on core/contracts/*, verifier-no-edit, dangerous-bash veto, Stop-gate);
  agents/ (writer, reviewer, verifier, test-writer); skills/ stubs (methodology, geospatial,
  golden-case, brand-180climate, self-improving-code).
- coordination/: ALREADY created by Cowork — do NOT recreate. Wire render_board.py into the end of
  each step (or the Stop-hook) so board.html stays current.
- .github/workflows/ci.yml: lint + type-check + tests on every PR; block merge on red.
- LICENSE (Apache-2.0), .gitignore (secrets, __pycache__, build artifacts, .claude/worktrees/).
- README.md = the portfolio headline: present the system as enterprise-grade AI development — shared-core
  architecture, multi-agent orchestration (Builder + Reviewer + Verifier + Test-writer), Dreaming/memory
  consolidation, the self-improving CoV loop, and the Verifier quality-control gate. Professional, no
  job-seeking language. Include the reproducible free-tier setup + the GEE non-commercial caveat (ADR-0007).

### Acceptance criteria (Definition of Done)
- Tree matches §12; core/contracts/ imports and type-checks clean.
- CI runs and is GREEN on a placeholder test.
- NO secrets anywhere in the repo.
- README documents a reproducible free-tier setup + headlines the orchestration.
- First commit (Conventional Commits) pushed to the PRIVATE GitHub repo; main protected.

### Evidence to return (coordination/evidence/WO-000/, link from OUTBOX.md)
- repo tree listing · CI green link · core/contracts type-check output · main-protection confirmation.

### Gate
Gate 0 — John approves scaffold + contracts + ADR-0001 (+ skim README) before WO-001 starts.
Write coordination/GATE.md = "GATE 0 READY" + evidence pointers, push, and STOP.

---
Next after Gate 0: WO-001 — vertical slice (one concession end-to-end: parse → boundary+area →
GFW loss → placeholder number → map + verdict + AI rationale → capture → email info@180climate.net).
Then Gate 1.
