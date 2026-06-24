# OUTBOX — Builder (VS Code) · WO-CARBON-008 COMPLETE · 2026-06-24

## Status: STOPPED for John / Cowork review

Commit: `e9e892b` — pushed to origin/main
Tests: **101/101 passed** (was 81; +20 new report tests)

---

## (A) Frontend tweaks — all done

**(i) Methodology pill now reads engine's MethodologyRoute**
- `loss_overlay` in `/api/carbon` now carries `baseline_class`, `verra_family`, `additionality_basis`
- Frontend pill uses `ov.baseline_class`/`ov.verra_family` — PEAT correctly shows **"no settled method"** (pill-warn class, brown) per ADR-0012
- Fallback guard retained for missing overlay

**(ii) Mobile (WhatsApp) moved to "Your details", required**
- Field label: "Mobile (WhatsApp) *"
- Required validation in `submitCarbon()` before API call
- `_cache.mobile` flows into: carbon API payload (`contact.mobile`), lead API body, report download payload
- Removed from lead gate (was optional there); lead gate now only shows company if not given in step 1

**(iii) Project type optional**
- First `<option value="">` added: "— permit-driven (default) —" (selected by default)
- Red star removed; label now "(optional)"
- Note shown below select: "We'll confirm your project type from your land."
- When blank, JS defaults to `"REDD"` before submitting — contract `Literal["REDD","PEAT"]` always satisfied

## (B) Report module — done

**`reports/generator.py`** (new):
- `make_filename()` → `YYMMDDHHMM` UTC, shared base for `.pdf` and `.docx`
- `ReportData` dataclass — all fields from engine result + contact
- `generate_pdf(data)` → bytes — reportlab A4; range in large green font, no single number, no "%", IPCC Tier 1, dominant-uncertainty paragraph, Engage CTA with `info@180climate.net`
- `generate_docx(data)` → bytes — python-docx; same sections, same invariants

**`POST /api/report?fmt=pdf|docx`** (new endpoint):
- Accepts same `CarbonInput` as `/api/carbon`
- Reruns engine, builds `ReportData`, returns file download with YYMMDDHHMM filename

**Download buttons in Step 2 results**:
- "Download PDF" and "Download DOCX" buttons — visible for eligible verdict only
- JS `downloadReport(fmt)` fetches `/api/report`, triggers browser download

**`tests/test_report.py`** (new, 20 tests):
- PDF: header, range, no-%, IPCC Tier, dominant-uncertainty, Engage CTA, APD methodology, peat-no-settled-method, non-eligible-no-range
- DOCX: header, range, no-%, IPCC Tier, dominant-uncertainty, Engage CTA, additionality basis, peat-no-settled-method

---

## ADR-0009 invariants — verified in tests
- Range shown (never single number) ✓  No `% accuracy` / `% confidence` strings ✓
- IPCC Tier 1 label present ✓  "dominant uncertainty" present ✓
- "Engage 180Climate" CTA + `info@180climate.net` present ✓
- PEAT: "no settled method" shown in pill + report ✓

---

## Evidence
- 101 tests green (`pytest -q` → 101 passed, 1 harmless httpx warning)
- Commit e9e892b pushed to origin/main

## Next: WO-CARBON-009 (lead delivery → Gate P) — awaiting John / Cowork approval
