"""engines/carbon/engine.py — Carbon Pre-FS slice engine (WO-001).

PLACEHOLDER estimate only. Real biomass/peat/GFW data integration is WO-CARBON-001..004.
The eligibility gate logic and contract shapes are production-ready; numbers are stubs.

Determinism invariant: pure functions + typed models; no LLM calls here.
"""
from __future__ import annotations
from core.contracts import (
    CarbonInput, CarbonEstimate, EligibilityResult, GateResult,
    MethodologyRoute, QualityFactors, CarbonGates,
)
from core.contracts import Boundary, ForestData


_GATES = CarbonGates()

# PLACEHOLDER multipliers — replaced by real biomass calc in WO-CARBON-004
_PLACEHOLDER_LOW_TCO2_PER_HA = 40.0
_PLACEHOLDER_HIGH_TCO2_PER_HA = 65.0


def run_eligibility(inp: CarbonInput, boundary: Boundary) -> EligibilityResult:
    gates: dict[str, GateResult] = {}

    # Gate 1: permit type
    if inp.permit_type in _GATES.valid_permit_types:
        gates["permit_type"] = GateResult(status="pass", detail=f"{inp.permit_type} is a valid permit type")
    else:
        gates["permit_type"] = GateResult(
            status="fail", detail=f"{inp.permit_type!r} is not a recognised permit type (HTI or HA)"
        )

    # Gate 2: permit years remaining
    if inp.permit_years_remaining >= _GATES.min_years_remaining:
        gates["permit_years"] = GateResult(
            status="pass", detail=f"{inp.permit_years_remaining} years remaining (≥{_GATES.min_years_remaining})"
        )
    else:
        gates["permit_years"] = GateResult(
            status="flag",
            detail=f"Only {inp.permit_years_remaining} years remaining (minimum {_GATES.min_years_remaining} — soft flag)",
        )

    # Gate 3: area
    area = boundary.area_ha
    if area >= _GATES.min_area_ha:
        gates["area"] = GateResult(status="pass", detail=f"{area:,.0f} ha (≥{_GATES.min_area_ha:,} ha)")
    elif area > 0:
        gates["area"] = GateResult(
            status="fail",
            detail=f"{area:,.0f} ha is below the {_GATES.min_area_ha:,} ha minimum for v1",
        )
    else:
        # Point input — area unknown, flag rather than fail
        gates["area"] = GateResult(
            status="flag",
            detail="Area unknown (point input); supply a polygon to confirm ≥20,000 ha",
        )

    # Gate 4: within Indonesia
    if boundary.within_indonesia:
        gates["inside_iup"] = GateResult(status="pass", detail="Centroid is within Indonesia bounding box")
    else:
        gates["inside_iup"] = GateResult(
            status="flag", detail="Centroid may be outside Indonesia — verify the IUP boundary"
        )

    # Overall verdict
    statuses = [g.status for g in gates.values()]
    if "fail" in statuses:
        verdict = "hard_no"
    elif "flag" in statuses:
        verdict = "flagged"
    else:
        verdict = "eligible"

    reasons = [g.detail for g in gates.values() if g.status != "pass"]
    return EligibilityResult(gates=gates, verdict=verdict, reasons=reasons)


def build_methodology_route(inp: CarbonInput) -> MethodologyRoute:
    if inp.permit_type == "HTI":
        return MethodologyRoute(
            baseline_class="planned_clearfell",
            verra_family="APD route (VM0009/legacy — advisor-confirm)",
            cited_methods=["VM0009"],
            is_planned=True,
            notes="HTI = planned clear-fell foregone. Never VM0048/AUD family.",
        )
    # HA
    return MethodologyRoute(
        baseline_class="planned_selective",
        verra_family="IFM (VM0010 / VM0045 v1.2)",
        cited_methods=["VM0010", "VM0045"],
        is_planned=True,
        notes="HA = planned selective-logging foregone. IFM family.",
    )


def run_carbon_engine(inp: CarbonInput, boundary: Boundary, forest: ForestData) -> CarbonEstimate:
    eligibility = run_eligibility(inp, boundary)
    methodology = build_methodology_route(inp)

    # PLACEHOLDER estimate — area * fixed multiplier. Real calc in WO-CARBON-004.
    effective_area = boundary.area_ha if boundary.area_ha > 0 else 25_000.0
    low = round(effective_area * _PLACEHOLDER_LOW_TCO2_PER_HA, 0)
    high = round(effective_area * _PLACEHOLDER_HIGH_TCO2_PER_HA, 0)

    quality = QualityFactors(
        additionality="PLACEHOLDER — legal harvest right foregone; confirm with WO-CARBON-003",
        permanence="PLACEHOLDER — assess fire/leakage risk in WO-CARBON-004",
        leakage="PLACEHOLDER — assess displacement risk in WO-CARBON-004",
        methodology_fit=f"PLACEHOLDER — {methodology.verra_family}; confirm with advisor",
    )

    return CarbonEstimate(
        eligibility=eligibility,
        methodology=methodology,
        forest=forest,
        quantity_low_tco2e=low,
        quantity_high_tco2e=high,
        uncertainty=(
            "PLACEHOLDER estimate (±30 %+). Real range in WO-CARBON-004. "
            "Free satellite data — Tier 1 indicative screening only."
        ),
        quality=quality,
    )
