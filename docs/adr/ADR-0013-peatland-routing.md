# ADR-0013 — Peatland routing in the Pre-Feasibility screening tool

- **Status:** Proposed (advisor-reviewed; supersedes the ADR-0013 v1/v2 peat handling) → recommend John approve + **Gate C**
- **Date:** 2026-06-24
- **Decision owner:** 180Climate (PFS screening tool)
- **Tags:** additionality, regulatory-surplus, peat, REDD+, WRC, baseline
- **Supersedes:** "route by permit + geometry; peat produces an indicative tonnage labelled 'no settled method.'"

## Context
The v1/v2 drafts let peat parcels produce an indicative tonnage. Two findings make that unsafe to ship, even as a freemium screen.

**Finding 1 — the implicit crediting basis fails the regulatory-surplus test on protected peat.** A geometry-driven peat tonnage only makes sense under an avoided-conversion baseline ("a legal clearing right exists and is foregone"). On legally protected peat, clearing is already prohibited → "not clearing" is the legal baseline, not an additional action → crediting it credits avoidance of an illegal act. Under Verra VCS this fails the **regulatory-surplus / legal-requirements test**; for AFOLU the baseline must reflect enforced legal constraints. So on protected peat the avoided-conversion number is **affirmatively non-additional**, not merely "unsettled."

**Finding 2 — "protected" is two overlapping legal regimes, neither fully resolvable from free data.**
1. **Ecosystem function** — peat ≥3 m, peat-dome (*kubah gambut*), per-KHG minimum protection share, designated *fungsi lindung*. Source: **PP 71/2014 jo PP 57/2016**; damage standard (water table >0.4 m below surface) consolidated in **PP 22/2021**.
2. **Moratorium** — permanent suspension of new permits on primary natural forest + peatland, mapped in **PIPPIB** (~6-monthly). Source: **Inpres 5/2019** (lineage Inpres 10/2011 → 6/2013 → 8/2015 → 6/2017). Bites on all mapped peatland regardless of depth.

These don't share a boundary. "Developable peat" = `(<3 m) ∧ (outside PIPPIB) ∧ (valid pre-existing permit) ∧ (outside protection/conservation forest under UU 41/1999)`. The 3 m boundary itself is **not free-data determinable** (official *fungsi lindung/budidaya* line set per-KHG by decree; on-ground 3 m needs auger/coring/GPR; national depth rasters too coarse).

**Worked case — VCS 1899 (Sumatra Merang).** Deep (>3 m) dome, crediting since 2016 — superficially a counter-example to Finding 1. It is not: per the Verra registry it is **ARR; WRC under VM0007** — restoration + peat rewetting, **not avoided-conversion**. Its additionality is *intervention additionality* (rewetting + fire prevention reversing ongoing degradation that the law penalises causing but does not fund anyone to reverse). The lesson: the valid pathway on protected peat is a per-project methodological call (avoided-conversion → generally non-additional; restoration/WRC → potentially additional), and a permit+geometry screen on free data cannot tell which applies.

## Decision
**Peat parcels route to a qualitative flag and never emit a tonnage.**
1. **Two independent overlays, evaluated separately** (not collapsed to one boolean):
   - **Overlay A — ecosystem function:** parcel ∩ KHG *fungsi lindung* / peat-dome (published KHG function maps); depth treated as unknown unless field data is supplied.
   - **Overlay B — moratorium:** parcel ∩ current PIPPIB peatland polygon.
   - **Supporting (advisory):** forest-function status (UU 41/1999); concession/permit presence.
2. **Output is a flag, not a number.** Return `peat_present = true` and `peat_additionality_status = "flag — manual methodological review required"`. **No `tCO2e` for the peat component under any branch.**
   - If A or B intersects → *"presumed non-additional on an avoided-conversion basis (clearing legally prohibited → fails regulatory surplus); a restoration/WRC pathway may be additional but is project-specific and out of automated scope."*
   - If neither intersects but peat present → *"developability not determinable from free data (depth needs field survey; permit + forest-function must be confirmed); no tonnage asserted."*
3. **Mineral-soil / non-peat parcels** are unaffected — continue under the existing permit + geometry tonnage logic (with the forest-presence gate; see companion ADR-0013-auto-routing).
4. **The report must render a short plain-language rationale** next to the peat flag so the owner understands why no number is shown (not "the tool failed").

