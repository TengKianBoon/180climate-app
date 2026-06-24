"""narrative/narrator.py — Template-based carbon narrative.

WO-CARBON-005 / WO-CARBON-006:
  - Corrected framing: observed-loss floor ≠ APD/IFM registry-grade planned baseline.
  - Tonnage suppressed for hard_no / flagged verdicts.
  - Peat routing note updated (ADR-0012: VM0027 removed — inactivated 2023).
  - VM0009 labelled "active but in transition — advisor-confirm at deal time."
  - HA labelled "IFM (VM0045 / VM0010) — advisor-confirm active version."
  - Peat EF labelled conservative (deeply-drained plantation peat is often higher).
  - Buffer labelled as placeholder for AFOLU non-permanence risk-tool output.
  - Co-dominant REDD uncertainties: baseline AND carbon density.
  - "Engage 180Climate" CTA at end.

LLM calls in this product: narrative/ (template — currently no live call) and classifier/ (intake boundary only — NEVER in number path). The number/verdict path remains deterministic.
"""
from __future__ import annotations
from core.contracts import (
    NarrativeRequest, NarrativeResult, CarbonEstimate,
)


_DISCLAIMER = (
    "Indicative Tier 1 screening only — not registry-grade, not financial advice. "
    "This figure uses IPCC default values and a proxy loss rate; it is not a verified "
    "avoided-emissions claim. Confirm with a full feasibility study, accredited methodology, "
    "and independent third-party verification before any financial or crediting claim."
)

_ENGAGE_CTA = (
    "**Engage 180Climate** — if this concession is a candidate for a carbon project, "
    "the next step is a structured feasibility scoping with 180Climate. "
    "Contact: info@180climate.net"
)

_METHODOLOGY_NOTE = {
    "planned_clearfell": (
        "**Methodology basis (indicative):** Based on the HTI permit, the applicable methodology "
        "family is APD (Avoided Planned Deforestation). The current active Verra methodology for this "
        "route is VM0009 — active but in transition; confirm with your methodology advisor at deal time. "
        "The additionality basis is the legal harvest right foregone: the concession holder has a legal "
        "right to clear-fell but is choosing to forego it. This is a planned-deforestation baseline — "
        "not the unplanned-deforestation (AUD / VM0048) family."
    ),
    "planned_selective": (
        "**Methodology basis (indicative):** Based on the HA permit, the applicable methodology "
        "family is IFM (Improved Forest Management). Applicable Verra methodologies: "
        "IFM (VM0045 / VM0010) — advisor-confirm active version at deal time. "
        "The additionality basis is the legal harvest right foregone: the concession holder has a legal "
        "right to selectively log but is choosing to forego it. This is a planned selective-logging "
        "baseline — not the unplanned-deforestation (AUD / VM0048) family."
    ),
    "peat": (
        "**Methodology basis (indicative):** Peat avoided-conversion projects sit in an unsettled "
        "methodology landscape as of 2026. VM0027 was inactivated by Verra in 2023 — it is a "
        "rewetting methodology, not an avoided-drainage/conversion methodology, and must never be "
        "cited for this activity type. No settled active Verra methodology for avoided tropical-peat "
        "conversion currently exists. This screening uses IPCC Tier-1 default emission factors only "
        "(IPCC 2013 Wetlands Supplement Table 2.1). Methodology route must be confirmed with a "
        "qualified methodology advisor. Never VM0027 / VM0048 / VM0007."
    ),
}


