# Phase 2 — Carbon Engine Work Orders (WO-CARBON-001 … 005)

**Author:** Cowork (planner) · **Date:** 2026-06-24 · **Gate at end:** Gate M (John + independent advisor)
**Consumes** `core/contracts/` only — any contract change needs an ADR + Gate C.

## Goal of Phase 2
Turn the placeholder slice into the **real, defensible carbon engine**: real free-tier data, the eligibility gates, the Verra methodology routing, an avoided-emissions **range + quality + IPCC tier**, and the Verra-family narrative. **Determinism invariant holds — the only LLM call is the narrative.**

## Execution & budget (the multi-agent showcase)
Run as **parallel git worktrees** (this is the portfolio exhibit of multi-agent orchestration), **cap ~3 concurrent**. **Tiered models:** **Opus** for the number/methodology path (**003, 004**) + their reviews/verify; **Sonnet** for data adapters (001), golden cases (002), narrative templates (005). **Retry budget 2 → STOP + QUESTIONS.**

## Order & dependencies
1. **WO-CARBON-001 (data)** ∥ **WO-CARBON-002 (golden cases)** — parallel first → **STOP for Cowork review** (data + golden cases are the test oracle).
2. → **WO-CARBON-003 (eligibility + routing, Opus)**
3. → **WO-CARBON-004 (estimate range + quality, Opus)**
4. → **WO-CARBON-005 (narrative + Verra rationale)**
5. → **Gate M** (John signs off numbers + routing + disclaimers; send the Claude.ai advisor one line for an independent read first).

---

### WO-CARBON-001 — Real geospatial data integration · *Sonnet*
**Objective:** replace the GFW stub with real free-tier sources **behind a swappable adapter** (ADR-0007), populating `ForestData`.
**In scope:** GFW/Hansen annual loss; ESA CCI Biomass → `biomass_tco2_per_ha` proxy; peat presence/depth proxy; `loss_after_2020_ha`; all behind a `DataSource` interface so paid hi-res can swap in later (this is the "easy vendor swap"); GEE non-commercial flagged in README.
**Acceptance:** `ForestData` populated from real sources on the golden concessions; `data_sources` labelled; `uncertainty_band` human-readable; **stub ↔ real swap test passes**; deterministic given cached inputs; no secrets.
**Evidence:** sample `ForestData` for golden concessions; data-source labels; swap-test output.

### WO-CARBON-002 — Golden cases · *Sonnet*
**Objective:** encode the test oracle from spec §15 so correctness is pinned.
**In scope:** input→expected for every eligibility-gate combo (HTI/HA, >5 yr, ≥20,000 ha, inside-IUP) → eligible/flagged/hard_no; methodology routing by permit type; output is a **range + band + IPCC tier** (never a single number, never a "%"); determinism. Numeric expected ranges are pinned once 003/004 define the calc, then **frozen**; structure/routing/format pinned now.
**Acceptance:** golden suite in CI; covers all gate combos + all routes + the "no single number / no %" lint; **red on violation**.
**Evidence:** golden fixtures committed; CI green.

### WO-CARBON-003 — Eligibility gates + methodology routing · **Opus (high-stakes number path)**
**Objective:** the defensible core — eligibility verdicts + correct Verra-family routing.
**In scope:** `EligibilityResult` (permit_type HTI/HA · permit_years_remaining > 5 · area ≥ 20,000 ha · within-IUP) → eligible/flagged/hard_no + reasons; `MethodologyRoute` by permit type — **HTI→APD (clear-fell foregone), HA→IFM (selective foregone), Peat→interim** (ADR-0001); `additionality_basis = "legal harvest right foregone"`; `is_planned = True` for HTI/HA; **never** the VM0048 family for foregone-harvest; **never** VM0007.
**Acceptance:** all golden gate + routing cases pass; routing matches `docs/methodology.md`; contract-guard clean; deterministic.
**Evidence:** golden routing results; methodology.md cross-check; **Opus** Reviewer + Verifier reports.

### WO-CARBON-004 — Avoided-emissions range + quality · **Opus (high-stakes number path)**
**Objective:** the actual numbers — a transparent avoided-emissions **range** + quality + IPCC tier.
**In scope:** `CarbonEstimate.quantity_low_tco2e` / `quantity_high_tco2e` (a **range**, never single); `uncertainty` band; **IPCC Tier** label (free = Tier 1 screening; hi-res/LiDAR = toward Tier 2; field + accredited + verified = Tier 3); `QualityFactors` (additionality, permanence, leakage, methodology_fit); math = eligible area × carbon density × project-type factor × baseline loss-rate × risk/buffer — transparent + deterministic. **ADR-0009 enforced.**
**Acceptance:** golden cases produce expected ranges + tiers; **lint fails on any single bare number or "% accuracy/confidence"**; baseline stated as the dominant uncertainty; deterministic.
**Evidence:** sample estimates (range + band + tier) for golden concessions; **Opus** Reviewer + Verifier reports.

### WO-CARBON-005 — Narrative + Verra rationale · *Sonnet (codes the templates; runtime LLM is the product's narrative)*
**Objective:** the defensible AI rationale — the **only** LLM call in the product.
**In scope:** `NarrativeResult` cites the correct Verra family by permit type; states additionality as **"legal harvest right foregone"**; uses IPCC-Tier language; states **baseline (not satellite) is the dominant uncertainty**; brief non-binding disclaimer; ends with the **"Engage 180Climate"** CTA. The number path stays deterministic (narrative explains, never computes).
**Acceptance:** narrative cites the routed family; additionality wording present; **no single number / no "%" in output**; disclaimer + CTA present; determinism invariant intact.
**Evidence:** sample narratives for golden concessions; lint for forbidden phrasing.

---

## Gate M (the big human gate)
John reviews **the numbers, the routing, and the disclaimers**. Recommended: send the Claude.ai advisor one line — *"Gate M ready — github.com/TengKianBoon/180climate-app"* — for an **independent** read on methodology + numbers **before** John signs off. *Agents prove conformance; John defines truth.*
