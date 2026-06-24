# OUTBOX — Builder · WO-DEPLOY-PREP-001 · 2026-06-25

## Status: COMPLETE — STOPPED for Cowork review

---

## Delivered

### Procfile
```
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### .python-version
```
3.13
```
(Matches `actions/setup-python@v5` → `python-version: "3.13"` in `.github/workflows/ci.yml`.)

### render.yaml
Render Blueprint for one-click deploy. All env vars listed as `sync: false` placeholders — **no secrets, no values**. Full list: `PIPPIB_SNAPSHOT_PATH`, `EMAIL_HOST/PORT/USE_SSL/USER/PASSWORD/FROM`, `GOOGLE_SHEETS_ID`, `GOOGLE_CREDENTIALS_JSON`, `ANTHROPIC_API_KEY`. See `docs/deploy-runbook.md` for what to fill in.

---

## Verification

- App boots via Procfile command: **`python -m uvicorn api.main:app --host 0.0.0.0 --port 8001`** → `Application startup complete.`
- `GET /` → **200** (funnel HTML)
- `GET /health` → **200** `{"status":"ok"}`
- **246 tests pass** locally (245 + 1 network smoke; CI will show 245 + 1 skipped — same as before)
- No app logic / number / contract changes

---

## Commit

- `ef17857` feat(deploy): Procfile + .python-version 3.13 + render.yaml (WO-DEPLOY-PREP-001)

---

## Next (John's deploy-time actions)

Follow `docs/deploy-runbook.md` in order:
1. PIPPIB 2026 I shapefile → GeoJSON → `PIPPIB_SNAPSHOT_PATH`
2. Hostinger SMTP creds (`EMAIL_*`, critical: `EMAIL_FROM=john@180climate.net`)
3. Google Sheets service account (`GOOGLE_SHEETS_ID`, `GOOGLE_CREDENTIALS_JSON`)
4. Anthropic API key (optional, `ANTHROPIC_API_KEY`)
5. Render → new Web Service from GitHub → set env vars → deploy → custom domain `app.180climate.net` → Wix CNAME
6. End-to-end Gate L test (§8 in runbook)
