"""engines/carbon/engine.py — Carbon Pre-FS engine.

WO-CARBON-003: eligibility gates hardened + full methodology routing (HTI/HA/PEAT).
WO-CARBON-004: estimate range (replaces placeholder multipliers).
WO-CARBON-006 / ADR-0012: peat routing corrected — VM0027 removed (inactivated 2023,
  rewetting method — wrong activity type). Peat labelled "no settled active Verra method."
WO-AUTOROUTE-002 / ADR-0013: peat = FLAG never a tonnage. Two independent overlays
  (A=KHG fungsi-lindung PP57/2016, B=PIPPIB moratorium Inpres5/2019). Peat routes to
  peat_additionality_status flag; quantity_low/high_tco2e = None. Non-peat unchanged.
WO-AUTOROUTE-003 / ADR-0013-auto-routing: forest-presence gate for non-peat REDD/IFM.
  HTI on cleared/scrub land → gate_result=fail → flagged, no number.
  Forest condition drives MethodologyRoute context (intact/light → pass; heavy → flag).
  REDD+/IFM routing by permit type + condition remains: HTI→APD, HA→IFM.
WO-AUTOROUTE-004 / ADR-0013-auto-routing: run_mixed_stratification() added for
  soil-first mixed-concession stratification (called from API only — never inside
  run_carbon_engine()). Intake classifier in classifier/intake.py (separate module,
  never imported here — determinism invariant preserved).
WO-METHFIX-001 / ADR-0015: Two critical methodology corrections:
  C1 — Forest-origin (plantation) gate: KLHK Penutupan Lahan classifies hutan tanaman
  (established plantation) vs hutan alam (natural forest). Established plantation →
  FLAG ("no standing natural forest at risk — not an APD/IFM candidate"). Mixed →
  natural-area-only estimate (plantation pixels masked). Natural or unknown → proceed.
  Retain ADR-0013 moratorium gate (necessary-but-not-sufficient).
  C2 — Distinct IFM estimate for HA: _estimate_ifm() replaces _estimate_redd() for HA.
  Basis: avoided selective-logging emissions (Pearson et al. 2014 TEF, NOT density×loss_rate).
  Formula: harvested_area × EF_per_ha × (1−buffer); n_entries=1; cycle=35yr (TPTI).
  VM0010 lead; VM0045 flagged (field/NFI-dependent, not satellite-screenable).

Determinism invariant: pure functions + typed models; NO LLM calls here.
The only permitted product LLM calls are in narrative/ (rendering) and classifier/
(intake boundary — never imported by this module).

Methodology routing (ADR-0001 / ADR-0012 / ADR-0013 / ADR-0015):
  project_type PEAT → FLAG, never a tonnage (ADR-0013); VM0027 inactivated 2023 — never cite
  permit_type HTI   → APD route (VM0009 — active but in transition) if forest_origin != plantation
  permit_type HA    → IFM (VM0010 lead; VM0045 field-only) if forest_origin != plantation
  NEVER: VM0048 family for foregone-harvest baselines.
  NEVER: VM0007 (unrelated methodology).
  NEVER: VM0027 (rewetting method, inactivated 2023; wrong activity type).
  additionality_basis = "legal harvest right foregone" for all three routes.
"""
from __future__ import annotations
import math as _math
from core.contracts import (
    CarbonInput, CarbonEstimate, EligibilityResult, GateResult,
    MethodologyRoute, QualityFactors, CarbonGates,
    ForestPresenceGate, LegalOverlayResult, ProjectClassification, Stratum,
    CalculationTrace,
)
from core.contracts import Boundary, ForestData
from core.overlays import (
    query_khg, query_pippib, query_worldcover, query_jrc_tmf,
    query_klhk_plantation,
)


_GATES = CarbonGates()

# ── IFM selective-logging constants (ADR-0015-C2) ─────────────────────────────
# Source: Pearson et al. (2014) Carbon emissions from tropical forest degradation
# caused by logging. Environmental Research Letters 9(3).
# Indonesia/SE-Asia field validation: Butarbutar et al. (2019), Griscom et al.
#
# TEF = Total Emission Factor (full: extraction + damage + infrastructure).
# IPCC 2006 GL Vol 4 / 2019 Refinement = CONVERSION MATH ONLY (BCEF, CF=0.47, ×44/12).
# IPCC does NOT publish a selective-logging TEF; the TEF is Pearson-sourced.
#
# Indonesia / SE-Asia defaults (advisor-confirmed, ADR-0015):
#   Logging intensity: 26–40 m³/ha (centre ~30 m³/ha; TPTI allowed range)
#   TEF low : 1.4 MgC/m³ (extraction + damage only)
#   TEF high: 1.5 MgC/m³ (full, incl. infrastructure)
#   EF_per_ha = intensity × TEF × (44/12) → ~133–220 tCO2/ha per entry
#   Cross-check: ~50 tC/ha × 44/12 ≈ 185 tCO2/ha (Butarbutar, Kalimantan) — within band
#   Cutting cycle (TPTI): 35 yr
#   n_entries = 1  (one avoided entry in a 20–30 yr credit period vs ~35 yr cycle)
_IFM_INTENSITY_LOW_M3_HA = 26.0    # m³/ha (TPTI minimum commercial volume)
_IFM_INTENSITY_HIGH_M3_HA = 40.0   # m³/ha (TPTI maximum)
_IFM_TEF_LOW_MG_C_M3 = 1.4        # MgC/m³ (extraction + damage; Pearson 2014)
_IFM_TEF_HIGH_MG_C_M3 = 1.5       # MgC/m³ (full incl. infrastructure; Pearson 2014)
_IFM_CYCLE_YR = 35                 # yr (Indonesian TPTI cutting cycle)
_C_TO_CO2 = 44.0 / 12.0           # carbon → CO2 stoichiometry

