# OUTBOX — written by: Builder (VS Code) · Date: 2026-06-24

## Status: STOPPED — awaiting Cowork UI review (WO-CARBON-007)

WO-CARBON-007 complete. Frontend upgraded: real carbon range, IPCC Tier 1 badge,
annual forest loss chart, ADR-0003 funnel gate, on-brand. 81 tests pass.
Verifier: 48/48 acceptance criteria PASS (no blockers). Playwright unavailable for
screenshots — API + HTML structure verified via TestClient.
**Stopping here for Cowork to review the UI before WO-CARBON-008 (report).**

---

## What changed in WO-CARBON-007

### `api/main.py`
- `summary` field: removed `[PLACEHOLDER]` — now `"5,816,578 – 8,309,397 tCO₂e (lifetime) · IPCC Tier 1 · APD (VM0009)"` for eligible; `"Eligibility issues: …"` for non-eligible
- `loss_overlay` dict enriched: now carries `quantity_low_tco2e`, `quantity_high_tco2e`, `verdict`, `area_ha` for frontend
- Annual loss `data` keys serialised as strings (explicit) for JSON compatibility

### `frontend/index.html` — complete overhaul from WO-001 placeholder
| Feature | WO-001 (before) | WO-CARBON-007 (after) |
|---|---|---|
| Carbon range | "[PLACEHOLDER]" string | Large "5,816,578 – 8,309,397 tCO₂e" display |
| IPCC Tier | Absent | "IPCC Tier 1" navy pill badge |
| Methodology | Absent | "APD (VM0009)" / "IFM (VM0045/VM0010)" pill |
| Forest loss | Stub legend ("WO-CARBON-001") | Annual bar chart 2001–2022 with 2016–22 window highlighted |
| Verdict card | Plain badge | Colour-coded gradient card (green/amber/red) |
| Funnel gate | Mobile field only | ADR-0003 compliant: name+email → headline result; mobile+company → full report |
| Brand | Basic | 180° logo, #1a1a2e/#2d6a4f colour scheme |
| [PLACEHOLDER] references | 2 | 0 |
| "stub" / "WO-CARBON-001" artifacts | 2 | 0 |

---

## Verifier results (48/48 PASS)

### API checks (16/16)
- engine = "carbon" ✓
- verdict contains "Eligible" (golden HTI case) ✓
- summary = "5,816,578 – 8,309,397 tCO₂e (lifetime) · IPCC Tier 1 · APD (VM0009/legacy…)" — no [PLACEHOLDER] ✓
- loss_overlay.quantity_low_tco2e = 5,816,578.0 (exact) ✓
- loss_overlay.quantity_high_tco2e = 8,309,397.0 (exact) ✓
- loss_overlay.data: 22 year-keys 2001–2022 ✓
- loss_overlay.verdict = "eligible" ✓
- loss_overlay.area_ha = 73,787.2 ha ✓
- narrative contains "legal harvest right foregone" ✓
- narrative contains "Tier 1" ✓
- narrative ends with "Engage 180Climate" CTA ✓
- disclaimer.kind = "carbon_non_binding" ✓
- carrot contains "info@180climate.net" ✓
- data_sources non-empty (GFW/Hansen + ESA CCI) ✓

### HTML structure checks (32/32)
- No [PLACEHOLDER] anywhere ✓
- step-form: name, email, company, iup_name, permit_type, permit_years, project_type, coords/geojson tabs ✓
- step-result: verdict-card, range-display, tier-row, #map, loss-chart, narrative-text, lead-gate ✓
- step-done: confirmation + info@180climate.net ✓
- ADR-0003 funnel gate: lead-gate with mobile field gating "full report" ✓
- Brand colours: #1a1a2e header, #2d6a4f buttons ✓
- No "stub" or "WO-CARBON-001" artifacts ✓
- Annual loss CSS: loss-row, loss-bar, .win (as .loss-bar.win) ✓
- IPCC Tier badge: pill-tier class ✓
- Markdown renderer: md() function in JS ✓

Note: Playwright unavailable for pixel screenshots. Visual review is via the spec checklist above.
To view the UI: `uvicorn api.main:app --reload --port 8000` → `http://localhost:8000`

---

## Key data parameters (unchanged from 001c)

- Carbon range (golden HTI, 73,787 ha, 20yr): **5,816,578 – 8,309,397 tCO₂e**
- Density: ESA CCI Biomass v3.0 2018, tile N10E110, 266.5 tCO₂/ha
- Loss rate: Hansen GFC-2022, tile 10N_110E, 2.641%/yr (7-yr avg 2016–2022)
- IPCC Tier 1 throughout · not registry-grade

---

## Items for Cowork UI review

**U1 (funnel gate):** ADR-0003 compliant — name+email gives headline result; mobile+company gates the full report. Confirm gate is at the right level of friction.

**U2 (annual loss chart):** Shows all 22 years 2001–2022 as a bar chart; 2016–2022 window highlighted in red. Avg shown as a legend in the map and as a chart note. Confirm this is sufficient for the screening tool (no map tile overlay — satellite loss tiles deferred, not in scope for WO-007).

**U3 (narrative rendering):** `**bold**` markdown rendered to `<strong>` in-browser; `---` → `<hr>`. No LLM call in this path — template narrative only.

**U4 (non-eligible verdict):** For hard_no/flagged cases, the range display is suppressed (shows empty) and the summary shows the eligibility issues. Confirm this is the right UX for those verdicts.

**U5 (next step):** If approved → WO-CARBON-008 (PDF + DOCX report, ADR-0010).

---

## Counts
- Tests: **81** (all passing)
- Verifier: 48/48 PASS
- [PLACEHOLDER] references: 0 (was 2)
- "stub" / "WO-CARBON-001" artifacts: 0 (was 2)
- Screenshot: PLAYWRIGHT_UNAVAILABLE — visual verification requires local server

## Next step (awaiting Cowork go-ahead)
→ Cowork reviews UI checklist + runs `uvicorn api.main:app --port 8000` for visual check
→ If approved: merge `feat/carbon-007` → main → begin WO-CARBON-008 (PDF+DOCX report)
