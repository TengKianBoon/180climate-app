# OUTBOX — Builder -> Cowork · WO-EUDR-LAYMAN-013 · 2026-07-01

## Status: CI GREEN -- 455 tests pass (+2 new) -- STOPPED for Cowork review

Copy/layout/logging only. No contract change. No gate.

---

## What shipped (commit 814ee1a)

### 1. "What this is" intro — report + screen (verbatim WO copy)

**PDF** (`reports/generator.py`): light-blue intro box inserted after header HR, before hero.
Verbatim copy: "This is a free early check for Indonesian producers and exporters…"
EUDR defined on first use; DDS defined ("the declaration filed in the EU's online system (TRACES)…").

**Screen** (`frontend/index.html`): matching intro card at top of EUDR step-form, same copy.

### 2. Demote dataset names

**PDF**: hero label is now "EU Deforestation Regulation — Plot Check". Datasets footnote added below intro:
"Maps used: JRC Global Forest Cover 2020, Hansen Global Forest Change, and RADD alerts — public satellite data the EU itself references."

**Screen**: hero chip updated from "Checked against the EU's own forest maps (JRC GFC2020 + Hansen)"
-> "Checked against the EU's own satellite forest maps" (JRC names moved to the "how this is checked" link).

### 3. Rename "Triage" -> "Plot Check" everywhere user-facing

| Location | Before | After |
|---|---|---|
| PDF doc title | "180Climate EUDR Triage Report" | "180Climate EUDR Plot Check Report" |
| PDF header subtitle | "EUDR Triage Report" | "EUDR Plot Check — your EU deforestation-rule report" |
| PDF hero label | "EU Deforestation Regulation — Triage Result" | "EU Deforestation Regulation — Plot Check" |
| Screen hero rlbl | "EUDR plot triage result" | "EUDR Plot Check result" |

### 4. Checklist heading rename

PDF + screen: "DDS Readiness Checklist" -> "Your readiness checklist — what you'll need for the EU filing (the DDS)."

### 5. Checklist spacing fix (the bug John flagged)

PDF: replaced `BODY` (spaceAfter=6) / `SMALL` (spaceAfter=0) styles with:
- `ITEM_H`: spaceBefore=12, spaceAfter=2 — heading grouped tight to its note; big gap BEFORE each new item
- `ITEM_NOTE`: spaceBefore=0, spaceAfter=2 — note follows heading immediately

Screen: inter-item gap `readiness-list { gap: .45rem }` -> `.70rem` (each card visually separate).

### 6. Glossary box

**PDF**: 8-term two-column table before the CTA — EUDR, DDS, Geolocation pack, TRACES, Operator/"first placer", Standard risk, SVLK, HGU (Hak Guna Usaha). Plain-language definitions verbatim from WO.

**Screen**: collapsible `<details>` card ("Plain-language guide — the words we use explained") before CTA in result step. Same 8 terms.

### 7. Geolocation pack section

PDF heading: "Your Art-9 Geolocation Pack" -> "Your Geolocation Pack (the EU's 'Article 9' rule)"
Body copy: "plot(s)" -> proper `{pack_count} {'plot'/'plots'}` + plain Art-9 language.

### 8. Advisor cleanups (from WO-012, folded in)

| Fix | Before | After |
|---|---|---|
| inconclusive.label | "Inconclusive — treat as review needed" | "Inconclusive — review needed" |
| clear headline n==1 | "All 1 plot screened — not certified…" | "1 plot screened — not certified…" |
| plot(s) in downloadGeopack() | `length + ' plot(s) exported.'` | proper singular/plural |

### 9. Amber-rate logging

`api/main.py`: module-level `log = logging.getLogger(__name__)` added (also fixes latent log.error/log.warning references). Per-run INFO log: `overall`, `plots`, `loss`, `clear`, `inconclusive`, `invalid` counts + per-plot `[{id, detection, geometry_ok}]` list. Logging only — NO threshold change.

---

## Tests (+2 new, 455 total)

| Test | Assertion |
|---|---|
| `test_eudr_inconclusive_label_not_flagged` | inconclusive.label contains "Inconclusive", not "Flagged" |
| `test_eudr_clear_headline_singular_no_all_1` | single clear plot: headline does not say "All 1" |

```
mypy core/contracts/__init__.py --ignore-missing-imports -> Success: no issues found
pytest tests/ -> 455 passed, 1 warning (+2 net new)
git grep "plot(s)" -> source files clean (remaining hits: coordination docs + test assertion strings only)
```

Banned-string guard green. Legality limb intact. "not certified, still needs a DDS" render-guard intact.
