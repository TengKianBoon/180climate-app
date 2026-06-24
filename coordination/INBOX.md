# INBOX — Cowork (planner) · 2026-06-24 · WO-CARBON-009 (lead delivery → Gate P)

## WO-008 review: APPROVED (report defensible + on-brand; 3 UI fixes correct; 101 green). Merged on main.

## Git discipline (unchanged): work on main, commit coordination/ FIRST, commit+push each step, no branches, no stash.

## WO-CARBON-009 — Lead delivery → Gate P · Sonnet · on main
Wire the lead pipeline (ADR-0004 + ADR-0010). All lead email → info@180climate.net.
- **On report download / lead submit:** email **info@180climate.net** with the **DOCX attached** (reuse
  reports/generator.generate_docx) + the **full lead-capture form** (name, email, mobile/WhatsApp, company,
  concession, permit type, project type, area, geometry summary) + timestamp; **subject "{concession} — {filename}"**.
- **Append the lead to the Google Sheet** (ADR-0004).
- **SECRETS:** email (SMTP) + Sheets credentials live in **host env config, NEVER in the repo.** In CI/build:
  **mock** the email (write to a local outbox file) + a stub Sheet writer. Real creds wired at deploy (Gate P).
- **Acceptance:** download/submit → email function called with DOCX + full form (assert via the mock/outbox file)
  → Sheet append (mock in CI); end-to-end on a golden lead; **no secrets in repo**; tests green.
- **→ Gate P** (John verifies the real email + attachment + form capture + Sheet end-to-end; John provides the
  real SMTP + Sheets creds in host config). Write coordination/GATE.md = "GATE P READY" + evidence, STOP.

Retry budget 2 → QUESTIONS. Regenerate board + commit + push each step.

## QUEUED (pre-launch, MANDATORY before Gate L): ADR-0013 auto-routing + IFM + "describe your own" option; brand logo swap. (docs/pre-launch-backlog.md)
