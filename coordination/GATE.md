# GATE M READY

**Date:** 2026-06-24
**WO:** WO-CARBON-006 (Gate-M fixes — peat routing correction + narrative rewrite)
**Phase:** P2 · Carbon engine → Phase 3 boundary

## What happened at Gate M

Independent methodology advisor returned CONDITIONAL GO on the carbon engine (WO-CARBON-003/004). All conditions resolved in WO-CARBON-006:

1. **Peat routing corrected (ADR-0012):** VM0027 removed everywhere (engine, fixture, narrative, docs). Peat route now labelled "No settled active Verra method for avoided tropical-peat conversion as of 2026 — route to be confirmed; IPCC Tier-1 indicative." `cited_methods=[]` for peat. Never VM0027 / VM0048 / VM0007.

2. **Narrative rewritten (WO-CARBON-005/006B):** Observed-loss floor separated from planned baseline. "FS = bigger number" framing dropped. VM0009 "active but in transition." IFM "VM0045 / VM0010 — advisor-confirm." Peat EF "conservative." Buffer "risk-tool placeholder." Co-dominant REDD uncertainties. Tonnage suppressed for hard_no/flagged. "Engage 180Climate" CTA added.

3. **Quick wins (WO-CARBON-006C):** HA label updated. Carbon density grounding noted as WO-CARBON-001b scope.

## Evidence

- `coordination/evidence/WO-CARBON-003/review-report.txt` — Opus APPROVED (routing)
- `coordination/evidence/WO-CARBON-004/review-report.txt` — Opus APPROVED (estimate range)
- `coordination/evidence/WO-CARBON-006/review-report.txt` — Opus APPROVED (peat fix + narrative)
- `docs/adr/ADR-0012-peat-routing-correction.md` — approved ADR
- `docs/gate-m-advisor-pack.md` — full methodology/numbers pack (updated post-fix)
- `docs/methodology.md` — updated normative routing table

## Acceptance criteria

- [x] Peat routing: no VM0027 in cited_methods (empty), no VM0027/VM0048/VM0007 in verra_family
- [x] PEAT golden fixture asserts verra_family_must_not_contain + cited_methods_must_be_empty
- [x] Narrative: observed-loss floor ≠ planned baseline (explicit separation)
- [x] Narrative: no "FS = bigger number" framing
- [x] Narrative: tonnage suppressed for hard_no / flagged
- [x] Narrative: "Engage 180Climate" CTA present
- [x] Narrative: buffer labelled as placeholder for risk-tool output
- [x] Narrative: peat EF labelled conservative
- [x] Narrative: co-dominant REDD uncertainties (baseline + carbon density)
- [x] No "% accuracy" / "% confidence" anywhere (ADR-0009)
- [x] 81 golden-case tests green
- [x] ADR-0012 approved and implemented

## Next

John approves Gate M → Phase 3 (frontend + report pipeline + email + PDF/DOCX).

*Never advance a gate yourself — that's John.*

---

# GATE 1 READY

**Date:** 2026-06-24
**WO:** WO-001 — vertical slice spine (end-to-end, ugly but real)
**Written by:** VS Code (builder)

## Acceptance criteria status

- [x] Coords AND GeoJSON parse → Boundary + area_ha; malformed input → clear 422 error
- [x] GFW forest stub returns ForestData; annual_loss_ha series in map overlay
- [x] Placeholder carbon range + non-binding disclaimer in EngineResult
- [x] Lead form submits → email function called with correct payload (file-log mode for CI)
- [x] One golden case committed (`tests/fixtures/carbon/WO001_golden.json`); CI green
- [x] Deterministic: same input → same output; no LLM in number path

## Evidence pointers
- `coordination/evidence/WO-001/pytest-output.txt` — 26 passed, 0 failed
- `coordination/evidence/WO-001/slice-description.txt` — pipe walk-through + per-criterion status
- GitHub commit: https://github.com/TengKianBoon/180climate-app/commit/0ad2722

## What to review
Open `frontend/index.html` via `uvicorn api.main:app --reload` at localhost:8000 to see the slice running.
Enter any coordinates (e.g. `-0.5,117.5`) or paste a GeoJSON polygon to see the full flow.

## Next
John approves Gate 1 → Phase 2 opens: WO-CARBON-001 (real GFW data integration),
WO-CARBON-002 (golden cases), WO-CARBON-003 (eligibility + methodology routing — Opus),
WO-CARBON-004 (estimate range + quality), WO-CARBON-005 (narrative + Verra rationale).

---

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
