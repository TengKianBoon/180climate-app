# GATE P READY

**Date:** 2026-06-24
**WO:** WO-CARBON-009 — Lead delivery pipeline (email DOCX + Google Sheet append)

---

## Evidence

- **116 tests green** (pytest -q → 116 passed, 1 harmless warning)
- **15 new lead-delivery tests** (tests/test_lead_delivery.py) — all 15 PASS
- Pushed to origin/main

### Acceptance criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | /api/lead + /api/report both email info@180climate.net with DOCX attached | PASS |
| 2 | Subject = "{concession} — {YYMMDDHHMM}" | PASS |
| 3 | Full form: name, email, mobile/WA, company, concession, permit type, project type, area, geometry summary, timestamp | PASS |
| 4 | DOCX attached, size > 1 KB | PASS |
| 5 | Google Sheet append (CI: JSONL outbox; real: gspread lazy-import) | PASS |
| 6 | No secrets in repo (creds only from host env) | PASS |
| 7 | /api/lead without geo still sends email (graceful degradation) | PASS |
| 8 | End-to-end golden lead: HTI eligible concession | PASS |

---

## What wires at deploy (John's action)

Set in host env config before Gate L:

  EMAIL_HOST=<smtp.host>
  EMAIL_PORT=587
  EMAIL_USER=<smtp-user>
  EMAIL_PASSWORD=<smtp-password>
  EMAIL_FROM=noreply@180climate.net

  GOOGLE_SHEETS_ID=<spreadsheet-id>
  GOOGLE_CREDENTIALS_JSON=<service-account-json-string>

Sheet row-1 headers (exact order):
  timestamp | iup_name | name | email | mobile | company | permit_type |
  permit_years_remaining | project_type | area_ha | geometry_summary |
  verdict | quantity_low_tco2e | quantity_high_tco2e | filename_base

---

## Architecture

  /api/report (download)  → engine → DOCX → _deliver() → email + Sheet → file to browser
  /api/lead  (form submit) → engine (if geo) → DOCX → _deliver() → email + Sheet → {"status":"emailed"}

CI: OUTBOX_DIR env var → JSONL outbox files; tests assert on written JSON. No network in CI.

---

## Next: Gate L (launch readiness)

Mandatory before Gate L (docs/pre-launch-backlog.md):
- ADR-0013 auto-routing + IFM + describe-your-own project type
- Brand logo swap
- Real SMTP + Sheets creds wired (John verifies end-to-end)

**To advance to Gate L: wire real creds in host config, trigger a real screening → download → verify email inbox + Sheet.**
