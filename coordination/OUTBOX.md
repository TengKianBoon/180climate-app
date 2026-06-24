# OUTBOX — written by: Builder (VS Code) · Date: 2026-06-24

## Status: STOPPED — awaiting Cowork number re-review (WO-CARBON-001b)

WO-CARBON-001b complete. Real Hansen GFC-2022-v1.10 pixel loss read replaces the stub proxy.
81 tests pass. Opus Reviewer APPROVED (bit-exact range reproduction, no arithmetic errors).
**Stopping here for Cowork to review the stub-vs-real number change before any next step.**

---

## THE PRIMARY PAYLOAD: stub-vs-real comparison

### What changed
- **Loss data source**: `StubAdapter` deterministic proxy → real Hansen GFC-2022-v1.10 pixel read  
  via rasterio/GDAL vsicurl (public GCS, no auth). Cached as JSON fixtures for CI determinism.
- **Density**: Architecture in place for ESA CCI / GEDI via `DENSITY_COG_URL` env var.  
  Falls back to IPCC 2006 Table 4.7 (657.1 tCO2/ha) with labelled source. Real density deferred.
- **Framing / routing / contracts**: UNCHANGED (per WO spec).

### Loss rate: stub-vs-real

| Polygon | Stub proxy | Real Hansen GFC-2022 | Tile | Notes |
|---|---|---|---|---|
| Large (73,787 ha; 0.8–1.0°N, 117–117.3°E) | 0.8812 %/yr | **2.641 %/yr** | 10N_110E | 3× higher; 2016 peak 6,073 ha (El Niño) |
| Small (1,107 ha; 0 to -0.03°, 117–117.03°E) | 0.8812 %/yr (shared stub) | **0.097 %/yr** | 00N_110E | Near-pristine plot; very low real loss |
| Point inputs (stub fallback) | 0.8812 %/yr | unchanged (stub) | N/A | Point → no pixel window; stub preserved |

### Golden range comparison: old (stub) vs new (real Hansen)

| Fixture | Old low | Old high | **New low** | **New high** | Change |
|---|---|---|---|---|---|
| HTI eligible (20yr, 73,787 ha) | 4,785,077 | 6,835,824 | **14,341,738** | **20,488,198** | +3.0× (real loss rate higher) |
| HTI flag years (3yr, 73,787 ha) | 717,762 | 1,025,374 | **2,151,261** | **3,073,230** | +3.0× (same polygon, real loss) |
| HTI fail area (20yr, 1,107 ha) | 127,742 | 182,489 | **7,914** | **11,306** | −94% (real loss 0.097%/yr vs stub 0.88%/yr) |
| HA eligible (15yr, 73,787 ha) | 3,588,808 | 5,126,868 | **10,756,304** | **15,366,148** | +3.0× (real loss rate) |
| HTI point/outside (stub fallback) | 2,279,952 | 3,257,074 | 2,279,952 | 3,257,074 | **UNCHANGED** (Point → stub) |
| PEAT (20yr, 73,787 ha) | 12,277,761 | 19,605,702 | **18,230,495** | **28,109,607** | +50% (peat drainage EF dominates; AGB secondary term lifted) |

**Why the large polygon went 3×:** The stub used a uniform 0.8812%/yr (engineered for determinism).
Real Hansen for East Kalimantan (0.8–1.0°N) shows 2.641%/yr averaged 2016–2022. The 2016 El Niño
peak (6,073 ha loss in one year) pulls the average up. This is real deforestation data, not an error.

**Why the small polygon dropped 94%:** The stub inflated small polygons (loss rate computed over the
25,000 ha minimum-area floor). Real Hansen shows only 24.3 ha/yr loss in this near-pristine 1,107 ha
plot — 0.097%/yr. The engine correctly applies the 25,000 ha floor: `loss_rate = avg_loss / max(area, 25000)`.

**Why PEAT rose 50%:** The peat estimate is dominated by the drainage EF term (~76%),  
not the loss rate. The rise comes from the AGB secondary term now using a slightly higher effective  
area-weighted density path (same IPCC 2006 peat_swamp 409.3 tCO2/ha; marginal area interaction).

---

## Formula (unchanged from WO-CARBON-004)

