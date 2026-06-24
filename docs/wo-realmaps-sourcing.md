# WO-REALMAPS-001 — Wire the real KHG + PIPPIB legal overlays (replace CI stubs)

**Author:** Cowork (planner) · **Date:** 2026-06-24 · **Sources verified live this date.**
**Phase:** P4 pre-launch · **This is the last technical Gate-L blocker.** Until it lands, Overlay A
(peat ecosystem function) and Overlay B (PIPPIB moratorium) are CI stubs, so no real concession gets a
real legal verdict — the peat flag can't actually fire on real geometry.

Authoritative ADRs (unchanged — this WO does NOT touch contracts): `docs/adr/ADR-0013-peatland-routing.md`,
`docs/adr/ADR-0013-auto-routing.md`. **Build on `main`, no feature branches.** Model: **Sonnet** (adapters/IO;
no number-path or contract change). Retry budget 2 → `coordination/QUESTIONS.md`.

---

## The two authoritative sources (each verified live 2026-06-24)

### Overlay A — Peat Ecosystem Function (KHG *fungsi lindung* / dome) · PP 57/2016
- **Primary endpoint — BIG *One Map* (Kebijakan Satu Peta), public, scale 1:50,000:**
  `https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/SUMBER_DAYA_ALAM_DAN_LINGKUNGAN/MapServer/48`
- **Verified live:** `esriGeometryPolygon`; spatial ref **WGS84 (wkid 4326)** — *same CRS as our `Boundary`,
  so no reprojection for the query*; `capabilities: "Map,Query,Data"`; `supportedQueryFormats: JSON, geoJSON`;
  `maxRecordCount: 1000`; supports pagination + query-with-distance; national extent (95.97–140.95 E, −8.01–4.36 N).
- **Decisive field — `feg_50k`** (string), two values:
  - `"Fungsi Lindung E.G."`  → **PROTECTED peat function** → Overlay A `intersects = True`
  - `"Fungsi Budidaya E.G."` → cultivation function
- **Other useful fields:** `kode_khg` (the KHG hydrological-unit code — capture for provenance),
  `peat_thick` (thickness *class* — a useful secondary signal, **but NOT a substitute** for the 3 m legal
  line, which still needs auger/coring/GPR per ADR-0013), `tnh_gambut`, `feg_peat`.
