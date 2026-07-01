# ADR-0018 — EUDR contracts: detection enum, categorical readiness, role + stamps (no "compliant" strings)

**Status:** ACCEPTED — **Gate C signed by John (2026-06-29).** Advisor field-name/wording divergence check runs in parallel (resolve before the E4+ UI Work Orders).
**Type:** `core/contracts` change (EUDR models) → **Gate C**. **Opus** build (WO-E1). First EUDR Work Order.
**Governs:** `docs/eudr-design-v2.md` (C1/C2/M1/M2) + `docs/eudr-value-first.md`. **Carbon contracts untouched.**

## Context
The EUDR models in `core/contracts` are stubs (`Plot`, `EUDRInput`, `PlotVerdict.deforestation_free: bool`, `EUDRVerdict`).
The design + value-first principle require the engine to be a **triage & DDS-prep screen, never a compliance verdict** —
which has to be enforced at the contract layer so no downstream code can emit a legal clearance.

## Decision
1. **`PlotVerdict.deforestation_free: bool` → `detection: Literal["clear_in_screen","loss_detected","inconclusive","geometry_invalid"]`.**
   Free satellite detects *no loss detected*, not legal "deforestation-free." `inconclusive` is a first-class state
   (cloud / <4 ha / agroforestry / radar noise / degradation invisible to free data).
2. **Readiness is CATEGORICAL** — per-component `Literal["complete","incomplete"]` (or ✓/✗), **no 0–100 score**. If any
   numeric `readiness_score` exists, remove it (false precision + a litigation handle).
3. **Role enum** on `EUDRInput`: `Literal["eu_first_placer","downstream_operator","non_eu_supplier"]` — only the first
   EU-market placer files the DDS (often the exporter's EU buyer); drives the "who files" explainer.
4. **Two separate risk fields** (never conflated): `country_benchmark_risk` (lookup; Indonesia = `"standard"`) and
   `plot_satellite_risk` (from the triage). 
5. **Provenance stamp** on every `PlotVerdict` / `EUDRVerdict`: `datasets_version: str` + `run_date: date` (Hansen/JRC/RADD
   versions + screening date).
6. **Banned strings (hook-enforced, like the carbon contract-guard):** no `"compliant"`, `"deforestation-free"`,
   `"DDS-ready"`, `"due diligence statement ready"` anywhere in EUDR output. Export naming = "geolocation pack for DDS preparation."
7. **Commodity** enum = the 5 Indonesia-relevant (`palm`,`rubber`,`timber`,`cocoa`,`coffee`); others → `"manual_review"`.

## Invariants & tests
- `PlotVerdict.detection` is the enum; **no boolean deforestation_free remains**; grep-test asserts the banned strings
  never appear in any EUDR serialized output or template. Readiness has no numeric score. Every verdict carries
  `datasets_version` + `run_date`. Country vs plot risk are distinct fields. Determinism intact (pure functions; no LLM in the verdict path).

## Consequences
+ The legal posture is enforced in the type system, not just copy; the per-plot detection enum is also **more useful**
  (actionable per-plot) than a bool — value and rigour aligned.
− All EUDR stubs/tests that reference `deforestation_free` are updated; downstream E2–E7 build on these types.

## Gate C evidence to gather
The enum migration; banned-string guard test; categorical readiness; role + risk + stamp fields; carbon contracts
unchanged; advisor confirms field names + the safe wording in `docs/eudr-design-v2.md` still match.

## Micro-amendments — advisor divergence check (2026-06-29; John + advisor approved; in-window per "resolve before E4+")
1. **Remove the stored `PlotVerdict.geometry_ok` bool → computed property** `geometry_ok == (detection != "geometry_invalid")`.
   `detection` is the single source of truth; dual storage would drift. (Builder folds into WO-E2.)
2. **`plot_satellite_risk` → derived from `detection`** (computed property, or pinned invariant + test):
   `clear_in_screen→low`, `loss_detected→high`, `inconclusive→inconclusive`, **`geometry_invalid→inconclusive`** ("couldn't observe").
3. `EUDRVerdict.overall` confirmed = `clear_in_screen / loss_detected / review_needed` — **no bare `clear`/`pass`/`ok`**
   value (guard satisfied). `clear_in_screen` is governed at render time by the **value-first render guard** (see
   `docs/eudr-value-first.md`), not a banned-string add.
4. **Legal facts confirmed (advisor):** deadlines **30 Dec 2026 / 30 Jun 2027** (OJ 23 Dec 2025 — current); Indonesia =
   `standard` per Implementing Reg **2025/1093** (140 low / 4 high [BY/MM/KP/RU] / rest standard) — stamp the benchmark
   version. SME postal-address simplification is **low-risk-country-only** → Indonesian plots still need real geolocation
   regardless of operator size → the geolocation pack stays central to the value prop. **Two substantive limbs:**
   deforestation-free **and** legality — the free screen covers only the first (see value-first (b) legality note).
