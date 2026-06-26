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
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


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


# ── WO-AUTOROUTE-004: classifier exclusion + mixed stratification ─────────────

def test_number_path_deterministic_classifier_excluded():
    """Number path is classifier-free: engine.py must not import from classifier/.

    Asserts two things:
    1. engines/carbon/engine.py source does not contain 'classifier' (structural)
    2. run_carbon_engine() is deterministic (same input → same output twice)
    """
    engine_src = (
        Path(__file__).parent.parent / "engines" / "carbon" / "engine.py"
    ).read_text(encoding="utf-8")
    # Check for import statements only — the word "classifier" may appear in docstrings/comments
    assert "from classifier" not in engine_src, (
        "INVARIANT VIOLATION (ADR-0013-auto-routing): engine.py must not import "
        "from classifier/ — the number/verdict path must remain deterministic."
    )
    assert "import classifier" not in engine_src, (
        "INVARIANT VIOLATION (ADR-0013-auto-routing): engine.py must not import "
        "classifier — the number/verdict path must remain deterministic."
    )

    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    b = parse_geo(inp.geo)
    f = query_forest_data(b)
    e1 = run_carbon_engine(inp, b, f)
    e2 = run_carbon_engine(inp, b, f)
    assert e1.quantity_low_tco2e == e2.quantity_low_tco2e, (
        "Determinism violation: quantity_low differs between runs"
    )
    assert e1.quantity_high_tco2e == e2.quantity_high_tco2e, (
        "Determinism violation: quantity_high differs between runs"
    )
    assert e1.eligibility.verdict == e2.eligibility.verdict, (
        "Determinism violation: verdict differs between runs"
    )


MIXED_FIXTURES = ["WO006_mixed_concession.json"]


@pytest.mark.parametrize("fixture_name", MIXED_FIXTURES)
def test_mixed_stratification_peat_flag_mineral_number(fixture_name: str):
    """ADR-0013-auto-routing: mixed concession → peat stratum flag+no-number; mineral has range."""
    from engines.carbon.engine import run_mixed_stratification

    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_mixed_stratification(inp, boundary, forest)
    exp = case["expected_mixed"]

    assert estimate.classification is not None, "Mixed concession must have classification"
    assert estimate.classification.dominant_soil == exp["dominant_soil"], (
        f"Expected dominant_soil={exp['dominant_soil']!r}, got {estimate.classification.dominant_soil!r}"
    )
    strata = estimate.classification.strata
    assert len(strata) == 2, f"Expected 2 strata for mixed concession, got {len(strata)}"

    peat_s = next((s for s in strata if s.soil_type == "peat"), None)
    mineral_s = next((s for s in strata if s.soil_type == "mineral"), None)
    assert peat_s is not None, "No peat stratum found in mixed classification"
    assert mineral_s is not None, "No mineral stratum found in mixed classification"

    assert peat_s.quantity_low_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0013): peat stratum must have quantity_low=None, "
        f"got {peat_s.quantity_low_tco2e}"
    )
    assert peat_s.quantity_high_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0013): peat stratum must have quantity_high=None, "
        f"got {peat_s.quantity_high_tco2e}"
    )
    assert peat_s.eligibility_verdict == "flagged"

    if exp.get("mineral_has_range"):
        assert mineral_s.quantity_low_tco2e is not None, (
            "Mineral stratum must have a range for this mixed fixture"
        )
        assert mineral_s.quantity_high_tco2e is not None
        assert mineral_s.quantity_low_tco2e < mineral_s.quantity_high_tco2e, (
            "Mineral stratum range must be quantity_low < quantity_high"
        )
        assert estimate.quantity_low_tco2e == mineral_s.quantity_low_tco2e, (
            "CarbonEstimate.quantity_low must match mineral stratum quantity_low"
        )

    assert estimate.eligibility.verdict == exp["overall_verdict"], (
        f"Expected overall verdict={exp['overall_verdict']!r}, "
        f"got {estimate.eligibility.verdict!r}"
    )


