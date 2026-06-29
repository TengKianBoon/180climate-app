# OUTBOX — Builder → Cowork · WO-PDFONLY-EMAILLOG-001 · 2026-06-29

## Status: CI GREEN ✅ — STOPPED for Cowork review (292 tests passed)

---

## Part A — Public download: PDF only

### What changed

**`frontend/index.html`:**
- Removed `<button class="btn btn-outline" onclick="downloadReport('docx')">Download DOCX</button>` from `report-dl-card`
- Updated card heading copy: `"Value-first PDF + DOCX…"` → `"Your value-first PDF report…"`
- Updated lead-gate copy: `"Receive a PDF + DOCX with…"` → `"Receive a PDF report with…"`

**Backend: unchanged.** DOCX is still generated in `api/main.py` and attached to the internal lead email sent to `info@180climate.net`. The public user now only sees and downloads the PDF.

---

## Part B — Stdout observability logging

### `api/main.py`
Added at module level (before any route handlers):
```python
import logging, sys
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    force=True,
)
```
All INFO/ERROR lines from `email.py` and `sheets.py` now appear in the Render log stream.

### `api/email.py`

| Branch | Log line |
|---|---|
| `EMAIL_HOST` not set | `INFO EMAIL: EMAIL_HOST NOT SET -> outbox, NO email sent` |
| Before SMTP connect | `INFO EMAIL: connecting {host}:{port} ssl={use_ssl} FROM={from_addr} TO={_TO}` |
| SMTP success | `INFO EMAIL: SENT OK` |
| SMTP exception | `ERROR EMAIL: SMTP ERROR: {exc}` |

Password is **never logged** (only host/port/ssl/from/to).

### `api/sheets.py`

| Branch | Log line |
|---|---|
| `GOOGLE_SHEETS_ID` not set | `INFO SHEETS: GOOGLE_SHEETS_ID NOT SET -> outbox` |
| Append success | `INFO SHEETS: appended row to {sheets_id}` |
| Exception | `ERROR SHEETS: ERROR: {exc}` |

Credentials JSON is **never logged**.

---

## Tests

**292 tests green — no behaviour change to delivery path.**

No new tests added (logging is an ops concern; existing `test_email_*` and `test_sheets_*` tests continue to pass with the outbox path).

---

## Commit

`ac54bcd` — pushed to `main` — `feat(ux+ops): PDF-only public download + email/sheet observability (WO-PDFONLY-EMAILLOG-001)`
