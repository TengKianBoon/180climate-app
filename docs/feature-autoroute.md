# Feature design — Automatic land characterization & methodology routing (→ ADR-0013)

**Author:** Cowork (planner) · **Date:** 2026-06-24
**Status:** DECIDED — **deferred build, MANDATORY before launch (Gate L blocker).** Will be **ADR-0013 + a WO batch**, a **contract change → Gate C**, and **advisor-reviewed** first.

## The why (corrected)
The project-type field is **friction**: forest-concession owners are *timber* businesspeople, not carbon experts — a **required** "REDD vs Peat" field is a red star they can't cross, and they abandon the form. So (1) **interim:** make project type **optional** and never block on it; (2) **before launch:** the tool **auto-determines** the project type + methodology from the land, so the owner never has to choose.

## Interim (WO-008, now — no contract change)
- Project type is **optional** in the UI (no red star); the app does **not** wait for it.
- When blank → default to the **permit-driven forest route** (HTI→APD, HA→IFM; **not** peat) + a note: *"We'll confirm your project type from your land."*
- Keep **REDD+ / PEAT** options selectable. (IFM-as-category + auto-detect arrive in ADR-0013.)

## Target categories (ADR-0013) — REMEMBER IFM
Three carbon project categories the tool will route to:
- **REDD+** — avoided deforestation (mineral-soil forest).
- **IFM** — Improved Forest Management / logged-to-protected (HA selective-logging foregone). **← include as a first-class target category.**
- **Peat** — avoided drainage/conversion.

## What decides the methodology, and how we identify it (from the geometry)
| Characteristic | Why it matters | Free data source (swappable, ADR-0007) |
|---|---|---|
| **Peat vs mineral soil** | THE fork: peat → avoided-drainage; mineral soil → REDD+/IFM | Tropical peatland map (Gumbricht et al. 2017 / CIFOR; or Indonesia BRG/KLHK). Contract has `peat_present` + `peat_depth_proxy_m`. |
| **Forest cover & condition** | Forest to protect? intact / degraded / non-forest; REDD+ vs IFM | ESA WorldCover 10 m + Hansen tree-cover (already integrated) |
| **Carbon density** | Magnitude | ESA CCI Biomass (integrated, WO-001c) |
| **Observed loss rate** | Baseline floor | Hansen GFC (integrated) |
| **Permit type (HTI / HA)** | Legal management → APD vs IFM (not satellite-derivable) | Owner input (kept) |

## Decision logic (deterministic — no LLM in the path)
Clip each layer to the boundary → peat %, forest %, density, loss. Then:
- **Peat fraction ≥ threshold** → peat / avoided-drainage for that fraction ("no settled active Verra method as of 2026 — to be confirmed," ADR-0012; Tier-1 indicative).
- **Forested mineral-soil fraction** → **REDD+ / IFM** by permit + condition: HTI → APD (VM0009); HA → IFM (VM0045 / VM0010).
- **Mixed concession → MULTIPLE methodologies** (per area fraction) + a combined indicative range.
- Non-forest / negligible peat → flagged.

## How it plugs in
New **characterization** step in the geospatial core: boundary → `LandCharacterization` → `ProjectClassification` (project_type(s) + MethodologyRoute(s) + area fractions). Engine routes by it (auto), UI drops the manual selector (shows the auto result + advanced override), report states the auto-determined category(ies).

## Implications (why ADR-0013 + Gate C + advisor)
- **Contract change:** multiple methodologies per concession → `MethodologyRoute` becomes a list / new `ProjectClassification` → `core/contracts` → **Gate C**. Adding **IFM** to `project_type` lands here too.
- **New data adapters:** peat map + land cover (free, swappable).
- **Advisor first:** the peat-dataset choice + the REDD+/IFM/Peat + mixed-concession crediting logic — sanity-checked by the independent advisor (like the VM0027 catch), via one uploaded file.

## Sequence to launch
WO-008 (report + mobile + remove red star) → WO-009 (lead → Gate P) → **ADR-0013 auto-routing + IFM (advisor-reviewed) — MANDATORY before Gate L** → go-live.
