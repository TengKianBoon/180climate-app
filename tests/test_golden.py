"""tests/test_golden.py — parametrized golden-case suite for the carbon engine.

Covers all eligibility gate combos, methodology routing, and ADR-0009 invariants.
WO-CARBON-003: adds PEAT routing fixture + forest-type-aware biomass assertions.
WO-CARBON-004: numeric range assertions added to eligibility fixtures once frozen.

Test categories:
  test_eligibility_golden         — gate combos: eligible / flagged / hard_no
  test_methodology_routing_golden — HTI→APD, HA→IFM, PEAT→VM0027; never VM0048/VM0007
  test_no_forbidden_phrases_*     — lint: no "% accuracy", no "% confidence"
  test_estimate_is_always_range   — quantity_low < quantity_high (ADR-0009)
  test_determinism                — same input → same output every time
  test_biomass_is_real_ipcc_value — forest-type-aware IPCC 2006 value check
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import pytest

from core.contracts import GeoInput, CarbonInput, ContactInfo
from core.geo import parse_geo
from core.forest import query_forest_data
from engines.carbon.engine import run_carbon_engine, build_methodology_route

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "carbon"

_FORBIDDEN_PHRASES = [
    r"%\s*accuracy",
    r"%\s*confidence",
    r"% accurate",
]


def _load(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text())


def _make_input(d: dict) -> CarbonInput:
    return CarbonInput(**d)


# ── Eligibility gate fixtures ─────────────────────────────────────────────────

ELIG_FIXTURES = [
    "WO002_HTI_eligible.json",
    "WO002_HTI_flag_years.json",
    "WO002_HTI_fail_area.json",
    "WO002_HA_eligible.json",
    "WO002_HTI_flag_outside.json",
]


@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_eligibility_golden(fixture_name: str):
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    exp = case["expected"]
    assert estimate.eligibility.verdict == exp["eligibility_verdict"], (
        f"{fixture_name}: expected verdict={exp['eligibility_verdict']!r}, "
        f"got {estimate.eligibility.verdict!r}"
    )
    for gate_key, expected_status in exp.get("gates", {}).items():
        actual = estimate.eligibility.gates[gate_key].status
        assert actual == expected_status, (
            f"{fixture_name}: gate {gate_key!r} expected {expected_status!r}, "
            f"got {actual!r}"
        )


@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_methodology_is_planned_for_all_elig_cases(fixture_name: str):
    """Invariant (ADR-0001): is_planned MUST be True for HTI and HA foregone-harvest."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    assert estimate.methodology.is_planned is True, (
        f"INVARIANT VIOLATION (ADR-0001): is_planned must be True for {inp.permit_type}"
    )


