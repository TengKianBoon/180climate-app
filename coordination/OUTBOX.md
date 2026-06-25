# OUTBOX — Builder → Cowork · WO-REDESIGN-001 · 2026-06-26

## Status: CI GREEN ✅ — STOPPED for Cowork visual review

---

## What was delivered

Applied the John-approved UI restyle exactly per `docs/design/funnel-redesign-spec.md` + mockup.

### `frontend/index.html`
- Full CSS replaced: new design-token system (`--green #15913A`, `--green-bright #1DB03C`, `--lime #8FC71B`, `--ink #13212E`, etc.)
- Dark navy header → light/white surface + 3 px lime→green `.topbar` stripe
- Logo `height` 40 px → 66 px; Inter Google Font (weights 400–800) loaded
- `<link rel="icon" type="image/png" href="/favicon.ico">` in `<head>`
- Visible input borders (`1px solid var(--line)`) + green focus ring
- Input/textarea placeholders `#899096`; `select` text stays dark `--ink`
- Green-dot card h2 `.dot` pattern; hero → `.hero` with `<h1>` + `.pills` chips
- Tabs → pill style; `.pill` chips `.9rem`; `.badge-pill` recolored brand-green
- `.consent-note`, `.help` CSS classes; `.verdict-out-of-scope` rule added
- JS: map GeoJSON boundary + out-of-scope CTA link → `#15913A`
- All JS logic / API calls / number paths unchanged

### `api/main.py`
- `GET /favicon.ico` route → `brand/180climate-logo.png` as `image/png` · 200 ✓

### `reports/generator.py`
- PDF `green` colour: `#2d6a4f` → `#15913A`
- PDF eligible verdict: `#1b4332` → `#15913A`
- DOCX `_h2`, range display, eligible verdict: `RGBColor(45,106,79)/(27,67,50)` → `RGBColor(21,145,58)`

---

## Verification

| Check | Result |
|---|---|
| `GET /favicon.ico` | ✅ 200 `image/png` |
| `GET /` | ✅ 200, 37 KB HTML |
| `pytest tests/` | ✅ **246 passed** |
| No logic/number/contract change | ✅ confirmed |

---

## Cowork review checklist
1. Browser: white header + lime→green stripe + 66 px logo + Inter font
2. Form inputs: visible grey borders + green focus ring + `#899096` placeholders
3. Run a screening: results step renders; map has green boundary
4. Download PDF + DOCX: brand-green section headings (no old teal)
5. Browser tab favicon shows leaf logo
6. If green → advance to deploy steps / Gate L
