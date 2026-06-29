"""tests/test_eudr_api.py — EUDR API endpoint (WO-EUDR-BLOCKER-004, E4).

Tests POST /api/eudr with pasted GeoJSON (the common path for the MVP).
All adapter calls go through committed fixtures (offline, deterministic).

Key invariants checked:
  - loss_detected case → overall_headline contains "could block your shipment"
  - clear_in_screen case → detail contains "not certified" framing; no bare clear tick
  - geometry_invalid case → plot comes back with fixing action
  - No EUDR_BANNED_SUBSTRINGS in any response JSON
  - Render guards: clear_in_screen never appears without the DDS framing
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.contracts import EUDR_BANNED_SUBSTRINGS

client = TestClient(app, raise_server_exceptions=True)

# ── Test geometries (centroid maps exactly to fixture keys) ────────────────────

def _fc(polygons: list[dict], ids: list[str] | None = None) -> str:
    """Build a GeoJSON FeatureCollection string from a list of polygon geometry dicts."""
    features = []
    for i, geom in enumerate(polygons):
        fid = (ids[i] if ids else None) or f"plot_{i + 1}"
        features.append({"type": "Feature", "properties": {"id": fid}, "geometry": geom})
    return json.dumps({"type": "FeatureCollection", "features": features})


# Polygon centred at lon=113.000, lat=-1.000 → fixture: -1.000_113.000 (loss_detected)
# Uses 6-decimal coords to pass Art-9 precision check.
_POLY_LOSS = {
    "type": "Polygon",
    "coordinates": [[[
        112.989999, -1.009999
    ], [
        113.010001, -1.009999
    ], [
        113.010001, -0.990001
    ], [
        112.989999, -0.990001
    ], [
        112.989999, -1.009999
    ]]],
}

# Polygon centred at lon=114.000, lat=-2.000 → fixture: -2.000_114.000 (clear_in_screen)
_POLY_CLEAR = {
    "type": "Polygon",
    "coordinates": [[[
        113.989999, -2.009999
    ], [
        114.010001, -2.009999
    ], [
        114.010001, -1.990001
    ], [
        113.989999, -1.990001
    ], [
        113.989999, -2.009999
    ]]],
}

# Polygon centred at lon=110.000, lat=1.500 → fixture: 1.500_110.000 (inconclusive — no baseline)
_POLY_INCON = {
    "type": "Polygon",
    "coordinates": [[[
        109.989999, 1.490001
    ], [
        110.010001, 1.490001
    ], [
        110.010001, 1.510001
    ], [
        109.989999, 1.510001
    ], [
        109.989999, 1.490001
    ]]],
}

# Low-precision coords → geometry_invalid (only 4 decimal places)
_POLY_BADGEO = {
    "type": "Polygon",
    "coordinates": [[[
        113.0001, -1.0001
    ], [
        113.0101, -1.0001
    ], [
        113.0101, -0.9901
    ], [
        113.0001, -0.9901
    ], [
        113.0001, -1.0001
    ]]],
}


def _post(geojson_text: str, commodity: str = "palm") -> dict:
    """POST /api/eudr and return parsed JSON (asserts 200)."""
    r = client.post(
        "/api/eudr",
        data={
            "geojson_text": geojson_text,
            "commodity": commodity,
            "role": "non_eu_supplier",
            "name": "Test User",
            "email": "test@example.com",
        },
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    return r.json()


# ── No banned strings ─────────────────────────────────────────────────────────

def test_no_banned_strings_in_loss_response():
    body = _post(_fc([_POLY_LOSS]))
    body_json = json.dumps(body)
    for banned in EUDR_BANNED_SUBSTRINGS:
        assert banned not in body_json, (
            f"Banned substring {banned!r} found in EUDR response"
        )


def test_no_banned_strings_in_clear_response():
    body = _post(_fc([_POLY_CLEAR]))
    body_json = json.dumps(body)
    for banned in EUDR_BANNED_SUBSTRINGS:
        assert banned not in body_json, (
            f"Banned substring {banned!r} found in EUDR response"
        )


# ── Overall engine tag ─────────────────────────────────────────────────────────

def test_engine_tag_is_eudr():
    body = _post(_fc([_POLY_LOSS]))
    assert body["engine"] == "eudr"


# ── loss_detected render guards ───────────────────────────────────────────────

def test_loss_detected_overall():
    body = _post(_fc([_POLY_LOSS]))
    assert body["overall"] == "loss_detected"


def test_loss_detected_headline_contains_could_block():
    """Render guard: any loss_detected → headline must warn about shipment blocking."""
    body = _post(_fc([_POLY_LOSS]))
    assert "could block your shipment" in body["overall_headline"], (
        f"loss_detected headline must mention blocking, got: {body['overall_headline']!r}"
    )


def test_loss_detected_count():
    body = _post(_fc([_POLY_LOSS]))
    assert body["loss_count"] == 1
    assert body["plot_count"] == 1


def test_loss_detected_plot_fields():
    body = _post(_fc([_POLY_LOSS]))
    plot = body["plots"][0]
    assert plot["detection"] == "loss_detected"
    assert plot["plot_satellite_risk"] == "high"
    assert plot["geometry_ok"] is True
    # Verbatim wording per eudr-design-v2.md
    assert "resolve it before the plot enters a DDS" in plot["detail"]
    assert "EU inspector" in plot["detail"]


# ── clear_in_screen render guards ─────────────────────────────────────────────

def test_clear_in_screen_overall():
    body = _post(_fc([_POLY_CLEAR]))
    assert body["overall"] == "clear_in_screen"


def test_clear_in_screen_headline_never_bare():
    """Render guard: clear_in_screen headline must carry DDS framing, never a bare 'Clear ✓'."""
    body = _post(_fc([_POLY_CLEAR]))
    hl = body["overall_headline"]
    # Must carry the 'not certified' or 'needs a DDS' framing
    assert "not certified" in hl or "needs a DDS" in hl, (
        f"clear_in_screen headline must carry DDS framing, got: {hl!r}"
    )


def test_clear_in_screen_plot_detail_has_dds_framing():
    """Render guard: clear plot detail must say 'not certified, still needs a DDS'."""
    body = _post(_fc([_POLY_CLEAR]))
    plot = body["plots"][0]
    assert plot["detection"] == "clear_in_screen"
    assert plot["plot_satellite_risk"] == "low"
    # Must have the framing — not a bare green tick
    assert "not certified" in plot["action"] or "needs a DDS" in plot["action"], (
        f"clear plot action must carry DDS framing, got: {plot['action']!r}"
    )


def test_clear_in_screen_counts():
    body = _post(_fc([_POLY_CLEAR]))
    assert body["clear_count"] == 1
    assert body["loss_count"] == 0


# ── inconclusive ──────────────────────────────────────────────────────────────

def test_inconclusive_overall():
    body = _post(_fc([_POLY_INCON]))
    assert body["overall"] == "review_needed"


def test_inconclusive_plot_fields():
    body = _post(_fc([_POLY_INCON]))
    plot = body["plots"][0]
    assert plot["detection"] == "inconclusive"
    assert plot["plot_satellite_risk"] == "inconclusive"
    assert "needs-review" in plot["detail"]


# ── geometry_invalid ──────────────────────────────────────────────────────────

def test_geometry_invalid_returned():
    body = _post(_fc([_POLY_BADGEO]))
    assert body["invalid_count"] == 1
    plot = body["plots"][0]
    assert plot["detection"] == "geometry_invalid"
    assert plot["geometry_ok"] is False
    assert "Art 9" in plot["detail"]


def test_geometry_invalid_does_not_clear():
    """geometry_invalid must never produce a clear headline."""
    body = _post(_fc([_POLY_BADGEO]))
    hl = body["overall_headline"]
    assert "could block" not in hl   # not loss_detected
    # And not a false 'all clear'
    assert "All" not in hl or "not certified" in hl


# ── Mixed batch: loss + clear ──────────────────────────────────────────────────

def test_mixed_loss_dominates():
    """Any loss_detected in batch → overall loss_detected + blocking headline."""
    body = _post(_fc([_POLY_CLEAR, _POLY_LOSS], ["P_clear", "P_loss"]))
    assert body["overall"] == "loss_detected"
    assert "could block your shipment" in body["overall_headline"]
    assert body["loss_count"] == 1
    assert body["clear_count"] == 1
    assert body["plot_count"] == 2


def test_mixed_order_preserved():
    body = _post(_fc([_POLY_CLEAR, _POLY_LOSS], ["A", "B"]))
    ids = [p["plot_id"] for p in body["plots"]]
    assert ids == ["A", "B"]


# ── Stamp + provenance ─────────────────────────────────────────────────────────

def test_stamps_present():
    body = _post(_fc([_POLY_LOSS]))
    assert body["run_date"]
    assert body["datasets_version"]
    plot = body["plots"][0]
    assert plot["run_date"]
    assert "JRC" in plot["datasets_version"] or "Hansen" in plot["datasets_version"]


def test_jrc_attribution_present():
    body = _post(_fc([_POLY_LOSS]))
    assert "JRC" in body["jrc_attribution"]
    assert "European Commission" in body["jrc_attribution"]


# ── Legality note ─────────────────────────────────────────────────────────────

def test_legality_note_present():
    body = _post(_fc([_POLY_LOSS]))
    assert "legality" in body["legality_note"].lower() or "legally" in body["legality_note"].lower()
    assert "deforestation" in body["legality_note"].lower()


def test_timber_note_only_for_timber():
    body_palm  = _post(_fc([_POLY_LOSS]), commodity="palm")
    body_timber = _post(_fc([_POLY_LOSS]), commodity="timber")
    assert body_palm["timber_note"] is None
    assert body_timber["timber_note"] is not None
    assert "degradation" in body_timber["timber_note"].lower()


# ── Country benchmark risk ─────────────────────────────────────────────────────

def test_country_benchmark_risk_is_standard():
    body = _post(_fc([_POLY_LOSS]))
    assert body["country_benchmark_risk"] == "standard"


# ── No file, no text → 422 ────────────────────────────────────────────────────

def test_missing_geometry_returns_422():
    r = client.post(
        "/api/eudr",
        data={
            "commodity": "palm",
            "role": "non_eu_supplier",
            "name": "Test",
            "email": "t@t.com",
        },
    )
    assert r.status_code == 422


# ── File upload path ──────────────────────────────────────────────────────────

def test_file_upload_geojson():
    content = _fc([_POLY_LOSS]).encode()
    r = client.post(
        "/api/eudr",
        data={
            "commodity": "palm",
            "role": "non_eu_supplier",
            "name": "Test",
            "email": "t@t.com",
        },
        files={"file": ("plots.geojson", content, "application/geo+json")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["overall"] == "loss_detected"