@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_additionality_basis_for_all_elig_cases(fixture_name: str):
    """Invariant (ADR-0001): additionality_basis must be 'legal harvest right foregone'."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    assert estimate.methodology.additionality_basis == "legal harvest right foregone", (
        f"INVARIANT VIOLATION (ADR-0001): additionality_basis wrong for {inp.permit_type}: "
        f"got {estimate.methodology.additionality_basis!r}"
    )


# ── Methodology routing fixtures ──────────────────────────────────────────────

ROUTING_FIXTURES = [
    "WO002_routing_HTI.json",
    "WO002_routing_HA.json",
    "WO003_routing_PEAT.json",    # WO-CARBON-006/ADR-0012: PEAT → no settled method (VM0027 inactivated 2023)
]


@pytest.mark.parametrize("fixture_name", ROUTING_FIXTURES)
def test_methodology_routing_golden(fixture_name: str):
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    route = build_methodology_route(inp)
    exp = case["expected_methodology"]

    assert route.baseline_class == exp["baseline_class"], (
        f"{fixture_name}: baseline_class expected {exp['baseline_class']!r}, "
        f"got {route.baseline_class!r}"
    )
    assert route.is_planned == exp["is_planned"], (
        "INVARIANT VIOLATION (ADR-0001): is_planned must be True for HTI/HA"
    )
    assert route.additionality_basis == exp["additionality_basis"], (
        f"INVARIANT VIOLATION (ADR-0001): additionality_basis wrong: {route.additionality_basis!r}"
    )
    for frag in exp.get("verra_family_contains", []):
        assert frag in route.verra_family, (
            f"{fixture_name}: expected verra_family to contain {frag!r}, "
            f"got {route.verra_family!r}"
        )
    for bad in exp.get("verra_family_must_not_contain", []):
        assert bad not in route.verra_family, (
            f"INVARIANT VIOLATION (ADR-0012): {bad!r} must NEVER appear in verra_family "
            f"(got {route.verra_family!r})"
        )
    for bad in exp.get("cited_methods_must_not_contain", []):
        for m in route.cited_methods:
            assert bad not in m, (
                f"INVARIANT VIOLATION (ADR-0001/0012): {bad!r} must NEVER appear in cited_methods "
                f"for foregone-harvest baselines (got {route.cited_methods})"
            )
    if exp.get("cited_methods_must_be_empty"):
        assert route.cited_methods == [], (
            f"INVARIANT VIOLATION (ADR-0012): cited_methods must be empty for peat route "
            f"(no settled active Verra method); got {route.cited_methods}"
        )


# ── ADR-0009 invariants: no single number, no %, always a range ──────────────

@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_no_forbidden_phrases_in_output(fixture_name: str):
    """Lint (ADR-0009): no '% accuracy' or '% confidence' anywhere in estimate output."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    dump = estimate.model_dump_json()
    for pattern in _FORBIDDEN_PHRASES:
        assert not re.search(pattern, dump, re.IGNORECASE), (
            f"INVARIANT VIOLATION (ADR-0009): forbidden phrase {pattern!r} found "
            f"in estimate output for {fixture_name}"
        )


@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_estimate_is_always_a_range(fixture_name: str):
    """Invariant (ADR-0009): estimate must always be a range — quantity_low < quantity_high."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    assert estimate.quantity_low_tco2e < estimate.quantity_high_tco2e, (
        f"INVARIANT VIOLATION (ADR-0009): estimate must be a range for {fixture_name}. "
        f"low={estimate.quantity_low_tco2e}, high={estimate.quantity_high_tco2e}"
    )


@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_determinism(fixture_name: str):
    """Invariant: same input → same output every time (no randomness, no LLM in number path)."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    b = parse_geo(inp.geo)
    f = query_forest_data(b)
    e1 = run_carbon_engine(inp, b, f)
    e2 = run_carbon_engine(inp, b, f)
    assert e1.quantity_low_tco2e == e2.quantity_low_tco2e, "Determinism violation: low estimate differs"
    assert e1.quantity_high_tco2e == e2.quantity_high_tco2e, "Determinism violation: high estimate differs"
    assert e1.eligibility.verdict == e2.eligibility.verdict, "Determinism violation: verdict differs"
    assert e1.methodology.baseline_class == e2.methodology.baseline_class, (
        "Determinism violation: baseline_class differs"
    )


