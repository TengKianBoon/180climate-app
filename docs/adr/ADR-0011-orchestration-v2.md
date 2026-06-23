# ADR-0011 — Orchestration v2 (role redesign + enterprise-grade exhibit)

**Status:** Accepted · 2026-06-23 · **Deciders:** John (owner), Cowork (planner)
**Supersedes:** the role/communication parts of the orchestration plan and the role half of ADR-0008.

## Context
The original design put the Claude.ai project (the "Brain") on the critical path, issuing
every Work-Order batch. But the Claude.ai project is the *only* surface blind to the repo
folder, so it is the *only* source of John's cut-paste. John's goal: **minimum cut-paste,
human-in-the-loop only on important decisions**, a deterministic defensible product, and a
public repo that **exhibits enterprise-grade AI development competency** (FDE / AI solution
architect positioning) without any public job-seeking language.

## Decision
1. **Redefine the roles** (full design: `docs/orchestration-v2.md`):
   - **VS Code Claude Code = Builder** — writes/runs/commits; inner Writer→Reviewer→Verifier→Test loop.
   - **Cowork = Orchestrator / Planner / Evaluator / Memory-keeper** — authors Work Orders, independently reviews evidence (separate agent = independence without paste), runs the self-improving CoV, runs the Dreaming/consolidation pass.
   - **John = decision authority at gates only.**
   - **Claude.ai project = optional outside advisor, OFF the critical path** (reads GitHub; one line at a gate, only if a second opinion is wanted).
2. **Communication = the `coordination/` folder** + a self-contained `board.html` regenerated each step (`render_board.py`). Two signals interrupt John: `QUESTIONS.md` non-empty, or `GATE.md` READY.
3. **Models (budget default): tiered.** Haiku/Sonnet for scaffold, plumbing, tests, boilerplate; **Opus only for the number-path Work Orders + adversarial review/verify + CoV.** Cap concurrent agents/worktrees at ~3. (All-Opus-everywhere is reversible for a deliberate showcase session, but is a Max-20x cap risk; tiered is the default.)
4. **Enterprise-grade exhibit (standard practice, not an add-on):** the repo is built to *show competency* — a clean README headlining the orchestration (multi-agent, Dreaming memory, self-improving loops, Verifier quality control), ADRs, golden-case tests, a visible `coordination/` + `evidence/` + `journal.md` trail, Conventional Commits, and **1–2 deliberate Agent-Teams / parallel-worktree showcase sessions in Phase 2** with their evidence preserved.

## Consequences
- **+** Near-zero cut-paste; John pulled in only at gates/questions.
- **+** Independence preserved (Cowork ⟂ VS Code; black-box Verifier; human owns truth at Gate M).
- **+** Budget-safe on Max 20x via tiering + capped parallelism.
- **+** The build doubles as a credible enterprise-AI-orchestration portfolio artifact.
- **−** Cowork polls on a cadence (not real-time); the real-time loop is VS Code's. The folder is async, so neither blocks the other.