- **Legal basis (from the layer's own metadata):** PP 57/2016, PermenLHK 14/2017, and SK chain
  SK.295/2017, SK.296/2019, SK.938/2019, SK.446/2020, SK.270/2022, SK.1152/2022.
- **Alt endpoint (KLHK PKG, if BIG is down):**
  `https://pkgppkl.menlhk.go.id/arcgis/rest/services/peta_dasar/Peta_Fungsi_Ekosistem_Gambut/MapServer`
- Underlying decree of record: **SK.130/MENLHK/SETJEN/PKL.0/2/2017** (national peat function map;
  fungsi lindung 12,398,482 ha / fungsi budidaya 12,269,321 ha).

### Overlay B — PIPPIB moratorium map · Inpres 5/2019 (permanent moratorium)
- **Endpoint:** `https://geoportal.menlhk.go.id/server/rest/services/dbjvcbsyfs/PIPPIB_AR_250K/MapServer/0`
- **Current version:** **PIPPIB Tahun 2025 Periode II**, **SK Menteri Kehutanan No. 6156 Tahun 2025**
  (issued 17 Sep 2025). Layer 0 is named accordingly. Supports **Query**; shapefile / **UTM, WGS84**, scale 1:250,000.
- **Updated every 6 months** (Inpres 5/2019, Amar Ketiga). **DO NOT hardcode "2025 II"** — read the live
  layer name/date at startup and log it; a 2026 Periode I may already be published.
- **Categories** (the map distinguishes moratorium type): `PIPPIB GAMBUT` (peat), `PIPPIB KAWASAN`
  (protection/conservation forest), `PIPPIB PRIMER` (primary natural forest). For Overlay B (peat moratorium),
  **any** intersecting moratorium polygon ⇒ inside the moratorium; capture which category.
- **⚠ Ministry split (Oct 2024):** KLHK → **Kementerian Kehutanan** (forestry/PIPPIB) + **Kementerian
  Lingkungan Hidup** (environment/peat). Forestry portals are migrating to `*.kehutanan.go.id`
  (e.g. `sigap.kehutanan.go.id`). **Step 1 of this WO: confirm the live PIPPIB endpoint + its current field
  names** by GET-ing `…/MapServer/0?f=pjson` from your machine before coding.

---

## Recommended approach — Option A: live ArcGIS REST spatial query
Both layers are public and `Query`-capable, so query them at runtime instead of bundling shapefiles. This keeps
PIPPIB current automatically and fits the existing overlay design (I/O adapter, per-centroid cache, CI fixtures).

For each adapter — `core/overlays/khg.py` (A) and `core/overlays/pippib.py` (B):
1. POST to `{layer}/query` with: `geometry` = the concession polygon (GeoJSON → Esri JSON, or send the
   bounding envelope for a cheaper first pass), `geometryType=esriGeometryPolygon`, `inSR=4326`,
   `spatialRel=esriSpatialRelIntersects`, `outFields=<key fields>`, `returnGeometry=true` (to sum intersect
   area) or `false` (presence only), `f=geojson`. (Use POST — concession polygons overflow a GET URL.)
2. **A:** add `where=feg_50k='Fungsi Lindung E.G.'` → any feature returned ⇒ `intersects=True`
   (capture `kode_khg`, `peat_thick`, and intersect `area_ha`). No feature ⇒ `intersects=False`.
3. **B:** any moratorium feature intersecting ⇒ `intersects=True` (capture the category: gambut/primer/kawasan).
   None ⇒ `intersects=False`.
4. **Failure path (critical ADR-0013 invariant):** timeout (~10 s), non-200, or parse failure ⇒
   `OverlayIntersection.intersects = None`, `note="data unavailable"` ⇒ **FLAG**. **Never** collapse an error
   to `False` (a false "no intersection" would wrongly imply "developable peat"). `None ≠ negative.`
5. Cache by rounded centroid (existing pattern). **CI stays fixture-based — no live calls in the test suite.**
6. Log the active PIPPIB layer name + date on each live call (provenance for the report).

## Invariants to keep (non-negotiable)
- Overlays **never** enter the deterministic number path (unchanged — assert still holds).
- `intersects=None` = "unavailable" = **FLAG**, never "developable".
- Engine stays pure/deterministic; overlays are I/O behind the cache; tests use fixtures.
- Peat output stays a **FLAG + two independent statuses (A, B)** — **never a tonnage** (`Stratum` validator unchanged).

## Option B (fallback) — snapshot shapefiles
If the gov endpoints prove unreliable/rate-limited: export both layers once (geoportal export, or a formal
KLHK/Kemenhut SHP data request — `indonesia-geospasial.com` documents the procedure), store as **versioned
snapshots** in host config / a data dir (not in git if large), query locally with `geopandas`/`shapely`.
More deterministic, but **must be refreshed each PIPPIB period** — keep a manifest noting the SK number + date.

## Acceptance criteria
1. A concession polygon known to sit on *fungsi-lindung* peat ⇒ Overlay A `intersects=True` ⇒ the peat-flag
   status string fires (still no tonnage).
2. A concession outside the moratorium ⇒ B `intersects=False`; one inside ⇒ `True` (+ category captured).
3. Simulated endpoint failure ⇒ `intersects=None` ⇒ **FLAG**, never a false negative; verdict stays safe.
4. The deterministic suite stays fixture-based and **green (231+)**; add **one** network-marked live smoke
   test (skipped by default in CI).
5. **No change to any carbon number**; peat still no-tonnage; overlays still excluded from the number path.
6. Update `docs/adr/ADR-0013-peatland-routing.md` "Citation status" + record overlay provenance (endpoints,
   PIPPIB SK/period, peat-function SK chain) in the OUTBOX.

## Build steps
1. From your machine, GET `…/PIPPIB_AR_250K/MapServer/0?f=pjson` **and** `…/MapServer/48?f=pjson`; confirm
   live field names + the current PIPPIB period. Note them in the OUTBOX.
2. Implement the REST query per adapter (`httpx`, timeout, retry ≤ 1) + the `None`-on-failure path.
3. Keep CI fixtures; add the one network-marked live smoke test.
4. Re-verify determinism + 231 green; manually spot-check 2–3 real concessions (one peat-lindung, one mineral,
   one inside moratorium).
5. Commit + push (Conventional Commits); write `OUTBOX.md`; **STOP for Cowork review** (this is a pre-launch
   WO, not a gate — Cowork reviews, then routes the Gate-L evidence to John).

*Disclaimers unchanged: pre-feasibility screen, 1:50k/1:250k maps → output is a **flag for manual review**,
never a legal determination. The 3 m depth line still needs field survey.*
