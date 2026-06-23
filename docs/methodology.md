# 180Climate — Carbon Methodology Routing

**Status:** Normative · **ADR:** ADR-0001 · **Updated:** 2026-06-24

The carbon engine is **methodology-agnostic**: it computes a transparent avoided-emissions range
(deterministic pure functions). The **AI narrative** cites the correct Verra family by permit type,
using this routing table. The routing is enforced by golden-case tests and the contract-guard hook.

---

## Routing table (normative)

| Permit / project type | Baseline class | Verra family cited in narrative |
|---|---|---|
| **HTI** (industrial timber plantation; legal right to clear-fell) | Planned clear-fell foregone | **APD route** (VM0009/legacy — advisor-confirm) |
| **HA** (natural-forest logging; legal right to selectively log) | Planned selective-logging foregone | **IFM (VM0045 / VM0010)** — advisor-confirm active version |
| **Peat** | Avoided drainage/subsidence | **No settled active Verra method** for avoided tropical-peat conversion as of 2026 — route to be confirmed with advisor; IPCC Tier-1 indicative only. VM0027 inactivated 2023 (rewetting method — wrong activity). Never VM0027 / VM0048 / VM0007. |
| *(reference only)* Unplanned / illegal loss (AUD) | — | VM0048 + VMD0055 + VT0007 — **NEVER used for foregone-harvest** |

---

## Hard rules

1. **`is_planned` MUST be `True`** for HTI and HA foregone-harvest baselines.
2. **`additionality_basis` MUST be `"legal harvest right foregone"`** for HTI and HA.
3. **Never cite VM0007** (deprecated; excluded from ICVCM Core Carbon Principles) or the VM0048 family
   for a foregone-legal-harvest baseline.
4. **Peat routing is unresolved** — VM0027 was inactivated by Verra in 2023 (it is a rewetting method, not avoided conversion). **Never VM0027 / VM0048 / VM0007** for a peat avoided-conversion project. Label as "No settled active Verra method as of 2026 — route to be confirmed; IPCC Tier-1 indicative." The engine computes a transparent IPCC Tier-1 avoided-drainage range; cite no Verra method. (ADR-0012.)
5. The narrative **always states** the additionality basis explicitly.

---

## Background (ADR-0001 context)

The Verra landscape shifted: unplanned-deforestation (AUD) moved to **VM0048 v1.0 + VMD0055 v1.1 + VT0007**
with jurisdictionally-set third-party baselines. Planned foregone-legal-harvest baselines fit **APD**
(HTI clear-fell foregone) and **IFM VM0010 / VM0045** (HA selective-logging foregone). VM0007 and several
legacy methods are **deprecated / excluded from ICVCM Core Carbon Principles**.

The key insight: HTI/HA foregone-harvest is a **PLANNED** baseline — not unplanned deforestation.
Routing to the AUD family (VM0048) would be technically incorrect and reputationally damaging.

---

## Uncertainty (ADR-0009)

All carbon outputs carry:
- A **range** (`quantity_low_tco2e` … `quantity_high_tco2e`) — never a single point estimate.
- An **uncertainty band** string (e.g. "±20% — free satellite, Tier 1 screening").
- An **IPCC Tier label**: free satellite = Tier 1; hi-res/LiDAR = toward Tier 2; field + accredited + verification = Tier 3.
- A plain-language statement: **"the baseline/counterfactual — not satellite resolution — is the dominant uncertainty."**
- **Never** a "% accuracy" or "% confidence" string.

---

## Gate M

Before any public release, **Gate M** (John) verifies:
- Correct routing on all golden cases.
- Numbers (range + band + IPCC tier) are defensible.
- Additionality wording and disclaimers are correct.
- No deprecated method is cited.
