# OUTBOX — Builder · WO-AUTOROUTE-001 · 2026-06-24

## Status: COMPLETE — stopping for Cowork review (contract is the constitution)

WO-AUTOROUTE-001 (contract change + legal/forest data adapters) complete.
145 tests green (was 116 + 29 new overlay tests). Opus reviewer: **PASS**.

---

## What was delivered

### Contract changes (core/contracts/__init__.py — Gate C authorized, ADR-0013)
- `CarbonInput.project_type` expanded: `Literal["REDD", "PEAT", "IFM", "other"]`
- `CarbonInput.project_type_description: Optional[str] = None` (for "other" free-text)
- **New types** (all additive — 116 original tests unaffected):
  - `OverlayIntersection` — result of one spatial overlay query; `intersects=None` means "data unavailable" (NOT a negative result)
  - `LegalOverlayResult` — **two independent overlays**: `overlay_a_khg` (PP57/2016 ecosystem function) + `overlay_b_pippib` (Inpres5/2019 moratorium); plus `peat_additionality_status: str`
  - `ForestPresenceGate` — forest presence + condition gate; `gate_result: Literal["pass", "flag", "fail"]`
  - `Stratum` — one classified land-area unit; soil-first; `quantity_low_tco2e/high: Optional[float]` (None for peat)
  - `ProjectClassification` — `list[Stratum]` + `dominant_soil` + `auto_determined`
- `CarbonEstimate.classification: Optional[ProjectClassification] = None` (backward compat; None = not yet classified)
- `api/main.py` `LeadRequest.project_type` expanded to match

### Adapters (core/overlays/ — Sonnet; swappable; cached for CI)
- `query_khg(boundary)` → OverlayIntersection — KHG fungsi-lindung/dome (PP57/2016)
- `query_pippib(boundary)` → OverlayIntersection — PIPPIB moratorium peatland (Inpres5/2019)
- `query_worldcover(boundary)` → WorldCoverResult — ESA WorldCover 10m land cover (NOT peat ID)
- `query_jrc_tmf(boundary)` → JRCTMFResult — JRC TMF tropical moist forest disturbance
- All: CI fixture cache `tests/fixtures/overlays/{adapter}_{lat:.3f}_{lon:.3f}.json`
- 8 fixture files for 2 centroids: mineral-forest (-0.500, 117.500) + peat-dome (0.900, 117.150)
- Live query placeholders — `_query_live()` returns safe None result (WO-003+ to implement real pixel reads)

### Tests
- `tests/test_overlays.py`: 29 tests — new contract types, KHG/PIPPIB/WorldCover/JRC-TMF adapters (fixture + no-fixture paths), determinism, peat-no-tonnage invariant, IFM/"other" project_type
- `tests/test_contracts.py`: updated import list with new ADR-0013 types
- **145 passed** (29 new + 116 original all green)

---

## Opus reviewer findings
**PASS.** No invariant violations. Key confirmed:
- Two overlays independent (not collapsed)
- `intersects=None` ≠ `False` semantics locked in contract + tests
- Peat tonnage = None locked in `test_stratum_peat_no_tonnage`
- WorldCover note clearly states "cannot identify peat"
- Gate C authorization confirmed

Minor non-blocking observations (for WO-002 awareness):
- `**cached` spread in KHG/PIPPIB adapters — harmless on current fixtures; pydantic rejects unexpected keys
- Mutable `list[str] = []` in Stratum/ProjectClassification — safe in Pydantic BaseModel (deep-copies per instance)

---

## Next: WO-AUTOROUTE-002 (Opus — peat = FLAG never a tonnage)
When Cowork clears this review, the next step is WO-002:
- Wire `LegalOverlayResult` into the engine's peat branch
- Downgrade the existing PEAT golden number (18–28 M tCO2e) to a flag + peat_additionality_status
- Add SMPP-style fixture (deep dome → flag, never excluded)
- Report copy: plain-language rationale next to the peat flag
- STOP for Cowork review (integrity-critical)