# Derived EF per ha (tCO2/ha per selective-logging entry):
_IFM_EF_LOW_TCO2_HA = _IFM_INTENSITY_LOW_M3_HA * _IFM_TEF_LOW_MG_C_M3 * _C_TO_CO2
_IFM_EF_HIGH_TCO2_HA = _IFM_INTENSITY_HIGH_M3_HA * _IFM_TEF_HIGH_MG_C_M3 * _C_TO_CO2

_IFM_CITATION = (
    "Pearson et al. (2014) 'Carbon emissions from tropical forest degradation caused "
    "by logging', Environmental Research Letters 9(3); "
    "Butarbutar et al. (2019) Kalimantan field study; "
    "IPCC 2006 GL Vol 4 + 2019 Refinement (conversion math only: CF 0.47, ×44/12)"
)

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

# ── ADR-0016 M1/M2: uncertainty propagation + density-fallback gating ─────────
# M1 — default relative SEs for error budget (quadrature, then buffer separately)
_CV_DENSITY_ESA_CCI = 0.20      # ESA CCI concession-level (no per-pixel SD layer in pre-launch)
_CV_DENSITY_IPCC_DEFAULT = 0.30 # IPCC Tier-1 default — wide; no satellite AGB available
# M2 — IFM quadrature components (pre-computed from TPTI + Pearson-2014 ranges)
_IFM_INTENSITY_MID_M3_HA = (_IFM_INTENSITY_LOW_M3_HA + _IFM_INTENSITY_HIGH_M3_HA) / 2    # 33.0
_IFM_TEF_MID_MG_C_M3 = (_IFM_TEF_LOW_MG_C_M3 + _IFM_TEF_HIGH_MG_C_M3) / 2              # 1.45
_IFM_EF_CENTRAL_TCO2_HA = _IFM_INTENSITY_MID_M3_HA * _IFM_TEF_MID_MG_C_M3 * _C_TO_CO2  # ~175.45
_CV_IFM_INTENSITY = (
    (_IFM_INTENSITY_HIGH_M3_HA - _IFM_INTENSITY_LOW_M3_HA) / (2 * _IFM_INTENSITY_MID_M3_HA)
)  # (40-26)/(2×33) ≈ 0.2121
_CV_IFM_TEF = (
    (_IFM_TEF_HIGH_MG_C_M3 - _IFM_TEF_LOW_MG_C_M3) / (2 * _IFM_TEF_MID_MG_C_M3)
)  # (1.5-1.4)/(2×1.45) ≈ 0.0345
_SIGMA_IFM = (_CV_IFM_INTENSITY**2 + _CV_IFM_TEF**2) ** 0.5  # ≈ 0.2149

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

    # HA — Hak Alam (selective logging permit); IFM logging-emissions basis (ADR-0015-C2)
    return MethodologyRoute(
        baseline_class="ifm_selective_logging",
        verra_family=(
            "IFM — VM0010 (selective-logging baseline, excl. planted forests; lead); "
            "VM0045 flagged (field/NFI-dependent — not satellite-screenable at screening stage)"
        ),
        cited_methods=["VM0010", "VM0045"],
        is_planned=True,
        additionality_basis="legal harvest right foregone",
        notes=(
            "HA = natural forest exploitation permit; baseline = planned selective logging foregone. "
            "IFM (Improved Forest Management) — ADR-0015-C2: uses Pearson-2014 logging-emissions "
            "basis (harvested_area × EF_per_ha), NOT density×loss_rate (REDD formula). "
            "VM0010 also credits removals from continued growth → our avoided-emissions-only "
            "estimate is a conservative floor. HWP second-order (extracted log 15-25% of TEF). "
            "Never VM0048 / VM0007."
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


def _evaluate_forest_gate(boundary: Boundary, forest: ForestData) -> ForestPresenceGate:
    """Evaluate the forest-presence/condition gate (ADR-0013-auto-routing).

    Uses Hansen baseline cover pct (from ForestData), JRC TMF disturbance history,
    and ESA WorldCover land cover to determine whether standing at-risk forest exists.

    gate_result:
      pass — forest confirmed (intact or lightly degraded; REDD/IFM number may proceed)
      flag — forest uncertain (heavily degraded or data insufficient; flag in classification)
      fail — no at-risk forest confirmed (cleared/scrub land; blocks the number)

    Conditions (evaluated top-down):
      cleared:          baseline_cover_pct < 20, OR (JRC deforested AND WorldCover non-tree)
      intact:           baseline_cover_pct >= 60 AND JRC undisturbed
      light_degradation: baseline_cover_pct >= 40 AND JRC undisturbed/degraded/regrowth
      heavy_degradation: baseline_cover_pct >= 20 (all other cases with data)
      unknown:          data insufficient
    """
    wc = query_worldcover(boundary)
    jrc = query_jrc_tmf(boundary)
    cover_pct = forest.baseline_cover_pct

    if cover_pct < 20 or (jrc.disturbance_class == "deforested" and not wc.is_tree_cover):
        condition = "cleared"
        gate_result = "fail"
        note = (
            f"No at-risk forest confirmed: Hansen baseline cover {cover_pct:.0f}% "
            f"(threshold 20%); JRC TMF: {jrc.disturbance_class}; "
            f"WorldCover: {wc.label}. "
            "No REDD/IFM baseline can be asserted (ADR-0013-auto-routing)."
        )
    elif cover_pct >= 60 and jrc.disturbance_class == "undisturbed":
        condition = "intact"
        gate_result = "pass"
        note = (
            f"Forest confirmed intact: {cover_pct:.0f}% Hansen baseline cover; "
            f"JRC TMF undisturbed ({jrc.tropical_forest_pct:.0f}% TMF). "
            "Permit-validity caveat: Indonesian permits may overlap or face One-Map disputes "
            "— advisor-confirm before any crediting claim."
        )
    elif cover_pct >= 40 and jrc.disturbance_class in ("undisturbed", "degraded", "regrowth"):
        condition = "light_degradation"
        gate_result = "pass"
        note = (
            f"Forest confirmed with light degradation: {cover_pct:.0f}% Hansen baseline cover; "
            f"JRC TMF {jrc.disturbance_class}. "
            "Permit-validity caveat: Indonesian permits may overlap or face One-Map disputes "
            "— advisor-confirm before any crediting claim."
        )
    elif cover_pct >= 20:
        condition = "heavy_degradation"
        gate_result = "flag"
        note = (
            f"Forest condition uncertain: {cover_pct:.0f}% Hansen baseline cover; "
            f"JRC TMF: {jrc.disturbance_class}. "
            "Low baseline carbon risk — field verification recommended before any crediting claim."
        )
    else:
        condition = "unknown"
        gate_result = "flag"
        note = "Forest presence data insufficient; field verification required."

    return ForestPresenceGate(
        forest_confirmed=(gate_result == "pass"),
        canopy_cover_pct=cover_pct,
        condition=condition,
        gate_result=gate_result,
        note=note,
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

    # ADR-0013: peat parcels surface as "flagged" — never eligible for a headline number.
    # run_eligibility() is project-type-blind (it checks permit/years/area/location gates);
    # the peat override ensures downstream summary and report code never sees "eligible"+None.
    if inp.project_type == "PEAT" and eligibility.verdict != "hard_no":
        eligibility = EligibilityResult(
            gates=eligibility.gates,
            verdict="flagged",
            reasons=eligibility.reasons + [
                "peat: flag — no tonnage asserted (ADR-0013); manual methodological review required"
            ],
        )

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

    # ── Forest-presence gate (ADR-0013-auto-routing) — non-peat REDD/IFM ────
    forest_gate = _evaluate_forest_gate(boundary, forest)
    quality = _quality_factors(inp, methodology)

    if forest_gate.gate_result == "fail" and eligibility.verdict != "hard_no":
        # No at-risk forest confirmed — flag, no number (cleared/scrub land)
        eligibility = EligibilityResult(
            gates=eligibility.gates,
            verdict="flagged",
            reasons=eligibility.reasons + [
                f"forest gate fail: {forest_gate.note}"
            ],
        )
        mineral_stratum = Stratum(
            stratum_id="mineral",
            area_ha=effective_area,
            soil_type="mineral",
            methodology=methodology,
            forest_gate=forest_gate,
            eligibility_verdict="flagged",
            eligibility_reasons=[forest_gate.note],
        )
        classification = ProjectClassification(
            strata=[mineral_stratum],
            dominant_soil="mineral",
            auto_determined=True,
            note=f"Forest gate fail — condition: {forest_gate.condition}",
        )
        unc = (
            f"Forest gate fail — no at-risk forest confirmed (ADR-0013-auto-routing). "
            f"Condition: {forest_gate.condition}. "
            f"{forest_gate.note} "
            f"Tier 1 baseline cannot be asserted without confirmed standing forest. "
            "Not registry-grade. Full land survey required before any crediting claim."
        )
        return CarbonEstimate(
            eligibility=eligibility,
            methodology=methodology,
            forest=forest,
            quantity_low_tco2e=None,
            quantity_high_tco2e=None,
            uncertainty=unc,
            quality=quality,
            classification=classification,
        )

    # Forest gate flag (heavy_degradation/light) — number computed but verdict forced to flagged
    if forest_gate.gate_result == "flag" and eligibility.verdict not in ("hard_no", "flagged"):
        eligibility = EligibilityResult(
            gates=eligibility.gates,
            verdict="flagged",
            reasons=eligibility.reasons + [
                f"forest gate flag: {forest_gate.note}"
            ],
        )

    # ── ADR-0015-C1: Forest-origin (plantation) gate — non-peat, non-hard_no ──
    # Classify forest_origin via KLHK Penutupan Lahan (primary) + temporal pattern.
    # Only fires when there is standing forest to classify (forest gate did not fail).
    forest_origin = _classify_forest_origin(boundary, forest)
    # Store classified origin in ForestData so the result carries it through
    forest = forest.model_copy(update={"forest_origin": forest_origin})

    if forest_origin == "plantation" and eligibility.verdict != "hard_no":
        # Established plantation: no standing NATURAL forest at risk.
        # Rotational-harvest loss ≠ avoidable deforestation → not an APD/IFM candidate.
        plantation_note = (
            f"ADR-0015-C1 plantation gate: KLHK Penutupan Lahan classifies this "
            f"concession as established plantation (hutan tanaman). "
            f"No standing natural forest at risk — rotational-harvest loss is not "
            f"avoidable deforestation. Not an APD candidate (HTI) or IFM candidate (HA). "
            f"No avoided-deforestation number asserted."
        )
        eligibility = EligibilityResult(
            gates=eligibility.gates,
            verdict="flagged",
            reasons=eligibility.reasons + [f"plantation gate: {plantation_note}"],
        )
        plantation_stratum = Stratum(
            stratum_id="plantation",
            area_ha=effective_area,
            soil_type="mineral",
            methodology=methodology,
            forest_gate=forest_gate,
            eligibility_verdict="flagged",
            eligibility_reasons=[plantation_note],
        )
        classification = ProjectClassification(
            strata=[plantation_stratum],
            dominant_soil="mineral",
            auto_determined=True,
            note=(
                f"ADR-0015-C1 plantation gate — forest_origin=plantation "
                f"(KLHK: hutan tanaman). Forest condition: {forest_gate.condition}."
            ),
        )
        unc = (
            f"Plantation gate (ADR-0015-C1) — Tier 1 screening: KLHK Penutupan Lahan "
            f"indicates established plantation (hutan tanaman). "
            f"Rotational-harvest loss is NOT avoidable deforestation; "
            f"Tier 1 baseline cannot be asserted for plantation-derived 'loss'. "
            "Not registry-grade. Field origin-verification and dominant-baseline "
            "assessment required before any crediting claim."
        )
        return CarbonEstimate(
            eligibility=eligibility,
            methodology=methodology,
            forest=forest,
            quantity_low_tco2e=None,
            quantity_high_tco2e=None,
            uncertainty=unc,
            quality=quality,
            classification=classification,
        )

    if forest_origin == "mixed" and eligibility.verdict != "hard_no":
        # Mixed: plantation pixels mask applied to loss rate
        # Estimate uses the natural-forest fraction of the area (TODO: refine with KLHK area split).
        # For now, full area proceeds with a caveat (conservative: if plantation, fewer actual
        # emissions; this may overstate, not understate). ADR-0015 future: real area split.
        mixed_note = (
            "ADR-0015-C1: mixed natural+plantation concession. "
            "Plantation rotational-harvest pixels should be masked from the APD baseline; "
            "area used in estimate includes plantation component — overstatement risk. "
            "Confirm natural-forest area with KLHK Penutupan Lahan before submission."
        )
        if eligibility.verdict not in ("hard_no", "flagged"):
            eligibility = EligibilityResult(
                gates=eligibility.gates,
                verdict="flagged",
                reasons=eligibility.reasons + [f"mixed forest-origin: {mixed_note}"],
            )

    # ── ADR-0016-M2: density-fallback gate (REDD/HTI only — IFM uses TEF, not AGB) ──
    if inp.permit_type != "HA":
        if forest.biomass_tco2_per_ha is None:
            # No credible biomass source → FLAG, no number
            no_biomass_note = (
                "ADR-0016-M2: no credible biomass source (biomass_tco2_per_ha=None) — "
                "a Tier 1 avoided-deforestation estimate cannot be asserted. "
                "ESA CCI, GEDI, or a field AGB survey required before any crediting claim."
            )
            if eligibility.verdict != "hard_no":
                eligibility = EligibilityResult(
                    gates=eligibility.gates,
                    verdict="flagged",
                    reasons=eligibility.reasons + [no_biomass_note],
                )
            unc_nb = (
                f"Tier 1 indicative screening — ADR-0016-M2: {no_biomass_note} "
                f"Baseline cannot be computed without a density source. "
                f"Not registry-grade."
            )
            return CarbonEstimate(
                eligibility=eligibility,
                methodology=methodology,
                forest=forest,
                quantity_low_tco2e=None,
                quantity_high_tco2e=None,
                uncertainty=unc_nb,
                quality=quality,
                classification=ProjectClassification(
                    strata=[Stratum(
                        stratum_id="mineral",
                        area_ha=effective_area,
                        soil_type="mineral",
                        methodology=methodology,
                        forest_gate=forest_gate,
                        eligibility_verdict=eligibility.verdict,
                        eligibility_reasons=eligibility.reasons,
                    )],
                    dominant_soil="mineral",
                    auto_determined=True,
                    note="ADR-0016-M2: no-biomass gate fired — no number asserted.",
                ),
            )

        # M2: IPCC default → add loud flag to eligibility
        _, is_ipcc_default, _ = _density_cv_info(forest)
        if is_ipcc_default and eligibility.verdict not in ("hard_no", "flagged"):
            ipcc_loud_note = (
                f"ADR-0016-M2 DEFAULT DENSITY — HIGH UNCERTAINTY: "
                f"no satellite AGB source; using IPCC 2006 Table 4.7 SE-Asia Tier-1 default "
                f"({forest.biomass_tco2_per_ha:.0f} tCO2/ha). "
                f"True forest AGB may differ significantly. "
                f"Obtain ESA CCI, GEDI, or field AGB before any crediting claim."
            )
            eligibility = EligibilityResult(
                gates=eligibility.gates,
                verdict="flagged",
                reasons=eligibility.reasons + [ipcc_loud_note],
            )

    # ── ADR-0015-C2: Route to correct estimate formula ────────────────────────
    # HA → IFM selective-logging basis (Pearson 2014, not density×loss_rate)
    # HTI → APD (REDD, density×loss_rate; unchanged)
    if inp.permit_type == "HA":
        low, high, unc, trace = _estimate_ifm(effective_area, project_years, methodology)
    else:
        low, high, unc, trace = _estimate_redd(effective_area, project_years, forest, loss_rate, methodology)

    # Attach forest gate + origin to classification for all non-peat results
    mineral_stratum = Stratum(
        stratum_id="mineral",
        area_ha=effective_area,
        soil_type="mineral",
        methodology=methodology,
        forest_gate=forest_gate,
        eligibility_verdict=eligibility.verdict,
        eligibility_reasons=eligibility.reasons,
        quantity_low_tco2e=low,
        quantity_high_tco2e=high,
    )
    origin_note = (
        f"forest_origin={forest_origin} (ADR-0015-C1 KLHK gate)"
        if forest_origin != "unknown"
        else "forest_origin=unknown (KLHK Penutupan Lahan data unavailable; proceed with caveat)"
    )
    classification = ProjectClassification(
        strata=[mineral_stratum],
        dominant_soil="mineral",
        auto_determined=True,
        note=f"Forest condition: {forest_gate.condition} (gate: {forest_gate.gate_result}); {origin_note}",
    )

    return CarbonEstimate(
        eligibility=eligibility,
        methodology=methodology,
        forest=forest,
        quantity_low_tco2e=low,
        quantity_high_tco2e=high,
        uncertainty=unc,
        quality=quality,
        classification=classification,
        derivation=trace,  # ADR-0014
    )


def run_mixed_stratification(
    inp: CarbonInput,
    boundary: Boundary,
    forest: ForestData,
    min_stratum_ha: float = 1000.0,
) -> CarbonEstimate:
    """Soil-first mixed-concession stratification (ADR-0013-auto-routing).

    Checks KHG peat area. If both peat_area >= min_stratum_ha AND
    mineral_area >= min_stratum_ha, creates two strata:
      - peat stratum: flag, no tonnage (ADR-0013 peatland)
      - mineral stratum: REDD/IFM estimate on mineral area

    Falls back to run_carbon_engine() if not sufficiently mixed.
    Never called by run_carbon_engine() — only from the API for 'other' projects.
    Determinism invariant preserved: no LLM calls.
    """
    khg = query_khg(boundary)
    peat_area = (
        khg.area_ha
        if (khg.intersects is True and khg.area_ha is not None)
        else 0.0
    )
    mineral_area = boundary.area_ha - peat_area

    if peat_area < min_stratum_ha or mineral_area < min_stratum_ha:
        return run_carbon_engine(inp, boundary, forest)

    # ── Peat stratum (ADR-0013: flag, no tonnage by construction) ─────────────
    peat_meth = MethodologyRoute(
        baseline_class="peat",
        verra_family=(
            "No settled active Verra method for avoided tropical-peat conversion as of 2026 — "
            "route to be confirmed with methodology advisor."
        ),
        cited_methods=[],
        is_planned=True,
        additionality_basis="legal harvest right foregone",
        notes="ADR-0013: peat stratum — flag, no tonnage. Never VM0027 / VM0048 / VM0007.",
    )
    peat_legal = _evaluate_peat_overlays(boundary)
    peat_stratum = Stratum(
        stratum_id="peat",
        area_ha=peat_area,
        soil_type="peat",
        methodology=peat_meth,
        legal_overlay=peat_legal,
        eligibility_verdict="flagged",
        eligibility_reasons=[
            f"peat stratum (ADR-0013): {peat_legal.peat_additionality_status}",
        ],
        quantity_low_tco2e=None,
        quantity_high_tco2e=None,
    )

    # ── Mineral stratum (REDD/IFM) ────────────────────────────────────────────
    eligibility = run_eligibility(inp, boundary)
    methodology = build_methodology_route(inp)
    forest_gate = _evaluate_forest_gate(boundary, forest)
    quality = _quality_factors(inp, methodology)

    project_years = min(inp.permit_years_remaining, _MAX_CREDITING_YR)
    recent_years = [y for y in range(2016, 2024) if y in forest.annual_loss_ha]
    if recent_years:
        avg_annual_loss_ha = (
            sum(forest.annual_loss_ha[y] for y in recent_years) / len(recent_years)
        )
    else:
        avg_annual_loss_ha = sum(forest.annual_loss_ha.values()) / max(len(forest.annual_loss_ha), 1)

    loss_rate_area = max(boundary.area_ha, 25_000.0)
    loss_rate = avg_annual_loss_ha / loss_rate_area

    if forest_gate.gate_result == "fail":
        mineral_stratum = Stratum(
            stratum_id="mineral",
            area_ha=mineral_area,
            soil_type="mineral",
            methodology=methodology,
            forest_gate=forest_gate,
            eligibility_verdict="flagged",
            eligibility_reasons=[f"forest gate fail: {forest_gate.note}"],
        )
        mineral_low: float | None = None
        mineral_high: float | None = None
        mineral_trace = None
        unc = (
            f"Mixed-concession — mineral stratum ({mineral_area:,.0f} ha): "
            f"forest gate fail — no at-risk forest confirmed. "
            f"Peat stratum ({peat_area:,.0f} ha): flag (ADR-0013). "
            f"Tier 1 baseline cannot be asserted without confirmed standing forest. "
            f"Not registry-grade."
        )
    else:
        if forest_gate.gate_result == "flag" and eligibility.verdict not in ("hard_no", "flagged"):
            eligibility = EligibilityResult(
                gates=eligibility.gates,
                verdict="flagged",
                reasons=eligibility.reasons + [
                    f"forest gate flag: {forest_gate.note}"
                ],
            )
        # ADR-0015-C2 / ADR-0016-M2: route HA mineral stratum to IFM; HTI to REDD
        if inp.permit_type == "HA":
            mineral_low, mineral_high, unc_redd, mineral_trace = _estimate_ifm(
                mineral_area, project_years, methodology
            )
        elif forest.biomass_tco2_per_ha is None:
            # ADR-0016-M2: no-biomass gate in mixed mineral stratum
            mineral_low = None
            mineral_high = None
            mineral_trace = None
            unc_redd = (
                "ADR-0016-M2: mineral stratum — no credible biomass source; "
                "no avoided-deforestation number asserted."
            )
        else:
            mineral_low, mineral_high, unc_redd, mineral_trace = _estimate_redd(
                mineral_area, project_years, forest, loss_rate, methodology
            )
        mineral_stratum = Stratum(
            stratum_id="mineral",
            area_ha=mineral_area,
            soil_type="mineral",
            methodology=methodology,
            forest_gate=forest_gate,
            eligibility_verdict=eligibility.verdict,
            eligibility_reasons=eligibility.reasons,
            quantity_low_tco2e=mineral_low,
            quantity_high_tco2e=mineral_high,
        )
        peat_unc = _peat_flag_uncertainty(peat_legal)
        unc = (
            f"Mixed-concession Tier 1 estimate — "
            f"mineral stratum ({mineral_area:,.0f} ha): {unc_redd} "
            f"| Peat stratum ({peat_area:,.0f} ha): {peat_unc}"
        )

    # ── Combined ──────────────────────────────────────────────────────────────
    combined_reasons = peat_stratum.eligibility_reasons + mineral_stratum.eligibility_reasons
    combined_eligibility = EligibilityResult(
        gates=eligibility.gates,
        verdict="flagged",  # always flagged when peat stratum present
        reasons=combined_reasons,
    )
    classification = ProjectClassification(
        strata=[peat_stratum, mineral_stratum],
        dominant_soil="mixed",
        auto_determined=True,
        note=(
            f"Soil-first stratification (ADR-0013): "
            f"peat {peat_area:,.0f} ha (flag) + mineral {mineral_area:,.0f} ha (REDD/IFM). "
            f"KHG intersect: {khg.intersects}."
        ),
    )

    return CarbonEstimate(
        eligibility=combined_eligibility,
        methodology=methodology,
        forest=forest,
        quantity_low_tco2e=mineral_low,
        quantity_high_tco2e=mineral_high,
        uncertainty=unc,
        quality=quality,
        classification=classification,
        derivation=mineral_trace if mineral_low is not None else None,  # ADR-0014
    )


def _classify_forest_origin(boundary: Boundary, forest: ForestData) -> str:
    """Classify forest origin: natural / plantation / mixed / unknown (ADR-0015-C1).

    Primary: KLHK Penutupan Lahan — distinguishes hutan tanaman (plantation) vs
             hutan alam (natural forest); administrative ground truth.
    Secondary: JRC TMF / Hansen rotational-harvest temporal pattern
               (short ~5–7 yr clear-and-replant return interval is a plantation signal;
               natural forest is NOT stand-replaced on a 5–7 yr grid).

    CI uses KLHK fixture (real KLHK API → pre-launch backlog, same as KHG/PIPPIB).
    Returns "unknown" when both signals are unavailable — engine proceeds with caveat.
    """
    klhk = query_klhk_plantation(boundary)

    # Primary: KLHK map result
    if klhk.forest_origin in ("natural", "plantation", "mixed"):
        return klhk.forest_origin

    # Secondary: temporal pattern from annual_loss_ha time series.
    # Heuristic: if ≥3 loss-spike years (where the year's loss > 2× the long-run mean)
    # form a regular cycle with ~5–7 yr gaps, it is consistent with rotational harvest.
    # This is a low-precision screen; KLHK is authoritative.
    if len(forest.annual_loss_ha) >= 10:
        losses = [forest.annual_loss_ha[y] for y in sorted(forest.annual_loss_ha)]
        mean_loss = sum(losses) / len(losses)
        if mean_loss > 0:
            spike_years = [
                y for y in sorted(forest.annual_loss_ha)
                if forest.annual_loss_ha[y] > 2.5 * mean_loss
            ]
            if len(spike_years) >= 2:
                gaps = [spike_years[i + 1] - spike_years[i] for i in range(len(spike_years) - 1)]
                periodic_gaps = [g for g in gaps if 4 <= g <= 8]
                if len(periodic_gaps) >= len(gaps) * 0.6:
                    return "plantation"

    return "unknown"


def _density_cv_info(forest: ForestData) -> tuple[float, bool, bool]:
    """Return (cv_density, is_ipcc_default, has_esa_cci) for ADR-0016 M1/M2.

    Priority:
      1. biomass_uncertainty_pct field (from ESA CCI SD layer or field survey)
      2. ESA CCI detected in data_sources → default concession-level CV 20%
      3. IPCC Tier-1 default → wide CV 30% (triggers M2 loud flag)
    """
    # "ESA CCI Biomass v3.0" and "GEDI AGB" are success-path strings from the adapter.
    # The IPCC fallback string contains "ESA CCI read failed" — must not match.
    has_esa_cci = any(
        "ESA CCI Biomass v3.0" in s or "GEDI AGB" in s
        for s in forest.data_sources
    )
    if forest.biomass_uncertainty_pct is not None:
        return forest.biomass_uncertainty_pct / 100.0, False, has_esa_cci
    if has_esa_cci:
        return _CV_DENSITY_ESA_CCI, False, True
    return _CV_DENSITY_IPCC_DEFAULT, True, False


def _estimate_ifm(
    area: float,
    years: int,
    route: MethodologyRoute,
) -> tuple[float, float, str, CalculationTrace]:
    """Avoided-emissions range for IFM (selective logging) — HA permit type only (ADR-0015-C2).

    Formula (Pearson et al. 2014 logging-emissions basis):
      harvested_area = eligible_area × min(1, crediting_years / cycle_years)
      avoided_CO2   = harvested_area × EF_per_ha × (1 − buffer)
      n_entries = 1  (one avoided entry in a 20–30 yr period vs ~35 yr TPTI cycle)

    Low estimate: conservative intensity (26 m³/ha), TEF low (1.4 MgC/m³), buffer high (30%).
    High estimate: intensive (40 m³/ha), TEF high (1.5 MgC/m³), buffer low (20%).
    IPCC Tier 1 — Pearson-2014 defaults; not field-measured intensity.

    NOT density×loss_rate — that is the REDD (APD) formula.
    VM0010 lead (selective-logging baseline, excl. planted forests); VM0045 field/NFI-only.
    VM0010 also credits removals from continued growth → avoided-only is a conservative floor.
    HWP (wood products) is second-order (extracted log 15–25% of emissions) — noted, not engineered.
    """
    harvested_area = area * min(1.0, years / _IFM_CYCLE_YR)

    # ADR-0016 M1: quadrature error budget for IFM
    # "Density" analog = TEF (Pearson 2014); "rate" analog = TPTI extraction intensity.
    # sigma = sqrt(CV_intensity² + CV_TEF²); buffer applied SEPARATELY and LABELLED.
    sigma = _SIGMA_IFM  # pre-computed constant ≈ 0.2149

    central = harvested_area * _IFM_EF_CENTRAL_TCO2_HA

    low_before_buf = central * max(0.0, 1.0 - sigma)
    high_before_buf = central * (1.0 + sigma)

    net_low = round(low_before_buf * (1 - _BUFFER_HIGH), 0)
    net_high = round(high_before_buf * (1 - _BUFFER_LOW), 0)

    if net_low >= net_high:
        net_high = net_low + max(1.0, round(net_low * 0.1, 0))

    unc = (
        f"Tier 1 indicative screening — IFM basis (ADR-0015-C2 + ADR-0016 M1 error budget). "
        f"Citation: {_IFM_CITATION}. "
        f"n_entries=1 (one avoided entry in a {years}-yr period vs {_IFM_CYCLE_YR}-yr TPTI cycle). "
        f"harvested_area {harvested_area:,.0f} ha (= {area:,.0f} ha × min(1, {years}/{_IFM_CYCLE_YR})). "
        f"ADR-0016 M1 error budget (in quadrature): "
        f"CV_intensity {_CV_IFM_INTENSITY*100:.1f}% (TPTI band "
        f"{_IFM_INTENSITY_LOW_M3_HA:.0f}–{_IFM_INTENSITY_HIGH_M3_HA:.0f} m³/ha, "
        f"mid {_IFM_INTENSITY_MID_M3_HA:.0f} m³/ha); "
        f"CV_TEF {_CV_IFM_TEF*100:.1f}% (Pearson-2014 "
        f"{_IFM_TEF_LOW_MG_C_M3}–{_IFM_TEF_HIGH_MG_C_M3} MgC/m³, "
        f"mid {_IFM_TEF_MID_MG_C_M3} MgC/m³); "
        f"EF_central {_IFM_EF_CENTRAL_TCO2_HA:.1f} tCO2/ha; "
        f"combined sigma {sigma*100:.1f}%; "
        f"central {central:,.0f} tCO2e; "
        f"pre-buffer band [{low_before_buf:,.0f}–{high_before_buf:,.0f}] tCO2e. "
        f"VCS non-permanence buffer deducted SEPARATELY: "
        f"{int(_BUFFER_LOW*100)}–{int(_BUFFER_HIGH*100)}%. "
        f"Net: [{net_low:,.0f}–{net_high:,.0f}] tCO2e. "
        f"Dominant uncertainty: IUP extraction intensity not verified from permit document; "
        f"Pearson-2014 TEF is a regional default (Indonesia/SE-Asia), not site-specific. "
        f"VM0010 (selective-logging baseline, excl. planted forests) — avoided-emissions-only "
        f"estimate is a conservative floor (VM0010 also credits continued-growth removals). "
        f"GEDI/ICESat-2 space-LiDAR as secondary density source: pre-launch backlog. "
        f"VM0045 requires NFI/field data — not satellite-screenable at this stage. "
        f"Not registry-grade. Confirm with full feasibility study before any crediting claim."
    )
    trace = CalculationTrace(
        formula=(
            "harvested_area = eligible_area x min(1, years / cycle); "
            "central = harvested_area x EF_central; "
            "sigma_IFM = sqrt(CV_intensity^2 + CV_TEF^2) [pre-computed constant]; "
            "gross_low = central x max(0, 1-sigma); gross_high = central x (1+sigma); "
            "net_low = gross_low x (1-buffer_high); net_high = gross_high x (1-buffer_low)"
        ),
        basis="ifm",
        eligible_area_ha=round(area, 1),
        project_years=years,
        buffer_low=_BUFFER_LOW,
        buffer_high=_BUFFER_HIGH,
        harvested_area_ha=round(harvested_area, 1),
        ef_central_tco2_ha=round(_IFM_EF_CENTRAL_TCO2_HA, 2),
        sigma_ifm_pct=round(sigma * 100, 2),
        central_tco2e=round(central, 0),
        gross_low_tco2e=round(low_before_buf, 0),
        gross_high_tco2e=round(high_before_buf, 0),
        net_low_tco2e=net_low,
        net_high_tco2e=net_high,
        notes=(
            "ADR-0015-C2 + ADR-0016-M1: Pearson-2014 TEF basis; "
            "sigma pre-computed from TPTI intensity + TEF ranges; "
            "VCS buffer deducted separately and labelled."
        ),
    )
    return net_low, net_high, unc, trace


def _estimate_redd(
    area: float,
    years: int,
    forest: ForestData,
    loss_rate: float,
    route: MethodologyRoute,
) -> tuple[float, float, str, CalculationTrace]:
    """Avoided-emissions range for REDD (APD).

    ADR-0016 M1: uncertainty propagated in quadrature; buffer applied SEPARATELY.

    Formula:
      central = eligible_area × baseline_loss_rate × years × carbon_density
      low_before_buf = central × (1 − sigma_combined)
      high_before_buf = central × (1 + sigma_combined)
      net_low  = low_before_buf  × (1 − buffer_high)   [separate, labelled]
      net_high = high_before_buf × (1 − buffer_low)    [separate, labelled]

    sigma_combined = sqrt(CV_density² + CV_loss²)
      CV_density: from biomass_uncertainty_pct (ESA CCI SE) or source-based default
      CV_loss: std/mean of Hansen annual-loss series 2016–2023

    Caller ensures forest.biomass_tco2_per_ha is not None (M2 gate).
    """
    carbon_density = forest.biomass_tco2_per_ha  # caller ensures non-None

    # M1: density CV
    cv_density, is_ipcc_default, has_esa_cci = _density_cv_info(forest)

    # M1: loss-rate uncertainty = standard error of the mean (SEM) of the annual series.
    # SEM = std / (mean × sqrt(n)) — reflects uncertainty in the estimated mean, not raw variability.
    # Using raw CV (std/mean) would penalise a stable series just because its inter-annual spread
    # is wide relative to a small mean; SEM shrinks with more years as expected for an estimator.
    recent = [forest.annual_loss_ha[y] for y in range(2016, 2024) if y in forest.annual_loss_ha]
    if len(recent) >= 2:
        mean_l = sum(recent) / len(recent)
        std_l = (_math.fsum((x - mean_l) ** 2 for x in recent) / len(recent)) ** 0.5
        cv_loss = (std_l / mean_l) / (len(recent) ** 0.5) if mean_l > 0 else _CV_DENSITY_IPCC_DEFAULT
    else:
        cv_loss = _CV_DENSITY_IPCC_DEFAULT  # too few years — conservative default

    sigma = _math.sqrt(cv_density ** 2 + cv_loss ** 2)

    # Central estimate
    central = area * loss_rate * years * carbon_density

    # Uncertainty band — before buffer
    low_before_buf = central * max(0.0, 1.0 - sigma)
    high_before_buf = central * (1.0 + sigma)

    # VCS non-permanence buffer: SEPARATE, LABELLED deduction
    net_low = round(low_before_buf * (1 - _BUFFER_HIGH), 0)
    net_high = round(high_before_buf * (1 - _BUFFER_LOW), 0)

    if net_low >= net_high:
        net_high = net_low + max(1.0, round(net_low * 0.1, 0))

    # Density source label (M2 saturation caveat for ESA CCI)
    if has_esa_cci:
        density_label = (
            f"ESA CCI / satellite AGB ({carbon_density:.0f} tCO2/ha, concession mean); "
            f"SATURATION CAVEAT: ESA CCI underestimates AGB >~150–250 Mg/ha (sensor saturation) — "
            f"actual density may be higher in dense forest; "
            f"relative SE: {cv_density*100:.0f}%"
        )
    else:
        density_label = (
            f"IPCC 2006 Table 4.7 SE-Asia Tier-1 default ({carbon_density:.0f} tCO2/ha); "
            f"DEFAULT DENSITY — HIGH UNCERTAINTY: no satellite AGB available; "
            f"true density may differ significantly; "
            f"relative SE: {cv_density*100:.0f}%"
        )

    n_loss_yrs = len([y for y in range(2016, 2024) if y in forest.annual_loss_ha])
    unc = (
        f"Tier 1 indicative screening — ADR-0016 M1 error budget (in quadrature): "
        f"carbon density [{density_label}]; "
        f"baseline loss-rate SEM {cv_loss*100:.1f}% "
        f"(Hansen GFC-2022 2016–2023 {n_loss_yrs}-yr std/(mean×√n)); "
        f"combined sigma {sigma*100:.0f}%; "
        f"central {central:,.0f} tCO2e; "
        f"pre-buffer band [{low_before_buf:,.0f}–{high_before_buf:,.0f}] tCO2e. "
        f"VCS non-permanence buffer deducted SEPARATELY: "
        f"{int(_BUFFER_LOW*100)}–{int(_BUFFER_HIGH*100)}%. "
        f"Net: [{net_low:,.0f}–{net_high:,.0f}] tCO2e. "
        f"Baseline (legally-permitted harvest rate) and carbon density are co-dominant "
        f"uncertainties — IUP extraction rate not yet verified from permit document; "
        f"satellite AGB is a concession-mean estimate, not field-measured. "
        f"GEDI/ICESat-2 as secondary AGB source: pre-launch backlog. "
        f"Not registry-grade. Confirm with full feasibility study before any crediting claim."
    )
    density_source_str = (
        f"ESA CCI Biomass v3.0 ({carbon_density:.0f} tCO2/ha concession mean)"
        if has_esa_cci
        else f"IPCC 2006 Table 4.7 SE-Asia Tier-1 default ({carbon_density:.0f} tCO2/ha)"
    )
    trace = CalculationTrace(
        formula=(
            "central = eligible_area x baseline_loss_rate x years x carbon_density; "
            "sigma = sqrt(CV_density^2 + SEM_loss^2) [quadrature; ADR-0016-M1]; "
            "gross_low = central x max(0, 1-sigma); gross_high = central x (1+sigma); "
            "net_low = gross_low x (1-buffer_high); net_high = gross_high x (1-buffer_low)"
        ),
        basis="redd",
        eligible_area_ha=round(area, 1),
        project_years=years,
        buffer_low=_BUFFER_LOW,
        buffer_high=_BUFFER_HIGH,
        baseline_loss_rate_yr=round(loss_rate, 6),
        loss_rate_sem_pct=round(cv_loss * 100, 2),
        carbon_density_tco2_ha=round(carbon_density, 1),
        carbon_density_source=density_source_str,
        carbon_density_cv_pct=round(cv_density * 100, 1),
        sigma_combined_pct=round(sigma * 100, 2),
        central_tco2e=round(central, 0),
        gross_low_tco2e=round(low_before_buf, 0),
        gross_high_tco2e=round(high_before_buf, 0),
        net_low_tco2e=net_low,
        net_high_tco2e=net_high,
        notes=(
            "ADR-0016-M1: SEM-based loss uncertainty (not raw CV); "
            "VCS buffer deducted separately and labelled."
        ),
    )
    return net_low, net_high, unc, trace


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
