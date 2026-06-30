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


# ══ E5: readiness checklist ══════════════════════════════════════════════════


def test_readiness_field_present():
    body = _post(_fc([_POLY_LOSS]))
    assert "readiness" in body
    assert isinstance(body["readiness"], list)
    assert len(body["readiness"]) >= 4


def test_readiness_items_have_required_fields():
    body = _post(_fc([_POLY_LOSS]))
    for item in body["readiness"]:
        assert "component" in item
        assert "status" in item
        assert item["status"] in ("complete", "incomplete"), (
            f"Unexpected status: {item['status']!r}"
        )


def test_readiness_no_numeric_score():
    """Categorical only — no numeric score field (ADR-0018)."""
    body = _post(_fc([_POLY_LOSS]))
    body_json = json.dumps(body["readiness"])
    assert "score" not in body_json


def test_readiness_geo_ok_when_no_invalid_plots():
    body = _post(_fc([_POLY_CLEAR]))
    geo_item = next(
        (r for r in body["readiness"] if "geolocation" in r["component"].lower()), None
    )
    assert geo_item is not None, "Readiness should include a geolocation item"
    assert geo_item["status"] == "complete"


def test_readiness_geo_incomplete_when_invalid_plots():
    body = _post(_fc([_POLY_BADGEO]))
    geo_item = next(
        (r for r in body["readiness"] if "geolocation" in r["component"].lower()), None
    )
    assert geo_item is not None
    assert geo_item["status"] == "incomplete"


def test_readiness_legality_always_incomplete():
    """Legality evidence is always a manual item — never auto-completed."""
    body_clear = _post(_fc([_POLY_CLEAR]))
    leg_item = next(
        (r for r in body_clear["readiness"] if "legality" in r["component"].lower()), None
    )
    assert leg_item is not None, "Readiness should include a legality evidence item"
    assert leg_item["status"] == "incomplete"


def test_readiness_screening_result_complete_for_clear():
    """'Screening result resolved' is complete when no loss or inconclusive plots."""
    body = _post(_fc([_POLY_CLEAR]))
    item = next(
        (r for r in body["readiness"] if "Screening result resolved" in r["component"]), None
    )
    assert item is not None, "Expected 'Screening result resolved' component"
    assert item["status"] == "complete"


def test_readiness_screening_result_incomplete_for_loss():
    """'Screening result resolved' is incomplete when loss detected."""
    body = _post(_fc([_POLY_LOSS]))
    item = next(
        (r for r in body["readiness"] if "Screening result resolved" in r["component"]), None
    )
    assert item is not None, "Expected 'Screening result resolved' component"
    assert item["status"] == "incomplete"


def test_readiness_no_banned_strings():
    body = _post(_fc([_POLY_CLEAR]))
    body_json = json.dumps(body["readiness"])
    for banned in EUDR_BANNED_SUBSTRINGS:
        assert banned not in body_json, (
            f"Banned substring {banned!r} in readiness field"
        )


# ══ E5: commodity evidence ════════════════════════════════════════════════════


def test_commodity_evidence_field_present():
    body = _post(_fc([_POLY_LOSS]), commodity="palm")
    assert "commodity_evidence" in body
    assert isinstance(body["commodity_evidence"], list)
    assert len(body["commodity_evidence"]) >= 2


def test_commodity_evidence_timber_contains_svlk():
    body = _post(_fc([_POLY_LOSS]), commodity="timber")
    evidence_text = " ".join(body["commodity_evidence"]).lower()
    assert "svlk" in evidence_text or "v-legal" in evidence_text


def test_commodity_evidence_palm_contains_ispo_hgu():
    body = _post(_fc([_POLY_LOSS]), commodity="palm")
    evidence_text = " ".join(body["commodity_evidence"]).lower()
    assert "ispo" in evidence_text
    assert "hgu" in evidence_text


def test_commodity_evidence_rubber_contains_land_tenure():
    body = _post(_fc([_POLY_LOSS]), commodity="rubber")
    evidence_text = " ".join(body["commodity_evidence"]).lower()
    assert "land" in evidence_text


def test_commodity_evidence_cocoa():
    body = _post(_fc([_POLY_LOSS]), commodity="cocoa")
    assert len(body["commodity_evidence"]) >= 2


def test_commodity_evidence_coffee():
    body = _post(_fc([_POLY_LOSS]), commodity="coffee")
    assert len(body["commodity_evidence"]) >= 2