@pytest.mark.parametrize("fixture_name", MIXED_FIXTURES)
def test_mixed_stratum_areas_sum_to_boundary(fixture_name: str):
    """ADR-0013: sum of stratum areas must equal the total boundary area (no double-counting)."""
    from engines.carbon.engine import run_mixed_stratification

    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_mixed_stratification(inp, boundary, forest)

    if estimate.classification and estimate.classification.dominant_soil == "mixed":
        total_stratum = sum(s.area_ha for s in estimate.classification.strata)
        assert abs(total_stratum - boundary.area_ha) < 1.0, (
            f"Stratum areas {total_stratum:,.1f} ha don't sum to boundary {boundary.area_ha:,.1f} ha "
            f"(each hectare must be in exactly one stratum — ADR-0013)"
        )


# ── WO-AUTOROUTE-005: peat overlay combos ────────────────────────────────────

PEAT_OVERLAY_FIXTURES = [
    "WO007_PEAT_Aonly.json",
    "WO007_PEAT_Bonly.json",
    "WO007_PEAT_neither.json",
]


@pytest.mark.parametrize("fixture_name", PEAT_OVERLAY_FIXTURES)
def test_peat_overlay_combo_no_tonnage(fixture_name: str):
    """All peat overlay combos must produce no tonnage (ADR-0013)."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    exp = case["expected_peat_flag"]
    assert estimate.quantity_low_tco2e is None, (
        f"INVARIANT (ADR-0013): peat must have quantity_low=None for {fixture_name}"
    )
    assert estimate.quantity_high_tco2e is None


@pytest.mark.parametrize("fixture_name", PEAT_OVERLAY_FIXTURES)
def test_peat_overlay_combo_status_matches(fixture_name: str):
    """Each overlay combo produces the correct peat_additionality_status text."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    exp = case["expected_peat_flag"]

    peat_strata = [s for s in estimate.classification.strata if s.soil_type == "peat"]
    assert peat_strata, f"{fixture_name}: no peat stratum"
    status = peat_strata[0].legal_overlay.peat_additionality_status
    assert exp["peat_additionality_status_contains"].lower() in status.lower(), (
        f"{fixture_name}: expected status to contain {exp['peat_additionality_status_contains']!r}, "
        f"got {status!r}"
    )


@pytest.mark.parametrize("fixture_name", PEAT_OVERLAY_FIXTURES)
def test_peat_overlay_combo_overlays_independent(fixture_name: str):
    """Each overlay combo stores A and B independently (not collapsed to one bool)."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    exp = case["expected_peat_flag"]

    peat_strata = [s for s in estimate.classification.strata if s.soil_type == "peat"]
    lor = peat_strata[0].legal_overlay
    if exp["overlay_a_khg_intersects"] is not None:
        assert lor.overlay_a_khg.intersects == exp["overlay_a_khg_intersects"], (
            f"{fixture_name}: KHG expected {exp['overlay_a_khg_intersects']}, "
            f"got {lor.overlay_a_khg.intersects}"
        )
    if exp["overlay_b_pippib_intersects"] is not None:
        assert lor.overlay_b_pippib.intersects == exp["overlay_b_pippib_intersects"], (
            f"{fixture_name}: PIPPIB expected {exp['overlay_b_pippib_intersects']}, "
            f"got {lor.overlay_b_pippib.intersects}"
        )


@pytest.mark.parametrize("fixture_name", PEAT_OVERLAY_FIXTURES)
def test_peat_overlay_combo_never_hard_no(fixture_name: str):
    """All peat combos must be 'flagged', never 'hard_no'."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    assert estimate.eligibility.verdict != "hard_no", (
        f"INVARIANT (ADR-0013): peat must never be hard_no (got hard_no for {fixture_name})"
    )
    assert estimate.eligibility.verdict == "flagged"


# ── WO-AUTOROUTE-005: forest gate variants ────────────────────────────────────

FOREST_GATE_VARIANT_FIXTURES = [
    "WO008_forest_intact.json",
    "WO008_forest_heavy.json",
]


