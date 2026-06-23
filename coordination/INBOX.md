# INBOX — the task right now   ·   written by: Cowork (planner)   ·   DISPATCHED 2026-06-24

## WO-001 — Vertical slice spine (end-to-end, ugly but real)
**Phase:** P1 · **Depends on:** WO-000 (Gate 0 approved) · **Worktree:** feat/spine
**Models:** Sonnet (wiring) · **Retry budget:** 2 → STOP + write QUESTIONS.md

**Objective:** One sample concession flows end-to-end and produces a verdict + map + placeholder
AI rationale, and a lead email is sent. Prove the whole pipe connects before widening.

### In scope
- `core/geo.py` — parse coord string + GeoJSON dict → Boundary (area_ha, centroid, within_indonesia)
- `core/forest.py` — deterministic GFW-stub → ForestData (real integration is WO-CARBON-001)
- `engines/carbon/engine.py` — eligibility gates + placeholder estimate range (labeled PLACEHOLDER)
- `narrative/narrator.py` — template narrative (no LLM for the slice; LLM wired in WO-CARBON-005)
- `api/main.py` — FastAPI: POST /api/carbon → EngineResult; POST /api/lead → email
- `api/email.py` — SMTP via env vars; file-log fallback for CI
- `frontend/index.html` — single HTML page: form → map (Leaflet CDN) + verdict + lead form
- `tests/test_slice.py` — geo parsing, carbon engine, API route; one committed golden case
- `tests/fixtures/carbon/WO001_golden.json` — golden case (input → expected output)
- Update `requirements.txt` + `.github/workflows/ci.yml` with new deps

### Out of scope / do NOT touch
- Real biomass/peat logic, real GFW API calls
- Methodology routing detail (HTI→APD naming not needed for the slice)
- EUDR engine, parallel modules
- `core/contracts/*` (consume only — no changes)

### Acceptance criteria
- [ ] Coords AND GeoJSON parse → Boundary + area_ha; malformed input → clear error
- [ ] Forest stub returns ForestData; loss overlay renders on the Leaflet map
- [ ] Placeholder carbon range + brief non-binding disclaimer render in the page
- [ ] Lead form submits → email function called with correct payload (tested via mock)
- [ ] One golden case committed; CI green end-to-end
- [ ] Deterministic: same input → same output; no LLM in number path

### Evidence to return (coordination/evidence/WO-001/)
- pytest output (all green) · screenshot/description of the rendered slice · email mock test output · golden case file

### Gate
Gate 1 — John: slice green end-to-end. Write coordination/GATE.md = "GATE 1 READY" + evidence pointers, push, and STOP.