@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_data_sources_labelled(fixture_name: str):
    """Acceptance (WO-CARBON-001): ForestData.data_sources must be non-empty and labelled."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    assert forest.data_sources, "ForestData.data_sources must be non-empty"
    assert forest.uncertainty_band, "ForestData.uncertainty_band must be non-empty"


@pytest.mark.parametrize("fixture_name", ELIG_FIXTURES)
def test_biomass_is_populated_and_labelled(fixture_name: str):
    """Acceptance (WO-CARBON-001b/c): biomass_tco2_per_ha is populated with a real source label.

    WO-CARBON-001c: density is now real ESA CCI Biomass v3.0 2018 for polygon inputs
    (concession-mean AGB), or IPCC Tier-1 fallback for Point inputs. Both are legitimate
    real values — the old IPCC >=500 threshold assumed intact-forest defaults and is no
    longer appropriate for concession-mean satellite estimates of actively-cleared areas.

    Checks:
      - biomass_tco2_per_ha > 50 (any plausible tropical-region value; excludes zero/null)
      - data_sources contains a density/biomass label (ESA CCI or IPCC fallback)
    """
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    assert forest.biomass_tco2_per_ha is not None and forest.biomass_tco2_per_ha > 50, (
        f"biomass_tco2_per_ha={forest.biomass_tco2_per_ha} is not a plausible "
        f"tropical value (expected >50 tCO2/ha) for {fixture_name}"
    )
    has_density_label = any(
        any(kw in s for kw in ("ESA CCI", "GEDI", "Biomass", "biomass"))
        for s in forest.data_sources
    )
    assert has_density_label, (
        f"No density source label found in data_sources for {fixture_name}. "
        f"Sources: {forest.data_sources}"
    )


# ── WO-CARBON-004: frozen numeric ranges ─────────────────────────────────────
# These values are computed by the engine and frozen on 2026-06-24.
# They are the test oracle for Gate M — Cowork reviews these numbers before sign-off.
# Any change to the formula MUST regenerate these values AND update this fixture.

RANGE_FIXTURES = [
    "WO002_HTI_eligible.json",
    "WO002_HTI_flag_years.json",
    "WO002_HTI_fail_area.json",
    "WO002_HA_eligible.json",
    "WO002_HTI_flag_outside.json",
    "WO003_routing_PEAT.json",
]


@pytest.mark.parametrize("fixture_name", RANGE_FIXTURES)
def test_golden_ranges(fixture_name: str):
    """WO-CARBON-004: frozen range values must match engine output exactly (determinism oracle).

    WO-AUTOROUTE-002: peat fixture now has null quantities (flag, not a number).
    Non-peat fixtures still assert exact frozen range values.
    """
    case = _load(fixture_name)
    if "expected_range" not in case:
        pytest.skip(f"No expected_range in {fixture_name}")
    exp = case["expected_range"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    exp_low = exp["quantity_low_tco2e"]
    exp_high = exp["quantity_high_tco2e"]

    if exp_low is None:
        # Peat flag — assert no tonnage (ADR-0013)
        assert estimate.quantity_low_tco2e is None, (
            f"{fixture_name}: peat must have quantity_low_tco2e=None, "
            f"got {estimate.quantity_low_tco2e}"
        )
        assert estimate.quantity_high_tco2e is None, (
            f"{fixture_name}: peat must have quantity_high_tco2e=None, "
            f"got {estimate.quantity_high_tco2e}"
        )
    else:
        # Non-peat — assert exact frozen range
        assert estimate.quantity_low_tco2e == exp_low, (
            f"{fixture_name}: quantity_low_tco2e expected {exp_low:,.0f}, "
            f"got {estimate.quantity_low_tco2e:,.0f}"
        )
        assert estimate.quantity_high_tco2e == exp_high, (
            f"{fixture_name}: quantity_high_tco2e expected {exp_high:,.0f}, "
            f"got {estimate.quantity_high_tco2e:,.0f}"
        )
        assert estimate.quantity_low_tco2e < estimate.quantity_high_tco2e, (
            "INVARIANT VIOLATION (ADR-0009): non-peat estimate must be a range"
        )

    assert "Tier 1" in estimate.uncertainty, (
        f"{fixture_name}: IPCC Tier 1 label missing from uncertainty band"
    )


@pytest.mark.parametrize("fixture_name", RANGE_FIXTURES)
def test_uncertainty_contains_ipcc_tier(fixture_name: str):
    """ADR-0009: uncertainty band must cite an IPCC Tier label (and baseline for non-peat)."""
    case = _load(fixture_name)
    if "expected_range" not in case:
        pytest.skip(f"No expected_range in {fixture_name}")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    assert "Tier 1" in estimate.uncertainty, (
        f"IPCC Tier label missing from uncertainty_band in {fixture_name}"
    )
    # Peat flag uncertainty uses "baseline" via the regulatory-surplus explanation
    assert "baseline" in estimate.uncertainty.lower() or "dominant uncertainty" in estimate.uncertainty.lower(), (
        f"Dominant uncertainty (baseline) not mentioned in uncertainty_band for {fixture_name}"
    )


# ── WO-AUTOROUTE-002: peat flag tests ────────────────────────────────────────

PEAT_FLAG_FIXTURES = [
    "WO003_routing_PEAT.json",
    "WO004_SMPP_peat_flag.json",
]


@pytest.mark.parametrize("fixture_name", PEAT_FLAG_FIXTURES)
def test_peat_flag_no_tonnage(fixture_name: str):
    """ADR-0013 invariant: peat must NEVER emit a tonnage — quantity_*=None by construction."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0013): peat must have quantity_low_tco2e=None "
        f"(got {estimate.quantity_low_tco2e} for {fixture_name})"
    )
    assert estimate.quantity_high_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0013): peat must have quantity_high_tco2e=None "
        f"(got {estimate.quantity_high_tco2e} for {fixture_name})"
    )


