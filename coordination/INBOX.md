# INBOX — Cowork (planner) · 2026-06-24 · WO-CARBON-008 (report + UI tweaks) — re-dispatched after git recovery

## Git discipline for the PRODUCTIZE phase (important)
- Work **directly on `main`** — NO feature branches for WO-008/009 (avoids the merge/CRLF collision).
- **First step:** `git add coordination/ && git commit` to absorb this dispatch, THEN do the work.
- Commit + push each green step. NEVER stash coordination/. `.gitattributes` now enforces LF.

## WO-CARBON-008 — Report (PDF + DOCX) + UI tweaks · Sonnet · on main
### (A) Frontend tweaks (no contract change)
- (i) Methodology pill + report read the route from the **engine's MethodologyRoute** (NOT client-side
  permit_type) — verify a PEAT project shows "no settled method" (ADR-0012 consistency).
- (ii) **Mobile (WhatsApp)** → move into "Your details", make it **COMPULSORY** (required like name+email;
  label "Mobile (WhatsApp)"); carry into the lead email.
- (iii) **Project type → OPTIONAL (remove the red star).** The app must NOT require/wait for it. When blank,
  default to the permit-driven forest route (HTI→APD, HA→IFM; NOT peat) + a note: "We'll confirm your
  project type from your land." Keep REDD+/PEAT selectable. (Frontend defaults when blank → no contract change.)

### (B) Report (PDF + DOCX)
- PDF (user) + DOCX (internal), same content, filename = YYMMDDHHMM shared base. Carry: range + band + IPCC
  Tier + screening qualifier + "baseline is the dominant uncertainty" (ADR-0009); engine-sourced methodology +
  additionality wording; brief non-binding disclaimer; ends with "Engage 180Climate" CTA (info@180climate.net).
  No single number / no "%". Golden snapshot test.

### Then STOP for Cowork review. → WO-CARBON-009 (lead delivery → Gate P).
Retry budget 2 → QUESTIONS. Regenerate board + commit + push each step.

## QUEUED (pre-launch, MANDATORY before Gate L; not now): ADR-0013 auto-routing + IFM + "describe your own"
project-type option (intake classifier → in/out-of-scope triage); brand logo swap. See docs/pre-launch-backlog.md.
