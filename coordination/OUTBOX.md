# OUTBOX — written by: Builder (VS Code) · Date: 2026-06-24

## Status: STOPPED — awaiting Cowork final number re-review (WO-CARBON-001c)

WO-CARBON-001c complete. Real ESA CCI Biomass v3.0 2018 density replaces the IPCC 657.1 tCO2/ha
default for polygon inputs. 81 tests pass. Opus Reviewer APPROVED (no blockers).
**Stopping here for Cowork to review the IPCC-default-vs-real-density change before productize.**

---

## THE PRIMARY PAYLOAD: IPCC-default-vs-real density comparison

### What changed in WO-CARBON-001c
- **Density source**: IPCC 2006 Table 4.7 blanket default (657.1 tCO2/ha) → real ESA CCI Biomass v3.0 2018  
  concession-mean AGB, clipped to polygon boundary via rasterio/GDAL vsicurl (CEDA public, no auth).
  Cached as JSON fixtures for CI offline determinism.
- **Fallback chain**: DENSITY_COG_URL env override → ESA CCI Biomass v3.0 2018 (auto) → IPCC Tier-1 (labelled).
- **Loss rates**: UNCHANGED (WO-CARBON-001b real Hansen values; not re-read here).
- **Framing / routing / contracts**: UNCHANGED.

### ESA CCI Biomass v3.0 2018 — what we read

| Polygon | ESA CCI tile | AGB (tDM/ha) | → tCO2/ha (× 0.47 × 44/12) | Source label |
|---|---|---|---|---|
| Large (73,787 ha; 0.9°N centroid) | N10E110 | 155 tDM/ha | **266.5 tCO2/ha** | ESA CCI Biomass v3.0 2018 (CEDA public, tile N10E110, 100m) |
| Small (1,107 ha; -0.015°N centroid) | N00E110 | 101 tDM/ha | **174.2 tCO2/ha** | ESA CCI Biomass v3.0 2018 (CEDA public, tile N00E110, 100m) |
| Point inputs | N/A | N/A | 657.1 tCO2/ha | IPCC 2006 Table 4.7 Tier-1 fallback (no polygon window for pixel read) |

**Why lower than IPCC default:** The ESA CCI concession-mean includes already-disturbed pixels (logged, partial-canopy, edge-degraded areas) within the polygon boundary. The IPCC Tier-1 value (657.1 tCO2/ha) represents intact lowland moist dipterocarp forest — a ceiling, not a concession average. Satellite-measured AGB is the more defensible input for a real concession.

### Golden range comparison: IPCC default (001b) vs real ESA CCI (001c)

| Fixture | 001b low | 001b high | **001c low** | **001c high** | Density ratio |
|---|---|---|---|---|---|
| HTI eligible (20yr, 73,787 ha) | 14,341,738 | 20,488,198 | **5,816,578** | **8,309,397** | 266.5/657.1 = 0.406 |
| HTI flag years (3yr, 73,787 ha) | 2,151,261 | 3,073,230 | **872,487** | **1,246,410** | 0.406 |
| HTI fail area (20yr, 1,107 ha) | 7,914 | 11,306 | **2,098** | **2,997** | 174.2/657.1 = 0.265 |
| HA eligible (15yr, 73,787 ha) | 10,756,304 | 15,366,148 | **4,362,433** | **6,232,048** | 0.406 |
| HTI point/outside (stub/IPCC) | 2,279,952 | 3,257,074 | 2,279,952 | 3,257,074 | **UNCHANGED** (Point → IPCC fallback) |
| PEAT (20yr, 73,787 ha) | 18,230,495 | 28,109,607 | 18,230,495 | 28,109,607 | **UNCHANGED** (peat uses hardcoded peat_swamp AGB, not `forest.biomass_tco2_per_ha`) |

**Why the large polygon dropped ~59%:** Concession-mean AGB (266.5 tCO2/ha) is ~41% of IPCC intact-forest default (657.1 tCO2/ha). A real East Kalimantan logging concession has already lost much of its above-ground biomass to prior selective harvest — 266 tCO2/ha is plausible and conservative.

**Why the small polygon dropped more (~73%):** ESA CCI measured only 174.2 tCO2/ha for that 1,107 ha plot. Small near-border polygons in Kalimantan are often more degraded; the lower biomass reflects this.

---

## Formula (unchanged from WO-CARBON-004)

