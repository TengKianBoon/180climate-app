# GATE C — ADR-0016 (uncertainty propagation + density gating) — SIGNED

**Decision:** APPROVED by John ("proceed", 2026-06-26); advisor post-build confirm waived by John for this one.
**Authorizes:** the `core/contracts` + number-path change in ADR-0016 — `ForestData.biomass_uncertainty_pct`, M1
uncertainty propagation (density SE + loss CV in quadrature; buffer applied separately), M2 density-fallback gating.
**Ranges WIDEN (intended); goldens re-baselined.**
**Build:** WO-METHFIX-002 (INBOX) — Opus. **Post-build:** Cowork verifies (band widens, buffer separate, default-density
loud-flag, no-biomass flag, peat unchanged, before→after documented).
**Prior gate:** ADR-0015 (plantation + IFM) — built, Cowork-verified, advisor confirm waived by John.
