# OUTBOX — Builder (VS Code) · WO-CARBON-009 COMPLETE · GATE P READY · 2026-06-24

## Status: STOPPED — awaiting John to wire real SMTP + Sheets creds + sign Gate P

Tests: **116/116 passed** (+15 lead-delivery tests over WO-008's 101)

---

## Deliverables

### `api/email.py` — rewritten
New signature: `send_lead_email(iup_name, filename_base, form_data, docx_bytes=None)`
- Subject: `"{iup_name} — {filename_base}"` (YYMMDDHHMM)
- Body: full form (name, email, mobile, company, concession, permit type, project type, area, geometry, timestamp)
- DOCX as MIMEBase attachment when provided
- CI fallback (EMAIL_HOST unset): appends to `{OUTBOX_DIR}/outbox_emails.jsonl`
- SMTP failure: also falls back to JSONL so no lead is silently lost

### `api/sheets.py` — new
`append_lead(row: dict) -> bool`
- CI fallback (GOOGLE_SHEETS_ID unset): appends to `{OUTBOX_DIR}/outbox_leads.jsonl`
- Real mode: lazy-imports `gspread` + `google.oauth2.service_account` (not in requirements.txt — deploy-only)
- Sheet column order documented in GATE.md

### `api/main.py` — wired
- `_deliver(form_data, docx_bytes, filename_base)` — shared helper (email + Sheet)
- `/api/report`: always generates DOCX for email (regardless of fmt param); calls `_deliver()` before returning download
- `/api/lead`: expanded `LeadRequest` (includes `geo: Optional[GeoInput]`); if geo provided, re-runs engine → generates DOCX → calls `_deliver()`; graceful degradation if geo absent (email sent without DOCX)
- `_build_form_data()` → assembles full lead dict with geometry_summary

### `frontend/index.html` — `submitLead()` updated
Now sends: `iup_address`, `permit_years_remaining`, `project_type`, `geo` from `_cache` — gives the API enough to regenerate DOCX

### `tests/test_lead_delivery.py` — new, 15 tests
All CI-safe (no SMTP, no Sheets):
- `OUTBOX_DIR` env var → temp dir (isolated per test via `tempfile.mkdtemp`)
- `/api/lead` tests (8): status=emailed, outbox written, subject format, form fields, DOCX size, Sheet row, no-geo degradation, no secrets
- `/api/report` tests (7): email triggered on PDF+DOCX download, DOCX attached, subject format, Sheet row, geometry summary, Content-Disposition

---

## ADR-0004 invariant — verified
- `grep -r "EMAIL_PASSWORD\|GOOGLE_CREDENTIALS" api/ tests/` → 0 hits (only env var reads)
- No credential strings in any committed file

---

## What John must do to pass Gate P

1. Add to host `.env` / deploy config:
   ```
   EMAIL_HOST=smtp.example.com
   EMAIL_PORT=587
   EMAIL_USER=...
   EMAIL_PASSWORD=...
   EMAIL_FROM=noreply@180climate.net
   GOOGLE_SHEETS_ID=<spreadsheet-id>
   GOOGLE_CREDENTIALS_JSON=<service-account-json>
   ```
2. `pip install gspread google-auth` on the deploy host (not in CI requirements)
3. Run a real screening → click "Download PDF" → verify email in inbox (info@180climate.net) with DOCX
4. Check Sheet has the new lead row
5. Sign GATE P → dispatch Gate L

## Next: Gate L (pre-launch-backlog.md)