def generate_narrative(request: NarrativeRequest) -> NarrativeResult:
    """Generate a defensible template narrative consistent with ADR-0001/0009/0012.

    Tonnage is suppressed for hard_no / flagged verdicts to avoid presenting a
    tempting number against an ineligible or uncertain concession.
    """
    payload = request.payload
    estimate: CarbonEstimate | None = None
    try:
        estimate = CarbonEstimate(**payload)
    except Exception:
        return NarrativeResult(
            text="[Narrative generation failed — malformed payload]",
            citations=[],
        )

    elig = estimate.eligibility
    meth = estimate.methodology
    low = estimate.quantity_low_tco2e
    high = estimate.quantity_high_tco2e
    unc = estimate.uncertainty
    is_mixed = (
        estimate.classification is not None
        and estimate.classification.dominant_soil == "mixed"
    )

    # ── Verdict block ─────────────────────────────────────────────────────────
    if elig.verdict == "eligible":
        verdict_text = (
            "The concession appears eligible for a carbon project under current screening criteria."
        )
    elif elig.verdict == "flagged":
        reasons_text = "; ".join(elig.reasons)
        verdict_text = (
            f"The concession has one or more flags that require clarification: {reasons_text}. "
            "These flags do not automatically disqualify the project, but must be resolved before "
            "any crediting claim or registry submission."
        )
    else:  # hard_no
        reasons_text = "; ".join(elig.reasons)
        verdict_text = (
            f"The concession does not meet minimum eligibility criteria: {reasons_text}. "
            "A carbon project under current v1 screening criteria is not viable without addressing "
            "the above. Contact 180Climate to discuss what changes would alter this assessment."
        )

    # ── Carbon estimate block ─────────────────────────────────────────────────
    # Show range for eligible OR mixed-concession flagged (mineral stratum has a number).
    # Suppress for hard_no / flagged (non-mixed) — do not present a tempting number.
    if low is not None:
        baseline_class = meth.baseline_class
        range_label = (
            "**Indicative Carbon Range (mineral stratum — peat stratum separately flagged)**"
            if is_mixed
            else "**Indicative Carbon Range**"
        )
        if baseline_class == "peat":
            basis_note = (
                "This figure is a deliberately conservative floor derived from IPCC Tier-1 default "
                "emission factors for tropical drained peatland (IPCC 2013 Wetlands Supplement "
                "Table 2.1: 9–13 tCO₂-eq/ha/yr). The peat drainage emission factor used here is "
                "conservative; deeply-drained plantation peat is often higher. "
                "The buffer deduction (20–30%) is a placeholder for the AFOLU non-permanence "
                "risk-tool output — the actual VCS buffer requires project-specific inputs. "
                "Peat depth and drainage intensity are not measured at this screening stage."
            )
            unc_note = (
                "Co-dominant uncertainties: (1) peat depth and drainage intensity — not measured; "
                "deeply-drained plantation peat EFs can be 2–4× the IPCC default; "
                "(2) peat layer extent — no spatial peat map applied at this screening stage."
            )
        else:
            basis_note = (
                "This figure is a deliberately conservative floor derived from OBSERVED forest loss "
                "(8-year satellite average loss rate, 2016–2023) and IPCC 2006 Table 4.7 SE-Asia "
                "default biomass (657.1 tCO₂/ha for lowland moist tropical forest). "
                "It is NOT the APD/IFM (VM0009) planned-harvest baseline — the registry-grade "
                "baseline is established and independently justified only at registry grade, "
                "based on the documented planned harvest rate from the IUP permit, "
                "which may be higher or may be constrained by additionality, leakage, or "
                "conservative-baseline rules. "
                "The buffer deduction (20–30%) is a placeholder for the AFOLU non-permanence "
                "risk-tool output — the actual VCS buffer requires project-specific inputs."
            )
            unc_note = (
                "Co-dominant uncertainties: (1) baseline harvest rate — the legally-permitted "
                "extraction rate from the IUP permit has not yet been verified from permit documents; "
                "(2) carbon density — IPCC 2006 default biomass is unverified against field "
                "measurements or satellite-derived AGB (ESA CCI / GEDI grounding deferred to "
                "WO-CARBON-001b)."
            )

        estimate_block = f"""
{range_label}
Estimated avoided emissions: {low:,.0f} – {high:,.0f} tCO₂e (project lifetime).
Uncertainty: {unc}

**Basis for this figure**
{basis_note}

**Dominant uncertainties**
{unc_note}
"""
    else:
        # Suppress tonnage for hard_no / flagged — do not present a tempting number
        estimate_block = (
            "\n*(Indicative tonnage not shown for flagged or ineligible concessions — "
            "resolve the eligibility issues above before proceeding to a carbon estimate.)*\n"
        )

    meth_note = _METHODOLOGY_NOTE.get(meth.baseline_class, "")

    text = f"""{verdict_text}
{estimate_block}
{meth_note}

**Important:** Field validation, an accredited methodology selection, and independent third-party verification are required before any creditable or financial claim. The baseline / counterfactual and carbon density are co-dominant uncertainties for REDD projects; peat depth and drainage intensity are co-dominant for PEAT projects.

{_DISCLAIMER}

---

{_ENGAGE_CTA}"""

    citations = [
        "ADR-0001 — Carbon methodology stance",
        "ADR-0009 — Uncertainty & confidence communication",
        "ADR-0012 — Peat routing correction (VM0027 inactivated 2023)",
        "IPCC (2006) Guidelines for National GHG Inventories, Table 4.7 — SE-Asia biomass",
        "IPCC (2013) Wetlands Supplement, Table 2.1 — Tropical drained peat EF",
    ]
    if meth.baseline_class != "peat" and meth.verra_family:
        citations.append(meth.verra_family)

    return NarrativeResult(
        text=text,
        citations=citations,
    )