@pytest.mark.parametrize("fixture_name", PEAT_FLAG_FIXTURES)
def test_peat_flag_status_is_flag(fixture_name: str):
    """ADR-0013: peat_additionality_status must start with 'flag' for all peat concessions."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.classification is not None, (
        f"{fixture_name}: peat estimate must have classification"
    )
    assert len(estimate.classification.strata) >= 1
    peat_strata = [s for s in estimate.classification.strata if s.soil_type == "peat"]
    assert peat_strata, f"{fixture_name}: no peat stratum in classification"
    stratum = peat_strata[0]
    assert stratum.legal_overlay is not None, "peat stratum must have legal_overlay"
    status = stratum.legal_overlay.peat_additionality_status
    assert "flag" in status, (
        f"INVARIANT VIOLATION (ADR-0013): peat_additionality_status must contain 'flag', "
        f"got: {status!r}"
    )


@pytest.mark.parametrize("fixture_name", PEAT_FLAG_FIXTURES)
def test_peat_flag_never_hard_no(fixture_name: str):
    """ADR-0013 fail-safe: peat routes to 'flagged', NEVER 'hard_no' (don't auto-exclude SMPP class)."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.eligibility.verdict != "hard_no", (
        f"INVARIANT VIOLATION (ADR-0013): peat concession must never be 'hard_no' — "
        f"valid restoration/WRC pathway may exist (e.g. VCS1899 class). "
        f"Got verdict={estimate.eligibility.verdict!r} for {fixture_name}"
    )


@pytest.mark.parametrize("fixture_name", PEAT_FLAG_FIXTURES)
def test_peat_stratum_validator_enforced(fixture_name: str):
    """Pydantic validator on Stratum prevents peat tonnage by construction."""
    from core.contracts import Stratum
    import pytest as _pytest
    with _pytest.raises(Exception):
        Stratum(
            stratum_id="peat_bad",
            area_ha=10_000.0,
            soil_type="peat",
            quantity_low_tco2e=1_000_000.0,   # must raise — peat cannot have a tonnage
            quantity_high_tco2e=2_000_000.0,
        )


@pytest.mark.parametrize("fixture_name", PEAT_FLAG_FIXTURES)
def test_peat_overlays_independent(fixture_name: str):
    """ADR-0013: the two overlays A and B are always evaluated independently — not collapsed."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.classification is not None
    peat_strata = [s for s in estimate.classification.strata if s.soil_type == "peat"]
    stratum = peat_strata[0]
    lor = stratum.legal_overlay
    assert lor is not None
    # Verify the two overlays are separate fields (never collapsed to one bool)
    assert hasattr(lor, "overlay_a_khg"), "Overlay A must be a separate field"
    assert hasattr(lor, "overlay_b_pippib"), "Overlay B must be a separate field"
    # Each is an OverlayIntersection — can independently be True, False, or None
    from core.contracts import OverlayIntersection
    assert isinstance(lor.overlay_a_khg, OverlayIntersection)
    assert isinstance(lor.overlay_b_pippib, OverlayIntersection)


# ── WO-AUTOROUTE-003: forest-presence gate tests ──────────────────────────

FOREST_GATE_FIXTURES = ["WO005_HTI_cleared.json"]


@pytest.mark.parametrize("fixture_name", FOREST_GATE_FIXTURES)
def test_forest_gate_fail_no_number(fixture_name: str):
    """ADR-0013-auto-routing: cleared land must NEVER emit a tonnage — quantity_*=None."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0013-auto-routing): cleared land must have "
        f"quantity_low_tco2e=None (got {estimate.quantity_low_tco2e} for {fixture_name})"
    )
    assert estimate.quantity_high_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0013-auto-routing): cleared land must have "
        f"quantity_high_tco2e=None (got {estimate.quantity_high_tco2e} for {fixture_name})"
    )


