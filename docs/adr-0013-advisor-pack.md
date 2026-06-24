# ADR-0013 — Advisor Review Pack (auto land-routing + IFM + "describe your own")

**For:** the strategic/methodology advisor (Claude.ai project) · **From:** Cowork (planner) · **Date:** 2026-06-24
**This file is self-contained — you do not need repo access.** Don't rewrite; identify risks and recommend, like the VM0027 review.

## What I'm asking
We're about to build **automatic methodology routing**: from a concession's geometry, the tool decides the **carbon project type + Verra methodology** itself (so owners — who are timber people, not carbon experts — never have to pick). Before we build it (it's a contract change + methodology-sensitive), please pressure-test the approach below.

## Product context (1 paragraph)
180Climate's free tool gives an **indicative, Tier-1** avoided-emissions **range** for Indonesian forestry concessions. It's **methodology-agnostic** (transparent IPCC-based math; advisor-confirms the exact Verra route for the commercial deal), outputs a **range + IPCC tier** (never a single number, never "% accuracy"), and never cites the deprecated/withdrawn methods (**never VM0048 family / VM0007 / VM0027** — peat already routes to "no settled active Verra method as of 2026"). Additionality basis = **"legal harvest right foregone."**

## The proposed auto-routing (deterministic)
From the boundary, compute peat %, forest cover/condition, carbon density, observed loss, then:
- **peat fraction ≥ threshold → Peat** route ("no settled active method," ADR-0012);
- **forested mineral-soil → REDD+ or IFM** by permit + condition (HTI→APD; HA→IFM);
- **mixed concession → multiple methodologies** (per area fraction) + a combined range;
- plus a **"describe your own"** free-text option → an intake classifier → in-scope (route) or out-of-scope (apologise + contact us).
Candidate free datasets: peat — **Gumbricht et al. 2017 (CIFOR)** and/or **Indonesia BRG/KLHK** peat map; land cover — **ESA WorldCover**; tree cover/loss — **Hansen** (already used); biomass — **ESA CCI** (already used).

## Please answer (independently)
1. **Peat detection:** which free dataset most reliably identifies tropical-peat **extent (and depth, if any)** in Indonesia as of 2026 — Gumbricht 2017, the Indonesian BRG/KLHK peat map, PEATMAP, or another? What **peat-fraction threshold** should trigger the peat route for a screening tool?
2. **REDD+ vs IFM:** how should we distinguish, from land data + permit type, an **avoided-deforestation (REDD+)** candidate from an **improved-forest-management (IFM / logged-to-protected)** candidate? Is permit type (HTI vs HA) enough, or do we need forest-condition signals (intact vs logged)?
3. **Mixed concessions:** when a concession spans peat **and** mineral-soil forest, what's the defensible way to present **multiple methodologies + a combined indicative range** (per area fraction)? Any double-counting / leakage / boundary pitfalls to avoid?
4. **"Describe your own":** for a free-text project description, what's a **conservative, defensible** way to triage in-scope vs out-of-scope **without overclaiming**? (We plan an intake classifier that maps to a known category or flags out-of-scope → "contact us.")
5. **2026 pitfalls:** any methodology/integrity traps in this auto-routing that a skeptical funder or rival would attack (the kind of thing the VM0027 catch surfaced)?