## Rationale (regulatory surplus, for the record)
Verra VCS additionality requires the activity to exceed enforced legal requirements. Where clearing is legally prohibited, the avoided-conversion baseline collapses ("not clearing" is mandated → not surplus → not additional). On Indonesian peat the prohibition arises via *fungsi lindung* (PP 71/2014 jo 57/2016), the permanent moratorium (Inpres 5/2019), protection/conservation forest status (UU 41/1999), and — for the burn-and-clear baseline — the nationwide ban on clearing by fire (**UU 32/2009 §69, sanction §108**). A restoration/rewetting/avoided-fire pathway satisfies regulatory surplus differently (the without-project scenario is continued oxidation + recurrent fire of already-drained peat — which the law penalises causing but does not compel/finance anyone to reverse). **Hence protection status is not a binary creditability switch — automated screening must defer to manual review, not auto-assert or auto-exclude.**

## Consequences
- **+** Defensible to a VCS validator and hostile DD; never credits avoidance of an illegal act (the v1 trap). The two-overlay structure is auditable. Avoids the opposite error (flat "peat = exclude") that would wrongly screen out legitimate restoration/WRC opportunities (the SMPP class).
- **−** The freemium screen loses its peat headline number (accepted — a wrong/indefensible number is worse than an honest flag; the flag + rationale is itself a lead-qualification signal). Requires report copy + maintaining the KHG-function and PIPPIB overlays. The existing Gate-M peat number is downgraded to a flag.

## Alternatives considered
1. Emit an indicative tonnage with a disclaimer (v1) — **rejected** (affirmatively non-additional on protected peat, not merely uncertain; reputational/methodological liability).
2. Flat "peat = exclude / zero" — **rejected** (overbroad; ignores valid restoration/WRC additionality, e.g. SMPP).
3. Require depth data before any peat output — **rejected for the free first-pass** (kills the UX); retained as a paid-tier path.

## Follow-ups
- Source + version-pin the KHG *fungsi lindung* maps and the latest SK PIPPIB; record refresh cadence.
- Paid-tier upgrade: accept user-supplied depth/concession docs to convert the flag into a methodology-specific assessment.
- Confirm whether the 2026 national framework (see Citation status) alters avoided-conversion vs restoration registration; revisit if so.

## References
PP 71/2014 (peat ecosystem protection; *fungsi lindung/budidaya*, KHG, ≥3 m, clearing prohibition) · PP 57/2016 (amends 71/2014; dome protection) · PP 22/2021 (post-Cipta-Kerja; damage standard, >0.4 m water table) · Inpres 5/2019 (permanent moratorium + PIPPIB) · UU 41/1999 (forest function) · UU 32/2009 (§69 burning ban, §108 sanction) · UU 11/2020 → UU 6/2023 (Cipta Kerja / OSS) · Verra VCS Standard (additionality / regulatory surplus; AFOLU baseline) · VCS 1899 Sumatra Merang (AFOLU; ARR; WRC; VM0007; 2016-01-01→2062-12-31) — registry-verified 2026-06-24.

## Citation status
Article-level numbers (e.g. PP 71/2014 clearing prohibition; UU 32/2009 §69/§108) are from working knowledge — **pin against the official statute text (peraturan.bpk.go.id) before external publication.** Framework attributions are reliable. The **2026 carbon-sales layer (Permenhut 6/2026, SRUK, corresponding-adjustment/dual-track) is past verifiable knowledge → John confirms against current registry rules.**

## Appendix A — VCS 1899 traced through the routing (fail-safe demonstration)
| Gate | Input (free data) | Result | Effect |
|---|---|---|---|
| 0 · Peat present? | peat extent / land cover | Yes — dome peatland | enter peat branch → no-tonnage path |
| A · ecosystem function | KHG *fungsi lindung* / dome | intersects (dome) | "presumed non-additional, avoided-conversion" |
| B · moratorium (PIPPIB) | PIPPIB peatland polygon | ambiguous (RE concession may be excluded; not resolvable without licence record) | reinforces "defer — not determinable" |
| supporting · permit | OSS / concession overlay | licence likely present; type (RE vs HTI) not distinguishable | activity type can't be inferred |

**Tool output:** `peat_present=true`, `peat_tCO2e=null`, `peat_additionality_status="flag — manual methodological review required"`.
**Manual review then finds:** actual basis = ARR/WRC restoration under VM0007 → *additional*. The flag correctly resolves to a valid project via the restoration pathway the tool declined to auto-score.
**Fail-safe:** the tool never asserted an avoided-conversion tonnage on protected peat (no false-positive), and didn't auto-exclude SMPP (no false-negative). The valid/invalid call was routed to manual review — the only place it can correctly be made. The v1 counterfactual would have emitted a non-additional avoided-conversion number on one of Indonesia's more credible peat projects — the strongest standalone argument for flag-not-number.
