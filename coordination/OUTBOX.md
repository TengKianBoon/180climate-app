# OUTBOX — Builder → Cowork · WO-EUDR-READINESS-007 (E5) · 2026-06-30

## Status: CI GREEN ✅ — 426 tests pass (+26 new E5 tests) — STOPPED for Cowork review

4 new sections added below the per-plot blocker table. All render guards pass. No banned strings.

---

## What shipped

### `api/main.py` — 4 new response fields on `POST /api/eudr`

| Field | Source | Content |
|---|---|---|
| `readiness` | `_build_readiness()` | 5 categorical ✓/incomplete items; NO numeric score |
| `commodity_evidence` | `_EUDR_COMMODITY_EVIDENCE[commodity]` | Commodity-keyed list of legality docs to gather |
| `who_files` | `_EUDR_WHO_FILES[role]` | Role-keyed `{who, detail, action}` explainer |
| `indonesia_context` | `_EUDR_INDONESIA_CONTEXT` | Static standard-risk context + deadlines |

#### Readiness checklist (5 components)
| Component | Logic |
|---|---|
| Plots have valid geolocation (EUDR Art. 9) | `complete` if `inval_count == 0` |
| Plots screened against the EU's forest maps | always `complete` |
| No deforestation flagged in screening | `complete` if `loss_count == 0 AND incon_count == 0` |
| Commodity legality evidence gathered | always `incomplete` (manual item) |
| Who files the DDS — role identified | always `complete` |

No numeric score — categorical only (ADR-0018 invariant).

#### Commodity evidence (what to gather for DDS)
- `timber` → SVLK (V-Legal), IPK/IPPKH logging permit, HGU, AMDAL, SKSHH
- `palm` → ISPO/RSPO, HGU, IUP-B, land title, no-burn record
- `rubber/cocoa/coffee` → land title (SHM/SHGB), cooperative records, farm registration
- `manual_review` → land title, permits, contact 180Climate

#### Who-files explainer (role-keyed)
- `non_eu_supplier` → "Your EU buyer / importer files the DDS — not you." + geolocation pack action
- `eu_first_placer` → "You file the DDS — before the product is released on the EU market." + TRACES action
- `downstream_operator` → "You verify the DDS filed above you — you no longer file your own." + get reference number action

#### Indonesia context (static)
- Risk: Standard risk → Full due diligence required
- Deadlines: 30 Dec 2026 (large/medium) / 30 Jun 2027 (micro/small)
- Simplified route: explicitly noted as NOT applicable to Indonesia
- Action: start preparing geolocation pack now

### `frontend/index.html` — 4 new sections + CSS

CSS: `.readiness-item.complete/.incomplete`, `.evidence-list li`, `.who-files-box`, `.indonesia-box` + deadline grid.

HTML: after legality/timber notes, before CTA move:
1. "DDS readiness checklist" — card with `.readiness-list`
2. "What to gather for your DDS" — card with `.evidence-list`
3. "Who files the Due Diligence Statement" — `.who-files-box`
4. "Indonesia — standard risk" — `.indonesia-box` with deadline grid

JS in `renderEudrResult()`: renders all 4 sections from API response fields.

### `tests/test_eudr_api.py` — 26 new E5 tests

| Group | Tests |
|---|---|
| Readiness | field present, required fields, no numeric score, geo complete/incomplete, legality always incomplete, deforestation complete/incomplete, no banned strings |
| Commodity evidence | palm (ISPO+HGU), timber (SVLK), rubber/cocoa/coffee, no banned strings across all commodities |
| Who files | field present (who/detail/action), non_eu_supplier says buyer, eu_first_placer says you, downstream says no longer, no banned strings for all 3 roles |
| Indonesia context | field present (risk/deadlines), standard risk + full DD, 2026+2027 deadlines, simplified not applicable, no banned strings |

---

## API smoke

```
2-plot batch (1 loss + 1 clear), palm, non_eu_supplier:
  overall: loss_detected  headline: "1 plot could block your shipment"

readiness (5):
  COMPLETE  | Plots have valid geolocation (EUDR Art. 9)
  COMPLETE  | Plots screened against the EU's forest maps
  INCOMPLETE| No deforestation flagged in screening
  INCOMPLETE| Commodity legality evidence gathered
  COMPLETE  | Who files the DDS — role identified

evidence (5, palm): ISPO, HGU, IUP-B, land title, no-burn record

who_files.who: "Your EU buyer / importer files the DDS — not you."

indonesia: Standard risk | Full due diligence required
  Large and medium operators -> 30 December 2026
  Micro and small operators  -> 30 June 2027
```

---

## mypy + pytest

```
mypy core/contracts/__init__.py --ignore-missing-imports → Success: no issues found
pytest tests/ → 426 passed, 1 warning (was 400; +26 new E5 tests)
```
