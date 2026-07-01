# OUTBOX — Builder -> Cowork · WO-SHOWCASE-020 · 2026-07-01

## Status: CI GREEN -- 463 tests pass -- STOPPED for Cowork review

Docs + tags + releases only. No code change. No gate.

---

## What shipped

### 1. README + roadmap commit (f2a447b)

`git add README.md docs/production-roadmap.md`
`git commit -m "docs: portfolio showcase README + production roadmap"`

Both files were already present in the working tree (README.md modified, docs/production-roadmap.md untracked).

### 2. Annotated SemVer tags

| Tag | Commit | Message |
|---|---|---|
| `v1.0.0` | `ceb8b1d` (GATE P SIGNED — carbon v1 build complete) | Carbon Pre-Feasibility Engine (live) |
| `v1.1.0` | `f2a447b` (HEAD — docs commit above) | EUDR Export Readiness Engine (live) |

`git push --tags` → both tags visible on GitHub.

### 3. GitHub Releases (gh CLI — TengKianBoon authenticated)

| Release | URL |
|---|---|
| v1.0.0 — Carbon Pre-Feasibility Engine (live) | https://github.com/TengKianBoon/180climate-app/releases/tag/v1.0.0 |
| v1.1.0 — EUDR Export Readiness Engine (live) | https://github.com/TengKianBoon/180climate-app/releases/tag/v1.1.0 |

Release notes match the WO verbatim.

```
pytest tests/ -> 463 passed, 1 warning
```