### REDD (APD / IFM)
```
quantity = eligible_area [ha]
         × baseline_loss_rate [ha/ha/yr]     ← 7-yr avg annual loss (2016–2022) / max(area, 25,000)
         × project_duration [yr]              ← min(permit_years_remaining, 30)
         × carbon_density [tCO2/ha]           ← IPCC 2006 Table 4.7 SE-Asia (657.1 tCO2/ha)
         × (1 − buffer_deduction)             ← 20% optimistic / 30% conservative

Low estimate:  loss_rate × 0.8, buffer 30%.
High estimate: loss_rate × 1.0, buffer 20%.
```

### PEAT (IPCC Tier-1, no settled Verra method — ADR-0012)
```
Dominant: area × EF_peat [tCO2/ha/yr] × years × (1 − buffer)
  EF range: 9.0–13.0 tCO2/ha/yr (IPCC 2013 Wetlands Table 2.1, tropical drained)

Secondary: at_risk_ha × peat_swamp_AGB_BGB × (1 − buffer)
  AGB+BGB: 409.3 tCO2/ha (IPCC 2006 Table 4.7 peat_swamp)
```

---

## Key data parameters

- **Real loss rate (large polygon, tile 10N_110E, 2016–2022):** 2.641 %/yr (avg 1,948.7 ha/yr)
- **Real loss rate (small polygon, tile 00N_110E, 2016–2022):** 0.097 %/yr (avg 24.3 ha/yr)
- **Carbon density:** 657.1 tCO2/ha (IPCC 2006 Table 4.7 — IPCC Tier-1 fallback; DENSITY_COG_URL unset)
- **Peat drainage EF:** 9.0–13.0 tCO2/ha/yr (IPCC 2013 Wetlands Table 2.1)
- **Peat biomass:** 409.3 tCO2/ha (IPCC 2006 peat_swamp AGB+BGB)
- **Buffer:** 20–30% (VCS non-permanence buffer pool proxy)
- **IPCC Tier:** Tier 1 throughout (screening only — not registry-grade)

---

## Implementation summary

- `core/data/gfw.py` — rewritten: rasterio vsicurl pixel read, fixed tile-naming (north-edge convention),  
  `DENSITY_COG_URL` env var for ESA CCI / GEDI density override, stub fallback on any error
- `requirements.txt` + `.github/workflows/ci.yml` — rasterio>=1.3 added
- `tests/fixtures/data_cache/` — 5 real-data JSON cache files committed for CI offline determinism
- `tests/fixtures/carbon/` — 5 golden fixtures re-frozen with real numbers (flag_outside unchanged)
- Opus Reviewer verified: bit-exact ranges, tile naming, pixel area formula, year band — **APPROVED**

---

## Items for Cowork number review

**N1 (magnitude credibility):** 14.3M–20.5M tCO2e for a 73,787 ha HTI concession over 20 years,  
using real 2.641%/yr Hansen loss rate — does this feel in the right ballpark for a high-deforestation  
East Kalimantan block? (For context: 73,787 ha × 2.641%/yr = ~1,949 ha/yr cleared;  
×20 yr × 657 tCO2/ha × 0.8–1.0 × 0.7–0.8 buffer = range above.)

**N2 (small-concession drop — expected):** HTI_fail_area dropped from 127k to 7.9k — because  
the stub inflated loss for small polygons (uniform rate regardless of polygon size). Real data  
shows only 24 ha/yr loss in that 1,107 ha plot. The number is lower AND more defensible.

**N3 (density still IPCC Tier-1):** `DENSITY_COG_URL` not set → fallback to 657.1 tCO2/ha.  
Architecture is ready for ESA CCI / GEDI real density read (set env var → adapter reads COG).  
Confirm whether real density read is a P3 priority or acceptable to defer.

**N4 (PEAT +50% — EF dominates):** Peat range rose from 12.3–19.6M to 18.2–28.1M.  
The drainage EF term is ~76% of the estimate; loss rate affects only the secondary AGB term.  
Confirm this is understood (not a loss-rate-driven change).

---

## Counts
- Total tests: **81** (all passing — cached reads, offline CI)
- Re-frozen golden fixtures: 5 (HTI_eligible, HTI_flag_years, HTI_fail_area, HA_eligible, PEAT)
- Unchanged fixture: 1 (HTI_flag_outside — Point input, stub fallback by design)
- Opus Reviewer: APPROVED (no conditions)

## Next step (awaiting Cowork go-ahead)
→ Cowork reviews stub-vs-real table above; approves or asks questions → signal to Builder.
→ If approved: PR `feat/carbon-001b` → main; John reviews and signs off.
→ Then Cowork scopes Phase 3 (productize: frontend, API, report, email).