@pytest.mark.parametrize("fixture_name", FOREST_GATE_VARIANT_FIXTURES)
def test_forest_gate_condition_and_result(fixture_name: str):
    """Forest gate variants: condition and gate_result must match expectations."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    exp = case["expected_forest_gate"]

    assert estimate.classification is not None
    fg = estimate.classification.strata[0].forest_gate
    assert fg is not None, f"{fixture_name}: no forest_gate on stratum"
    assert fg.condition == exp["forest_condition"], (
        f"{fixture_name}: expected condition={exp['forest_condition']!r}, got {fg.condition!r}"
    )
    assert fg.gate_result == exp["forest_gate_result"], (
        f"{fixture_name}: expected gate_result={exp['forest_gate_result']!r}, got {fg.gate_result!r}"
    )


@pytest.mark.parametrize("fixture_name", FOREST_GATE_VARIANT_FIXTURES)
def test_forest_gate_variant_has_number(fixture_name: str):
    """Forest gate pass/flag variants (intact and heavy): number IS computed (gate not fail)."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    exp = case["expected_forest_gate"]

    if exp.get("quantity_low_tco2e_not_null"):
        assert estimate.quantity_low_tco2e is not None, (
            f"{fixture_name}: expected quantity_low_tco2e to be computed (forest gate "
            f"{exp['forest_gate_result']!r} does not block number)"
        )
        assert estimate.quantity_high_tco2e is not None
        assert estimate.quantity_low_tco2e < estimate.quantity_high_tco2e


@pytest.mark.parametrize("fixture_name", FOREST_GATE_VARIANT_FIXTURES)
def test_forest_gate_variant_eligibility(fixture_name: str):
    """Forest gate intact/heavy: eligibility verdict matches expected."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    exp = case["expected_forest_gate"]
    assert estimate.eligibility.verdict == exp["eligibility_verdict"], (
        f"{fixture_name}: expected verdict={exp['eligibility_verdict']!r}, "
        f"got {estimate.eligibility.verdict!r}"
    )


# ── WO-AUTOROUTE-005: full invariant sweep across all REDD/IFM golden fixtures ─

ALL_REDD_FIXTURES = [
    "WO002_HTI_eligible.json",
    "WO002_HA_eligible.json",
    "WO002_HTI_flag_years.json",
    "WO002_HTI_fail_area.json",
    "WO002_HTI_flag_outside.json",
    "WO005_HTI_cleared.json",
    "WO008_forest_intact.json",
    "WO008_forest_heavy.json",
]

ALL_PEAT_FIXTURES = [
    "WO003_routing_PEAT.json",
    "WO004_SMPP_peat_flag.json",
    "WO007_PEAT_Aonly.json",
    "WO007_PEAT_Bonly.json",
    "WO007_PEAT_neither.json",
]


@pytest.mark.parametrize("fixture_name", ALL_PEAT_FIXTURES)
def test_all_peat_no_forbidden_phrases(fixture_name: str):
    """Invariant: no forbidden phrases in any peat estimate output."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    dump = estimate.model_dump_json()
    for pattern in _FORBIDDEN_PHRASES:
        assert not re.search(pattern, dump, re.IGNORECASE), (
            f"INVARIANT VIOLATION (ADR-0009): forbidden phrase {pattern!r} in {fixture_name}"
        )


@pytest.mark.parametrize("fixture_name", ALL_REDD_FIXTURES)
def test_all_redd_no_forbidden_phrases(fixture_name: str):
    """Invariant: no forbidden phrases in any REDD/IFM estimate output."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    dump = estimate.model_dump_json()
    for pattern in _FORBIDDEN_PHRASES:
        assert not re.search(pattern, dump, re.IGNORECASE), (
            f"INVARIANT VIOLATION (ADR-0009): forbidden phrase {pattern!r} in {fixture_name}"
        )


@pytest.mark.parametrize("fixture_name", ALL_REDD_FIXTURES + ALL_PEAT_FIXTURES)
def test_all_fixtures_is_planned_and_additionality_correct(fixture_name: str):
    """Invariant (ADR-0001): is_planned=True and additionality_basis='legal harvest right foregone'."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    assert estimate.methodology.is_planned is True, (
        f"INVARIANT VIOLATION (ADR-0001): is_planned must be True for {fixture_name}"
    )
    assert estimate.methodology.additionality_basis == "legal harvest right foregone", (
        f"INVARIANT VIOLATION (ADR-0001): additionality_basis wrong for {fixture_name}"
    )


