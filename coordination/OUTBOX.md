# OUTBOX — Builder → Cowork · WO-BREVO-EMAIL-001 · 2026-06-29

## Status: CI GREEN ✅ — STOPPED for Cowork review (297 tests passed, 5 new)

---

## Change — `api/email.py`

### New fallback order

| Priority | Condition | Action |
|---|---|---|
| 1 | `BREVO_API_KEY` set | POST to Brevo HTTPS API (port 443 — Render-safe) |
| 2 | `EMAIL_HOST` set | smtplib SMTP (non-Render envs; unchanged behaviour) |
| 3 | Neither | JSONL outbox (CI / dev mode; unchanged behaviour) |

### Brevo request

```
POST https://api.brevo.com/v3/smtp/email
Headers: api-key: <BREVO_API_KEY>  (key never logged)
         content-type: application/json
         accept: application/json

Body:
  sender:      {name: "180Climate", email: "john@180climate.net"}
  to:          [{email: "info@180climate.net"}]
  subject:     "{iup_name} — {filename_base}"
  htmlContent: <lead details wrapped in <pre> with html.escape()>
  attachment:  [{name: "<filename_base>.docx", content: "<base64>"}]  (omitted if no DOCX)
```

### Logging

| Branch | Log line |
|---|---|
| HTTP 201 | `INFO EMAIL: SENT OK (Brevo) -> info@180climate.net (subject="…")` |
| Non-201 | `ERROR EMAIL: BREVO ERROR: <status> <body[:500]>` + outbox fallback |
| Exception | `ERROR EMAIL: BREVO ERROR: <exc>` + outbox fallback |
| No BREVO_API_KEY, no EMAIL_HOST | `INFO EMAIL: EMAIL_HOST NOT SET -> outbox, NO email sent` (unchanged) |

**BREVO_API_KEY is never logged.**

### Refactors

- Extracted `_write_outbox()` helper — eliminates 3 identical outbox-write blocks
- Added `_build_html_body()` — wraps plain-text body in `<pre>` with `html.escape()` for Brevo `htmlContent`
- Extracted `_send_via_brevo()` and `_send_via_smtp()` private helpers

### What did NOT change

- SMTP path: identical behaviour, identical log lines
- Outbox fallback: identical JSONL format (same fields; Brevo/SMTP error adds `_brevo_error` or `_smtp_error` key)
- `_build_body()` text body: unchanged (used by smtplib + as source for HTML)
- `_TO = "info@180climate.net"`, `_FROM_EMAIL = "john@180climate.net"` unchanged

---

## Tests — `tests/test_lead_delivery.py`

**5 new tests in `TestBrevoEmail` class:**

| Test | What it verifies |
|---|---|
| `test_brevo_201_sent_ok` | Mock 201 → True, api-key in request header, no outbox written |
| `test_brevo_4xx_writes_outbox` | Mock 401 → False, outbox record with `_brevo_error=True` |
| `test_brevo_network_exception_writes_outbox` | `ConnectError` → False, outbox record |
| `test_no_brevo_key_falls_back_to_outbox` | No key + no EMAIL_HOST → True, outbox record |
| `test_brevo_key_never_in_outbox` | Mock 500 → key string absent from outbox JSON |

All use `unittest.mock.patch("api.email.httpx.post", ...)` — no network calls in CI.

**Updated:**
- `ci_outbox` fixture now also `delenv("BREVO_API_KEY")` to prevent env bleed into pre-existing tests
- `test_no_secrets_in_payload` now also asserts `"BREVO_API_KEY" not in content`

---

## Deploy instruction (for John)

Set `BREVO_API_KEY` as an environment variable in the Render dashboard. Once set, all lead emails will route via Brevo HTTPS rather than SMTP. No code change needed.

---

## Commit

`f5f9370` — pushed to `main` — `feat(email): send via Brevo HTTPS API when BREVO_API_KEY set (WO-BREVO-EMAIL-001)`
