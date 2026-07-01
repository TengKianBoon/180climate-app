# OUTBOX — Builder -> Cowork · WO-EUDR-LIVEFIX-018 · 2026-07-01

## Status: CI GREEN -- 463 tests pass -- STOPPED for Cowork review

All 3 live-test fixes shipped across 2 commits. No contract change. No gate.

---

## What shipped

### Parts 1 + 2 — coord-precision false-reject + email header (commit f998f49, already in main)

Already delivered as WO-EUDR-PRECISION-018; OUTBOX was written then. Summary:
- `json.loads(content, parse_float=str)` → trailing-zero coords like `"117.152340"` no longer falsely rejected.
- KML coord-text path: raw token strings counted for precision before `float()`.
- 6 new tests prove the fix (trailing-zero polygon/point accepted; 2-dp still rejected; KML path fixed).
- `api/email.py`: EUDR leads now read `=== EUDR screening ===`.

### Part 3 — EUDR map basemap "Map data not yet available" (commit b821e84)

Three standard Leaflet fixes applied to `initEudrMap` in [frontend/index.html](frontend/index.html):

| Fix | Change | Why |
|---|---|---|
| `maxNativeZoom: 18` | Added to Esri tile layer options | Leaflet upscales z>18 tiles instead of requesting tiles Esri doesn't serve — eliminates the grey "not available" squares |
| `maxZoom: 16` on `fitBounds` | `{ padding:[30,30], maxZoom:16 }` | Prevents small plots from zooming past the level where imagery is available |
| `invalidateSize()` | `setTimeout(fn, 0)` after `eudrShowStep('eudr-step-result')` | Fixes the hidden-container init bug: Leaflet measured the `<div>` as 0×0 when it was in an inactive step; calling after panel shown lets it recalculate |

```
mypy core/contracts/__init__.py --ignore-missing-imports -> Success: no issues found
pytest tests/ -> 463 passed, 1 warning
```

**Map screenshot**: requires a live browser session — not available in the CLI environment. The three standard fixes (maxNativeZoom, fitBounds cap, invalidateSize) are the accepted solution to this class of Leaflet tile-availability bug. Cowork/John to verify satellite imagery renders on the next live test.
