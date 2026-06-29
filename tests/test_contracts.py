"""Placeholder test: verify core/contracts imports cleanly and config defaults are correct."""
from datetime import date

import pytest

from core.contracts import (
    CarbonInput, EligibilityResult, MethodologyRoute, CarbonEstimate,
    EUDRInput, PlotVerdict, EUDRVerdict, LeadCapture, CarbonGates, EUDRConfig,
    ContactInfo, GeoInput, GateResult, ForestData, QualityFactors,
    Plot, ChecklistItem, NarrativeRequest, NarrativeResult,
    # ADR-0013 new types (WO-AUTOROUTE-001)
    OverlayIntersection, LegalOverlayResult, ForestPresenceGate,
    Stratum, ProjectClassification,
    # ADR-0018 EUDR types (WO-EUDR-CONTRACTS-001)
    ReadinessItem, EUDR_BANNED_SUBSTRINGS,
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


# ──────────────────────────────────────────────────────────────────────────────
# ADR-0018 — EUDR contracts (WO-EUDR-CONTRACTS-001)
# Triage & DDS-prep screen, never a compliance verdict. Carbon contracts untouched.
# ──────────────────────────────────────────────────────────────────────────────

_CONTACT = ContactInfo(name="Exporter Co", email="ops@exporter.id")
_GEO = GeoInput(fmt="coords", payload="-0.5 117.5")


def _make_plot(plot_id: str = "P1", commodity: str = "palm") -> Plot:
    return Plot(plot_id=plot_id, geo=_GEO, commodity=commodity, geometry_type="polygon")


def _make_plot_verdict(plot_id: str, detection: str) -> PlotVerdict:
    """geometry_ok and plot_satellite_risk are computed from detection — not passed here."""
    return PlotVerdict(
        plot_id=plot_id,
        detection=detection,
        loss_after_2020_ha=0.0 if detection == "clear_in_screen" else 3.2,
        commodity="palm",
        datasets_version="Hansen v1.11; JRC GFC2020; RADD 2026-06",
        run_date=date(2026, 6, 29),
    )


def _make_eudr_verdict() -> EUDRVerdict:
    """A fully-populated verdict exercising every detection + risk value."""
    plots = [
        _make_plot_verdict("P1", "clear_in_screen"),
        _make_plot_verdict("P2", "loss_detected"),
        _make_plot_verdict("P3", "inconclusive"),
        _make_plot_verdict("P4", "geometry_invalid"),
    ]
    return EUDRVerdict(
        overall="review_needed",
        plots=plots,
        country_benchmark_risk="standard",
        legality_checklist=[
            ChecklistItem(item="SK IUP / HGU", status="present"),
            ChecklistItem(item="Plasma/community attestation", status="attest"),
        ],
        geolocation_pack={"type": "FeatureCollection", "features": []},
        readiness=[
            ReadinessItem(component="Geolocation polygons", status="complete"),
            ReadinessItem(component="Legality documents", status="incomplete",
                          note="Awaiting HGU scan"),
        ],
        applicable_deadline="2026-12-30",
        datasets_version="Hansen v1.11; JRC GFC2020; RADD 2026-06",
        run_date=date(2026, 6, 29),
    )


def test_eudr_input_role_commodity_and_country_risk():
    """EUDRInput carries the ADR-0018 role + commodity enums and country benchmark risk."""
    inp = EUDRInput(
        contact=_CONTACT,
        role="eu_first_placer",
        commodity="palm",
        plots=[_make_plot()],
    )
    assert inp.role == "eu_first_placer"
    assert inp.commodity == "palm"
    # Indonesia default
    assert inp.country_benchmark_risk == "standard"
    # New role vocabulary, not the old operator/trader stub
    with pytest.raises(Exception):
        EUDRInput(contact=_CONTACT, role="operator", commodity="palm", plots=[_make_plot()])


def test_plot_verdict_uses_detection_enum_not_bool():
    """PlotVerdict.detection replaced the deforestation_free bool (ADR-0018)."""
    pv = _make_plot_verdict("P1", "clear_in_screen")
    assert pv.detection == "clear_in_screen"
    # The boolean clearance field must be gone — no legal "deforestation-free" verdict.
    assert not hasattr(pv, "deforestation_free")
    # detection is a first-class 4-state enum
    for det in ("clear_in_screen", "loss_detected", "inconclusive", "geometry_invalid"):
        assert _make_plot_verdict("Px", det).detection == det
    # rejects anything outside the enum
    with pytest.raises(Exception):
        _make_plot_verdict("Pbad", "deforestation_free")


def test_eudr_readiness_is_categorical_no_numeric_score():
    """Readiness is a list of ✓/✗ components — no 0–100 readiness_score (ADR-0018)."""
    verdict = _make_eudr_verdict()
    assert not hasattr(verdict, "readiness_score")
    assert all(r.status in ("complete", "incomplete") for r in verdict.readiness)
    # No field on the model is named like a numeric score
    assert "readiness_score" not in EUDRVerdict.model_fields


def test_eudr_country_and_plot_risk_are_distinct_fields():
    """country_benchmark_risk and plot_satellite_risk are separate, never conflated (ADR-0018)."""
    verdict = _make_eudr_verdict()
    assert "country_benchmark_risk" in EUDRVerdict.model_fields
    # plot_satellite_risk is now a computed field (ADR-0018 micro-amendment)
    assert "plot_satellite_risk" in PlotVerdict.model_computed_fields
    assert "plot_satellite_risk" not in PlotVerdict.model_fields
    # Country risk on verdict; satellite risk derived per-plot — different axes.
    assert "plot_satellite_risk" not in EUDRVerdict.model_fields
    assert "country_benchmark_risk" not in PlotVerdict.model_fields
    assert verdict.country_benchmark_risk == "standard"
    assert verdict.plots[1].plot_satellite_risk == "high"


def test_eudr_provenance_stamp_present():
    """Every PlotVerdict + EUDRVerdict carries datasets_version + run_date (ADR-0018)."""
    verdict = _make_eudr_verdict()
    assert verdict.datasets_version
    assert isinstance(verdict.run_date, date)
    for pv in verdict.plots:
        assert pv.datasets_version
        assert isinstance(pv.run_date, date)


# ── ADR-0018 micro-amendments: computed geometry_ok + plot_satellite_risk ────────

def test_geometry_ok_is_computed_from_detection():
    """PlotVerdict.geometry_ok is a computed property derived from detection — not a stored field.
    Drift between geometry_ok and detection is structurally impossible (ADR-0018 micro-amendment)."""
    assert "geometry_ok" not in PlotVerdict.model_fields, (
        "geometry_ok must be a computed property, not a stored field — it cannot drift from detection."
    )
    assert "geometry_ok" in PlotVerdict.model_computed_fields
    for det in ("clear_in_screen", "loss_detected", "inconclusive"):
        pv = _make_plot_verdict("Px", det)
        assert pv.geometry_ok is True, f"Expected geometry_ok=True for detection={det!r}"
    pv_inv = _make_plot_verdict("Pi", "geometry_invalid")
    assert pv_inv.geometry_ok is False


def test_plot_satellite_risk_is_derived_from_detection():
    """PlotVerdict.plot_satellite_risk is a computed property — not a stored field.
    Derivation: clear_in_screen→low, loss_detected→high, inconclusive→inconclusive,
    geometry_invalid→inconclusive (ADR-0018 micro-amendment)."""
    assert "plot_satellite_risk" not in PlotVerdict.model_fields, (
        "plot_satellite_risk must be computed from detection — not stored (can't drift)."
    )
    assert "plot_satellite_risk" in PlotVerdict.model_computed_fields
    expected = {
        "clear_in_screen": "low",
        "loss_detected": "high",
        "inconclusive": "inconclusive",
        "geometry_invalid": "inconclusive",
    }
    for det, expected_risk in expected.items():
        pv = _make_plot_verdict("Px", det)
        assert pv.plot_satellite_risk == expected_risk, (
            f"detection={det!r} should yield plot_satellite_risk={expected_risk!r}, "
            f"got {pv.plot_satellite_risk!r}"
        )


# ── Banned-string contract guard (mirrors the carbon contract-guard hook) ──────

def _find_banned(text: str) -> list[str]:
    """Return any banned EUDR legal-clearance substrings present in `text` (case-insensitive)."""
    low = text.lower()
    return [b for b in EUDR_BANNED_SUBSTRINGS if b.lower() in low]


def test_eudr_banned_strings_absent_from_serialized_output_and_schema():
    """No EUDR model's serialized output, enum, field name, default, or docstring may
    contain "compliant", "deforestation-free", "DDS-ready", or
    "due diligence statement ready" (ADR-0018)."""
    inp = EUDRInput(contact=_CONTACT, role="eu_first_placer",
                    commodity="manual_review", plots=[_make_plot()])
    verdict = _make_eudr_verdict()

    surfaces = [
        inp.model_dump_json(),
        verdict.model_dump_json(),
        # Schema captures every Literal enum value, field name, default, and class docstring.
        str(EUDRInput.model_json_schema()),
        str(Plot.model_json_schema()),
        str(PlotVerdict.model_json_schema()),
        str(EUDRVerdict.model_json_schema()),
        str(ReadinessItem.model_json_schema()),
    ]
    for surface in surfaces:
        hits = _find_banned(surface)
        assert not hits, f"Banned EUDR legal-clearance string(s) {hits} found in: {surface[:200]}"


def test_eudr_banned_string_guard_catches_a_violation():
    """Prove the guard actually fires: a deliberately-bad fixture that puts a banned
    phrase in a free-text field must be detected (the bad fixture lives only here)."""
    bad = ReadinessItem(
        component="DDS status",
        status="complete",
        note="This plot is deforestation-free and DDS-ready.",  # deliberately bad
    )
    hits = _find_banned(bad.model_dump_json())
    assert "deforestation-free" in hits and "dds-ready" in hits, (
        "Guard failed to detect banned legal-clearance phrasing — it would not protect output."
    )
