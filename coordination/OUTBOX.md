# OUTBOX — Builder -> Cowork · WO-EUDR-FINDING-016 · 2026-07-01

## Status: CI GREEN -- 457 tests pass -- STOPPED for Cowork review

Data-driven per-plot Finding. No contract change. No gate.

---

## What shipped (commit 479f03c)

### 1. `_eudr_finding_detail(pv, area_ha)` — data-driven finding builder

New pure function in `api/main.py`. Produces a real-numbers finding for each detection type:

| Detection | Finding (excerpt) |
|---|---|
| `loss_detected` (ha>0) | "We found about **12.4 ha** of tree-cover loss on this ~492 ha plot (~3%) after the EU's 31 December 2020 cutoff … Hansen annual loss / RADD radar … clear it before this plot enters a DDS." |
| `loss_detected` (ha==0, radar-only) | "Recent radar alerts (RADD) flagged possible tree-cover loss on this ~{area} ha plot … exact area isn't quantified yet … before this plot enters a DDS." |
| `inconclusive` | "We couldn't get a reliable read for this ~{area} ha plot … so we can't call it clear. A recent high-resolution image or a field check would resolve it." |
| `clear_in_screen` | "We checked this ~{area} ha plot … found no tree-cover loss after 31 December 2020 (Hansen shows zero; no RADD alerts). A good screening result — … still file a DDS …" |
| `geometry_invalid` | "… need ≥6 decimal places, WGS-84 … couldn't place it on the EU's maps. Fix the coordinates and re-submit." |

Number formatting: ha 1 dp ("<0.1" if 0<ha<0.05), area 0 dp, pct omitted if area=0.

### 2. `area_ha` threaded per plot (api layer — no engine/contract change)

`zip(plot_verdicts, validations)` pairs each verdict with its `PlotValidation`. Each `plots_out` dict now carries `"area_ha": round(val.area_ha, 1)`.

### 3. PDF Finding column → `p.get("detail")` (reports/generator.py)

Per-plot table Finding cell renders the data-driven `detail` string (changed from `p.get("label")` to `p.get("detail")`). Status chip + Next action unchanged.

### 4. Tests updated

`test_loss_detected_plot_fields` updated to match new data-driven detail:
- `"12.4 ha" in plot["detail"]` (fixture `loss_after_2020_ha=12.4`)
- `"31 December 2020" in plot["detail"]`

Inconclusive/geometry_invalid/clear guards pass without change — new templates still contain `"can't call it clear"`, `"≥6 decimal places"`, and DDS action framing.

Banned-string guard green: "DDS" (uppercase) is not in `EUDR_BANNED_SUBSTRINGS`.

```
mypy core/contracts/__init__.py --ignore-missing-imports -> Success: no issues found
pytest tests/ -> 457 passed, 1 warning
```
