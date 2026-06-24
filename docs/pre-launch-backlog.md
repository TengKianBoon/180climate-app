# 180Climate — Pre-Launch Backlog (must-do before Gate L go-live)

**Author:** Cowork (planner) · **Date:** 2026-06-24
These are **required before public launch (Gate L)** — tracked here so nothing slips. Current build focus is unchanged: **WO-008 (report + UX) → WO-009 (lead → Gate P)**. The items below come after Gate P, before go-live.

## Must-do before launch

### 1. ADR-0013 — Auto land-characterization & methodology routing
Design: [`feature-autoroute.md`](feature-autoroute.md). Auto-determine project type + methodology from the land (peat-vs-mineral; mixed-concession multi-methodology). Contract change → **Gate C** + **advisor review first**.
- **Target categories:** REDD+, **IFM** (first-class), Peat.
- **"Describe your own" (other) project-type option** *(new — John, 2026-06-24):* add a 3rd choice — a **free-text box** where the owner describes their project in their own words. Then:
  1. **Interpret** the description (an *intake classifier* — sits at the input layer, **NOT** in the deterministic number/verdict path, so the determinism invariant holds).
  2. Decide **in scope** (maps to a known methodology → route it) **or out of scope**.
  3. If **out of scope:** show a brief, polite **apology** + encourage them to **WhatsApp / email `info@180climate.net`** to discuss the scope in detail — and **capture the lead either way** (this is still a warm contact).
  - Project type stays **optional** (no red star); REDD+/PEAT remain selectable.

### 2. Brand logo
Replace the text "180°" header logo with the **official 180climate logo** (green two-tone leaf/flame mark above the "180climate" wordmark). Apply across the UI header + the PDF/DOCX report header/footer.
- **Action for John:** save the logo file into the repo at **`brand/180climate-logo.png`** (the `brand/` folder is created), or attach it in chat and Cowork will place it. *(Pasted-inline images can't be saved to the workspace as files.)*

### 3. Advisor wording pressure-test
Final narrative/report copy reviewed by the independent advisor (the offered wording check) before public.

### 4. Real lead delivery (Gate P)
Email (SMTP for `info@180climate.net`) + Google Sheets API credentials in **host config** (never in repo); end-to-end test of the funnel.

### 5. Hosting
Deploy the standalone app on **`app.180climate.net`** (ADR-0002), linked from the Wix site.

### 6. Carry-overs
GEE non-commercial caveat (ADR-0007); VM0009 / VM0010-vs-VM0045 advisor-confirm at deal time.

## Not blocking launch
Spatial peat-map refinement (OI-2), shapefile upload in the UI, satellite loss-tile map overlay.
