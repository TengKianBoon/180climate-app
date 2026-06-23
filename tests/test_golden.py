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
def test_biomass_is_real_ipcc_value(fixture_name: str):
    """Acceptance (WO-CARBON-001 / WO-CARBON-003): biomass_tco2_per_ha uses real IPCC 2006 values.

    Forest-type-aware thresholds (IPCC 2006 Table 4.7 SE-Asia):
      Non-peat projects: ≥500 tCO2/ha (lowland moist = 657.1; old stub range was 150–250)
      PEAT projects:     ≥350 tCO2/ha (peat_swamp = 390.6 tCO2/ha for AGB+BGB)
    """
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    is_peat = inp.project_type == "PEAT"
    threshold = 350.0 if is_peat else 500.0
    assert forest.biomass_tco2_per_ha >= threshold, (
        f"biomass_tco2_per_ha={forest.biomass_tco2_per_ha} is below IPCC 2006 SE-Asia threshold "
        f"({'peat_swamp ≥350' if is_peat else 'lowland moist ≥500'}) for {fixture_name}"
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

    These values are pinned for Gate M review. If the formula changes, regenerate with:
      python -c "from engines.carbon.engine import ...; print(estimate.quantity_low_tco2e)"
    and update the fixture's expected_range block.
    """
    case = _load(fixture_name)
    if "expected_range" not in case:
        pytest.skip(f"No expected_range in {fixture_name}")
    exp = case["expected_range"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e == exp["quantity_low_tco2e"], (
        f"{fixture_name}: quantity_low_tco2e expected {exp['quantity_low_tco2e']:,.0f}, "
        f"got {estimate.quantity_low_tco2e:,.0f}"
    )
    assert estimate.quantity_high_tco2e == exp["quantity_high_tco2e"], (
        f"{fixture_name}: quantity_high_tco2e expected {exp['quantity_high_tco2e']:,.0f}, "
        f"got {estimate.quantity_high_tco2e:,.0f}"
    )
    assert estimate.quantity_low_tco2e < estimate.quantity_high_tco2e, (
        "INVARIANT VIOLATION (ADR-0009): estimate must be a range, not a single value"
    )
    assert "Tier 1" in estimate.uncertainty, (
        f"{fixture_name}: IPCC Tier 1 label missing from uncertainty band"
    )


@pytest.mark.parametrize("fixture_name", RANGE_FIXTURES)
def test_uncertainty_contains_ipcc_tier(fixture_name: str):
    """ADR-0009: uncertainty band must cite an IPCC Tier label."""
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
    assert "baseline" in estimate.uncertainty.lower() or "dominant uncertainty" in estimate.uncertainty.lower(), (
        f"Dominant uncertainty (baseline) not mentioned in uncertainty_band for {fixture_name}"
    )
