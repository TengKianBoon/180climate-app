# OUTBOX — Builder -> Cowork · WO-SHOWCASE-022 · 2026-07-01

## Status: CI GREEN -- 463 tests pass -- STOPPED for Cowork review

Docs/git only. No code touched. No gate.

---

## What shipped (commit d857a9f)

### 1. 4 missing ADRs published

Added to `docs/adr/` (were untracked, not gitignored):
- `ADR-0014-derivation-trace.md`
- `ADR-0015-plantation-gate-ifm-basis.md`
- `ADR-0017-fixed-crediting-period.md`
- `ADR-0018-eudr-contracts.md`

`git ls-files docs/adr | wc -l` → **19** ✓ (ADR-0001..0018 all present; the two ADR-0013 files are a known numbering artifact, left as-is).

### 2. Root tidied — 6 loose files archived

`mkdir -p docs/archive` + `git mv` for all 6:

| From (root) | To |
|---|---|
| `180climate-MASTER-handover-spec.md` | `docs/archive/` |
| `180climate-build-and-orchestration-plan.md` | `docs/archive/` |
| `180climate-planning-batch-01.md` | `docs/archive/` |
| `180climate-carbon-confidence-report.pdf` | `docs/archive/` |
| `180climate-carbon-confidence-report (1).docx` | `docs/archive/` |
| `180climate-app-docs.zip` | `docs/archive/` |

`ls 180climate-*` in root → `No such file or directory` ✓

### 3. README changes committed

Cowork's edits: "How to read this repo" tour + corrected hooks(3)/skills(5) wording surfacing the `.claude/` harness.

```
pytest tests/ -> 463 passed, 1 warning
```
