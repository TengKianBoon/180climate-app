# OUTBOX — Builder → Cowork · WO-EUDR-BLOCKER-004 (E4) · 2026-06-30

## Status: CI GREEN ✅ — API smoke PASS — STOPPED for Cowork review (384 tests pass, +25 new)

EUDR API endpoint + value-first result page (the per-plot blocker table). Deterministic, no LLM.
Carbon contracts untouched. Brevo lead delivery reused.

---

## What shipped

### `POST /api/eudr` (new, `api/main.py`)
Accepts `multipart/form-data`:
- `file` — GeoJSON / KML / SHP upload (preferred); or
- `geojson_text` — pasted GeoJSON text
- `commodity`, `role`, contact fields

Pipeline: `parse_plots` (E2) → `triage_validated_plots` (E3) → JSON response.

Response fields (flat dict, no EUDRVerdict model — E5 will extend):
- `engine: "eudr"`, `overall`, `overall_headline`, `plot_count`, `loss_count`, `clear_count`
- `plots[]` — each with `detection`, `label`, `detail`, `action`, `plot_satellite_risk`, `geometry_ok`,
  `loss_after_2020_ha`, `run_date`, `datasets_version`
- `legality_note`, `timber_note` (only when commodity=timber), `jrc_attribution`, `footer`
- `country_benchmark_risk: "standard"` (Indonesia hardcoded for MVP)

**No banned strings** (enforced + tested): "compliant", "deforestation-free", "dds-ready",
"due diligence statement ready" never appear in any response field.

### Render guards (all tested, all pass)

| Guard | Behaviour |
|---|---|
| `loss_detected` headline | "X plot(s) could block your shipment" — tested `test_loss_detected_headline_contains_could_block` |
| `clear_in_screen` headline | "All X plots screened — not certified, still needs a DDS" — tested `test_clear_in_screen_headline_never_bare` |
| `clear_in_screen` action | "Screened against the EU's maps — not certified, still needs a DDS..." — tested `test_clear_in_screen_plot_detail_has_dds_framing` |
| Roll-up never softens a red | Any `loss_detected` → `overall=loss_detected` + blocking headline, even in mixed batch |
| No bare clear tick | Every `clear_in_screen` plot carries DDS framing in action; never "Clear ✓" |
| `geometry_invalid` | Returned with Art-9 fix message; never produces false clear |

### Frontend EUDR screen (new, `frontend/index.html`)

Screen-nav toggle: **Carbon Screening** | **EUDR Plot Check** at the top.

**Intake (`#screen-eudr #eudr-step-form`):**
- File upload tab (GeoJSON/KML/SHP) + paste GeoJSON tab
- Commodity select (palm/rubber/timber/cocoa/coffee/manual review)
- Role pick (Indonesian supplier / EU first placer / downstream operator)
- Contact (name, email, mobile, company)
- "Check my plots against the EU maps →" button

**Result (`#screen-eudr #eudr-step-result`):**
- **Hero card** — colour-coded (red/amber/teal) with `overall_headline`; never the same green as carbon compliance
- **Per-plot blocker table** — one row per plot, colour-coded: `loss_detected`=red, `inconclusive`=amber, `clear_in_screen`=teal (NOT the same green as verified-compliant), `geometry_invalid`=grey
- Verbatim advisor wording per detection state (from `docs/eudr-design-v2.md`)
- **Legality limb** plain next-action note (deforestation check ≠ legality check)
- **Timber note** — degradation not assessed (shown only for timber commodity)
- **JRC attribution** line
- **ONE footer disclaimer** (not a DDS, not legal advice)
- **"How this is checked"** link (dataset names behind the link, not in the hero)
- 180Climate CTA: "180Climate prepares your DDS — and verifies flagged plots on the ground"

---

## API smoke tests (2 runs)

**Run 1 — mixed batch (1 loss + 1 clear):**
```
Plot A (lon=113, lat=-1)  → loss_detected  (Kalimantan fixture: JRC forest + Hansen 12.4 ha loss)
Plot B (lon=114, lat=-2)  → clear_in_screen (fixture: JRC forest + Hansen 0.0 ha loss)
overall:   loss_detected
headline:  "1 plot could block your shipment"   ← render guard ✓
```

**Run 2 — clear only:**
```
Plot B alone → clear_in_screen
headline: "All 1 plot screened — not certified, still needs a DDS"  ← render guard ✓
detail:   "...A screening result, not a legal determination."
action:   "Screened against the EU's maps — not certified, still needs a DDS..."
```

**Run 3 — geometry_invalid (4-decimal coords):**
```
overall: review_needed
detection: geometry_invalid
action: "Fix the geometry and re-submit for screening."
```

---

## Tests — `tests/test_eudr_api.py` (24 new)

- `test_no_banned_strings_*` — both loss and clear responses scanned for all 4 banned substrings
- `test_engine_tag_is_eudr`
- Loss guards: overall, headline "could block", counts, verbatim detail ("EU inspector")
- Clear guards: overall, headline "not certified"/"needs a DDS", action framing, counts
- Inconclusive: overall `review_needed`, plot field + "needs-review" text
- Geometry invalid: invalid_count, `geometry_ok=False`, "Art 9" in detail
- Mixed batch: loss dominates overall + headline; order preserved
- Stamps: `run_date`, `datasets_version`, JRC attribution
- `legality_note` present; `timber_note` only for timber commodity
- `country_benchmark_risk = "standard"`
- No-geometry → 422
- File upload path tested

**384 tests pass** (was 359; +25). Green offline with `*_DISABLE_LIVE=true`. Pre-existing KHG live smoke excluded (network `ReadTimeout`).

---

## Commit
(pending push)
