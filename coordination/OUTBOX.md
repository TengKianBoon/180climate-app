# OUTBOX — Builder · WO-REALMAPS-001 · 2026-06-24

## Status: COMPLETE — stopping for Cowork review

---

## What was delivered

### Overlay A — KHG fungsi-lindung (BIG One Map) — LIVE
`core/overlays/khg.py` now does a real BIG ArcGIS REST spatial intersect query:
- Endpoint: BIG One Map MapServer/48, WGS84/4326, Query+Data capable
- Query: `where=feg_50k='Fungsi Lindung E.G.'`, polygon geometry from concession boundary
- Fields captured: `kode_khg`, `peat_thick` → included in `OverlayIntersection.note`
- SSL: `verify=False` (Indonesian government CA chain — expected)
- Timeout: 10s; any failure → `intersects=None` → FLAG (ADR-0013 invariant)
- Kill-switch: set `KHG_DISABLE_LIVE=true` to disable (e.g., for CI environments without committed fixture)

### Overlay B — PIPPIB moratorium — SNAPSHOT ONLY
`core/overlays/pippib.py` now supports local GeoJSON snapshot query:
- Live REST query NOT possible (exhaustive 2026-06-24 probe — see below)
- Set `PIPPIB_SNAPSHOT_PATH=/path/to/PIPPIB_2026_I.geojson` for real intersection check
- Loads once per process into shapely STRtree (fast in-memory spatial index)
- Category field `PIPPIB` captured: PIPPIB GAMBUT / PIPPIB KAWASAN / PIPPIB PRIMER
- Without env var → `intersects=None` → FLAG (conservative, safe)

### PIPPIB endpoint probe findings (2026-06-24) — critical for John
Every public endpoint tested returns Map-only capability or requires auth:
- `geoportal.menlhk.go.id/…/PIPPIB_AR_250K/MapServer/0` → capabilities: "Map", /query returns 400
- All 16 PIPPIB portal items → Map Services only, no FeatureServer with data
- `identify` operation → 0 results (view-only)
- WFS/WCS → 400
- `geoportal.kehutanan.go.id`, `gis.kehutanan.go.id` → DNS not resolving
- `sigap.kehutanan.go.id` → non-JSON responses
- `pippib_h` service → "Map,Query,Data" in metadata, but /query returns "Bad login user" (auth required)
- Current live period: **PIPPIB 2026 Periode I** (updated from 2025 II — confirms the 6-monthly cycle)

**Action needed from John (deploy-time):**
1. Download PIPPIB current snapshot from geoportal.menlhk.go.id (web UI download button)
2. Convert SHP → GeoJSON: `ogr2ogr -f GeoJSON PIPPIB_2026_I.geojson PIPPIB_AR_250K.shp`
3. Host in deploy environment's data dir
4. Set `PIPPIB_SNAPSHOT_PATH=/path/to/PIPPIB_2026_I.geojson`
**Until then: every peat concession shows PIPPIB=data unavailable → FLAG (conservative).**

### Tests
- `tests/test_overlay_adapters.py` (new): 14 deterministic unit tests + 1 network-marked live smoke test
- 1 network smoke test: `pytest tests/ -m network` — checks KHG live endpoint is up; skipped when `CI=true`
- All 245 tests pass (231 existing + 14 new)

### pyproject.toml changes
- Added `--basetemp=C:/dev/180climate-app/.pytest_tmp` to fix Windows PermissionError on pytest-of-User tmp dir
- Registered `network` mark to suppress PytestUnknownMarkWarning

---

## Open items for deploy (not code blockers)
1. PIPPIB snapshot download + `PIPPIB_SNAPSHOT_PATH` env var (John action, deploy-time)
2. `KHG_DISABLE_LIVE=true` not needed in production (CI fixtures cover all committed test cases)
3. Verify KHG live query on a real peat concession during UAT (one SMPP-area polygon)
