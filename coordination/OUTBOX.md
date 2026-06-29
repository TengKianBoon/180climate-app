# OUTBOX — Builder → Cowork · WO-CRM-GMAIL-001 · 2026-06-29

## Status: CI GREEN ✅ — STOPPED for Cowork review (299 tests passed, 2 new)

---

## Frontend — `frontend/index.html`

**Removed entirely:**
- `.lead-gate` CSS block
- `<div id="lead-gate-card">` — "Get the full pre-feasibility report" card with "Send me the report →" button
- `document.getElementById('lead-gate-card').style.display = 'block'` JS line
- `document.getElementById('lead-company-row').style.display = ...` JS line
- `submitLead()` function (~36 lines)

**Kept:** "Download your report — Download PDF" card (`report-dl-card`), which calls `/api/report?fmt=pdf`. That endpoint now both serves the PDF download to the visitor and emails John the PDF + lead details.

---

## Backend — `api/email.py`

| Change | Before | After |
|---|---|---|
| Recipient | `"info@180climate.net"` (hardcoded) | `LEAD_RECIPIENT_EMAIL` env var (default `leoniches@gmail.com`) |
| Subject | `"{iup_name} — {filename_base}"` | `"New 180Climate lead — {contact_name} · {iup_name}"` |
| Attachment | `{filename_base}.docx` | `{filename_base}.pdf` (MIME: `application/pdf`) |
| Body | Contact + concession fields | + verdict + lifetime tCO2e range + per-year range |

`_recipient()` function reads `LEAD_RECIPIENT_EMAIL` at call time (not import time) so tests and prod can override via env.

Enhanced `_build_body()`:
```
=== Carbon screening ===
Verdict:      eligible
Range:        6,680,000 – 11,530,000 tCO2e (lifetime) | 222,667 – 384,333 tCO2e/yr
Summary:      ...
```

Brevo `htmlContent` carries the same enhanced body, `<pre>`-wrapped + html-escaped. Key never logged.

---

## Backend — `api/main.py`

- `_deliver()`: `docx_bytes` → `pdf_bytes` parameter
- `_build_form_data()`: added `quantity_low_per_yr_tco2e` + `quantity_high_per_yr_tco2e` to form_data dict
- `/api/report?fmt=pdf`: generates PDF once → serves to visitor AND attaches to lead email (no DOCX generated for this path)
- `/api/report?fmt=docx`: generates DOCX once → serves to visitor AND attaches to lead email
- `/api/lead`: generates PDF (not DOCX) when geo provided (endpoint still exists; no longer triggered from UI)

---

## Tests — `tests/test_lead_delivery.py`

**Updated assertions:**
- `r["to"]` → `"leoniches@gmail.com"` (was `"info@180climate.net"`)
- `r["attachment_filename"].endswith(".pdf")` (was `.docx`)
- Subject checks → `"New 180Climate lead — Jane Smith"` prefix + IUP name in body

**New tests:**
- `test_report_email_recipient` — asserts `leoniches@gmail.com` on `/api/report?fmt=pdf`
- `test_report_email_body_has_carbon_fields` — asserts verdict, tCO2e range, per-year in `form_data`

---

## Deploy instruction (for John)

Set `LEAD_RECIPIENT_EMAIL=leoniches@gmail.com` in Render env vars (or omit — that's the default). Combined with `BREVO_API_KEY`, every "Download PDF" click will email `leoniches@gmail.com` with the PDF attached.

---

## Commit

`b5ef639` — pushed to `main` — `feat(crm): PDF-to-Gmail on Download PDF; drop lead-gate box (WO-CRM-GMAIL-001)`
