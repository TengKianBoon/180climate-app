# 180Climate App — Go-Live Deploy Runbook (→ Gate L)

**Author:** Cowork (planner) · **Date:** 2026-06-24 · Beginner-proof. Env-var names below are the **exact**
ones the committed code reads (verified against `api/email.py`, `api/sheets.py`, `classifier/intake.py`,
`core/overlays/pippib.py`). Do these in order; each is independent except hosting (last).

> The app is **one service** — `api/main.py` serves both the API and the frontend (`GET /` → `frontend/index.html`).
> So you deploy a single web app, not a separate frontend + backend.

---

## Accounts you'll need (one-time)
GitHub (have it) · a host account — **Railway** or **Render** · a **Google** account (Sheets) ·
**Anthropic Console** (classifier key, optional) · **Hostinger** (email — have it) · **Wix** (DNS — have it).

---

## 1. PIPPIB legal-map snapshot (Overlay B) — *the one with real legal weight*
**Why:** peat verdicts use the moratorium map. PIPPIB is a Map-only service (no live query), so the app reads a
local snapshot. Until you set it, peat correctly shows *"moratorium data unavailable → flag"* (safe, but not informative).

1. Get the data: go to **`geoportal.menlhk.go.id`** → open the **PIPPIB_AR_250K** layer → download/export the
   **shapefile** for the current period (**2026 Periode I**). *(If export isn't offered, file a SHP data request —
   `indonesia-geospasial.com` documents KLHK/Kemenhut's procedure.)*
2. Install GDAL's `ogr2ogr` (one-time): Windows → `winget install OSGeo.GDAL` (or use QGIS, which bundles it);
   Mac → `brew install gdal`; Linux → `sudo apt install gdal-bin`.
3. Convert SHP → GeoJSON:
   ```
   ogr2ogr -f GeoJSON -t_srs EPSG:4326 PIPPIB_2026_I.geojson PIPPIB_AR_250K.shp
   ```
   (`-t_srs EPSG:4326` normalizes it to lat/lon to match the app's geometry.)
4. Put `PIPPIB_2026_I.geojson` where the host can read it, and set the env var:
   `PIPPIB_SNAPSHOT_PATH=/path/to/PIPPIB_2026_I.geojson`

**Refresh** each PIPPIB period (~every 6 months); note the **SK number + date** alongside the file.
*(Overlay A — peat ecosystem function — is the live BIG One Map REST service, so it needs no snapshot.)*

---

## 2. Email delivery (Hostinger) — leads to `info@180climate.net`
**Why:** each report download emails the DOCX + the lead's full details to `info@180climate.net`
(subject `"{concession} — {filename}"`). `info@` is a **receive-only alias**, so the app **sends FROM `john@`**.

Set these env vars (port 465 / SSL is the Hostinger default that "just works"):

| Env var | Value |
|---|---|
| `EMAIL_HOST` | `smtp.hostinger.com` |
| `EMAIL_PORT` | `465` |
| `EMAIL_USE_SSL` | `true` |
| `EMAIL_USER` | `john@180climate.net` |
| `EMAIL_PASSWORD` | *(the `john@` mailbox password)* |
| `EMAIL_FROM` | `john@180climate.net` |

**⚠ Critical:** `EMAIL_FROM` defaults to `noreply@180climate.net`, which is **not a real mailbox** — if you leave
it unset, mail fails SPF/DKIM silently. **You must set `EMAIL_FROM=john@180climate.net`.**
*(Port 587 + STARTTLS also works: set `EMAIL_PORT=587` and omit `EMAIL_USE_SSL`.)*
Steps: confirm the `john@` mailbox + password in **hPanel → Emails**; ideally verify **SPF/DKIM** for the domain
so leads don't land in spam. Test by downloading a report and checking the `info@` inbox.

---

## 3. Google Sheets — lead backup
**Why:** every lead also appends a row to a Sheet (backup beyond email).

1. **Google Cloud Console** → create/select a project → **enable the Google Sheets API**.
2. Create a **Service Account** → **Keys → Add key → JSON** → download the JSON file.
3. Create the Google Sheet; add the **header row** (column order is defined at the top of `api/sheets.py`);
   copy the **Sheet ID** from its URL (`/spreadsheets/d/<THIS_PART>/edit`).
4. **Share the Sheet** with the service account's email (the `client_email` in the JSON) as **Editor**.
5. Set env vars:
   - `GOOGLE_SHEETS_ID` = the Sheet ID (just the ID, not the URL)
   - `GOOGLE_CREDENTIALS_JSON` = the **entire JSON file contents, inline as one string** (not a file path)

---

## 4. Classifier key (the "describe your own" free-text option) — optional
**Why:** maps free-text project descriptions to a methodology; without it, "other" safely defaults to out-of-scope.
- `console.anthropic.com` → **API Keys** → create key → set `ANTHROPIC_API_KEY=<key>`.
- Small per-call Haiku cost. It is **never** in the deterministic number path. Skip it and the funnel still works.

---

## 5. Hosting on `app.180climate.net`
**Recommended — start free ($0).** Use **Render's free tier**: it includes a **custom domain + managed HTTPS** and
deploys straight from GitHub. Trade-off: a free service **sleeps after 15 min idle** and takes **~30–60 s to
cold-start** on the next visit. For a pre-revenue lead funnel with low/sporadic traffic that's acceptable — **don't
pay until traffic justifies it.** When it does, upgrade in place to an **always-on** tier (**Render Starter $7/mo**
or **Railway Hobby ~$5/mo**) to remove the cold start. (Fly.io no longer has a free tier.) *Optional:* a free uptime
pinger (e.g. UptimeRobot every ~10 min) keeps the free instance warm and fits within Render's 750 free hours/month.

**Small builder prerequisite (dispatch first):** the repo has **no start command / Procfile / Dockerfile** yet.
Add a start command `uvicorn api.main:app --host 0.0.0.0 --port $PORT` (a `Procfile` or the host's start-command
field). `rasterio` ships GDAL wheels, so the plain Python build + `requirements.txt` should work; a `Dockerfile`
is the fallback if GDAL acts up.

Then:
1. Connect the GitHub repo (`TengKianBoon/180climate-app`) to Railway/Render → new **Web Service**.
2. Set **all env vars** from sections 1–4.
3. Set the **start command** above. Deploy; watch the build log go green.
4. **Add custom domain** `app.180climate.net` in the host's domain settings — it gives you a target hostname.
5. **DNS (Wix, per ADR-0002):** Wix **DNS settings** → add a **CNAME**: host `app` → *that target hostname*.
   TLS auto-provisions. Then **link `app.180climate.net` from the Wix nav**.

*RAM note:* 512 MB can be tight with the geo libs; v1's heavy reads are cached/placeholder so it should fit —
monitor and bump a tier if needed.

---

## 6. Brand logo (cosmetic — not a blocker)
Save the official logo to **`brand/180climate-logo.png`** in the repo (or attach it in chat and Cowork places it),
then the builder swaps it across the UI header + PDF/DOCX report.

## 7. Advisor wording check
Send the peat-flag + narrative copy to your independent advisor for a final pressure-test before public launch.

---

## 8. Final go-live verification (Gate P → Gate L)
End-to-end, on the live `app.180climate.net`:
1. Submit a concession → get a verdict (**peat flags**; a mineral concession returns a **range + IPCC Tier**, never a single number).
2. Download **PDF** + **DOCX**.
3. Confirm `info@180climate.net` received the email with the **DOCX attached** + full lead details (subject `"{concession} — {filename}"`).
4. Confirm the **Google Sheet** row appended.
5. Confirm the site loads over **HTTPS** and is **linked from Wix**.
6. **John (+ advisor) sign Gate L.** Cowork gathers this evidence; Cowork does not self-certify the gate.

---

## Env-var quick reference (set all on the host)
```
PIPPIB_SNAPSHOT_PATH=/path/to/PIPPIB_2026_I.geojson
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_USER=john@180climate.net
EMAIL_PASSWORD=********
EMAIL_FROM=john@180climate.net
GOOGLE_SHEETS_ID=<sheet id>
GOOGLE_CREDENTIALS_JSON=<entire service-account JSON, inline>
ANTHROPIC_API_KEY=<key>            # optional (free-text classifier)
```
Secrets live **only** in host config — never in the repo (CLAUDE.md invariant).
