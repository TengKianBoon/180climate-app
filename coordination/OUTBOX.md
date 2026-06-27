# OUTBOX — Builder → Cowork · WO-VALUEFIRST-001 · 2026-06-27

## Status: CI GREEN ✅ — STOPPED for Cowork review (285 tests passed)

---

## What was delivered

### Part 1 — Engine: ADR-0017 (project_years = 30 fixed; per-year fields)

**`core/contracts/__init__.py`** (Gate C signed):
- Added `quantity_low_per_yr_tco2e: Optional[float] = None`
- Added `quantity_high_per_yr_tco2e: Optional[float] = None`

**`engines/carbon/engine.py`**:
- `project_years = min(inp.permit_years_remaining, _MAX_CREDITING_YR)` → `project_years = _MAX_CREDITING_YR` (both `_estimate_redd` and `run_mixed_stratification`)
- Per-year fields populated: `round(low / _MAX_CREDITING_YR, 0)` and `round(high / _MAX_CREDITING_YR, 0)` in non-peat returns
- Peat `quantity_low_per_yr_tco2e = None`, `quantity_high_per_yr_tco2e = None` (no tonnage for peat)

**Golden re-baselines** (before → after, all 30-yr fixed):

| Fixture | Was | Now |
|---|---|---|
| HTI_eligible (20yr→30yr) | 4,456,388 – 11,525,779 | 6,684,581 – 17,288,669 |
| HTI_flag_years (3yr→30yr) | 668,458 – 1,728,867 | 6,684,581 – 17,288,669 |
| HTI_fail_area (20yr→30yr) | 165 – 5,806 | 248 – 8,709 |
| HA_eligible IFM (15yr→30yr) | 3,049,142 – 5,392,503 | 6,098,285 – 10,785,006 |
| HTI_flag_outside (20yr→30yr) | 1,994,594 – 4,234,612 | 2,991,891 – 6,351,918 |

IFM 30yr math: harvested_area = area × min(1, 30/35) = area × 6/7 (≈2× the 15yr figure). REDD: linear ×30/20 = 1.5×.

**`api/main.py`**: `_build_report_data()` + `loss_overlay` dict now include per-year fields and `derivation`.

---

### Part 2 — Value-first report (PDF + DOCX)

**`reports/generator.py`** — complete rewrite to value-first design:

Section order (ADR-0009 invariants preserved):
1. **Header** — logo + concession meta
2. **Hero** — green table cell: range + per-year + worth box (US$8/tonne indicative)
3. **Why Your Forest Qualifies** — substantive APD/IFM/peat pathway copy
4. **How Strong Is Your Project** — quality cards as strengths (2-column, no caveat language)
5. **How Your Number Is Built** — derivation table (if derivation present); peat: qualitative flag explanation
6. **What We Found on Your Land** — forest data bullets + flags reframed as opportunities + data sources credit
7. **How to Grow This Number** — RKU/RKT upload prompt
8. **Engage 180Climate** — dark green CTA box
9. **Footer (ONE line)** — "Indicative satellite screening — not a verified credit issuance or legal advice. IPCC Tier 1 approach. How this is calculated & legal notes: 180climate.net/methodology."

Removed from report body: `_DISCLAIMER`, `_ADDITIONALITY_CAVEAT`, `_DOMINANT_UNC` — all caveats remain in engine logic + docs/methodology.md only.

**`INDICATIVE_PRICE_USD_PER_TCO2E = 8`** — presentation-layer config only; no contracts change.

---

### Part 3 — Value-first result page (frontend)

**`frontend/index.html`**:

CSS additions: `.result-hero`, `.worth-box`, `.moves-h`, `.move`, `.cta-move`, `.result-foot`

New HTML structure (step-result):
- `#result-hero` card → `#result-lbl`, `#result-num`, `#result-sub`, `#result-chip`
- `#worth-box` → `#worth-text`
- `#map` (unchanged)
- `#oos-card` (out-of-scope fallback)
- `#moves-heading` + 3 move cards: `#move-plan`, `#move-land` (with `#move-land-detail`), `#move-cta`
- `#report-dl-card`, `#lead-gate-card`
- `#result-footer` (ONE line)

`renderResult()` rewritten:
- Populates all new element IDs
- `#result-hero` green gradient for eligible; amber for OOS
- `#worth-box` shows indicative $ computed client-side from `ov.quantity_{low,high}_per_yr_tco2e × 8`
- `#move-land-detail` surfaces peat/forest-condition flags as opportunities
- Out-of-scope: shows `#oos-card`, hides moves/worth/hero-range
- Footer always shown for non-OOS; `#report-dl-card` shown only for `hasRange`

---

## ADR-0009 invariants confirmed ✅

- Always a range; never a single bare tCO2e number ✅
- No "% accuracy" or "% confidence" strings ✅
- "IPCC Tier 1" present (in footer line for all reports) ✅
- Methodology label present (APD in why_qualifies / derivation table) ✅
- CTA with 180Climate + info@180climate.net present ✅
- Peat: no tonnage in report body ✅
- Zero body disclaimers ✅ · One footer line only ✅

---

## Test changes

- `tests/test_report.py`: removed 4 stale assertions (old section headers: "Quality Factors", "Forest Data Summary", "Assessment Narrative", "Data Sources"); removed 2 "dominant uncertainty" checks; updated CTA wording assertions; added new value-first structure checks.
- **285 tests passed** (was 287 — 2 tests removed as their sections no longer exist in value-first design; net: 0 failures)

---

## Numbers unchanged ✅ (beyond ADR-0017 30-yr re-baseline)
- No methodology routing change
- No peat number
- No confidence %
- Determinism intact