@pytest.mark.parametrize("fixture_name", ALL_PEAT_FIXTURES)
def test_all_peat_never_vm0027_vm0048_vm0007(fixture_name: str):
    """Invariant (ADR-0012): no forbidden methodology names in any peat output."""
    FORBIDDEN_METHODS = ["VM0027", "VM0048", "VM0007"]
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    for bad in FORBIDDEN_METHODS:
        assert bad not in estimate.methodology.verra_family, (
            f"INVARIANT VIOLATION (ADR-0012): {bad!r} must NEVER appear in verra_family "
            f"(got {estimate.methodology.verra_family!r} for {fixture_name})"
        )
        for m in estimate.methodology.cited_methods:
            assert bad not in m, (
                f"INVARIANT VIOLATION (ADR-0001/0012): {bad!r} in cited_methods for {fixture_name}"
            )


@pytest.mark.parametrize("fixture_name", ALL_REDD_FIXTURES)
def test_all_redd_never_vm0048_vm0007(fixture_name: str):
    """Invariant (ADR-0001): VM0048 and VM0007 must never appear in REDD/IFM output."""
    FORBIDDEN_METHODS = ["VM0048", "VM0007"]
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    for bad in FORBIDDEN_METHODS:
        assert bad not in estimate.methodology.verra_family, (
            f"INVARIANT VIOLATION (ADR-0001): {bad!r} in verra_family for {fixture_name}"
        )
        for m in estimate.methodology.cited_methods:
            assert bad not in m, (
                f"INVARIANT VIOLATION (ADR-0001): {bad!r} in cited_methods for {fixture_name}"
            )


# ── WO-METHFIX-001 / ADR-0015-C1: Plantation gate tests ──────────────────────

PLANTATION_FIXTURES = ["WO009_HTI_plantation.json"]


@pytest.mark.parametrize("fixture_name", PLANTATION_FIXTURES)
def test_plantation_gate_no_number(fixture_name: str):
    """ADR-0015-C1: established plantation must NEVER emit an avoided-deforestation number."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0015-C1): plantation must have quantity_low_tco2e=None "
        f"(got {estimate.quantity_low_tco2e} for {fixture_name})"
    )
    assert estimate.quantity_high_tco2e is None, (
        f"INVARIANT VIOLATION (ADR-0015-C1): plantation must have quantity_high_tco2e=None "
        f"(got {estimate.quantity_high_tco2e} for {fixture_name})"
    )


@pytest.mark.parametrize("fixture_name", PLANTATION_FIXTURES)
def test_plantation_gate_verdict_flagged(fixture_name: str):
    """ADR-0015-C1: plantation → 'flagged', never 'eligible' and never 'hard_no'."""
    case = _load(fixture_name)
    exp = case["expected_plantation"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.eligibility.verdict == exp["eligibility_verdict"], (
        f"{fixture_name}: expected verdict={exp['eligibility_verdict']!r}, "
        f"got {estimate.eligibility.verdict!r}"
    )
    assert estimate.eligibility.verdict != "hard_no", (
        f"INVARIANT (ADR-0015-C1): plantation must never be 'hard_no' — "
        f"no APD number is a different outcome from a hard exclusion."
    )


@pytest.mark.parametrize("fixture_name", PLANTATION_FIXTURES)
def test_plantation_gate_reason_contains_plantation(fixture_name: str):
    """ADR-0015-C1: eligibility reasons must mention 'plantation' for the plantation gate."""
    case = _load(fixture_name)
    exp = case["expected_plantation"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    reason_text = " ".join(estimate.eligibility.reasons).lower()
    assert exp["plantation_reason_contains"].lower() in reason_text, (
        f"{fixture_name}: expected reasons to contain {exp['plantation_reason_contains']!r}, "
        f"got reasons: {estimate.eligibility.reasons}"
    )


@pytest.mark.parametrize("fixture_name", PLANTATION_FIXTURES)
def test_plantation_gate_forest_origin_set(fixture_name: str):
    """ADR-0015-C1: ForestData.forest_origin must be 'plantation' after engine run."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.forest.forest_origin == "plantation", (
        f"{fixture_name}: expected forest_origin='plantation', "
        f"got {estimate.forest.forest_origin!r}"
    )


