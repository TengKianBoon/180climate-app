# ADR-0013 (companion) — Non-peat auto land-routing

**Status:** Proposed → John approve + Gate C (with `ADR-0013-peatland-routing.md`). Design: `docs/feature-autoroute.md`.
**Peat is governed by [`ADR-0013-peatland-routing.md`](ADR-0013-peatland-routing.md)** (advisor-reviewed: peat = flag, **never a tonnage**; two overlays; restoration/WRC vs avoided-conversion). This companion covers the **non-peat** auto-routing.

## Decision (non-peat)
1. **Auto land-characterization** from the boundary → project type + methodology, so owners never pick (project-type field stays **optional**; auto-determined; advanced override).
2. **Target categories:** REDD+, **IFM** (first-class), Peat (→ peatland ADR).
3. **Forest-presence/condition gate (REQUIRED before any REDD/IFM number):** confirm standing forest + condition (Hansen tree-cover + loss, ESA CCI/GEDI biomass, JRC TMF). **HTI on already-cleared/scrub land → no at-risk forest → flag likely-ineligible.** Permit type is the *presumption*; condition must *confirm*. Plus a **permit-validity caveat** (Indonesian permits overlap / One-Map disputes / permits-in-principle → never assume a valid right from a boundary; advisor-confirm).
4. **REDD+ vs IFM:** by permit + condition — HTI on standing natural forest → APD; HA on intact/lightly-logged → IFM; heavily-degraded → low baseline / flag.
5. **"Describe your own" (other) option:** free-text → an **intake classifier** at the *input* layer only (**never in the deterministic number path**); maps to a known category or **defaults to out-of-scope** ("contact us — WhatsApp/email info@180climate.net", capture the lead); extracts structured facts (never accepts user self-assessed eligibility); still requires geometry for any number.
6. **Mixed concessions → per-area stratification:** **soil-first** (forested peat → the peat stratum, each hectare → exactly one stratum, no double-counting trees-on-peat); stated no-internal-shifting/leakage assumption; minimum stratum size; **peat's wider uncertainty kept visible**; **per-stratum eligibility** (not one blended verdict). The peat stratum follows the peatland ADR (flag).
7. **Datasets (free, swappable):** official Indonesian maps as the legal reference (KHG function, PIPPIB) for the legal overlays; Hansen + ESA CCI/GEDI + JRC TMF for forest/condition; ESA WorldCover **cannot identify peat** (substrate, not land-cover).
8. **Contract change (Gate C):** `MethodologyRoute` → list / `ProjectClassification` with per-stratum routes + flags; add IFM + "other" to `project_type`; legal-overlay + forest-presence flags. **Determinism preserved** (classification deterministic on data + overlays; free-text classifier is intake-only).
