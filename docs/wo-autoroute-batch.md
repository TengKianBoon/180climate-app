# ADR-0013 build — WO-AUTOROUTE batch (auto land-routing + legal guardrails)

**Author:** Cowork (planner) · **Date:** 2026-06-24 · **Gate C signed.** Authoritative: `docs/adr/ADR-0013-peatland-routing.md` (peat) + `docs/adr/ADR-0013-auto-routing.md` (non-peat) + `docs/feature-autoroute.md`.
**Build on `main`, no feature branches. Commit coordination/ first, commit+push each step.** Models: **Opus** for the contract change + peat/forest routing logic + reviews; **Sonnet** for adapters, UI, classifier plumbing, tests. Retry 2 → QUESTIONS.

## Goal
Owners never pick a project type; the tool determines it from the land — **and never overclaims on peat**. Peat → flag (never a tonnage); REDD+/IFM gated on confirmed forest; mixed concessions stratified; a free-text "describe your own" option that stays out of the number path.

## Sequence (with Cowork checkpoints)

### WO-AUTOROUTE-001 · Contract change + legal/forest data adapters · Opus (contract) + Sonnet (adapters)
- `core/contracts`: `MethodologyRoute` → list / new `ProjectClassification` (per-stratum routes + flags); add **IFM** + **"other"** to `project_type`; add `peat_additionality_status`, legal-overlay flags, forest-presence flag. (Gate C signed; contract-guard hook.)
- Swappable adapters (free): **KHG fungsi-lindung/dome** (Overlay A), **PIPPIB moratorium** (Overlay B), **ESA WorldCover** (land cover — NOT peat), **JRC TMF** (forest disturbance). Cache for CI.
- **→ STOP — Cowork reviews the contract + adapters** (high-stakes; contract is the constitution).

### WO-AUTOROUTE-002 · Peat = FLAG, never a tonnage (ADR-0013-peatland) · Opus
- Two **separate** overlays (A function, B moratorium) evaluated independently. Output `peat_present=true` + `peat_additionality_status="flag — manual methodological review required"`; **no tCO2e for peat under any branch**; the two status notes (A/B intersects vs neither).
- **Downgrade the existing peat number** (the 18–28 M PEAT golden case) → flag. Update the PEAT golden fixture (assert no tonnage + the flag + status note). Add an **SMPP-style fixture** (deep dome → flag, never excluded).
- Report copy: plain-language rationale next to the peat flag.
- **→ STOP — Cowork reviews the peat behaviour** (integrity-critical).

### WO-AUTOROUTE-003 · Non-peat auto-routing + forest-presence gate · Opus (routing) + Sonnet (UI)
- Auto-determine project type from land; REDD+/IFM by permit + condition (HTI standing forest→APD; HA intact/light→IFM; degraded→flag). **Forest-presence gate:** no REDD/IFM number without confirmed at-risk forest (HTI-on-cleared → flag). Permit-validity caveat in narrative.
- UI: project type **optional** (auto-determined; advanced override).

### WO-AUTOROUTE-004 · "Describe your own" classifier + mixed-concession stratification · Sonnet
- Free-text "other" → **intake classifier** (OUT of the number path; default **out-of-scope** → apology + WhatsApp/email `info@180climate.net`, capture lead; extract structured facts; require geometry for any number). *(This is the one new runtime model call — intake only; determinism preserved.)*
- Mixed concessions → **soil-first stratification** (forested peat → peat stratum = flag; one hectare → one stratum; per-stratum eligibility; combined band keeps peat's wider uncertainty visible).

### WO-AUTOROUTE-005 · Golden cases + re-verify → Gate · Sonnet (+ Opus review)
- Golden fixtures: peat-flag (each overlay), forest-presence gate, REDD+/IFM routing, mixed stratification, free-text triage, **SMPP-as-flag**. Re-verify determinism + no single number / no "%".
- **→ Gate (John + advisor)** sign off the new peat-flag behaviour + routing before it counts as launch-ready.

## After this batch
Remaining pre-launch (docs/pre-launch-backlog.md): brand logo, advisor wording pressure-test, real email/Sheet creds, hosting → **Gate L go-live**.
