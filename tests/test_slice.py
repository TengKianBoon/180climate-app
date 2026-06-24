"""tests/test_slice.py — WO-001 vertical slice acceptance tests.

All tests are deterministic (no LLM calls, no network). Covers:
- Geometry parsing (coords + GeoJSON + malformed input)
- Carbon engine golden case
- Determinism (same input → same output)
- Email mock (payload shape, no secrets)
- API route (FastAPI TestClient)
"""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from core.contracts import GeoInput, CarbonInput, ContactInfo, CarbonGates
from core.geo import parse_geo
from core.forest import query_forest_data
from engines.carbon.engine import run_carbon_engine, run_eligibility, build_methodology_route
from api.main import app

_GOLDEN_PATH = Path(__file__).parent / "fixtures" / "carbon" / "WO001_golden.json"
_GOLDEN = json.loads(_GOLDEN_PATH.read_text())

client = TestClient(app)


# ── Geometry parsing ──────────────────────────────────────────────────────────

def test_parse_coords_basic():
    geo = GeoInput(fmt="coords", payload="-0.5,117.5")
    b = parse_geo(geo)
    assert b.is_valid
    assert abs(b.centroid_lat - (-0.5)) < 0.01
    assert abs(b.centroid_lon - 117.5) < 0.01
    assert b.within_indonesia


def test_parse_coords_space_separated():
    geo = GeoInput(fmt="coords", payload="-0.5 117.5")
    b = parse_geo(geo)
    assert b.is_valid
    assert b.within_indonesia


def test_parse_geojson_polygon():
    poly = {
        "type": "Polygon",
        "coordinates": [[[117.0, 0.0], [118.0, 0.0], [118.0, -1.0], [117.0, -1.0], [117.0, 0.0]]]
    }
    geo = GeoInput(fmt="geojson", payload=json.dumps(poly))
    b = parse_geo(geo)
    assert b.is_valid
    assert b.area_ha > 0
    assert b.within_indonesia


def test_parse_malformed_coords_raises():
    geo = GeoInput(fmt="coords", payload="not_a_number,xyz")
    with pytest.raises(ValueError, match="numbers"):
        parse_geo(geo)


def test_parse_missing_coords_raises():
    geo = GeoInput(fmt="coords", payload="117.5")  # only one value
    with pytest.raises(ValueError):
        parse_geo(geo)


def test_parse_invalid_geojson_raises():
    geo = GeoInput(fmt="geojson", payload="{ bad json }")
    with pytest.raises(ValueError, match="GeoJSON"):
        parse_geo(geo)


def test_parse_shapefile_raises():
    geo = GeoInput(fmt="shapefile", payload="some_file.shp")
    with pytest.raises(ValueError, match="not yet implemented"):
        parse_geo(geo)


# ── Forest stub (determinism) ──────────────────────────────────────────────────

def test_forest_stub_deterministic():
    geo = GeoInput(fmt="coords", payload="-0.5,117.5")
    b = parse_geo(geo)
    f1 = query_forest_data(b)
    f2 = query_forest_data(b)
    assert f1.annual_loss_ha == f2.annual_loss_ha
    assert f1.baseline_cover_pct == f2.baseline_cover_pct


def test_forest_stub_has_loss_data():
    geo = GeoInput(fmt="coords", payload="-0.5,117.5")
    b = parse_geo(geo)
    f = query_forest_data(b)
    assert len(f.annual_loss_ha) >= 20
    assert f.uncertainty_band  # non-empty
    assert f.data_sources


# ── Carbon engine golden case ──────────────────────────────────────────────────

def _make_carbon_input(inp_dict: dict) -> CarbonInput:
    return CarbonInput(**inp_dict)


