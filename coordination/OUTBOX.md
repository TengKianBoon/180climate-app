# OUTBOX — Builder → Cowork · WO-EUDR-GATEFIX-011 · 2026-06-30

## Status: CI GREEN ✅ — 453 tests pass (+7 new) — STOPPED for Cowork review

Gate-E advisor blocking fix (false-green hero) cleared + all polish items. No backend contract change.

---

## What shipped

### 1. [BLOCKING] PDF hero colour map — `reports/generator.py`

**Root cause fixed:** `hero_bg = red_bg if loss_count > 0 else cta_bg` collapsed 3 states to 2 — `review_needed` fell to green.

**New: module-level `EUDR_HERO_COLOUR` constant** (single source of truth for both PDF and JS):
```python
EUDR_HERO_COLOUR: dict[str, str] = {
    "loss_detected":   "#C0392B",  # red
    "review_needed":   "#8A5A00",  # amber — WCAG AA contrast ~6:1 with white
    "clear_in_screen": "#0E7A30",  # green
}
```

Used in `generate_eudr_pdf()`:
```python
hero_bg = colors.HexColor(EUDR_HERO_COLOUR.get(overall, EUDR_HERO_COLOUR["review_needed"]))
```

Hero sub-copy is also state-specific:
- `loss_detected`: "Plots flagged — your shipment may be affected…"
- `clear_in_screen`: "Screened against the EU's own maps — not certified, still needs a DDS…"
- `review_needed`: "One or more plots are inconclusive — review needed before filing a DDS…"

### 2. JS hero map — `frontend/index.html`

JS `renderEudrResult()` already had an explicit 3-state map. Refactored to object-lookup form to align with PDF constant and make it auditable:

```js
var _heroClass = {
  'loss_detected':   'eudr-hero-red',
  'review_needed':   'eudr-hero-amber',
  'clear_in_screen': 'eudr-hero-clear',
};
heroEl.classList.add(_heroClass[r.overall] || 'eudr-hero-amber');
```

Unknown `overall` now falls to amber (was green via `else` branch).

Also added DOM fallback in `downloadEudrReport()`:
```js
var contactName = _eudrContactName
  || ((document.getElementById('eudr-name') || {}).value || '');
var commodity = _eudrCommodity
  || ((document.getElementById('eudr-commodity') || {}).value || '');
```

Ensures `Screened for` and `Commodity` headers are populated even if state vars were cleared.

### 3. Grammar + label fixes — `api/main.py`

| Location | Before | After |
|---|---|---|
| `_eudr_overall_headline` | "2 plots need review" ✓, "1 plot need review" ✗ | "1 plot **needs** review" |
| readiness checklist | `"No deforestation flagged in screening"` | `"Screening result resolved"` |
| geometry readiness note | `"N plot(s) have invalid geometry"` | `"N plot/plots has/have invalid geometry"` |
| lead form `geometry_summary` | `"N EUDR plot(s)"` | `"N EUDR plot/plots"` |

---

## Tests (+7 new, 2 updated)

| Test | Assertion |
|---|---|
| `test_eudr_hero_colour_map_constants` | `EUDR_HERO_COLOUR` has red/amber/green at correct hex values |
| `test_eudr_hero_colour_map_pdf_loss_differs_from_clear` | loss PDF bytes ≠ clear PDF bytes |
| `test_eudr_hero_colour_map_pdf_review_differs_from_loss_and_clear` | review PDF bytes ≠ loss and ≠ clear |
| `test_eudr_headline_grammar_singular` | singular "needs" for 1 inconclusive plot |
| `test_eudr_headline_grammar_no_plot_s` | no literal `"plot(s)"` in any headline |
| `test_eudr_checklist_label_renamed` | `"Screening result resolved"` present; old `"No deforestation flagged"` absent |
| `test_eudr_geometry_note_no_plot_s` | no literal `"plot(s)"` in readiness notes |
| `test_readiness_screening_result_complete_for_clear` | (renamed from `_no_deforestation_complete_for_clear`) |
| `test_readiness_screening_result_incomplete_for_loss` | (renamed from `_no_deforestation_incomplete_for_loss`) |

```
mypy core/contracts/__init__.py --ignore-missing-imports → Success: no issues found
pytest tests/ → 453 passed, 1 warning (+7 net new)
```
