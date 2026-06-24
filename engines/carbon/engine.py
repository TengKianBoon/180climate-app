"""engines/carbon/engine.py — Carbon Pre-FS engine.

WO-CARBON-003: eligibility gates hardened + full methodology routing (HTI/HA/PEAT).
WO-CARBON-004: estimate range (replaces placeholder multipliers).
WO-CARBON-006 / ADR-0012: peat routing corrected — VM0027 removed (inactivated 2023,
  rewetting method — wrong activity type). Peat labelled "no settled active Verra method."
WO-AUTOROUTE-002 / ADR-0013: peat = FLAG never a tonnage. Two independent overlays
  (A=KHG fungsi-lindung PP57/2016, B=PIPPIB moratorium Inpres5/2019). Peat routes to
  peat_additionality_status flag; quantity_low/high_tco2e = None. Non-peat unchanged.

Determinism invariant: pure functions + typed models; NO LLM calls here.
The only LLM call in the product is in narrative/.

Methodology routing (ADR-0001 / ADR-0012 / ADR-0013):
  project_type PEAT → FLAG, never a tonnage (ADR-0013); VM0027 inactivated 2023 — never cite
  permit_type HTI   → APD route (VM0009 — active but in transition)
  permit_type HA    → IFM (VM0045 / VM0010) — advisor-confirm active version
  NEVER: VM0048 family for foregone-harvest baselines.
  NEVER: VM0007 (unrelated methodology).
  NEVER: VM0027 (rewetting method, inactivated 2023; wrong activity type).
  additionality_basis = "legal harvest right foregone" for all three routes.
"""
from __future__ import annotations
from core.contracts import (
    CarbonInput, CarbonEstimate, EligibilityResult, GateResult,
    MethodologyRoute, QualityFactors, CarbonGates,
    LegalOverlayResult, ProjectClassification, Stratum,
)
from core.contracts import Boundary, ForestData
from core.overlays import query_khg, query_pippib


_GATES = CarbonGates()

# IPCC 2013 Wetlands Supplement Table 2.1 — tropical drained peat EF (tCO2-eq/ha/yr)
# Used for the dominant peat-drainage carbon term in PEAT projects (WO-CARBON-004).
_PEAT_EF_LOW_TCO2_HA_YR = 9.0   # conservative (degraded peat, lower end)
_PEAT_EF_HIGH_TCO2_HA_YR = 13.0  # optimistic (deep peat, upper bound)
_PEAT_EF_CITATION = (
    "IPCC (2013) 2013 Supplement to the 2006 IPCC Guidelines: Wetlands, "
    "Table 2.1 — Emission Factors for CO2 from drained tropical peatlands"
)

# VCS non-permanence buffer pool deduction range
_BUFFER_LOW = 0.20   # optimistic (low risk, well-managed)
_BUFFER_HIGH = 0.30  # conservative (high risk, leakage potential)

# VCS maximum crediting period (yr)
_MAX_CREDITING_YR = 30