### REDD (APD / IFM)
```
quantity = eligible_area [ha]
         × baseline_loss_rate [ha/ha/yr]     ← 7-yr avg annual loss (2016–2022) / max(area, 25,000)
         × project_duration [yr]              ← min(permit_years_remaining, 30)
         × carbon_density [tCO2/ha]           ← ESA CCI concession-mean (or IPCC Tier-1 fallback)
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

## Key data parameters (WO-CARBON-001c)

- **Real loss rate (large polygon, tile 10N_110E, 2016–2022):** 2.641 %/yr (avg 1,948.7 ha/yr) — from 001b
- **Real loss rate (small polygon, tile 00N_110E, 2016–2022):** 0.097 %/yr (avg 24.3 ha/yr) — from 001b
- **Carbon density — large polygon:** 266.5 tCO2/ha (ESA CCI Biomass v3.0 2018, tile N10E110, AGB 155 tDM/ha)
- **Carbon density — small polygon:** 174.2 tCO2/ha (ESA CCI Biomass v3.0 2018, tile N00E110, AGB 101 tDM/ha)
- **Carbon density — Point inputs:** 657.1 tCO2/ha (IPCC 2006 Table 4.7 Tier-1 fallback, labelled)
- **Peat drainage EF:** 9.0–13.0 tCO2/ha/yr (IPCC 2013 Wetlands Table 2.1)
- **Buffer:** 20–30% (VCS non-permanence buffer pool proxy)
- **IPCC Tier:** Tier 1 throughout (screening only — not registry-grade)

---

## Opus Reviewer notes (non-blocking)

1. **AGB display rounding (cosmetic):** The label "155 tDM/ha → 266 tCO2/ha" uses a rounded integer for display; the stored `biomass_tco2_per_ha=266.5` is the authoritative figure from the true floating-point AGB. No arithmetic error.
2. **Zero-masking policy:** `treat_zero_as_nodata=True` excludes already-cleared pixels from the concession mean (avoids diluting density with non-forest pixels). This raises the mean above a naive area-weighted average including zeros — defensible for a pre-feasibility screening tool.
3. **JSON encoding:** `±` and arrow characters in uncertainty_band may render as replacement char in some Windows terminals (cp1252); harmless to tests and downstream PDF/DOCX rendering.

---

## Implementation summary

- `core/data/gfw.py` — density fallback chain: DENSITY_COG_URL → ESA CCI auto-tile → IPCC Tier-1; NW-corner tile naming; `_read_agb_cog` via rasterio vsicurl; source label in `data_sources`
- `engines/carbon/engine.py` — dynamic density-source label in `uncertainty` string (ESA CCI vs IPCC)
- `tests/test_golden.py` — `test_biomass_is_real_ipcc_value` → `test_biomass_is_populated_and_labelled`; threshold >50 tCO2/ha (any plausible tropical value)
- `tests/fixtures/data_cache/` — 2 polygon cache files regenerated with real ESA CCI density (266.5, 174.2 tCO2/ha); 3 unchanged
- `tests/fixtures/carbon/` — 4 golden fixtures re-frozen (HTI_eligible, HTI_flag_years, HTI_fail_area, HA_eligible); 2 unchanged (flag_outside, PEAT)
- Opus Reviewer: **APPROVED** (no blockers)

---

## Items for Cowork final number review

**N1 (magnitude credibility):** HTI eligible now 5.8M–8.3M tCO2e over 20 years for 73,787 ha.
Is this more credible than the 14.3M–20.5M IPCC-default estimate? (Sanity check: 73,787 ha × 2.641%/yr × 20yr × 266.5 tCO2/ha × 0.7–0.8 buffer ≈ 5.8M–8.3M. Math correct.)

**N2 (density defensibility):** ESA CCI concession-mean (266.5 tCO2/ha) is 41% of the IPCC intact-forest ceiling (657.1 tCO2/ha). Does this feel right for an East Kalimantan HTI concession that has been selectively logged?

**N3 (Point/PEAT unchanged):** Point inputs and PEAT still use IPCC fallback — by design. No change needed.

**N4 (next step):** If approved, merge `feat/carbon-001c` to main and begin Phase 3 (productize: frontend, report, email). Or flag any concerns before merge.

---

## Counts
- Total tests: **81** (all passing — cached reads, offline CI)
- Re-frozen golden fixtures: 4 (HTI_eligible, HTI_flag_years, HTI_fail_area, HA_eligible)
- Unchanged fixtures: 2 (HTI_flag_outside — Point/stub; PEAT — hardcoded peat_swamp AGB)
- Opus Reviewer: APPROVED (no blockers; 3 non-blocking notes)

## Next step (awaiting Cowork go-ahead)
→ Cowork reviews IPCC-vs-ESA-CCI table above; approves or asks questions → signal to Builder.
→ If approved: merge `feat/carbon-001c` → main → begin Phase 3 (productize).
