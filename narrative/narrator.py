"""narrative/narrator.py — Template-based narrative for the WO-001 slice.

PLACEHOLDER: no LLM call in the slice. Real Claude-powered narrative wired in WO-CARBON-005.
This module is the ONLY place where LLM calls will ever be made (determinism invariant).

The template produces a defensible, non-binding narrative consistent with ADR-0001/0009.
"""
from __future__ import annotations
from core.contracts import (
    NarrativeRequest, NarrativeResult, CarbonEstimate, EligibilityResult,
)


_DISCLAIMER = (
    "Indicative screening estimate only. Not registry-grade, not financial advice. "
    "Confirm with a full feasibility study before any financial or crediting claim."
)

_METHODOLOGY_NOTE = {
    "planned_clearfell": (
        "Based on the HTI permit, the applicable methodology family is the APD route "
        "(VM0009/legacy — advisor-confirm). The additionality basis is the legal harvest right foregone: "
        "the concession holder has a legal right to clear-fell but is choosing to forego it. "
        "This is a planned deforestation baseline — not the unplanned-deforestation (AUD/VM0048) family."
    ),
    "planned_selective": (
        "Based on the HA permit, the applicable methodology family is IFM (VM0010 / VM0045 v1.2). "
        "The additionality basis is the legal harvest right foregone: the concession holder has a legal "
        "right to selectively log but is choosing to forego it. "
        "This is a planned selective-logging baseline — not the unplanned-deforestation (AUD/VM0048) family."
    ),
    "peat": (
        "Peat concessions require the avoided drainage/subsidence approach. "
        "A standalone tropical peatland methodology is in development (VM0027 interim — advisor-confirm). "
        "Confirm with a methodology advisor before any commercial application."
    ),
}


def generate_narrative(request: NarrativeRequest) -> NarrativeResult:
    """Generate a template narrative. Replace with LLM call in WO-CARBON-005."""
    payload = request.payload
    estimate: CarbonEstimate | None = None
    try:
        estimate = CarbonEstimate(**payload)
    except Exception:
        pass

    if estimate is None:
        return NarrativeResult(
            text="[PLACEHOLDER — narrative generation failed; LLM wired in WO-CARBON-005]",
            citations=[],
        )

    elig = estimate.eligibility
    meth = estimate.methodology
    low = estimate.quantity_low_tco2e
    high = estimate.quantity_high_tco2e
    unc = estimate.uncertainty

    verdict_text = {
        "eligible": "The concession appears eligible for a carbon project under current screening criteria.",
        "flagged": (
            "The concession has one or more flags that require clarification: "
            + "; ".join(elig.reasons) + "."
        ),
        "hard_no": (
            "The concession does not meet minimum eligibility criteria for a v1 carbon project: "
            + "; ".join(elig.reasons) + "."
        ),
    }[elig.verdict]

    meth_note = _METHODOLOGY_NOTE.get(meth.baseline_class, "")

    text = f"""{verdict_text}

**Preliminary Carbon Estimate (PLACEHOLDER — WO-CARBON-004 will refine)**
Estimated avoided emissions: {low:,.0f} – {high:,.0f} tCO₂e over the project crediting period.
Uncertainty: {unc}

**Methodology (indicative)**
{meth_note}

**Important:** The baseline/counterfactual — not satellite resolution — is the dominant uncertainty. \
Field validation, an accredited methodology, and independent third-party verification are required \
before any creditable or financial claim.

{_DISCLAIMER}

[PLACEHOLDER narrative — real AI rationale in WO-CARBON-005]"""

    return NarrativeResult(
        text=text,
        citations=[
            "ADR-0001 — Carbon methodology stance",
            "ADR-0009 — Uncertainty & confidence communication",
            meth.verra_family,
        ],
    )