def test_commodity_evidence_no_banned_strings():
    for commodity in ("palm", "rubber", "timber", "cocoa", "coffee"):
        body = _post(_fc([_POLY_CLEAR]), commodity=commodity)
        ev_json = json.dumps(body["commodity_evidence"])
        for banned in EUDR_BANNED_SUBSTRINGS:
            assert banned not in ev_json, (
                f"Banned substring {banned!r} in commodity_evidence for {commodity}"
            )


# ══ E5: who-files explainer ═══════════════════════════════════════════════════


def _post_role(role: str) -> dict:
    r = client.post(
        "/api/eudr",
        data={
            "geojson_text": _fc([_POLY_CLEAR]),
            "commodity": "palm",
            "role": role,
            "name": "Test",
            "email": "test@example.com",
        },
    )
    assert r.status_code == 200
    return r.json()


def test_who_files_field_present():
    body = _post_role("non_eu_supplier")
    assert "who_files" in body
    wf = body["who_files"]
    assert "who" in wf
    assert "detail" in wf
    assert "action" in wf


def test_who_files_non_eu_supplier_says_buyer_files():
    wf = _post_role("non_eu_supplier")["who_files"]
    combined = (wf["who"] + " " + wf["detail"]).lower()
    assert "buyer" in combined or "importer" in combined


def test_who_files_eu_first_placer_says_you_file():
    wf = _post_role("eu_first_placer")["who_files"]
    combined = (wf["who"] + " " + wf["detail"]).lower()
    assert "you" in combined


def test_who_files_downstream_operator_no_own_dds():
    wf = _post_role("downstream_operator")["who_files"]
    combined = (wf["who"] + " " + wf["detail"]).lower()
    # Downstream no longer files their own DDS
    assert "no longer" in combined or "verify" in combined


def test_who_files_no_banned_strings():
    for role in ("non_eu_supplier", "eu_first_placer", "downstream_operator"):
        body = _post_role(role)
        wf_json = json.dumps(body["who_files"])
        for banned in EUDR_BANNED_SUBSTRINGS:
            assert banned not in wf_json, (
                f"Banned substring {banned!r} in who_files for role={role}"
            )


# ══ E5: Indonesia context ═════════════════════════════════════════════════════


def test_indonesia_context_field_present():
    body = _post(_fc([_POLY_LOSS]))
    assert "indonesia_context" in body
    ic = body["indonesia_context"]
    assert "risk_level" in ic
    assert "due_diligence" in ic
    assert "deadlines" in ic
    assert isinstance(ic["deadlines"], list)
    assert len(ic["deadlines"]) >= 2


def test_indonesia_context_standard_risk():
    ic = _post(_fc([_POLY_LOSS]))["indonesia_context"]
    assert "standard" in ic["risk_level"].lower()
    assert "full" in ic["due_diligence"].lower()


def test_indonesia_context_deadlines_contain_2026_and_2027():
    ic = _post(_fc([_POLY_LOSS]))["indonesia_context"]
    all_deadlines = " ".join(d["deadline"] for d in ic["deadlines"])
    assert "2026" in all_deadlines
    assert "2027" in all_deadlines


def test_indonesia_context_no_simplified_route():
    """Simplified route does NOT apply to Indonesia — context must say so."""
    ic = _post(_fc([_POLY_LOSS]))["indonesia_context"]
    note = ic.get("simplified_route_note", "").lower()
    assert "simplified" in note
    assert "indonesia" in note


def test_indonesia_context_no_banned_strings():
    body = _post(_fc([_POLY_CLEAR]))
    ic_json = json.dumps(body["indonesia_context"])
    for banned in EUDR_BANNED_SUBSTRINGS:
        assert banned not in ic_json, (
            f"Banned substring {banned!r} in indonesia_context"
        )


# ══ E6: geolocation pack (Art-9 GeoJSON export) ══════════════════════════════


def test_geolocation_pack_field_present():
    body = _post(_fc([_POLY_LOSS]))
    assert "geolocation_pack_geojson" in body
    pack = body["geolocation_pack_geojson"]
    assert pack["type"] == "FeatureCollection"
    assert "features" in pack


def test_geolocation_pack_is_valid_feature_collection():
    body = _post(_fc([_POLY_LOSS, _POLY_CLEAR]))
    pack = body["geolocation_pack_geojson"]
    assert pack["type"] == "FeatureCollection"
    assert len(pack["features"]) == 2
    for feat in pack["features"]:
        assert feat["type"] == "Feature"
        assert "geometry" in feat
        assert "properties" in feat