@pytest.mark.parametrize("fixture_name", PLANTATION_FIXTURES)
def test_plantation_gate_no_forbidden_phrases(fixture_name: str):
    """ADR-0009: no forbidden phrases in plantation flag output."""
    case = _load(fixture_name)
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    dump = estimate.model_dump_json()
    for pattern in _FORBIDDEN_PHRASES:
        assert not re.search(pattern, dump, re.IGNORECASE), (
            f"INVARIANT VIOLATION (ADR-0009): forbidden phrase {pattern!r} "
            f"in plantation fixture output for {fixture_name}"
        )


# ── WO-METHFIX-001 / ADR-0015-C2: IFM estimate formula tests ─────────────────

def test_ha_eligible_uses_ifm_basis():
    """ADR-0015-C2: HA estimate must use IFM logging basis — methodology.baseline_class='ifm_selective_logging'."""
    case = _load("WO002_HA_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.methodology.baseline_class == "ifm_selective_logging", (
        f"ADR-0015-C2: HA must use IFM basis (baseline_class='ifm_selective_logging'), "
        f"got {estimate.methodology.baseline_class!r}"
    )


def test_hti_eligible_uses_redd_not_ifm():
    """ADR-0015-C2: HTI must still use APD (REDD) basis — baseline_class='planned_clearfell'."""
    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.methodology.baseline_class == "planned_clearfell", (
        f"HTI must use APD/REDD basis (planned_clearfell), "
        f"got {estimate.methodology.baseline_class!r}"
    )


def test_ha_ifm_uncertainty_contains_pearson():
    """ADR-0015-C2: IFM uncertainty string must cite Pearson et al. (2014) as EF source."""
    case = _load("WO002_HA_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert "Pearson" in estimate.uncertainty, (
        "ADR-0015-C2: IFM uncertainty must cite Pearson et al. (2014) as EF source. "
        f"Got: {estimate.uncertainty[:200]}"
    )
    assert "VM0010" in estimate.uncertainty, (
        "ADR-0015-C2: IFM uncertainty must mention VM0010 (selective-logging baseline). "
        f"Got: {estimate.uncertainty[:200]}"
    )
    assert "n_entries=1" in estimate.uncertainty, (
        "ADR-0015-C2: n_entries=1 must be stated in uncertainty (no multi-cycle multiplication). "
        f"Got: {estimate.uncertainty[:200]}"
    )


