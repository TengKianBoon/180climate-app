# GATE 0 READY

**Date:** 2026-06-24
**WO:** WO-000 — scaffold + typed contracts + .claude harness + green CI
**Written by:** VS Code (builder)

## Acceptance criteria status

- [x] Tree matches spec §12 (`core/`, `engines/carbon/`, `engines/eudr/`, `narrative/`, `frontend/`, `api/`, `tests/`, `docs/`)
- [x] `core/contracts/__init__.py` imports and type-checks clean (`mypy` — "Success: no issues found in 1 source file")
- [x] CI runs and is GREEN on 5 placeholder tests (pytest 5/5 locally; workflow pushed and triggered on GitHub)
- [x] No secrets in the repo (`.gitignore` covers `.env`, `*.key`, `*.pem`; hook enforced)
- [x] README documents a reproducible free-tier setup + headlines multi-agent orchestration
- [x] `.claude/` harness: `CLAUDE.md`, `settings.json` (3 hooks), `agents/` × 4, `skills/` × 5
- [x] `docs/adr/ADR-0001..0011.md` committed
- [x] First commit pushed to private GitHub repo: https://github.com/TengKianBoon/180climate-app
- [~] `main` protected: **one open question — see QUESTIONS.md** (GitHub Free plan limitation; requires Pro or public repo for classic branch protection)

## Evidence pointers
- `coordination/evidence/WO-000/repo-tree.txt` — full git ls-files
- `coordination/evidence/WO-000/contracts-typecheck.txt` — mypy + pytest output
- `coordination/evidence/WO-000/ci-green.txt` — GitHub Actions URL (triggered)
- `coordination/evidence/WO-000/main-protection.txt` — limitation + three options for John

## One decision needed before full sign-off
See **QUESTIONS.md Q1**: branch protection on the private repo requires GitHub Pro.
Choose A (upgrade Pro), B (make public now), or C (defer to portfolio flip).
Everything else is complete.

## Next
John approves Gate 0 → WO-001 (vertical slice spine) begins.
