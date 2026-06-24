# OUTBOX — Builder · WO-REALMAPS-001 retry 1 · 2026-06-24

## Status: CI GREEN ✅ — STOPPED for Cowork review

---

## CI confirmation

- **Run:** https://github.com/TengKianBoon/180climate-app/actions/runs/28093080581
- **Commit:** a70781a
- **Result:** ✅ 245 passed, 1 skipped, 1 warning in 2.97s (lint-test job 26s)

---

## What was fixed in retry 1 (on top of 2af7d37)

1. **pyproject.toml** — replaced `--basetemp=C:/dev/...` (absolute Windows path, treated as relative on Linux → FileNotFoundError) with `--basetemp=.pytest_tmp` (relative, cross-platform).
2. **requirements.txt** — added `pypdf>=3.0` (missing from install list; `test_report.py` imports it; was pre-installed in dev venv, masking the gap).
3. **.gitignore** — added `.pytest_tmp/`.

*(Prior commit 2af7d37 fixed: ci.yml → pip install -r requirements.txt; cache.py encoding=utf-8; 7 data_cache fixtures re-encoded cp1252→UTF-8; test_slice.py:25 + test_lead_delivery.py:165 encoding.)*

---

## What was delivered (WO-REALMAPS-001 overlay logic — committed in 1f994d3)

### Overlay A — KHG fungsi-lindung (BIG One Map) — LIVE
`core/overlays/khg.py` does a real BIG ArcGIS REST spatial intersect query:
- Endpoint: BIG One Map MapServer/48, WGS84/4326, Query+Data capable
- Field `feg_50k='Fungsi Lindung E.G.'` = protected peat (PP57/2016)
- Fields captured: `kode_khg`, `peat_thick`
- SSL: `verify=False` (Indonesian government CA chain)
- Timeout: 10s; any failure → `intersects=None` → FLAG
- Kill-switch: `KHG_DISABLE_LIVE=true`

### Overlay B — PIPPIB moratorium — SNAPSHOT ONLY
`core/overlays/pippib.py` supports local GeoJSON snapshot query via shapely STRtree:
- Live REST: **not possible** (exhaustive probe — all 16 portal items Map-only, no public FeatureServer/Query; `pippib_h` Query requires auth)
- Current period confirmed: **PIPPIB 2026 Periode I**
- Set `PIPPIB_SNAPSHOT_PATH=/path/to/PIPPIB_2026_I.geojson` at deploy
- Without env var → `intersects=None` → FLAG (conservative)

### ADR-0013 invariant held
`intersects=None` = "unavailable" = FLAG — never collapses to False.

### Tests
- `tests/test_overlay_adapters.py`: 14 deterministic unit tests + 1 network-marked smoke
- 245 total (231 pre-existing + 14 new)

---

## Deploy-time actions (for John, not code blockers)
1. Download PIPPIB 2026 I shapefile from geoportal.menlhk.go.id → `ogr2ogr -f GeoJSON PIPPIB_2026_I.geojson PIPPIB_AR_250K.shp` → set `PIPPIB_SNAPSHOT_PATH`
2. Set `ANTHROPIC_API_KEY` for classifier
3. Set SMTP creds (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM=john@180climate.net`, `EMAIL_USE_SSL=true`)
4. Configure Google Sheets (`GOOGLE_SHEETS_ID`, `GOOGLE_CREDENTIALS_JSON`)
5. Place `brand/180climate-logo.png`