def test_ha_ifm_formula_reconciliation():
    """ADR-0015-C2 / ADR-0016-M1: IFM estimate reconciles to the documented derivation.

    Formula (M1 quadrature + separate buffer):
      harvested_area = 73,787 ha × min(1, 15/35) = 31,623 ha
      central = harvested_area × EF_central (~175.45 tCO2/ha using Pearson midpoints)
      sigma_IFM = sqrt(CV_intensity^2 + CV_TEF^2) ≈ 0.2149
      net_low = central × (1−sigma) × (1−buf_high); net_high = central × (1+sigma) × (1−buf_low)
    Frozen numbers: low=3,049,142; high=5,392,503 (ADR-0016-M1 re-baseline 2026-06-26).
    DO NOT assert 'smaller' — IFM may equal or exceed old REDD estimate.
    Assert formula basis (n_entries=1, no density×loss_rate).
    """
    case = _load("WO002_HA_eligible.json")
    exp = case["expected_range"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e == exp["quantity_low_tco2e"], (
        f"IFM low estimate mismatch: expected {exp['quantity_low_tco2e']:,.0f}, "
        f"got {estimate.quantity_low_tco2e:,.0f}"
    )
    assert estimate.quantity_high_tco2e == exp["quantity_high_tco2e"], (
        f"IFM high estimate mismatch: expected {exp['quantity_high_tco2e']:,.0f}, "
        f"got {estimate.quantity_high_tco2e:,.0f}"
    )
    # Assert range (ADR-0009)
    assert estimate.quantity_low_tco2e < estimate.quantity_high_tco2e, (
        "INVARIANT VIOLATION (ADR-0009): IFM estimate must be a range"
    )
    # Assert IFM basis — uncertainty should NOT mention 'density' (REDD formula) as the primary driver
    assert "Pearson" in estimate.uncertainty, (
        "IFM uncertainty must cite Pearson (logging-emissions basis, not density×loss_rate)"
    )


def test_natural_forest_hti_proceeds_to_number():
    """ADR-0015-C1: natural-forest HTI must NOT be blocked by plantation gate."""
    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e is not None, (
        "ADR-0015-C1: natural-forest HTI must produce a number (plantation gate must not fire)"
    )
    assert estimate.forest.forest_origin == "natural", (
        f"Expected forest_origin='natural' for WO002_HTI_eligible, "
        f"got {estimate.forest.forest_origin!r}"
    )


def test_natural_forest_ha_proceeds_to_number():
    """ADR-0015-C1: natural-forest HA must NOT be blocked by plantation gate."""
    case = _load("WO002_HA_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e is not None, (
        "ADR-0015-C1: natural-forest HA must produce a number (plantation gate must not fire)"
    )
    assert estimate.forest.forest_origin == "natural", (
        f"Expected forest_origin='natural' for WO002_HA_eligible, "
        f"got {estimate.forest.forest_origin!r}"
    )


# ── WO-METHFIX-002 / ADR-0016: M1 quadrature + M2 density-fallback gate ──────

def test_redd_uncertainty_uses_quadrature():
    """ADR-0016-M1: REDD uncertainty string must state 'in quadrature' (density SE + loss CV combined)."""
    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert "in quadrature" in estimate.uncertainty.lower(), (
        "ADR-0016-M1: REDD uncertainty must state 'in quadrature' (density SE + loss-rate CV). "
        f"Got: {estimate.uncertainty[:300]}"
    )


def test_redd_buffer_labelled_separately():
    """ADR-0016-M1: REDD uncertainty string must label VCS buffer as applied separately."""
    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    unc_lower = estimate.uncertainty.lower()
    assert "separately" in unc_lower or "separate" in unc_lower, (
        "ADR-0016-M1: VCS buffer must be labelled as applied separately in REDD uncertainty. "
        f"Got: {estimate.uncertainty[:300]}"
    )


def test_esa_cci_saturation_caveat_in_redd():
    """ADR-0016-M2: ESA CCI density label must state saturation caveat for ESA-CCI-sourced fixtures."""
    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert "saturation" in estimate.uncertainty.lower(), (
        "ADR-0016-M2: ESA CCI density label must state saturation caveat "
        "(underestimates AGB >~150–250 Mg/ha). "
        f"Got: {estimate.uncertainty[:300]}"
    )


def test_ipcc_default_loud_flag_in_uncertainty():
    """ADR-0016-M2: IPCC default density → 'DEFAULT DENSITY' must appear in uncertainty string."""
    case = _load("WO002_HTI_flag_outside.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert "DEFAULT DENSITY" in estimate.uncertainty, (
        "ADR-0016-M2: IPCC fallback density must emit 'DEFAULT DENSITY — HIGH UNCERTAINTY' "
        f"in uncertainty string. Got: {estimate.uncertainty[:300]}"
    )


def test_ipcc_default_verdict_flagged():
    """ADR-0016-M2: IPCC default density → verdict must be 'flagged' (loud flag changes eligible → flagged)."""
    case = _load("WO002_HTI_flag_outside.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.eligibility.verdict == "flagged", (
        "ADR-0016-M2: IPCC default density must change verdict to 'flagged'. "
        f"Got: {estimate.eligibility.verdict!r}"
    )


def test_no_biomass_no_number():
    """ADR-0016-M2: no credible biomass source → REDD estimate must be null (no number emitted)."""
    case = _load("WO010_REDD_no_biomass.json")
    exp = case["expected_no_biomass"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.quantity_low_tco2e is None, (
        f"ADR-0016-M2: no-biomass gate must produce quantity_low=None, "
        f"got {estimate.quantity_low_tco2e}"
    )
    assert estimate.quantity_high_tco2e is None, (
        f"ADR-0016-M2: no-biomass gate must produce quantity_high=None, "
        f"got {estimate.quantity_high_tco2e}"
    )


def test_no_biomass_verdict_flagged():
    """ADR-0016-M2: no credible biomass → verdict must be 'flagged'."""
    case = _load("WO010_REDD_no_biomass.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.eligibility.verdict == "flagged", (
        "ADR-0016-M2: no-biomass must produce verdict='flagged'. "
        f"Got: {estimate.eligibility.verdict!r}"
    )


def test_no_biomass_reason_contains():
    """ADR-0016-M2: no-biomass eligibility reasons must cite 'no credible biomass source'."""
    case = _load("WO010_REDD_no_biomass.json")
    exp = case["expected_no_biomass"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    reason_text = " ".join(estimate.eligibility.reasons).lower()
    assert exp["reason_contains"].lower() in reason_text, (
        f"ADR-0016-M2: expected reasons to contain {exp['reason_contains']!r}. "
        f"Got: {estimate.eligibility.reasons}"
    )


def test_no_biomass_uncertainty_label():
    """ADR-0016-M2: no-biomass uncertainty string must cite ADR-0016-M2."""
    case = _load("WO010_REDD_no_biomass.json")
    exp = case["expected_no_biomass"]
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert exp["uncertainty_contains"] in estimate.uncertainty, (
        f"ADR-0016-M2: uncertainty must contain {exp['uncertainty_contains']!r}. "
        f"Got: {estimate.uncertainty[:300]}"
    )


def test_ifm_uncertainty_uses_quadrature():
    """ADR-0016-M1: IFM uncertainty string must state 'in quadrature' (intensity CV + TEF CV combined)."""
    case = _load("WO002_HA_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert "in quadrature" in estimate.uncertainty.lower(), (
        "ADR-0016-M1: IFM uncertainty must state 'in quadrature'. "
        f"Got: {estimate.uncertainty[:300]}"
    )


def test_ifm_buffer_labelled_separately():
    """ADR-0016-M1: IFM uncertainty string must label VCS buffer as applied separately."""
    case = _load("WO002_HA_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    unc_lower = estimate.uncertainty.lower()
    assert "separately" in unc_lower or "separate" in unc_lower, (
        "ADR-0016-M1: VCS buffer must be labelled as applied separately in IFM uncertainty. "
        f"Got: {estimate.uncertainty[:300]}"
    )


# ── WO-DERIVE-001 / ADR-0014: derivation trace tests ─────────────────────────

def test_redd_derivation_reproduces_range():
    """ADR-0014 invariant: trace.net_low_tco2e == estimate.quantity_low_tco2e for REDD."""
    case = _load("WO002_HTI_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.derivation is not None, (
        "ADR-0014: REDD estimate must have derivation trace (not None)"
    )
    d = estimate.derivation
    assert d.basis == "redd", f"Expected basis='redd', got {d.basis!r}"
    assert d.net_low_tco2e == estimate.quantity_low_tco2e, (
        f"ADR-0014 INVARIANT: trace.net_low_tco2e ({d.net_low_tco2e:,.0f}) must equal "
        f"estimate.quantity_low_tco2e ({estimate.quantity_low_tco2e:,.0f})"
    )
    assert d.net_high_tco2e == estimate.quantity_high_tco2e, (
        f"ADR-0014 INVARIANT: trace.net_high_tco2e ({d.net_high_tco2e:,.0f}) must equal "
        f"estimate.quantity_high_tco2e ({estimate.quantity_high_tco2e:,.0f})"
    )
    # REDD-specific fields must be populated
    assert d.baseline_loss_rate_yr is not None, "REDD trace must have baseline_loss_rate_yr"
    assert d.carbon_density_tco2_ha is not None, "REDD trace must have carbon_density_tco2_ha"
    assert d.sigma_combined_pct is not None, "REDD trace must have sigma_combined_pct"
    assert d.central_tco2e is not None, "REDD trace must have central_tco2e"
    assert d.gross_low_tco2e <= d.gross_high_tco2e, "gross_low must <= gross_high (pre-buffer)"
    assert d.net_low_tco2e <= d.net_high_tco2e, "net_low must <= net_high"


def test_ifm_derivation_reproduces_range():
    """ADR-0014 invariant: trace.net_low_tco2e == estimate.quantity_low_tco2e for IFM."""
    case = _load("WO002_HA_eligible.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.derivation is not None, (
        "ADR-0014: IFM estimate must have derivation trace (not None)"
    )
    d = estimate.derivation
    assert d.basis == "ifm", f"Expected basis='ifm', got {d.basis!r}"
    assert d.net_low_tco2e == estimate.quantity_low_tco2e, (
        f"ADR-0014 INVARIANT: trace.net_low_tco2e ({d.net_low_tco2e:,.0f}) must equal "
        f"estimate.quantity_low_tco2e ({estimate.quantity_low_tco2e:,.0f})"
    )
    assert d.net_high_tco2e == estimate.quantity_high_tco2e, (
        f"ADR-0014 INVARIANT: trace.net_high_tco2e ({d.net_high_tco2e:,.0f}) must equal "
        f"estimate.quantity_high_tco2e ({estimate.quantity_high_tco2e:,.0f})"
    )
    # IFM-specific fields must be populated
    assert d.harvested_area_ha is not None, "IFM trace must have harvested_area_ha"
    assert d.ef_central_tco2_ha is not None, "IFM trace must have ef_central_tco2_ha"
    assert d.sigma_ifm_pct is not None, "IFM trace must have sigma_ifm_pct"
    assert d.central_tco2e is not None, "IFM trace must have central_tco2e"
    assert d.harvested_area_ha <= d.eligible_area_ha, (
        "harvested_area_ha must be <= eligible_area_ha (fraction of one TPTI cycle)"
    )


def test_peat_derivation_is_none():
    """ADR-0014 + ADR-0013: peat estimate must have derivation=None (no formula, no tonnage)."""
    case = _load("WO003_routing_PEAT.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.derivation is None, (
        f"ADR-0014 + ADR-0013: peat must have derivation=None (no formula, no tonnage). "
        f"Got derivation={estimate.derivation!r}"
    )


def test_plantation_derivation_is_none():
    """ADR-0014: plantation-flagged estimate must have derivation=None (no number asserted)."""
    case = _load("WO009_HTI_plantation.json")
    inp = _make_input(case["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    assert estimate.derivation is None, (
        f"ADR-0014: plantation flag must have derivation=None. Got {estimate.derivation!r}"
    )


def test_derivation_basis_matches_permit_type():
    """ADR-0014 consistency: basis='redd' for HTI, basis='ifm' for HA."""
    for fixture, expected_basis, permit in [
        ("WO002_HTI_eligible.json", "redd", "HTI"),
        ("WO002_HA_eligible.json", "ifm", "HA"),
    ]:
        case = _load(fixture)
        inp = _make_input(case["input"])
        boundary = parse_geo(inp.geo)
        forest = query_forest_data(boundary)
        estimate = run_carbon_engine(inp, boundary, forest)
        assert estimate.derivation is not None, f"{fixture}: derivation must not be None"
        assert estimate.derivation.basis == expected_basis, (
            f"{fixture}: expected basis={expected_basis!r} for {permit}, "
            f"got {estimate.derivation.basis!r}"
        )


def test_derivation_no_single_number_invariant():
    """ADR-0014 + ADR-0009: trace must always carry a range (net_low != net_high)."""
    for fixture in ["WO002_HTI_eligible.json", "WO002_HA_eligible.json"]:
        case = _load(fixture)
        inp = _make_input(case["input"])
        boundary = parse_geo(inp.geo)
        forest = query_forest_data(boundary)
        estimate = run_carbon_engine(inp, boundary, forest)
        d = estimate.derivation
        assert d is not None
        assert d.net_low_tco2e < d.net_high_tco2e, (
            f"ADR-0009/0014: derivation trace must carry a range "
            f"(net_low={d.net_low_tco2e:,.0f}, net_high={d.net_high_tco2e:,.0f}) for {fixture}"
        )
