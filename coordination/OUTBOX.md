# OUTBOX — Builder → Cowork · WO-EUDR-TRIAGE-003 (E3) · 2026-06-30

## Status: CI GREEN ✅ — live smoke PASS — STOPPED for Cowork review (359 tests pass, 33 new)

The EUDR per-plot **satellite triage engine**. Deterministic detection path (Opus). No LLM;
live reads fixture-cached for CI. **Carbon contracts untouched** (no Gate C change).

---

## What shipped

Three adapters (each mirrors the carbon overlay pattern: live HTTP + fixture-cache fallback +
`*_DISABLE_LIVE` switch + version stamp) feeding one deterministic detection engine.

| File | Role |
|---|---|
| `core/overlays/hansen_loss.py` | **Hansen lossyear** — REUSES `core/data/gfw.py` GFWHTTPAdapter; post-2020 loss = Σ(lossyear>2020) ha. `HANSEN_LOSS_DISABLE_LIVE`. |
| `core/overlays/jrc_gfc2020.py` | **JRC GFC2020** — the EU's reference map (credibility anchor); rasterio/vsicurl read of the global single COG; 2020 forest baseline. `JRC_GFC2020_DISABLE_LIVE`. |
| `core/overlays/radd.py` | **RADD** radar alerts via GFW Data API — **stubbed by default** (no free endpoint); enriches, never blocks. `RADD_DISABLE_LIVE`. |
| `engines/eudr/triage.py` | Combines the three → `PlotVerdict.detection` + `datasets_version` + `run_date`. |

### Detection logic (deterministic, pure)
- **`loss_detected`** — forest in JRC-2020 **AND** (Hansen loss_ha > 0 **OR** RADD alert > 2020-12-31)
- **`clear_in_screen`** — forest in JRC-2020 **AND** Hansen-confirmed **zero** post-2020 loss **AND** no RADD alert (RADD `None` allowed — enriches, not blocks)
- **`inconclusive`** — everything else (no/unknown 2020 baseline, Hansen unavailable, sub-resolution, any adapter `None`)

**HONESTY RULE (enforced + exhaustively tested):** when in doubt → `inconclusive` or `loss_detected`, **NEVER `clear_in_screen`**. `clear_in_screen` is the *only* positive case and requires a real 2020 forest baseline + Hansen-confirmed no-loss. Every adapter returns honest `None` on failure (never a fabricated zero / "no forest"). `geometry_invalid` plots (E2) pass through without any adapter call. `geometry_ok` + `plot_satellite_risk` follow from `detection` (ADR-0018 micro-amendments).

---

## 🔭 LIVE SMOKE (the WO's required manual live run)

**Plot:** East Kalimantan polygon, centroid **lat −0.46623, lon 117.31623**, ~900 ha, **no fixture → real live HTTP**. Run date 2026-06-30.

```
[JRC GFC2020]  forest_2020=True   forest_pct=12.6   (single COG, 4.1s)
               https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FOREST/GFC2020/LATEST/single-cog/JRC_GFC2020_V3_COG.tif
[Hansen loss]  loss_after_2020_ha=8.45              (real pixel read, 6.5s)
[RADD]         alert_after_cutoff=None              (stubbed — enriches, not blocking)
----------------------------------------------------------------------
VERDICT: detection=loss_detected   loss_ha=8.45   risk=high   geometry_ok=True
datasets_version: JRC GFC2020 V3 (EC JRC, 10m); Hansen GFC-2022-v1.10 lossyear (30m); RADD (stubbed…)
```

Real end-to-end read confirmed against **both** the EU reference map and Hansen. The honesty
rule was also observed live: on the **first** smoke (before the JRC URL was fixed) JRC 404'd →
`forest_2020=None` → engine returned **`inconclusive`** *despite* Hansen showing 8.45 ha of loss
— it refused to assert without a confirmed 2020 baseline. After pointing JRC at the real COG,
the same plot correctly became **`loss_detected`**.

---

## 🚩 FLAGS for Cowork (as the WO requested — verify, like we did for PIPPIB)

**FLAG 1 — JRC GFC2020 tile URL (RESOLVED during build; please confirm the choice).**
The WO's suggested per-tile name `JRC_GFC2020_V3_{lat}_{lon}.tif` (e.g. `…_N00_E110.tif`) **404'd**.
Live directory probe of `…/GFC2020/LATEST/` found three layouts:
- `single-cog/JRC_GFC2020_V3_COG.tif` ← **now the default** (global COG; one windowed vsicurl read works anywhere — no tile math)
- `single/JRC_GFC2020_V3.tif` (+ `.ovr`)
- `tiles/JRC_GFC2020_V3_{NS}{lat}_{EW}{lon}.tif` — **UNPADDED** (real names `N0_E110`, `N10_E110`, not `N00`)

**Ask:** confirm the single COG is acceptable as the standing source, and confirm the licence
(`copyright.txt` sits alongside; EC open-data / CC-BY-style). Override anytime via `JRC_GFC2020_URL`.

**FLAG 2 — RADD stubbed (enriches, not blocking).**
The GFW Data API RADD query endpoint requires an `x-api-key`, so no clean *free* HTTP endpoint
was confirmable at build. RADD is wired but **off by default** (returns `None`); triage relies on
Hansen + JRC, which is sufficient for `loss_detected`/`inconclusive`. **Ask:** provide/obtain a GFW
Data API key (set `RADD_GFW_API_URL` + `RADD_API_KEY`; key never logged) **or** accept Hansen+JRC-only
for MVP. RADD only ever *adds* `loss_detected`; it can never produce a false `clear_in_screen`.

---

## Tests — `tests/test_eudr_triage.py` (33) + 12 fixtures (4 scenarios × 3 adapters)

15-row detection truth table; exhaustive honesty-rule sweep (clear leaks nowhere); e2e
loss_detected / clear_in_screen / inconclusive(no-baseline) / inconclusive(Hansen-unavailable);
stamps present; determinism (identical re-run); batch geometry_invalid skip (adapter-call
trip-wire) + order/count; adapter fixture loads; Hansen `None` ≠ zero; `*_DISABLE_LIVE` →
unavailable → engine inconclusive; JRC unpadded tile-name + single-COG default resolver.

**359 tests pass** (was 326; +33). Also verified green with **all** live reads disabled
(`*_DISABLE_LIVE=true`) — true CI parity. Pre-existing `test_khg_live_smoke_mineral_land`
excluded (unrelated BIG endpoint `ReadTimeout`).

---

## Commit
`111688e` — pushed to `main` — `feat(eudr): per-plot satellite triage engine — JRC GFC2020 + Hansen + RADD (WO-EUDR-TRIAGE-003, E3)`
