# ADR-0015 — HTI plantation gate (C1) + IFM logging-emissions basis (C2)

**Status:** ACCEPTED — advisor-confirmed + Gate C signed by John, 2026-06-26
**Type:** number-path + `core/contracts` change → contract-guard hook · **Opus** build + review
**Origin:** advisor capstone recheck + methodology-confirm (Cowork-verified in code). **These corrections CHANGE numbers — that is the point.**

## Context
Two Critical flaws, both on the main permit types:
- **C1 — HTI plantation / Hansen harvest-cycle:** no plantation detection → an active HTI plantation's rotational
  harvest (Hansen "loss") is credited as avoided deforestation. The misleading-tonnage path.
- **C2 — IFM category error:** HA→IFM uses the avoided-deforestation `_estimate_redd` (full density × loss-rate).
  IFM (VM0010) baseline is *selective logging* — emissions are a **fraction** of stock per cutting cycle, not clearance.

## Decision

### C1 — Forest-origin gate (natural vs established plantation) before any APD number
- **Discriminator (advisor-corrected):** primary = **KLHK official maps** (Penutupan Lahan distinguishes *hutan
  tanaman* / plantation vs *hutan alam* / natural forest; concession layer for boundaries — administrative ground
  truth, and the user already declares permit = HTI) **+ rotational-harvest *temporal pattern*** (the short, regular
  ~5–7 yr clear-and-replant return interval in the **JRC TMF** / Hansen time series — natural forest is not
  stand-replaced on a 5–7 yr grid). **ESA WorldCover is DEMOTED** to coarse forest/non-forest/cropland support only —
  it cannot tell Acacia from dipterocarp, so it is **not** the plantation signal. (Oil-palm maps e.g. Descals don't
  help — HTI is *timber*, not palm.)
- **Standing natural forest** (not yet cleared) → legitimate **APD** candidate → number (corrected baseline below).
- **Established plantation / already-converted** → **FLAG:** *"established plantation — no standing natural forest at
  risk → not an APD candidate; rotational-harvest loss is not avoidable deforestation."* **No avoided-deforestation number.**
- **Mixed** → stratify: natural-forest area → APD; plantation area **excluded**. The natural-forest baseline loss-rate
  **must mask plantation rotational-harvest pixels** (via JRC TMF) before averaging Hansen loss.
- **Legal gate retained (ADR-0013) — necessary-but-not-sufficient:** standing natural forest under the
  **PIPPIB moratorium** has no legal right to convert → "legal harvest right foregone" is void → also **not-APD**. The
  ADR-0013 moratorium + forest-condition gate must still fire.
- Contract: add `ForestData.forest_origin: Literal["natural","plantation","mixed","unknown"]`.

### C2 — Distinct IFM (selective-logging) emissions basis for HA
- **EF SOURCE = Pearson et al. (2014)** + Indonesia field studies (Butarbutar 2019, Griscom). **IPCC 2006 Vol 4 +
  2019 Refinement is the *conversion math only*** (BCEF volume→biomass, carbon fraction ≈ 0.47, × 44/12) — **IPCC does
  not publish a selective-logging EF.** The extracted log is only **15–25 %** of emissions; **damage + infrastructure
  dominate** → use the **full Total Emission Factor (TEF)**, not just extracted-timber carbon.
- **Indonesia / SE-Asia defaults (advisor-confirmed):**
  - TEF ≈ **1.4–1.5 Mg C/m³** (full, incl. infrastructure); 0.82 Mg C/m³ (extraction + damage only).
  - Logging intensity ≈ **30 m³/ha** (band 26–40).
  - **EF_per_ha ≈ intensity × TEF × 44/12 ≈ ~160 tCO₂/ha** (cross-check: ~50 tC/ha ≈ **185 tCO₂/ha** per entry, Butarbutar Kalimantan).
  - Cutting cycle (TPTI) ≈ **35 yr**.
- **Engine form:**
  ```
  avoided_CO2 ≈ harvested_area × EF_per_ha × (1 − buffer)
    harvested_area = eligible_area × min(1, crediting_years / cycle_years)
    n_entries = 1          # ONE avoided entry in a 20–30 yr period vs a ~35 yr cycle — do NOT multiply by cycles
  ```
- **Citations:** lead with **VM0010** (selective-logging baseline, excludes planted forests). **VM0045 is field/NFI-
  dependent — NOT satellite-screenable**; flag it, don't present it as the satellite route.
- **Scope labels (don't over-build):** (a) VM0010 also credits *removals* from continued growth → our
  avoided-emissions-only estimate is a **conservative floor** — label it. (b) A share of the extracted log becomes
  long-lived wood products (not emitted); since extracted-log is 15–25 %, this is **second-order — note, don't engineer now**.

## Invariants & tests (advisor-corrected)
- **Plantation-HTI fixture → number *down* or FLAG** (no avoided-deforestation number).
- **HA→IFM uses the logging-basis formula path** (`harvested_area × EF_per_ha`, NOT `density × loss_rate`) and
  **reconciles to the shown derivation. DO NOT assert "smaller"** — HA may come out *comparable or larger* (the old
  Hansen-loss method under-counted selective logging, which Hansen mostly misses). Worked: 73,787 ha × (15/35) ×
  ~160–185 tCO₂/ha ≈ **~5–5.8 M tCO₂e** vs old REDD 3.59–5.13 M. **Test the basis + reconciliation, not the direction.**
- **n_entries = 1** (no multi-cycle multiplication).
- Peat unchanged (flag/None). Determinism intact.
- **Golden numbers WILL change for HA + plantation-HTI — re-baseline the goldens and document before→after per case** (this ADR authorizes it).

## Consequences
+ Removes the misleading-tonnage path (C1) and the IFM category error (C2).
− HA + plantation-HTI numbers change; goldens re-baselined; `core/contracts` change → **Gate C**. Methodology +
  factors are **advisor-confirmed** (above).

## Gate C evidence to gather (John/architect sign-off)
Contract diff (additive); the plantation-flag + IFM-basis tests green; the re-baselined goldens with a documented
before→after for each changed case; advisor confirms against the diff + goldens.
