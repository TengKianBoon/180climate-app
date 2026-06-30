# OUTBOX — Builder -> Cowork · WO-EUDR-BANGUARD-014 · 2026-07-01

## Status: CI GREEN -- 457 tests pass (+2 new) -- STOPPED for Cowork review

Copy-only fix. No contract change. No gate.

---

## What shipped (commit 59810ed)

### 1. "deforestation-free" removed from all user-facing copy

| File | Location | Before | After |
|---|---|---|---|
| `reports/generator.py` | DDS first-use, intro box (~L915) | "confirming your goods are deforestation-free and legally produced" | "stating your goods were not grown on land cleared of forest after 2020, and were produced legally" |
| `reports/generator.py` | Glossary DDS entry (~L1135) | "states they're deforestation-free and legal" | "it states they were not grown on deforested land (after 2020) and were produced legally" |
| `frontend/index.html` | DDS first-use, intro card (L628) | same as above | same reword |
| `frontend/index.html` | Glossary DDS dd (L821) | same as above | same reword |

`git grep -i "deforestation-free" -- reports/ frontend/ api/` -> **0 hits**.
(Remaining hits in `core/contracts/__init__.py` are the `EUDR_BANNED_SUBSTRINGS` definition itself — correct.)

### 2. Guard gap closed — 2 new tests

**`test_no_banned_strings_in_eudr_pdf_render`**: renders `generate_eudr_pdf()` on a sample
body, extracts all PDF text via `pypdf.PdfReader`, asserts none of `EUDR_BANNED_SUBSTRINGS`
appear in the extracted text. This catches banned strings in static report copy that the
JSON-level guard misses.

**`test_no_banned_strings_in_eudr_frontend_copy`**: reads `frontend/index.html`, extracts
the EUDR screen section (`id="screen-eudr"` to `</div><!-- /screen-eudr -->`), asserts none
of `EUDR_BANNED_SUBSTRINGS` appear. This catches banned strings in static HTML copy.

```
mypy core/contracts/__init__.py --ignore-missing-imports -> Success: no issues found
pytest tests/ -> 457 passed, 1 warning (+2 net new)
git grep -i "deforestation-free" -- reports/ frontend/ api/ -> 0
```