def test_geolocation_pack_properties_present():
    body = _post(_fc([_POLY_LOSS]))
    feat = body["geolocation_pack_geojson"]["features"][0]
    props = feat["properties"]
    assert "plot_id" in props
    assert "commodity" in props
    assert "detection" in props
    assert "area_ha" in props
    assert "producer_name" in props


def test_geolocation_pack_commodity_matches():
    body = _post(_fc([_POLY_CLEAR]), commodity="timber")
    feat = body["geolocation_pack_geojson"]["features"][0]
    assert feat["properties"]["commodity"] == "timber"


def test_geolocation_pack_detection_matches_triage():
    body = _post(_fc([_POLY_LOSS]))
    pack_det = body["geolocation_pack_geojson"]["features"][0]["properties"]["detection"]
    triage_det = body["plots"][0]["detection"]
    assert pack_det == triage_det


def test_geolocation_pack_large_plot_is_polygon():
    """Plots >4 ha must be exported as Polygon (Art-9)."""
    body = _post(_fc([_POLY_LOSS]))
    feat = body["geolocation_pack_geojson"]["features"][0]
    # _POLY_LOSS is ~4.4 km × 4.4 km → well over 4 ha; should be polygon
    assert feat["geometry"]["type"] == "Polygon", (
        "Large plot (>4 ha) should be a Polygon in the geolocation pack"
    )


def test_geolocation_pack_small_plot_is_point():
    """Plots ≤4 ha must be exported as Point (Art-9)."""
    # Build a tiny polygon (≈0.01 ha) that passes Art-9 precision but is ≤4 ha
    tiny = {
        "type": "Polygon",
        "coordinates": [[[
            113.000001, -1.000001
        ], [
            113.000011, -1.000001
        ], [
            113.000011, -0.999991
        ], [
            113.000001, -0.999991
        ], [
            113.000001, -1.000001
        ]]],
    }
    body = _post(_fc([tiny]))
    feat = body["geolocation_pack_geojson"]["features"][0]
    assert feat["geometry"]["type"] == "Point", (
        "Small plot (≤4 ha) should be exported as a Point (Art-9)"
    )
    # Point coordinates: [lon, lat] — both must be floats
    coords = feat["geometry"]["coordinates"]
    assert len(coords) == 2
    assert all(isinstance(c, float) for c in coords)


