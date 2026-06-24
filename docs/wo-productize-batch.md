# Phase 3 — Productize the Carbon Engine (WO-CARBON-007 → 009 → Gate P)

**Author:** Cowork (planner) · **Date:** 2026-06-24 · **Models:** Sonnet (no number-path) · **Gate:** P (PII/lead flow)
The carbon numbers are now real + defensible (Gate M signed; real Hansen loss + real ESA CCI density). This phase turns the engine into the shippable, lead-generating product. **Consumes contracts only.**

## Goal (the funnel, ADR-0003)
A visitor enters a concession → sees the **headline verdict + map** (light capture: name + email) → submits the **full lead form** → gets the **detailed PDF report** → and 180Climate receives the **lead** (DOCX email + Google Sheet). Standalone app on `app.180climate.net` (ADR-0002).

---

### WO-CARBON-007 — Frontend (map + funnel) · Sonnet
- User-facing app: input (coords / GeoJSON / shapefile) → map with forest-loss overlay + boundary → eligibility verdict + carbon **range** + IPCC Tier + rationale render. On-brand (`brand-180climate` skill).
- **Funnel gating (ADR-0003):** light capture up front (name + email) to see the headline verdict + map; the **detailed report + financial-model carrot gated** behind the full lead form.
- Consume the `EngineResult` contract; **no engine changes.** Verifier **screenshots** the rendered UI (golden concession) vs spec §15.
- **Acceptance:** parses coords AND GeoJSON/shapefile → map + verdict; range + Tier + disclaimer render; light-capture gate works; malformed input → clear error; on-brand; screenshots in evidence.
- **→ STOP for Cowork UI review (screenshots)** before the report/lead work.

### WO-CARBON-008 — Report (PDF + DOCX) · Sonnet
- Render the per-user report in **both PDF (user download) + DOCX (internal email)**, same content. Filename = creation timestamp `YYMMDDHHMM` (shared base for both).
- Content carries (ADR-0009): the **range + band + IPCC Tier + screening qualifier + "baseline is the dominant uncertainty"**; methodology routing + additionality wording; brief non-binding disclaimer; and **ends with the "Engage 180Climate" CTA** (full FS, field validation, methodology/baseline advisory, hi-res/LiDAR, EUDR, project development / market access; contact `info@180climate.net`, `www.180climate.net`).
- **Acceptance:** PDF + DOCX generate with the shared timestamp base; carry the uncertainty rules + CTA; **no single number / no "%"**; golden snapshot test.

### WO-CARBON-009 — Lead delivery → Gate P · Sonnet
- On the user clicking download: **email `info@180climate.net`** with the **DOCX attached** + the **full lead-capture form** (name, email, mobile, company, concession, permit type, project type, area, geometry summary) + timestamp; **subject `"{concession} — {filename}"`**.
- **Append the lead to the Google Sheet** (ADR-0004). All lead email → `info@180climate.net`.
- **SECRETS:** email + Sheets credentials live in **host environment config, NEVER in the repo.** In CI/build: file-log/mock the email + a stub Sheet writer; real creds wired at deploy.
- **Acceptance:** capture form → email function called with DOCX + full form (test inbox / file-log) → Sheet append (mock in CI); end-to-end on a golden lead; **no secrets in repo.**
- **→ Gate P** (John verifies the real email + attachment + form capture + Sheet end-to-end before go-live).

---

## After Gate P
Ship **carbon v1** (Gate L go-live) → **Phase 4: EUDR engine** (fast-follow, ADR-0005) → Gate E.

## Note for John (Gate P prep)
At deploy you'll provide the **real email (SMTP for `info@180climate.net`) + Google Sheets API credentials** into the host config — the build implements + tests the flow with mocks; the real send happens with your creds. I'll walk you through it at Gate P.
