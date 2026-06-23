# Gate M Advisor Pack — 180Climate Carbon Pre-FS Engine

**Date:** 2026-06-24 (updated post-WO-CARBON-006)
**Phase:** P2 · Carbon engine
**Gate:** M (methodology + numbers review before any public release)
**Status:** GATE M READY — all advisor-identified issues resolved (WO-CARBON-006 complete)

---

## 1. Advisor review outcome (CONDITIONAL GO → RESOLVED)

The independent methodology advisor reviewed the engine at WO-CARBON-003/004 completion and returned **CONDITIONAL GO** with these required fixes:

| Advisor item | Fix applied | Evidence |
|---|---|---|
| **Peat/VM0027 error** — VM0027 is a rewetting method (inactivated 2023); wrong activity type for avoided drainage/conversion | ADR-0012 approved; VM0027 removed from engine, fixture, narrative, docs (WO-CARBON-006A) | tests green (81/81); verra_family_must_not_contain assertion in golden fixture |
| **N1 framing** — "FS = bigger number" wording and "planned baseline likely higher" must be dropped; separate observed-loss floor from planned baseline | Narrative rewritten (WO-CARBON-005/006B): observed-loss floor explicitly ≠ APD/IFM planned baseline; FS framed as "defensible, independently-established, verifiable baseline (which may be higher OR constrained)" | narrator.py updated |
| Buffer framing | Buffer explicitly labelled "placeholder for AFOLU non-permanence risk-tool output" | narrator.py |
| Peat EF framing | EF 9–13 labelled "conservative; deeply-drained plantation peat is often higher" | narrator.py |
| Co-dominant REDD uncertainties | Narrative now states baseline AND carbon density as co-dominant | narrator.py |

---

## 2. What the engine does

The 180Climate carbon pre-feasibility engine produces an **indicative Tier-1 avoided-emissions range** for Indonesian timber concessions (HTI / HA permit types, and PEAT project overlay). It is:

- **Deterministic:** pure Python functions, no LLM in the number/verdict path.
- **Transparent:** every input, formula, and IPCC source is visible in the output.
- **Methodology-agnostic:** computes an avoided-emissions range using IPCC default values; does not submit to any registry or claim credits (ADR-0006).
- **Range-only:** always `quantity_low_tco2e … quantity_high_tco2e`; never a single number (ADR-0009).
- **Screened:** four eligibility gates before any estimate (permit type / permit years / area / within Indonesia).

---

## 3. Methodology routing (corrected per ADR-0012)

| Permit / project type | Baseline class | Verra family cited |
|---|---|---|
| **HTI** (planned clear-fell foregone) | `planned_clearfell` | APD (VM0009 — active but in transition; advisor-confirm at deal time) |
| **HA** (planned selective-logging foregone) | `planned_selective` | IFM (VM0045 / VM0010) — advisor-confirm active version |
| **Peat** (avoided drainage/conversion) | `peat` | **No settled active Verra method as of 2026 — route to be confirmed** |

**Invariants (enforced by golden-case tests + contract-guard hook):**
- `is_planned = True` for all three routes.
- `additionality_basis = "legal harvest right foregone"` for all three routes.
- Never VM0048 family / VM0007 / VM0027 for these project types.

**ADR-0012 (peat routing correction):**
VM0027 was inactivated by Verra on 2023-09-11 and is a rewetting methodology — incorrect activity type for avoided drainage/conversion. No active standalone Verra methodology for avoided tropical-peat conversion exists as of June 2026. The engine still computes a transparent IPCC Tier-1 avoided-drainage range (methodology-agnostic per ADR-0006); the number is unchanged.

---

## 4. Numbers reviewed (WO-CARBON-004 — frozen golden ranges)

| Fixture | Permit | Yrs | Area (ha) | Verdict | Low (tCO₂e) | High (tCO₂e) |
|---|---|---|---|---|---|---|
| HTI eligible | HTI | 20 | 73,787 | eligible | **4,785,077** | **6,835,824** |
| HTI flag years | HTI | 3 | 73,787 | flagged | 717,762 | 1,025,374 |
| HTI fail area | HTI | 20 | 1,107 | hard_no | 127,742 | 182,489 |
| HA eligible | HA | 15 | 73,787 | eligible | **3,588,808** | **5,126,868** |
| HTI outside IUP | HTI | 20 | proxy 25k | flagged | 2,279,952 | 3,257,074 |
| **PEAT (73k ha)** | HTI | 20 | 73,787 | eligible | **12,277,761** | **19,605,702** |

