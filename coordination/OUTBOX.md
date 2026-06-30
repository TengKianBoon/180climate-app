# OUTBOX — Builder → Cowork · WO-EUDR-REPORT-009 (E7) · 2026-06-30

## Status: CI GREEN ✅ — 446 tests pass (+8 new E7 tests) — STOPPED for Cowork review

EUDR MVP build complete (E1–E7). Value-first PDF report generated and attached to every EUDR lead email.

---

## What shipped

### `reports/generator.py` — `generate_eudr_pdf(body: dict) -> bytes`

New ReportLab PDF function. Sections (in value-first order):

1. **Header** — logo + "EUDR Triage Report" + contact/commodity/plot-count/run-date/reference meta
2. **Hero** — red table (`#C0392B`) for any flagged plots; green (`#0E7A30`) for all-clear. Headline from `overall_headline` (ADR-0018 render-safe wording). Sub: DDS framing always present.
3. **Per-plot status table** — red/amber/green/grey row backgrounds by detection state; columns: Plot ID / Status / Finding / Next action
4. **DDS Readiness checklist** — ✓/○ per component (no numeric score)
5. **Commodity evidence** — list from E5
6. **Who files the DDS** — role-keyed box from E5
7. **Indonesia context** — risk level + deadlines table (30 Dec 2026 / 30 Jun 2027)
8. **Geolocation pack note** — pack count + Art-9 rules note; never "DDS-ready" or "compliant"
9. **CTA** — green box: "Engage 180Climate — DDS preparation + on-the-ground verification"
10. **Footer** — ONE combined line: legality limb + JRC attribution + report ref

No banned strings in any section (tested in `test_eudr_report_no_banned_strings_in_pdf`).

### `api/email.py` — `subject_override: Optional[str] = None`

`send_lead_email()` accepts an optional subject override. When set, skips the auto-built subject.

### `api/main.py` — E7 wiring

**`POST /api/eudr`** — now generates PDF before the email call:
```python
eudr_pdf_body = {**body, "contact_name": name, "commodity": commodity, "filename_base": filename_base}
eudr_pdf_bytes = generate_eudr_pdf(eudr_pdf_body)
eudr_subject = f"New 180Climate EUDR lead — {name} · {len(plot_verdicts)} plots, {loss_count} flagged"
send_lead_email(..., pdf_bytes=eudr_pdf_bytes, subject_override=eudr_subject)
```

**`POST /api/eudr/report`** — new download endpoint:
- Request body: `{"result": <triage JSON from _eudrResult>, "contact_name": "...", "commodity": "..."}`
- Returns `application/pdf` with `Content-Disposition: attachment; filename="{YYMMDDHHMM}.pdf"`
- No re-running triage — client passes cached result

### `frontend/index.html`

New card above the geolocation pack card:
```html
<h3>Download your triage report (PDF)</h3>
<button onclick="downloadEudrReport()">Download triage report (PDF)</button>
```

`downloadEudrReport()` JS:
- Guards: no result → "Run a plot check first."
- Shows "Generating PDF…" while fetching
- POSTs `{result: _eudrResult, contact_name: _eudrContactName, commodity: _eudrCommodity}` to `/api/eudr/report`
- On success: Blob → `<a download>` click → PDF saved

`_eudrContactName` and `_eudrCommodity` variables set on each successful EUDR submission.

---

## Tests — `tests/test_eudr_api.py` (+8 new E7 tests)

| Test | Assertion |
|---|---|
| `test_eudr_report_endpoint_returns_pdf` | 200, content-type=application/pdf, len>1000 |
| `test_eudr_report_starts_with_pdf_magic_bytes` | `b"%PDF"` at start |
| `test_eudr_report_content_disposition_has_filename` | Content-Disposition has `.pdf"` |
| `test_eudr_report_no_banned_strings_in_pdf` | 4 banned substrings absent from raw bytes |
| `test_eudr_report_loss_response_non_empty` | loss-detected PDF > 500 bytes |
| `test_eudr_report_clear_response_non_empty` | all-clear PDF > 500 bytes |
| `test_eudr_lead_email_subject_format` | subject has "EUDR lead", "plots", "flagged" |
| `test_eudr_lead_email_has_pdf_bytes` | `pdf_bytes` is non-empty bytes |

---

## OPEN ITEM (carried from E6)

**Live TRACES uploader validation** — John's pre-launch check. Cannot test locally. One-function edit if TRACES needs different GeoJSON property names.

---

## mypy + pytest

```
mypy core/contracts/__init__.py --ignore-missing-imports → Success: no issues found
pytest tests/ → 446 passed, 1 warning (was 438; +8 new E7 tests)
```