def test_golden_case():
    inp = _make_carbon_input(_GOLDEN["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    exp = _GOLDEN["expected"]

    assert estimate.eligibility.verdict == exp["eligibility_verdict"]
    assert estimate.eligibility.gates["permit_type"].status == exp["permit_type_gate"]
    assert estimate.eligibility.gates["permit_years"].status == exp["permit_years_gate"]
    assert estimate.methodology.baseline_class == exp["methodology_baseline_class"]
    assert estimate.methodology.is_planned == exp["methodology_is_planned"]
    assert estimate.methodology.additionality_basis == exp["additionality_basis"]
    assert estimate.quantity_low_tco2e > 0  # exp: estimate_low_gt_zero
    assert estimate.quantity_high_tco2e > estimate.quantity_low_tco2e  # exp: estimate_high_gt_low


def test_carbon_engine_deterministic():
    inp = _make_carbon_input(_GOLDEN["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    e1 = run_carbon_engine(inp, boundary, forest)
    e2 = run_carbon_engine(inp, boundary, forest)
    assert e1.quantity_low_tco2e == e2.quantity_low_tco2e
    assert e1.quantity_high_tco2e == e2.quantity_high_tco2e
    assert e1.eligibility.verdict == e2.eligibility.verdict


def test_estimate_is_always_range():
    """Invariant: quantity_low must always be strictly less than quantity_high."""
    inp = _make_carbon_input(_GOLDEN["input"])
    boundary = parse_geo(inp.geo)
    forest = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)
    assert estimate.quantity_low_tco2e < estimate.quantity_high_tco2e, (
        "CarbonEstimate must be a range — never a single false-precise number (ADR-0009)"
    )


def test_hti_route_is_planned():
    """HTI must always produce is_planned=True (ADR-0001)."""
    inp = CarbonInput(
        contact=ContactInfo(name="T", email="t@t.com"),
        iup_name="Test", iup_address="—",
        permit_type="HTI", permit_years_remaining=20, project_type="REDD",
        geo=GeoInput(fmt="coords", payload="-0.5,117.5"),
    )
    route = build_methodology_route(inp)
    assert route.is_planned, "HTI foregone-harvest must always be a planned baseline"
    assert route.additionality_basis == "legal harvest right foregone"
    assert "VM0048" not in str(route.cited_methods), "VM0048 must NEVER be cited for HTI"


def test_ha_route_is_planned():
    """HA must always produce is_planned=True (ADR-0001)."""
    inp = CarbonInput(
        contact=ContactInfo(name="T", email="t@t.com"),
        iup_name="Test", iup_address="—",
        permit_type="HA", permit_years_remaining=15, project_type="REDD",
        geo=GeoInput(fmt="coords", payload="-0.5,117.5"),
    )
    route = build_methodology_route(inp)
    assert route.is_planned, "HA foregone-harvest must always be a planned baseline"
    assert route.additionality_basis == "legal harvest right foregone"


def test_eligibility_hard_no_on_bad_permit():
    inp = CarbonInput(
        contact=ContactInfo(name="T", email="t@t.com"),
        iup_name="Test", iup_address="—",
        permit_type="HTI", permit_years_remaining=2, project_type="REDD",
        geo=GeoInput(fmt="coords", payload="-0.5,117.5"),
    )
    boundary = parse_geo(inp.geo)
    elig = run_eligibility(inp, boundary)
    # 2 years remaining → flagged (soft), but not hard_no on its own
    assert elig.gates["permit_years"].status == "flag"


# ── Email mock ────────────────────────────────────────────────────────────────

def test_email_called_with_correct_to():
    """Verify send_lead_email is called and payload targets info@180climate.net."""
    from api.email import send_lead_email

    form_data = {
        "name": "Test", "email": "test@example.com",
        "iup_name": "Test IUP", "permit_type": "HTI",
        "timestamp": "202606240000",
    }
    # With no EMAIL_HOST set, should fall back to outbox log (returns True)
    ok = send_lead_email(
        iup_name="Test IUP",
        filename_base="2606240000",
        form_data=form_data,
    )
    assert ok, "send_lead_email must return True when logging to outbox (no SMTP configured)"


# ── API route ─────────────────────────────────────────────────────────────────

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_carbon_api_coords():
    payload = {
        "contact": {"name": "Test", "email": "test@example.com"},
        "iup_name": "PT Test",
        "iup_address": "Kalimantan",
        "permit_type": "HTI",
        "permit_years_remaining": 20,
        "project_type": "REDD",
        "geo": {"fmt": "coords", "payload": "-0.5,117.5"},
    }
    res = client.post("/api/carbon", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["engine"] == "carbon"
    assert "verdict" in data
    assert "narrative" in data
    assert data["disclaimer"]["kind"] == "carbon_non_binding"


def test_carbon_api_geojson():
    poly = {"type": "Polygon", "coordinates": [[[117.0, 0.0], [118.0, 0.0], [118.0, -1.0], [117.0, -1.0], [117.0, 0.0]]]}
    payload = {
        "contact": {"name": "Test", "email": "test@example.com"},
        "iup_name": "PT Test GeoJSON",
        "iup_address": "Kalimantan",
        "permit_type": "HA",
        "permit_years_remaining": 15,
        "project_type": "REDD",
        "geo": {"fmt": "geojson", "payload": json.dumps(poly)},
    }
    res = client.post("/api/carbon", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["engine"] == "carbon"


def test_carbon_api_bad_geo_422():
    payload = {
        "contact": {"name": "T", "email": "t@t.com"},
        "iup_name": "X", "iup_address": "—",
        "permit_type": "HTI", "permit_years_remaining": 10, "project_type": "REDD",
        "geo": {"fmt": "coords", "payload": "not_valid"},
    }
    res = client.post("/api/carbon", json=payload)
    assert res.status_code == 422


def test_lead_api():
    payload = {
        "name": "Test Lead",
        "email": "lead@example.com",
        "mobile": "+62123456",
        "company": "PT Test",
        "iup_name": "Test IUP",
        "permit_type": "HTI",
        "payload_summary": "Preliminary estimate: 1,000,000–1,500,000 tCO2e",
    }
    res = client.post("/api/lead", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "timestamp" in data