**Key parameters:**
- Baseline loss rate: **0.8812 %/yr** (8-yr satellite average 2016–2023; StubAdapter proxy — real Hansen pixel read deferred to WO-CARBON-001b)
- Biomass: **657.1 tCO₂/ha** (IPCC 2006 Table 4.7, lowland moist tropical, SE-Asia)
- Peat biomass: **409.3 tCO₂/ha** (IPCC 2006 Table 4.7, peat_swamp AGB+BGB)
- Peat drainage EF: **9.0–13.0 tCO₂-eq/ha/yr** (IPCC 2013 Wetlands Table 2.1, tropical drained; conservative — deeply-drained plantation peat is often higher)
- Buffer: **20–30%** (placeholder for VCS AFOLU non-permanence risk-tool output)
- IPCC Tier: **Tier 1** throughout (default values; no field measurement)

---

## 5. Narrative framing (WO-CARBON-005/006B — corrected)

- **Observed-loss floor separated from planned baseline:** figure is "a deliberately conservative floor derived from OBSERVED forest loss" — not the APD/IFM VM0009 planned-harvest baseline, which is only established at registry grade from the IUP permit document.
- **No "FS = bigger number" wording:** FS is "the defensible, independently-established, verifiable baseline (which may be higher OR constrained by additionality / leakage / conservative-baseline rules)."
- **VM0009:** "active but in transition — advisor-confirm at deal time."
- **IFM:** "IFM (VM0045 / VM0010) — advisor-confirm active version."
- **Peat EF:** "conservative; deeply-drained plantation peat is often higher."
- **Buffer:** "placeholder for the AFOLU non-permanence risk-tool output."
- **Co-dominant REDD uncertainties:** baseline AND carbon density (ESA CCI / GEDI grounding deferred to WO-CARBON-001b).
- **Tonnage suppressed** for `hard_no` and `flagged` verdicts.
- **"Engage 180Climate" CTA** at end of every narrative.
- **No single number / no "%"** anywhere in output (ADR-0009).

---

## 6. What is NOT claimed at this stage

- No registry submission, no credit issuance, no financial projection.
- No field measurement (Tier 1 only).
- No pixel-level Hansen loss read (deferred to WO-CARBON-001b).
- No peat depth survey.
- No spatial peat map applied.
- The baseline loss rate is a stub proxy (0.8812%/yr); real concession rates will differ.

---

## 7. Open items for follow-on work (not Gate-M blockers)

| ID | Item | WO |
|---|---|---|
| OI-1 | Real Hansen pixel loss rate (replace stub) | WO-CARBON-001b |
| OI-2 | Spatial peat map (confirm peat layer extent) | Future |
| OI-3 | VM0009 transition status (advisor-confirm when deal-ready) | Deal-time |
| OI-4 | IFM VM0045 vs VM0010 active version (advisor-confirm when deal-ready) | Deal-time |
| OI-5 | ESA CCI / GEDI carbon density grounding | WO-CARBON-001b |
| OI-6 | GEE non-commercial caveat (flagged in README + ADR-0007) | Ongoing |

---

## 8. Evidence pointers

- `coordination/evidence/WO-CARBON-003/review-report.txt` — Opus Reviewer + Verifier APPROVED (routing + eligibility hardening)
- `coordination/evidence/WO-CARBON-004/review-report.txt` — Opus Reviewer + Verifier APPROVED (estimate range, frozen golden ranges)
- `coordination/evidence/WO-CARBON-006/review-report.txt` — Opus Reviewer APPROVED (peat routing fix after docstring correction)
- `docs/adr/ADR-0012-peat-routing-correction.md` — approved ADR correcting peat routing
- `docs/methodology.md` — normative routing table (updated per ADR-0012)
- `tests/fixtures/carbon/WO003_routing_PEAT.json` — PEAT golden fixture (asserts no VM0027, cited_methods=[], verra_family_must_not_contain)
- `tests/test_golden.py` — 81 golden-case tests (all green)

---

*Gate M sign-off is John's decision. This pack documents that all advisor-identified issues are resolved, numbers are frozen and reviewed, routing is corrected per ADR-0012, and the engine is ready for John's sign-off.*
