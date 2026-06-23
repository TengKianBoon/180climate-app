# OUTBOX — written by: Builder (VS Code) · Date: 2026-06-24

## Status: STOPPED — awaiting Cowork number review before WO-CARBON-005 + Gate M

WO-CARBON-003 (routing + eligibility hardening) and WO-CARBON-004 (real estimate range) complete.
81 tests pass. Opus Reviewer + Verifier APPROVED on both WOs.
Stopping here for Cowork to review the ACTUAL NUMBERS before the narrative (WO-005) + Gate M.

---

## THE NUMBERS (the primary review payload)

### Formula (REDD — APD / IFM)
```
quantity = eligible_area [ha]
         × baseline_loss_rate [ha/ha/yr]     ← 8-yr avg annual loss (2016–2023) / max(area, 25,000)
         × project_duration [yr]              ← min(permit_years_remaining, 30)
         × carbon_density [tCO2/ha]           ← IPCC 2006 Table 4.7 SE-Asia (657.1 tCO2/ha lowland moist)
         × (1 − buffer_deduction)             ← 20% optimistic / 30% conservative

Low estimate:  loss_rate × 0.8, buffer 30%.
High estimate: loss_rate × 1.0, buffer 20%.
```

### Formula (PEAT — VM0027)
```
Dominant term: area × EF_peat [tCO2/ha/yr] × years × (1 − buffer)
  EF range: 9.0–13.0 tCO2/ha/yr
  Source: IPCC 2013 Wetlands Supplement Table 2.1 — tropical drained peatlands

Secondary term: at_risk_ha × peat_swamp_AGB_BGB × (1 − buffer)
  AGB+BGB: 409.3 tCO2/ha (IPCC 2006 Table 4.7 peat_swamp)

Note: peat SOIL carbon (drainage oxidation) is the dominant term (~76% of total estimate).
```

### Golden concession results (Tier 1 indicative screening — not registry-grade)

| Fixture | Permit | Yrs | Area (ha) | Verdict | Low (tCO2e) | High (tCO2e) |
|---|---|---|---|---|---|---|
| HTI eligible | HTI | 20 | 73,787 | eligible | **4,785,077** | **6,835,824** |
| HTI flag years | HTI | 3 | 73,787 | flagged | **717,762** | **1,025,374** |
| HTI fail area | HTI | 20 | 1,107 | hard_no | **127,742** | **182,489** |
| HA eligible | HA | 15 | 73,787 | eligible | **3,588,808** | **5,126,868** |
| HTI point/outside | HTI | 20 | proxy 25k | flagged | **2,279,952** | **3,257,074** |
| PEAT (73k ha) | HTI | 20 | 73,787 | eligible | **12,277,761** | **19,605,702** |

### Key parameters behind the numbers
- Baseline loss rate (golden concession, centroid 0.9°N 117.15°E): **0.8812 %/yr**
  (8-yr average from StubAdapter deterministic data; real Hansen pixel read deferred to WO-CARBON-001b)
- Biomass density: **657.1 tCO2/ha** (IPCC 2006 Table 4.7, lowland moist tropical, SE-Asia)
- Peat biomass: **409.3 tCO2/ha** (peat_swamp AGB+BGB)
- Peat drainage EF: **9.0–13.0 tCO2/ha/yr** (IPCC 2013 Wetlands Table 2.1, tropical drained)
- Buffer: **20–30%** (VCS non-permanence buffer pool proxy)
- IPCC Tier: **Tier 1** throughout (default values; no field measurement)

---

## WO-CARBON-003 summary

### Routing table (ADR-0001 — now fully implemented)
| project_type | permit_type | baseline_class | verra_family | cited_methods |
|---|---|---|---|---|
| PEAT | any | peat | VM0027 interim (advisor-confirm) | [VM0027] |
| REDD | HTI | planned_clearfell | APD (VM0009/legacy) | [VM0009] |
| REDD | HA | planned_selective | IFM (VM0010 / VM0045 v1.2) | [VM0010, VM0045] |

All routes: `is_planned=True`, `additionality_basis="legal harvest right foregone"`.
Never VM0048 family. Never VM0007. Enforced by golden lint tests.

### Eligibility gates (spec §10 — hardened)
All 4 gates (permit_type / permit_years / area / inside_iup) tested across all combos.
69 tests pass; Opus Reviewer + Verifier APPROVED.

---

## Items for Cowork number review

**N1 (biomass proxy — primary number risk):** The 0.8812%/yr loss rate comes from the deterministic stub, NOT real Hansen pixels. This is the dominant uncertainty — the real rate for a specific concession will differ significantly. The estimate is honestly labelled Tier 1 / screening, but Cowork should confirm this proxy magnitude is reasonable for the narrative framing.

**N2 (buffer range):** 20–30% is a conservative proxy for the VCS non-permanence buffer. Real VCS buffer calculation is project-specific. Cowork to confirm this range is defensible for the screening disclaimer.

**N3 (PEAT drainage EF):** 9–13 tCO2/ha/yr is the IPCC 2013 default range. Specific peat projects can vary widely by depth and drainage intensity (5–40 tCO2/ha/yr). The estimate is honest about this as the dominant uncertainty. Cowork to confirm the range is appropriate for a screening tool.

**N4 (stale spec note — peat_swamp biomass):** Spec doc says 390.6; actual IPCC computation = 409.3. Code and fixtures use 409.3 (correct). No action needed in code — noting for Cowork awareness.

**N5 (PEAT dominant-uncertainty wording):** PEAT uncertainty band states "peat depth and drainage intensity" as dominant rather than "baseline harvest rate". Methodologically accurate (drainage term = 76% of estimate). Flag for John at Gate M whether to re-align with the invariant-5 wording or update the invariant.

---

## Counts
- Total tests: **81** (26 original + 43 WO-002 + 1 WO-003 routing + 11 WO-004 range/tier)
- Golden fixtures: **8** (WO001 × 1, WO002 × 7, WO003 × 1 with range)
- Branches: feat/carbon-003, feat/carbon-004 — both merged to main

## Next step (awaiting Cowork go-ahead)
→ WO-CARBON-005 (narrative + Verra rationale, **Sonnet**) when numbers are approved.
→ Then Gate M (John + independent advisor review of numbers + routing + disclaimers).