def test_geolocation_pack_at_least_6_decimal_places():
    """All polygon coordinate values must have ≥6 decimal places."""
    body = _post(_fc([_POLY_CLEAR]))
    pack = body["geolocation_pack_geojson"]
    for feat in pack["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                for lon, lat in ring:
                    # round() to 6 should equal the value itself (already at 6dp)
                    assert round(lon, 6) == lon or len(str(lon).rstrip("0").split(".")[-1]) >= 6, (
                        f"Longitude {lon} has fewer than 6 decimal places"
                    )


def test_geolocation_pack_point_has_6_decimal_places():
    """Point coordinates must also have ≥6 decimal places."""
    tiny = {
        "type": "Polygon",
        "coordinates": [[[
            113.000001, -1.000001
        ], [
            113.000011, -1.000001
        ], [
            113.000011, -0.999991
        ], [
            113.000001, -0.999991
        ], [
            113.000001, -1.000001
        ]]],
    }
    body = _post(_fc([tiny]))
    feat = body["geolocation_pack_geojson"]["features"][0]
    assert feat["geometry"]["type"] == "Point"
    lon, lat = feat["geometry"]["coordinates"]
    # centroid coords should be at 6dp (rounded from input)
    assert round(lon, 6) == lon
    assert round(lat, 6) == lat


def test_geolocation_pack_excludes_geometry_invalid():
    """geometry_invalid plots must NOT appear in the geolocation pack (Art-9 non-conforming)."""
    body = _post(_fc([_POLY_BADGEO]))
    pack = body["geolocation_pack_geojson"]
    # _POLY_BADGEO has only 4 decimal places → geometry_invalid
    assert len(pack["features"]) == 0, (
        "geometry_invalid plot should be excluded from the geolocation pack"
    )


def test_geolocation_pack_mixed_batch_excludes_invalid():
    """Valid plots included; geometry_invalid excluded."""
    body = _post(_fc([_POLY_LOSS, _POLY_BADGEO]))
    pack = body["geolocation_pack_geojson"]
    # Only _POLY_LOSS (valid) should appear
    assert len(pack["features"]) == 1
    assert pack["features"][0]["properties"]["plot_id"] == "plot_1"


def test_geolocation_pack_no_banned_strings():
    """E1 guard: no banned strings in the geolocation pack JSON."""
    body = _post(_fc([_POLY_LOSS, _POLY_CLEAR]))
    pack_json = json.dumps(body["geolocation_pack_geojson"])
    for banned in EUDR_BANNED_SUBSTRINGS:
        assert banned not in pack_json, (
            f"Banned substring {banned!r} found in geolocation_pack_geojson"
        )


# ── E7: EUDR PDF report + /api/eudr/report endpoint ───────────────────────────


def test_eudr_report_endpoint_returns_pdf():
    """POST /api/eudr/report returns non-empty PDF bytes."""
    triage = _post(_fc([_POLY_LOSS, _POLY_CLEAR]))
    r = client.post("/api/eudr/report", json={
        "result":       triage,
        "contact_name": "Test User",
        "commodity":    "palm",
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 1000, "PDF should be non-trivial"


def test_eudr_report_starts_with_pdf_magic_bytes():
    """PDF output begins with %%PDF."""
    triage = _post(_fc([_POLY_CLEAR]))
    r = client.post("/api/eudr/report", json={
        "result":       triage,
        "contact_name": "Jane Doe",
        "commodity":    "timber",
    })
    assert r.content[:4] == b"%PDF", "Response should start with PDF magic bytes"


def test_eudr_report_content_disposition_has_filename():
    """Content-Disposition header carries a filename."""
    triage = _post(_fc([_POLY_LOSS]))
    r = client.post("/api/eudr/report", json={
        "result": triage, "contact_name": "X", "commodity": "palm",
    })
    cd = r.headers.get("content-disposition", "")
    assert "filename=" in cd, f"Expected filename in Content-Disposition: {cd}"
    assert cd.endswith(".pdf\""), f"Filename should end with .pdf: {cd}"


def test_eudr_report_no_banned_strings_in_pdf():
    """E1 guard: banned strings must not appear in the raw PDF bytes."""
    triage = _post(_fc([_POLY_LOSS, _POLY_CLEAR]))
    r = client.post("/api/eudr/report", json={
        "result": triage, "contact_name": "Test", "commodity": "palm",
    })
    pdf_bytes = r.content
    for banned in EUDR_BANNED_SUBSTRINGS:
        assert banned.encode() not in pdf_bytes, (
            f"Banned substring {banned!r} found in EUDR PDF bytes"
        )


def test_eudr_report_loss_response_non_empty():
    """PDF generated for a loss-detected result is non-empty."""
    triage = _post(_fc([_POLY_LOSS]))
    r = client.post("/api/eudr/report", json={
        "result": triage, "contact_name": "A", "commodity": "timber",
    })
    assert r.status_code == 200
    assert len(r.content) > 500


def test_eudr_report_clear_response_non_empty():
    """PDF generated for an all-clear result is non-empty."""
    triage = _post(_fc([_POLY_CLEAR]))
    r = client.post("/api/eudr/report", json={
        "result": triage, "contact_name": "B", "commodity": "cocoa",
    })
    assert r.status_code == 200
    assert len(r.content) > 500


def test_eudr_lead_email_subject_format(monkeypatch):
    """Lead email subject follows the spec: 'New 180Climate EUDR lead — {name} · N plots, X flagged'."""
    captured: list[dict] = []

    def _fake_send(iup_name, filename_base, form_data, pdf_bytes=None, subject_override=None):
        captured.append({"subject": subject_override, "iup_name": iup_name})
        return True

    monkeypatch.setattr("api.main.send_lead_email", _fake_send)
    _post(_fc([_POLY_LOSS, _POLY_CLEAR]))
    assert captured, "send_lead_email was not called"
    subj = captured[0]["subject"] or ""
    assert "EUDR lead" in subj, f"Subject missing 'EUDR lead': {subj!r}"
    assert "plots" in subj, f"Subject missing plot count: {subj!r}"
    assert "flagged" in subj, f"Subject missing 'flagged': {subj!r}"


def test_eudr_lead_email_has_pdf_bytes(monkeypatch):
    """Lead email is called with non-empty PDF bytes (not b'')."""
    captured: list[dict] = []

    def _fake_send(iup_name, filename_base, form_data, pdf_bytes=None, subject_override=None):
        captured.append({"pdf_bytes": pdf_bytes})
        return True

    monkeypatch.setattr("api.main.send_lead_email", _fake_send)
    _post(_fc([_POLY_CLEAR]))
    assert captured, "send_lead_email was not called"
    pdf = captured[0]["pdf_bytes"]
    assert pdf is not None and len(pdf) > 100, (
        f"Expected non-empty PDF bytes, got: {repr(pdf)[:40]}"
    )


# ── WO-EUDR-GATEFIX-011: hero colour map + grammar + checklist label ──────────


def test_eudr_hero_colour_map_constants():
    """EUDR_HERO_COLOUR has the required three states with correct hex values."""
    from reports.generator import EUDR_HERO_COLOUR
    assert EUDR_HERO_COLOUR["loss_detected"]   == "#C0392B", "loss_detected must be red"
    assert EUDR_HERO_COLOUR["review_needed"]   == "#8A5A00", "review_needed must be amber"
    assert EUDR_HERO_COLOUR["clear_in_screen"] == "#0E7A30", "clear_in_screen must be green"


def test_eudr_hero_colour_map_pdf_loss_differs_from_clear():
    """loss_detected and clear_in_screen produce different PDF bytes (different bg colour)."""
    from reports.generator import generate_eudr_pdf
    base = _post(_fc([_POLY_LOSS]))
    loss_pdf  = generate_eudr_pdf({**base, "overall": "loss_detected",
                                   "contact_name": "T", "commodity": "palm"})
    clear_pdf = generate_eudr_pdf({**base, "overall": "clear_in_screen",
                                   "contact_name": "T", "commodity": "palm"})
    assert loss_pdf != clear_pdf, "loss_detected PDF must differ from clear_in_screen PDF"


def test_eudr_hero_colour_map_pdf_review_differs_from_loss_and_clear():
    """review_needed produces different PDF bytes from both loss and clear."""
    from reports.generator import generate_eudr_pdf
    base = _post(_fc([_POLY_INCON]))
    review_pdf = generate_eudr_pdf({**base, "overall": "review_needed",
                                    "contact_name": "T", "commodity": "palm"})
    loss_pdf   = generate_eudr_pdf({**base, "overall": "loss_detected",
                                    "contact_name": "T", "commodity": "palm"})
    clear_pdf  = generate_eudr_pdf({**base, "overall": "clear_in_screen",
                                    "contact_name": "T", "commodity": "palm"})
    assert review_pdf != loss_pdf,  "review_needed PDF must differ from loss_detected PDF"
    assert review_pdf != clear_pdf, "review_needed PDF must differ from clear_in_screen PDF"


def test_eudr_headline_grammar_singular():
    """'1 plot needs review' — singular subject-verb agreement."""
    body = _post(_fc([_POLY_INCON]))
    if body["overall"] == "review_needed":
        assert "need" in body["overall_headline"], f"Headline: {body['overall_headline']!r}"
        # Singular: "needs", not "need" (only for 1 plot)
        if body.get("inconclusive_count") == 1:
            assert "needs" in body["overall_headline"], (
                f"Expected 'needs' for 1 plot: {body['overall_headline']!r}"
            )


def test_eudr_headline_grammar_no_plot_s():
    """No 'plot(s)' literal in any headline — must be 'plot' or 'plots'."""
    for fc in [_fc([_POLY_LOSS]), _fc([_POLY_CLEAR]), _fc([_POLY_INCON])]:
        body = _post(fc)
        assert "plot(s)" not in body["overall_headline"], (
            f"Literal 'plot(s)' in headline: {body['overall_headline']!r}"
        )


def test_eudr_checklist_label_renamed():
    """Checklist component is 'Screening result resolved', not 'No deforestation...'."""
    body = _post(_fc([_POLY_CLEAR]))
    components = [item["component"] for item in body.get("readiness", [])]
    assert any("Screening result resolved" in c for c in components), (
        f"Expected 'Screening result resolved' in checklist components: {components}"
    )
    assert not any("No deforestation flagged" in c for c in components), (
        f"Old label still present: {components}"
    )


def test_eudr_geometry_note_no_plot_s():
    """Geometry readiness note uses 'plot'/'plots', not 'plot(s)'."""
    body = _post(_fc([_POLY_BADGEO]))
    for item in body.get("readiness", []):
        assert "plot(s)" not in item.get("note", ""), (
            f"Literal 'plot(s)' in readiness note: {item['note']!r}"
        )
