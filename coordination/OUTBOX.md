# OUTBOX — Builder · WO-AUTOROUTE-002 · 2026-06-24

## Status: COMPLETE — stopping for John/Cowork review (peat = FLAG is an ADR-0013 safety guarantee)

WO-AUTOROUTE-002 complete. Opus FAIL fix applied (retry 1/2). **159 tests green.**

---

## What was delivered

### Engine (engines/carbon/engine.py)
- `_evaluate_peat_overlays(boundary) -> LegalOverlayResult`: 5-case logic
  - A∧B → "flag A+B" · A-only → "flag A" · B-only → "flag B"
  - both False → "flag developable uncertain (field survey needed)"
  - data-unavailable (any None) → "flag manual review"
- `_peat_flag_uncertainty(legal_overlay) -> str`: plain-language rationale with "Tier 1" + "baseline" keywords for narrative
- Peat branch of `run_carbon_engine()` returns `quantity_low/high_tco2e = None` + classification
- **Opus FAIL fix**: peat eligibility override after `run_eligibility()`:
  - Forces `verdict = "flagged"` (unless already `"hard_no"`) with reason:  
    `"peat: flag — no tonnage asserted (ADR-0013); manual methodological review required"`
  - Prevents `{None:,.0f}` crash when `verdict=="eligible"` but `quantity_*=None`

### Contracts (core/contracts/__init__.py)
- `CarbonEstimate.quantity_low/high_tco2e: Optional[float]` (None for peat)
- `Stratum` Pydantic `model_validator(mode="after")`: peat soil_type → quantity must be None; raises `ValueError` at construction time — peat-no-tonnage **true by construction**

### API (api/main.py)
- All `is_eligible = verdict == "eligible"` replaced with `has_range = estimate.quantity_low_tco2e is not None` across `/api/carbon`, `/api/report`, `/api/lead`, `_build_report_data()`, `_build_form_data()` — crash-safe for peat

### Report generator (reports/generator.py)
- Carbon range section gated on `data.quantity_low_tco2e is not None` (PDF + DOCX)
- Peat flag section added (PDF + DOCX): "Peat Additionality Flag" heading + plain-language copy covering regulatory context (PP57/2016, Inpres5/2019), why additionality fails on protected peat, and restoration/WRC as potentially additional pathway

### Fixtures
- `tests/fixtures/carbon/WO003_routing_PEAT.json`: downgraded from 18,230,495–28,109,607 tCO2e to `null, null` + `expected_peat_flag` assertion (`overlay_a_khg_intersects: true`, `overlay_b_pippib_intersects: true`)
- `tests/fixtures/carbon/WO004_SMPP_peat_flag.json`: SMPP-style (KHG=true, PIPPIB=null → "flag A + data-unavailable"); `never_hard_no: true` — demonstrates valid restoration path is never auto-excluded

### CI fixture cache (3 centroids)
- Mineral: (-0.500, 117.500) — KHG=false, PIPPIB=false
- Peat dome: (0.900, 117.150) — KHG=true(18500ha), PIPPIB=true(21200ha)
- SMPP: (-2.500, 103.500) — KHG=true(75000ha), PIPPIB=null

### Tests added
- `tests/test_overlays.py`: 29 tests (overlay adapters + new contract types)
- `tests/test_golden.py`: 5 peat-flag parametrized tests (no_tonnage, status_is_flag, never_hard_no, stratum_validator_enforced, overlays_independent)
- `tests/test_report.py`: peat flag section present (PDF+DOCX), peat no-tonnage in report (PDF+DOCX)

---

## ADR-0013 invariants confirmed (by test)
| Invariant | Test |
|-----------|------|
| Peat `quantity_*` = None | `test_peat_flag_no_tonnage` |
| `peat_additionality_status` is a flag | `test_peat_flag_status_is_flag` |
| Never `hard_no` for peat (restoration path open) | `test_peat_flag_never_hard_no` |
| Peat stratum rejects tonnage at construction | `test_peat_stratum_validator_enforced` |
| Overlay A and B evaluated independently | `test_peat_overlays_independent` |
| Peat report section present | `test_peat_flag_section_present` |
| Old PEAT tonnage absent from report | `test_peat_no_tonnage_in_report` |

---

## Opus reviewer finding (d30c274 — FAIL)
`run_eligibility()` is project-type-blind → peat with valid HTI gates gets `verdict=="eligible"` while engine returns `quantity_*=None` → `{None:,.0f}` crash in API; wrong report section selected. **Fixed in b46ff77.**

---

## 159 tests green
```
159 passed, 1 warning in 3.32s
```

---

## Next: WO-AUTOROUTE-003 (when John clears this)
- Non-peat auto-routing: forest-presence gate + REDD+/IFM permit-type routing
- Opus (logic) + Sonnet (UI)
