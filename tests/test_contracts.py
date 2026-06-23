"""Placeholder test: verify core/contracts imports cleanly and config defaults are correct."""
from core.contracts import (
    CarbonInput, EligibilityResult, MethodologyRoute, CarbonEstimate,
    EUDRInput, PlotVerdict, EUDRVerdict, LeadCapture, CarbonGates, EUDRConfig,
    ContactInfo, GeoInput, GateResult, ForestData, QualityFactors,
    Plot, ChecklistItem, NarrativeRequest, NarrativeResult,
)


def test_contracts_importable():
    """All contract classes import without error."""
    assert CarbonGates is not None
    assert EUDRConfig is not None


def test_carbon_gates_defaults():
    gates = CarbonGates()
    assert gates.min_area_ha == 20_000
    assert gates.min_years_remaining == 5
    assert "HTI" in gates.valid_permit_types
    assert "HA" in gates.valid_permit_types


def test_eudr_config_defaults():
    config = EUDRConfig()
    assert config.cutoff_date == "2020-12-31"
    assert config.operator_deadline == "2026-12-30"
    assert config.sme_deadline == "2027-06-30"
    assert config.as_of == "2026-06"


def test_methodology_route_additionality_default():
    route = MethodologyRoute(
        baseline_class="planned_clearfell",
        verra_family="APD (VM0009/legacy — advisor-confirm)",
        cited_methods=["VM0009"],
        is_planned=True,
    )
    assert route.additionality_basis == "legal harvest right foregone"
    assert route.is_planned is True


def test_carbon_estimate_is_range():
    """CarbonEstimate must carry both low and high — never a single number."""
    contact = ContactInfo(name="Test", email="test@example.com")
    geo = GeoInput(fmt="coords", payload="-0.5 117.5")
    eligibility = EligibilityResult(
        gates={"permit_type": GateResult(status="pass", detail="HTI valid")},
        verdict="eligible",
        reasons=[],
    )
    route = MethodologyRoute(
        baseline_class="planned_clearfell",
        verra_family="APD (VM0009/legacy — advisor-confirm)",
        cited_methods=["VM0009"],
        is_planned=True,
    )
    forest = ForestData(
        annual_loss_ha={2021: 500.0, 2022: 600.0},
        baseline_cover_pct=85.0,
        loss_after_2020_ha=1100.0,
        data_sources=["GFW/Hansen"],
        uncertainty_band="±20% — free satellite, Tier 1 screening",
    )
    quality = QualityFactors(
        additionality="high — legal harvest right foregone",
        permanence="medium",
        leakage="low",
        methodology_fit="APD — planned clearfell foregone",
    )
    estimate = CarbonEstimate(
        eligibility=eligibility,
        methodology=route,
        forest=forest,
        quantity_low_tco2e=500_000.0,
        quantity_high_tco2e=750_000.0,
        uncertainty="±20%",
        quality=quality,
    )
    assert estimate.quantity_low_tco2e < estimate.quantity_high_tco2e, (
        "CarbonEstimate must always be a range — never a single false-precise number."
    )