@pytest.mark.parametrize("fixture_name", FOREST_GATE_FIXTURES)
def test_forest_gate_fail_flagged_not_hard_no(fixture_name: str):
    """ADR-0013-auto-routing: cleared land → 'flagged', never 'hard_no' (restoration path may exist)."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.eligibility.verdict == "flagged", (
        f"{fixture_name}: expected 'flagged' for cleared land, "
        f"got {estimate.eligibility.verdict!r}"
    )
    assert estimate.eligibility.verdict != "hard_no", (
        f"INVARIANT VIOLATION: cleared land must never be hard_no "
        f"(reforestation pathway may exist). Got {estimate.eligibility.verdict!r}"
    )


@pytest.mark.parametrize("fixture_name", FOREST_GATE_FIXTURES)
def test_forest_gate_condition_cleared(fixture_name: str):
    """ADR-0013-auto-routing: classification must record forest_gate condition='cleared'."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.classification is not None, (
        f"{fixture_name}: cleared case must have classification"
    )
    strata = estimate.classification.strata
    assert len(strata) >= 1
    fg = strata[0].forest_gate
    assert fg is not None, f"{fixture_name}: stratum must have forest_gate"
    assert fg.gate_result == "fail", (
        f"{fixture_name}: expected gate_result='fail', got {fg.gate_result!r}"
    )
    assert fg.condition == "cleared", (
        f"{fixture_name}: expected condition='cleared', got {fg.condition!r}"
    )


@pytest.mark.parametrize("fixture_name", FOREST_GATE_FIXTURES)
def test_forest_gate_reason_in_eligibility(fixture_name: str):
    """ADR-0013-auto-routing: forest gate fail reason must appear in eligibility reasons."""
    case = _load(fixture_name)
    exp = case["expected_forest_gate"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    reason_text = " ".join(estimate.eligibility.reasons).lower()
    assert exp["forest_gate_reason_contains"].lower() in reason_text, (
        f"{fixture_name}: expected reason to contain "
        f"{exp['forest_gate_reason_contains']!r} in {estimate.eligibility.reasons}"
    )


def test_existing_hti_eligible_unchanged_after_forest_gate():
    """Regression: forest gate pass must not change existing HTI eligible numbers."""
    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    # Forest gate should pass (baseline_cover=70.7%, JRC degraded → light_degradation)
    assert estimate.classification is not None
    fg = estimate.classification.strata[0].forest_gate
    assert fg is not None
    assert fg.gate_result == "pass", (
        f"Forest gate should pass for existing HTI eligible fixture, got {fg.gate_result!r}. "
        "This means the forest gate is incorrectly blocking the number."
    )
    # Numbers unchanged
    exp = case["expected_range"]
    assert estimate.quantity_low_tco2e == exp["quantity_low_tco2e"], (
        f"REGRESSION: HTI eligible quantity_low changed after forest gate wiring. "
        f"Expected {exp['quantity_low_tco2e']:,.0f}, got {estimate.quantity_low_tco2e:,.0f}"
    )
    assert estimate.quantity_high_tco2e == exp["quantity_high_tco2e"], (
        f"REGRESSION: HTI eligible quantity_high changed after forest gate wiring. "
        f"Expected {exp['quantity_high_tco2e']:,.0f}, got {estimate.quantity_high_tco2e:,.0f}"
    )
