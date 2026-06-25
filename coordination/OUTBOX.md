# OUTBOX — Builder · WO-POLISH-001 · 2026-06-25

## Status: CI GREEN ✅ — STOPPED for Cowork review

---

## CI confirmation

- **Run:** https://github.com/TengKianBoon/180climate-app/actions/runs/28151792321
- **Commit:** b5eedec
- **Result:** ✅ 245 passed, 1 skipped, 1 warning in 3.30s

---

## What was delivered

Replaced U+2082 subscript `₂` with plain ASCII `2` in all user-facing strings:

| File | Occurrences fixed |
|---|---|
| `api/main.py` | 4 × `tCO₂e` → `tCO2e` |
| `frontend/index.html` | 1 × `tCO₂e` → `tCO2e` (range-unit span) |
| `narrative/narrator.py` | `tCO₂-eq`, `tCO₂/ha`, `tCO₂e` → plain ASCII |
| `reports/generator.py` | 1 × `tCO₂e` → `tCO2e` (range_str) |

No test assertions used the subscript form — no test changes needed.
Internal engine/gfw/biomass labels already used plain `tCO2` — untouched.

---

## Verification

- `range_str()` → `5,816,578 – 8,309,397 tCO2e` (clean ASCII, no garbled glyph)
- PDF generated: 47,260 bytes — hero number renders cleanly
- `₂` grep across all `.py` and `.html` files: 0 matches
- 246 tests pass locally; CI 245 + 1 skipped
