# OUTBOX — Builder → Cowork · WO-PIPPIB-LIVE-001 · 2026-06-27

## Status: CI GREEN ✅ — STOPPED for Cowork review (292 tests passed, 7 new)

---

## Live smoke result (required by INBOX)

Query point: polygon centred on `113.9, -2.6` (Central Kalimantan peat point from INBOX).

```
intersects : True
source     : PIPPIB moratorium (Inpres5/2019) — BIG One Map / Kementerian Kehutanan
note       : PIPPIB moratorium intersection confirmed (BIG live query); categories: PIPPIB KAWASAN
```

Endpoint responding. Category `PIPPIB KAWASAN` (conservation/protection forest moratorium) confirmed for that point.

---

## Part A — `core/overlays/pippib.py` rewrite

### What changed

**Flow (new):**
1. Fixture cache (`load_fixture("pippib", lat, lon)`) — CI-safe, deterministic
2. If `PIPPIB_DISABLE_LIVE=true` (kill-switch):
   - If `PIPPIB_SNAPSHOT_PATH` set → snapshot query (secondary fallback)
   - Else → `intersects=None` with note
3. Live BIG One Map query (primary):
   `POST {PIPPIB_BASE_URL}/8/query` with `where=1=1, geometryType=esriGeometryPolygon,
   inSR=4326, spatialRel=esriSpatialRelIntersects, outFields=pippib, returnGeometry=false, f=json`
   - Features found → `intersects=True` + all categories captured in `note`
   - Zero features → `intersects=False`
   - Any error/timeout/HTTP error/`error` in JSON → `intersects=None` → FLAG

**Functions added:**
- `_geojson_to_esri(geojson)` — mirrors khg.py (Polygon/MultiPolygon → Esri rings, wkid 4326)
- `_query_live(boundary, base)` — POST to BIG MapServer/8; field `pippib` (no where-filter needed; all layer features are moratorium zones)

**Functions retained (snapshot fallback):**
- `_load_snapshot(path)` — STRtree cache (unchanged)
- `_query_snapshot(boundary, path)` — shapely STRtree query (unchanged)

**Env vars:**
| Var | Purpose |
|---|---|
| `PIPPIB_BASE_URL` | Override BIG endpoint (testing/migration) |
| `PIPPIB_DISABLE_LIVE` | `true` = skip live query (CI kill-switch) |
| `PIPPIB_SNAPSHOT_PATH` | Local GeoJSON snapshot (secondary; no longer required) |

**Docstring:** updated to document live endpoint, `pippib` field values, and note authoritative version "PIPPIB 2025 Periode II, SK Menteri Kehutanan No. 6156/2025 (BIG-layer currency to be confirmed by advisor — noted, not blocking)."

**ADR-0013 invariant preserved:** `intersects=None` on any failure — never `False` on error.

---

## Part B — deploy-prep

### `requirements.txt`
Added (were missing; deploy crashes on import):
```
gspread>=6.0
google-auth>=2.0
anthropic>=0.30
```

### `api/email.py`
Changed `EMAIL_FROM` default:
```
Before: noreply@180climate.net
After:  john@180climate.net
```
(Both docstring line and runtime default updated.)

---

## Tests

**7 new tests in `tests/test_overlay_adapters.py`:**

| Test | What it checks |
|---|---|
| `test_pippib_live_no_features_returns_false` | Empty features list → `intersects=False` |
| `test_pippib_live_with_feature_returns_true_with_category` | `PIPPIB GAMBUT` feature → `intersects=True` + category in note |
| `test_pippib_live_network_failure_returns_none` | `ConnectError` → `intersects=None` (ADR-0013) |
| `test_pippib_live_server_error_returns_none` | `{"error": ...}` JSON → `intersects=None` |
| `test_pippib_disable_live_returns_none_no_http` | `PIPPIB_DISABLE_LIVE=true` → `None` without HTTP |
| `test_pippib_fixture_used_over_live` | Fixture hit → live never called |
| `test_pippib_live_smoke_peat_point` | `@pytest.mark.network` — skipped in CI; run manually |

**Updated tests (behaviour changed by new flow):**
- `test_pippib_no_snapshot_returns_none` → renamed `test_pippib_disable_live_no_snapshot_returns_none` (now requires `PIPPIB_DISABLE_LIVE=true` to reach None path)
- `test_pippib_snapshot_path_env_var_used` → now sets `PIPPIB_DISABLE_LIVE=true` as well (snapshot only used when live disabled)

**292 tests green (offline). Snapshot tests all pass unchanged.**

---

## Contract unchanged ✅
`OverlayIntersection` fields untouched — no Gate C required.