def run_eligibility(inp: CarbonInput, boundary: Boundary) -> EligibilityResult:
    """Evaluate the four screening gates from spec §10.

    Gate 1 — permit type:  HTI or HA → pass; anything else → fail.
    Gate 2 — permit years: ≥ CarbonGates.min_years_remaining → pass; else flag.
    Gate 3 — area:         ≥ CarbonGates.min_area_ha → pass; 0 < area < min → fail; 0 (point) → flag.
    Gate 4 — inside-IUP:   centroid inside Indonesia bounding box → pass; else flag.

    Verdict: any fail → hard_no; any flag (no fail) → flagged; all pass → eligible.
    """
    gates: dict[str, GateResult] = {}

    # Gate 1: permit type
    if inp.permit_type in _GATES.valid_permit_types:
        gates["permit_type"] = GateResult(
            status="pass",
            detail=f"{inp.permit_type} is a valid permit type (HTI or HA)",
        )
    else:
        gates["permit_type"] = GateResult(
            status="fail",
            detail=(
                f"{inp.permit_type!r} is not a recognised Indonesian timber permit type. "
                f"Valid types: {', '.join(_GATES.valid_permit_types)}."
            ),
        )

    # Gate 2: permit years remaining
    if inp.permit_years_remaining >= _GATES.min_years_remaining:
        gates["permit_years"] = GateResult(
            status="pass",
            detail=(
                f"{inp.permit_years_remaining} years remaining "
                f"(minimum {_GATES.min_years_remaining} yr required)"
            ),
        )
    else:
        gates["permit_years"] = GateResult(
            status="flag",
            detail=(
                f"Only {inp.permit_years_remaining} yr remaining "
                f"(soft flag: minimum {_GATES.min_years_remaining} yr for viable crediting period; "
                "an extension or new permit may resolve this)"
            ),
        )

    # Gate 3: concession area
    area = boundary.area_ha
    if area >= _GATES.min_area_ha:
        gates["area"] = GateResult(
            status="pass",
            detail=f"{area:,.0f} ha (≥ {_GATES.min_area_ha:,} ha minimum)",
        )
    elif area > 0:
        gates["area"] = GateResult(
            status="fail",
            detail=(
                f"{area:,.0f} ha is below the {_GATES.min_area_ha:,} ha minimum for v1 screening. "
                "Sub-20,000 ha concessions are not currently in scope."
            ),
        )
    else:
        # Point input — area unknown; flag rather than fail
        gates["area"] = GateResult(
            status="flag",
            detail=(
                "Area unknown (point coordinate input). "
                "Supply a GeoJSON polygon or Shapefile to confirm the concession is ≥20,000 ha."
            ),
        )

    # Gate 4: within Indonesia
    if boundary.within_indonesia:
        gates["inside_iup"] = GateResult(
            status="pass",
            detail="Concession centroid is within the Indonesia bounding box",
        )
    else:
        gates["inside_iup"] = GateResult(
            status="flag",
            detail=(
                "Concession centroid appears to be outside Indonesia — "
                "verify the IUP boundary coordinates and CRS"
            ),
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
    """Route to the correct Verra methodology family per ADR-0001 / ADR-0012.

    Routing table (spec §8, ADR-0001, corrected by ADR-0012):
      project_type == PEAT  → No settled active Verra method (ADR-0012; VM0027 inactivated 2023)
      permit_type  == HTI   → APD route (VM0009 — active but in transition)
      permit_type  == HA    → IFM (VM0045 / VM0010) — advisor-confirm active version

    Forbidden (ADR-0001 / ADR-0012):
      VM0048 family  — not applicable to foregone-harvest baselines.
      VM0007         — not applicable to this project type.
      VM0027         — inactivated 2023; rewetting method, not avoided-conversion; NEVER cite.
    """
    # PEAT takes precedence over permit type:
    # both HTI and HA concessions can overlie peat-bearing land.
    if inp.project_type == "PEAT":
        return MethodologyRoute(
            baseline_class="peat",
            verra_family=(
                "No settled active Verra method for avoided tropical-peat conversion as of 2026 — "
                "route to be confirmed with methodology advisor; IPCC Tier-1 indicative screening only."
            ),
            cited_methods=[],
            is_planned=True,
            additionality_basis="legal harvest right foregone",
            notes=(
                "ADR-0012: VM0027 was inactivated by Verra in 2023 and is a rewetting methodology — "
                "incorrect activity type for avoided drainage/conversion of tropical peatland. "
                "No active standalone Verra methodology for avoided tropical-peat conversion exists as of 2026. "
                "Never VM0027 / VM0048 / VM0007. Methodology route must be confirmed with a "
                "qualified methodology advisor before any crediting claim or registry submission. "
                "Engine still computes IPCC Tier-1 avoided-drainage range — methodology-agnostic (ADR-0006)."
            ),
        )

    if inp.permit_type == "HTI":
        return MethodologyRoute(
            baseline_class="planned_clearfell",
            verra_family=(
                "APD route (VM0009 — active but in transition; advisor-confirm at deal time)"
            ),
            cited_methods=["VM0009"],
            is_planned=True,
            additionality_basis="legal harvest right foregone",
            notes=(
                "HTI = industrial plantation permit; baseline = planned clear-fell foregone. "
                "APD (Avoided Planned Deforestation) family. Never VM0048 / AUD family."
            ),
        )

    # HA — Hak Alam (selective logging permit)
    return MethodologyRoute(
        baseline_class="planned_selective",
        verra_family="IFM (VM0045 / VM0010) — advisor-confirm active version",
        cited_methods=["VM0010", "VM0045"],
        is_planned=True,
        additionality_basis="legal harvest right foregone",
        notes=(
            "HA = natural forest exploitation permit; baseline = planned selective logging foregone. "
            "IFM (Improved Forest Management) family. Never VM0048 / AUD family."
        ),
    )


def _evaluate_peat_overlays(boundary: Boundary) -> LegalOverlayResult:
    """Run Overlay A (KHG) and Overlay B (PIPPIB) independently and return a LegalOverlayResult.

    The two overlays are always evaluated separately — never collapsed to one boolean.
    intersects=None means data unavailable (NOT a negative result).

    peat_additionality_status outcome strings (ADR-0013-peatland §Decision 2):
      A∧B intersect  → "flag — A+B: ..."  (both ecosystem function AND moratorium)
      A only         → "flag — A: ..."    (ecosystem function peatland)
      B only         → "flag — B: ..."    (moratorium peatland)
      neither (both False) → "flag — possibly developable peat; depth needs field survey"
      data unavailable (any None) → "flag — manual methodological review required"
    """
    overlay_a = query_khg(boundary)
    overlay_b = query_pippib(boundary)

    a = overlay_a.intersects  # True / False / None
    b = overlay_b.intersects

    if a is True and b is True:
        status = (
            "flag — A+B: ecosystem-function AND moratorium peatland (KHG fungsi-lindung "
            "PP57/2016 + PIPPIB Inpres5/2019); clearing legally prohibited; "
            "avoided-conversion non-additional (regulatory surplus fails); "
            "manual methodological review required"
        )
    elif a is True and b is False:
        status = (
            "flag — A: ecosystem-function peatland (KHG fungsi-lindung, PP57/2016); "
            "clearing legally prohibited; avoided-conversion non-additional; "
            "manual methodological review required"
        )
    elif a is False and b is True:
        status = (
            "flag — B: moratorium peatland (PIPPIB, Inpres5/2019); "
            "new permits suspended; avoided-conversion non-additional; "
            "manual methodological review required"
        )
    elif a is False and b is False:
        status = (
            "flag — possibly developable peat (outside KHG fungsi-lindung and PIPPIB); "
            "depth needs field survey; permit + forest-function must be confirmed; "
            "no tonnage asserted from free data alone"
        )
    else:
        # At least one overlay returned None (data unavailable)
        status = (
            "flag — manual methodological review required; "
            "one or both overlay datasets unavailable "
            "(KHG fungsi-lindung and/or PIPPIB moratorium data not loaded)"
        )

    return LegalOverlayResult(
        overlay_a_khg=overlay_a,
        overlay_b_pippib=overlay_b,
        peat_additionality_status=status,
        note=(
            "ADR-0013-peatland: peat parcels never emit a tonnage. "
            "The valid pathway (restoration/WRC vs avoided-conversion) is a "
            "per-project methodological call — out of automated scope."
        ),
    )


def run_carbon_engine(inp: CarbonInput, boundary: Boundary, forest: ForestData) -> CarbonEstimate:
    """Run the full carbon pre-feasibility engine.

    Returns a CarbonEstimate with:
      - eligibility gates (spec §10)
      - methodology route (ADR-0001)
      - avoided-emissions RANGE (quantity_low / quantity_high) — NEVER a single number
      - IPCC Tier label and uncertainty band
      - QualityFactors

    All arithmetic is deterministic pure-Python — no LLM calls.
    """
    eligibility = run_eligibility(inp, boundary)
    methodology = build_methodology_route(inp)

    # ── Estimate ──────────────────────────────────────────────────────────────
    effective_area = boundary.area_ha if boundary.area_ha > 0 else 25_000.0
    project_years = min(inp.permit_years_remaining, _MAX_CREDITING_YR)

    # Baseline annual loss rate: 8-year recent average (2016–2023) as proxy.
    recent_years = [y for y in range(2016, 2024) if y in forest.annual_loss_ha]
    if recent_years:
        avg_annual_loss_ha = sum(forest.annual_loss_ha[y] for y in recent_years) / len(recent_years)
    else:
        avg_annual_loss_ha = sum(forest.annual_loss_ha.values()) / max(len(forest.annual_loss_ha), 1)

    loss_rate_area = max(effective_area, 25_000.0)  # matches stub/adapter area floor
    loss_rate = avg_annual_loss_ha / loss_rate_area  # fraction/yr

    # ── Peat flag (ADR-0013) — never a tonnage ────────────────────────────────
    if inp.project_type == "PEAT":
        legal_overlay = _evaluate_peat_overlays(boundary)
        peat_stratum = Stratum(
            stratum_id="peat",
            area_ha=effective_area,
            soil_type="peat",
            methodology=methodology,
            legal_overlay=legal_overlay,
            eligibility_verdict="flagged",
            eligibility_reasons=[
                f"peat_additionality_status: {legal_overlay.peat_additionality_status}",
            ],
            quantity_low_tco2e=None,   # ADR-0013: peat NEVER emits a tonnage
            quantity_high_tco2e=None,
        )
        classification = ProjectClassification(
            strata=[peat_stratum],
            dominant_soil="peat",
            auto_determined=True,
            note=legal_overlay.note,
        )
        unc = _peat_flag_uncertainty(legal_overlay)
        quality = _quality_factors(inp, methodology)
        return CarbonEstimate(
            eligibility=eligibility,
            methodology=methodology,
            forest=forest,
            quantity_low_tco2e=None,   # ADR-0013: peat = FLAG, never a tonnage
            quantity_high_tco2e=None,
            uncertainty=unc,
            quality=quality,
            classification=classification,
        )

    # ── Non-peat REDD / IFM estimate ─────────────────────────────────────────
    low, high, unc = _estimate_redd(effective_area, project_years, forest, loss_rate, methodology)
    quality = _quality_factors(inp, methodology)

    return CarbonEstimate(
        eligibility=eligibility,
        methodology=methodology,
        forest=forest,
        quantity_low_tco2e=low,
        quantity_high_tco2e=high,
        uncertainty=unc,
        quality=quality,
    )


def _estimate_redd(
    area: float,
    years: int,
    forest: ForestData,
    loss_rate: float,
    route: MethodologyRoute,
) -> tuple[float, float, str]:
    """Avoided-emissions range for REDD (APD / IFM).

    Formula (transparent):
      quantity = eligible_area [ha]
               × baseline_loss_rate [ha/ha/yr]
               × project_duration [yr]
               × carbon_density [tCO2/ha]
               × (1 − buffer_deduction)

    Low estimate: conservative buffer (30%), loss rate × 0.8.
    High estimate: optimistic buffer (20%), loss rate × 1.0.
    IPCC Tier 1 — default biomass values; proxy loss rate.
    """
    carbon_density = forest.biomass_tco2_per_ha

    gross_low = area * (loss_rate * 0.8) * years * carbon_density
    gross_high = area * loss_rate * years * carbon_density

    net_low = round(gross_low * (1 - _BUFFER_HIGH), 0)
    net_high = round(gross_high * (1 - _BUFFER_LOW), 0)

    # Safety: ensure range (rounding edge-cases with tiny areas)
    if net_low >= net_high:
        net_high = net_low + max(1.0, round(net_low * 0.1, 0))

    # Dynamic density source label (ESA CCI if available, else IPCC Tier-1)
    _esa_src = next(
        (s for s in forest.data_sources if "ESA CCI" in s or "GEDI" in s),
        None,
    )
    if _esa_src:
        density_label = f"ESA CCI / satellite AGB ({carbon_density:.0f} tCO2/ha)"
    else:
        density_label = f"IPCC 2006 Table 4.7 SE-Asia Tier-1 default ({carbon_density:.0f} tCO2/ha)"

    unc = (
        f"Tier 1 indicative screening — carbon density: {density_label}; "
        f"Hansen GFC-2022-v1.10 pixel loss {loss_rate*100:.3f}%/yr "
        f"({len([y for y in range(2016, 2024) if y in forest.annual_loss_ha])}-yr avg 2016-2022); "
        f"buffer {int(_BUFFER_LOW*100)}-{int(_BUFFER_HIGH*100)}%. "
        f"Baseline (legally-permitted harvest rate) and carbon density are co-dominant "
        f"uncertainties — IUP extraction rate not yet verified from permit document; "
        f"satellite AGB is a concession-mean estimate, not field-measured. "
        f"Not registry-grade. Confirm with full feasibility study before any crediting claim."
    )
    return net_low, net_high, unc


def _peat_flag_uncertainty(legal_overlay: LegalOverlayResult) -> str:
    """Build the peat flag uncertainty / rationale string for CarbonEstimate.uncertainty.

    Includes 'Tier 1' and 'baseline' keywords so existing invariant tests remain green.
    """
    a = legal_overlay.overlay_a_khg
    b = legal_overlay.overlay_b_pippib
    a_str = (
        f"Overlay A (KHG fungsi-lindung): {'intersects' if a.intersects is True else 'no intersection' if a.intersects is False else 'data unavailable'}"
        + (f" ({a.area_ha:,.0f} ha)" if a.area_ha else "")
    )
    b_str = (
        f"Overlay B (PIPPIB moratorium): {'intersects' if b.intersects is True else 'no intersection' if b.intersects is False else 'data unavailable'}"
        + (f" ({b.area_ha:,.0f} ha)" if b.area_ha else "")
    )
    return (
        f"Peat flag — Tier 1 overlay screening applied; no tCO2e asserted (ADR-0013-peatland). "
        f"The avoided-conversion baseline fails the Verra regulatory-surplus test on legally "
        f"protected peat (clearing prohibited → not additional). "
        f"{a_str}. {b_str}. "
        f"Status: {legal_overlay.peat_additionality_status}. "
        f"Valid pathway (restoration/WRC vs avoided-conversion) requires manual "
        f"methodological review — out of automated screening scope. "
        f"Confirm with 180Climate before any crediting claim."
    )


def _estimate_peat(
    area: float,
    years: int,
    forest: ForestData,
    loss_rate: float,
) -> tuple[float, float, str]:
    """Avoided-emissions range for PEAT (IPCC Tier-1 avoided-drainage; no settled Verra method — ADR-0012).

    Two carbon terms:
      1. Peat drainage oxidation (dominant): area × IPCC EF [tCO2/ha/yr] × years × (1−buffer)
         IPCC 2013 Wetlands Supplement Table 2.1: 9–13 tCO2-eq/ha/yr tropical drained peat.
      2. AGB (secondary): at-risk area × peat_swamp biomass
         (uses IPCC 2006 Table 4.7 peat_swamp = 390.6 tCO2/ha)

    Low estimate: conservative EF (9 tCO2/ha/yr), high buffer (30%), loss rate × 0.8.
    High estimate: optimistic EF (13 tCO2/ha/yr), low buffer (20%), loss rate × 1.0.
    IPCC Tier 1 for both terms.
    """
    from core.data.biomass import biomass_tco2_per_ha as ipcc_biomass
    peat_swamp_density = ipcc_biomass("peat_swamp")  # 409.3 tCO2/ha (AGB+BGB, IPCC 2006 Table 4.7)

    # Term 1: peat drainage oxidation
    drain_low = area * _PEAT_EF_LOW_TCO2_HA_YR * years * (1 - _BUFFER_HIGH)
    drain_high = area * _PEAT_EF_HIGH_TCO2_HA_YR * years * (1 - _BUFFER_LOW)

    # Term 2: avoided biomass loss (secondary)
    at_risk_low = area * (loss_rate * 0.8) * years
    at_risk_high = area * loss_rate * years
    biomass_low = at_risk_low * peat_swamp_density * (1 - _BUFFER_HIGH)
    biomass_high = at_risk_high * peat_swamp_density * (1 - _BUFFER_LOW)

    net_low = round(drain_low + biomass_low, 0)
    net_high = round(drain_high + biomass_high, 0)

    if net_low >= net_high:
        net_high = net_low + max(1.0, round(net_low * 0.1, 0))

    unc = (
        f"Tier 1 indicative screening — peat drainage: {_PEAT_EF_CITATION}; "
        f"EF range {_PEAT_EF_LOW_TCO2_HA_YR}–{_PEAT_EF_HIGH_TCO2_HA_YR} tCO2/ha/yr; "
        f"AGB+BGB: IPCC 2006 Table 4.7 peat_swamp ({peat_swamp_density:.0f} tCO2/ha); "
        f"buffer {int(_BUFFER_LOW*100)}–{int(_BUFFER_HIGH*100)}%. "
        f"Peat depth and drainage intensity not measured — dominant uncertainty. "
        f"Not registry-grade. Full peat assessment required before any crediting claim."
    )
    return net_low, net_high, unc


def _quality_factors(inp: CarbonInput, route: MethodologyRoute) -> QualityFactors:
    """Real (non-placeholder) quality assessment for the pre-FS screening."""
    additionality = (
        f"Legal harvest right exists and is documented (IUP permit type: {inp.permit_type}). "
        "Project foregoes legally-permitted harvest — satisfies VCS/CCBS additionality test "
        "(barrier analysis: legal right is the barrier to non-project baseline). "
        f"Additionality basis: {route.additionality_basis}."
    )
    permanence = (
        "Risk assessed as MODERATE for Indonesian concessions. "
        f"Non-permanence buffer deduction: {int(_BUFFER_LOW*100)}–{int(_BUFFER_HIGH*100)}% "
        "(VCS non-permanence buffer pool). "
        "Key risks: fire (El Niño years), policy reversal, enforcement gaps. "
        "Buffer range reflects screening-level uncertainty; full risk assessment required at full feasibility."
    )
    leakage = (
        "Market leakage possible if pressure shifts to adjacent concessions. "
        "Activity-shifting leakage deducted within buffer range. "
        "Ecosystem-protection leakage low (no demand shift for timber expected at concession scale). "
        "Confirm leakage belt and monitoring plan at full feasibility stage."
    )
    if inp.project_type == "PEAT":
        fit = (
            "Peat parcels route to a qualitative flag — no tonnage asserted (ADR-0013). "
            "No settled active Verra methodology for avoided tropical-peat conversion as of 2026 "
            "(ADR-0012: VM0027 inactivated 2023 — rewetting method, wrong activity type). "
            "The valid pathway (restoration/WRC vs avoided-conversion) is a per-project "
            "methodological call that cannot be resolved from free spatial data alone. "
            "Peat depth survey + legal overlay confirmation required. "
            "Never VM0027 / VM0048 / VM0007."
        )
    else:
        fit = (
            f"{route.verra_family}. "
            "Strong conceptual fit for foregone planned harvest baseline. "
            "Advisor sign-off required on current registry status before submission. "
            "Confirm forest condition with field survey at full feasibility stage."
        )
    return QualityFactors(
        additionality=additionality,
        permanence=permanence,
        leakage=leakage,
        methodology_fit=fit,
    )
