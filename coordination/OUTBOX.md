# OUTBOX — written by: Builder (VS Code) · Date: 2026-06-24

## Status: STOPPED — awaiting Cowork review before WO-CARBON-003

WO-CARBON-001 (data adapters) and WO-CARBON-002 (golden cases) complete and merged to main.
68 tests pass. Stopping for Cowork to review data + golden cases before the Opus
number-path work (WO-CARBON-003 eligibility gates + WO-CARBON-004 estimate range).

---

## WO-CARBON-001 — Data Adapter Layer · COMPLETE

**Branches:** `feat/carbon-data` → merged to `main` · commit `c3c1698`

### What was built
- `core/data/adapter.py` — `DataAdapter` Protocol + `register()` + `get_adapter()`.
  Swap via `CARBON_DATA_ADAPTER` env var: `stub` | `gfw_http` (auto = `gfw_http` with disk cache).
- `core/data/biomass.py` — **Real IPCC 2006 Table 4.7 SE-Asia defaults.**
  - Lowland moist tropical: AGB 310 tDM/ha × CF 0.47 × 44/12 × (1 + BGB 0.23) = **657.1 tCO2/ha**
  - Full table: submontane, montane, peat_swamp, dryland all from published IPCC values.
  - Citation embedded in every `ForestData.data_sources` label.
- `core/data/stub.py` — `StubAdapter` (registered `"stub"`). Same deterministic logic as
  old `core/forest.py`; now a proper `DataAdapter` registered via decorator.
- `core/data/gfw.py` — `GFWHTTPAdapter` (registered `"gfw_http"`).
  - HTTP HEAD-checks the Hansen GFC-2022 COG tile (public GCS; no auth).
  - Uses IPCC 2006 biomass (real data). Loss-year series: stub-proxy pending rasterio (WO-CARBON-001b).
  - GEE non-commercial caveat documented inline (ADR-0007).
- `core/data/cache.py` — `CachedAdapter` (SHA-256 keyed on centroid + area).
  5 committed cache files in `tests/fixtures/data_cache/` cover all golden concessions → CI is offline-safe.
- `core/forest.py` — thin facade to `CachedAdapter(get_adapter())`. Public API unchanged.

### Adapter swap test (both satisfy DataAdapter Protocol)
```
CARBON_DATA_ADAPTER=stub     → StubAdapter (deterministic, no network)
CARBON_DATA_ADAPTER=gfw_http → GFWHTTPAdapter (IPCC biomass + Hansen HEAD check)
```

### Sample ForestData — golden concession (-0.5, 117.5)
```
biomass_tco2_per_ha: 657.1 tCO2/ha
data_sources:
  - "GFW/Hansen annual loss (stub — offline/CI mode)"
  - "Biomass: IPCC (2006) NGHGI Guidelines, Vol. 4 AFOLU, Table 4.7 — SE-Asia"
uncertainty_band: "±25 % — deterministic stub; Tier 1 indicative screening"
```

### What remains (WO-CARBON-001b — NOT in this WO)
- rasterio pixel-level read from Hansen COG tiles (GDAL vsicurl, no auth required).
- Adapter interface is ready; only the inner adapter body changes.

---

## WO-CARBON-002 — Golden Cases · COMPLETE

**Branches:** `feat/carbon-golden` → merged to `main` · commit `c75c77b`

### Fixtures (`tests/fixtures/carbon/`)
| Fixture | Permit | Yrs | Geo | Verdict | Gate statuses |
|---|---|---|---|---|---|
| WO002_HTI_eligible | HTI | 20 | 73,787 ha polygon | `eligible` | all pass |
| WO002_HTI_flag_years | HTI | 3 | 73,787 ha polygon | `flagged` | permit_years=flag |
| WO002_HTI_fail_area | HTI | 20 | 1,107 ha polygon | `hard_no` | area=fail |
| WO002_HA_eligible | HA | 15 | 73,787 ha polygon | `eligible` | all pass |
| WO002_HTI_flag_outside | HTI | 20 | Point 40°N,10°E (Europe) | `flagged` | area=flag, inside_iup=flag |
| WO002_routing_HTI | HTI | 20 | 73,787 ha polygon | routing | HTI→APD; never VM0048/VM0007 |
| WO002_routing_HA | HA | 20 | 73,787 ha polygon | routing | HA→IFM; never VM0048/VM0007 |

### `tests/test_golden.py` — 42 parametrized tests
| Test function | Invariant |
|---|---|
| `test_eligibility_golden` | Gate status + overall verdict |
| `test_methodology_is_planned_for_all_elig_cases` | `is_planned=True` (ADR-0001) |
| `test_additionality_basis_for_all_elig_cases` | `additionality_basis="legal harvest right foregone"` |
| `test_methodology_routing_golden` | `baseline_class`, `verra_family_contains`, `cited_methods_must_not_contain` |
| `test_no_forbidden_phrases_in_output` | No `"% accuracy"` or `"% confidence"` in full JSON (ADR-0009 lint) |
| `test_estimate_is_always_a_range` | `quantity_low < quantity_high` always (ADR-0009) |
| `test_determinism` | Same input → same outputs (no randomness in number path) |
| `test_data_sources_labelled` | Non-empty `data_sources` + `uncertainty_band` (WO-CARBON-001 acceptance) |
| `test_biomass_is_real_ipcc_value` | `biomass_tco2_per_ha ≥ 500` (IPCC 2006; old stub was 150–250) |

### Numeric ranges
Not committed yet. Structure/routing/gates/format are pinned now.
WO-CARBON-004 produces `quantity_low / quantity_high` expected values; those freeze these fixtures.

---

## Questions for Cowork before approving WO-CARBON-003

**Q1 (biomass default):** 657.1 tCO2/ha (IPCC 2006 lowland moist tropical) is used for all
Kalimantan concessions. Should peat-bearing concessions default to `peat_swamp` (390.6 tCO2/ha)
when the peat flag is set? WO-CARBON-003/004 will need this distinction.

**Q2 (pixel read):** Hansen rasterio pixel-read is deferred to WO-CARBON-001b.
Is that acceptable, or should it be in the 001/004 scope? The adapter layer is ready.

**Q3 (PEAT golden case):** ADR-0001 has a PEAT routing rule (→ VM0027 interim). No PEAT
golden fixture exists. Should it be added before WO-CARBON-003, or in scope for 003?

**Q4 (WO-003 scope):** The eligibility gate logic already exists in `engines/carbon/engine.py`
(working, tested). Should WO-003 HARDEN/EXTEND it (preferred), or rewrite from spec?

---

## Test summary
- Total: **68 tests** (26 original slice + 42 golden)
- Status: all green locally; pushed to main
- CI: will run on GitHub Actions on push

## Next step (awaiting Cowork go-ahead)
→ WO-CARBON-003 (eligibility gates + Verra routing hardening, **Opus**) when approved.
