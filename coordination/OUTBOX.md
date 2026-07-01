# OUTBOX — Builder -> Cowork · WO-EUDR-USEFUL-015 · 2026-07-01

## Status: CI GREEN -- 457 tests pass -- STOPPED for Cowork review

Copy/test only. No contract change. No gate.

---

## What shipped (commit c86ac46)

### 1. Per-plot plain-language findings — all 4 detection states

`_EUDR_VERBATIM` in `api/main.py` — verbatim from WO, observed-not-confirmed framing:

| Detection | New detail | New action |
|---|---|---|
| `loss_detected` | "Possible tree-cover loss showed up on the EU's satellite maps inside or near this plot's boundary, after the 31 Dec 2020 cutoff. This is what the satellite data suggests — observed, not yet confirmed on the ground." | "Get this plot checked before it enters a DDS. The signal could be older logging, a road, fire, or a mapping error — but it has to be cleared up first." |
| `inconclusive` | "We couldn't get a clear read for this plot — usually cloud cover, a small parcel, or radar noise. That means we can't call it clear, not that there's a problem." | "Needs a manual check (recent or higher-resolution imagery) before it can go into a DDS." |
| `clear_in_screen` | "No tree-cover-loss signal showed up on the EU's satellite maps for this plot after 2020." | "Clear in this screening — but a screen is not certification. It still needs a DDS, and confirm the plot's legality separately." |
| `geometry_invalid` | "We couldn't read this plot's boundary — the coordinates weren't precise enough (need ≥6 decimal places) or the shape was invalid." | "Fix the coordinates to ≥6 decimal places and re-submit so we can screen this plot." |

Colour/status chips unchanged (red/amber/green pinned map intact).
Render guard: `clear_in_screen` action still carries "needs a DDS" framing — `test_clear_in_screen_plot_detail_has_dds_framing` confirms.

### 2. Plot label — P1/P2 fallback

`engines/eudr/geometry.py` (GeoJSON, KML, SHP parsers): auto-fallback plot ID changed from `plot_{i+1}` to `P{i+1}` when no `properties.id`/`name`/`plot_id` is supplied. User-supplied names still take priority (unchanged).

### 3. Tests updated (3 verbatim assertions updated, no tests dropped)

| Test | Old assertion | New assertion |
|---|---|---|
| `test_loss_detected_plot_fields` | `"resolve it before the plot enters a DDS"` + `"EU inspector"` | `"observed, not yet confirmed on the ground"` + `"31 Dec 2020 cutoff"` |
| `test_inconclusive_plot_fields` | `"needs-review"` | `"can't call it clear"` |
| `test_geometry_invalid_returned` | `"Art 9"` | `"≥6 decimal places"` |

### 4. WO-014 items — already in main, not re-applied

- `"deforestation-free"` rewording in `reports/generator.py` + `frontend/index.html`: done in 59810ed.
- Guard tests (`test_no_banned_strings_in_eudr_pdf_render` + `test_no_banned_strings_in_eudr_frontend_copy`): done in 59810ed.
- `git grep -i "deforestation-free" -- reports/ frontend/ api/` → **0 hits**.

```
mypy core/contracts/__init__.py --ignore-missing-imports -> Success: no issues found
pytest tests/ -> 457 passed, 1 warning
```
