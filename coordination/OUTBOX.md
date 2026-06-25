# OUTBOX — Builder · WO-LOGO-001 · 2026-06-25

## Status: CI GREEN ✅ — STOPPED for Cowork review

---

## CI confirmation

- **Run:** https://github.com/TengKianBoon/180climate-app/actions/runs/28137789067
- **Commit:** edc562f
- **Result:** ✅ 245 passed, 1 skipped, 1 warning in 3.20s

---

## What was delivered

### brand/180climate-logo.png
Canonical asset committed (314×282 px, RGBA transparent background, 35 KB).
Stray root file `180climate logo 2.png` deleted (was untracked — no git rm needed).

### Surface 1 — funnel header (`frontend/index.html`)
- Replaced `<div class="logo">180°</div>` with `<img class="logo-img" src="/brand/logo.png" alt="180Climate" height="40">`
- Removed redundant `<div class="header-name">180Climate</div>` (wordmark is in the image)
- Replaced `.logo { font-size: 1.5rem... }` + `.header-name { ... }` CSS with `.logo-img { height: 40px; width: auto; display: block; }`
- New route `GET /brand/logo.png` in `api/main.py` serves the PNG file

### Surface 2 — report header (`reports/generator.py`)
- **PDF:** logo embedded via reportlab `Image` at 1.6 cm tall (width auto-computed from aspect 314/282 ≈ 1.113)
- **DOCX:** logo embedded via `run.add_picture()` at `Inches(0.55)` tall (python-docx preserves aspect)
- Graceful text fallback in both if `brand/180climate-logo.png` is missing at runtime

---

## Verification

| Check | Result |
|---|---|
| `GET /brand/logo.png` | 200 · `image/png` · 35,237 bytes |
| `GET /` contains `logo-img` class | ✅ |
| `GET /` no `header-name` div | ✅ (removed) |
| `GET /` no `180°` text | ✅ (removed) |
| PDF generated | ✅ 47,321 bytes (logo embedded) |
| DOCX generated | ✅ 72,730 bytes (logo embedded) |
| CI 245 + 1 skipped | ✅ |
| No contract / number change | ✅ |
