"""Synthetic regressions for explanation, overlap and original-upload retention."""
import base64
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, box, mapping

from api import main
from core.overlays.hansen_loss import HansenLossResult
from core.overlays.jrc_gfc2020 import JRCGFC2020Result
from core.overlays.radd import RADDResult
from engines.eudr import triage
from engines.eudr.boundaries import boundary_overlaps, format_area
from engines.eudr.geometry import parse_plots
from tests.test_intake import _configure


def collection(geometries):
    return json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"plot_id": f"S{i+1}"}, "geometry": g}
        for i, g in enumerate(geometries)]})


def adapters(monkeypatch, *, forest=True, loss=0.0, jrc_note="", loss_note=""):
    monkeypatch.setattr(triage, "query_jrc_gfc2020", lambda *a, **kw:
                        JRCGFC2020Result(forest, 90 if forest else 0, note=jrc_note))
    monkeypatch.setattr(triage, "query_hansen_loss", lambda *a, **kw:
                        HansenLossResult(loss, note=loss_note))
    monkeypatch.setattr(triage, "query_radd", lambda *a, **kw: RADDResult(None))
    monkeypatch.setattr(main, "send_lead_email", lambda **kw: True)


def post(content):
    response = TestClient(main.app).post("/api/eudr", data={
        "geojson_text": content, "commodity": "rubber",
        "name": "Synthetic tester", "email": "synthetic@example.invalid"})
    assert response.status_code == 200, response.text
    return response.json()


def test_nonforest_is_explained_and_loss_is_not_hidden(monkeypatch):
    adapters(monkeypatch, forest=False, loss=0.39)
    body = post(collection([mapping(box(113.000001, -1.002001, 113.002001, -1.000001))]))
    p = body["plots"][0]
    assert p["detection"] == "inconclusive"
    assert p["forest_2020"] is False and p["hansen_available"] is True
    assert "baseline_below_forest_threshold" in p["reason_codes"]
    assert "map read succeeded" in p["detail"] and "0.39 ha" in p["detail"]
    assert "cloud" not in p["detail"]
    assert "does not independently identify rubber" in body["commodity_identity_note"]


def test_overlap_requires_review_even_when_both_satellite_screens_are_clear(monkeypatch):
    adapters(monkeypatch)
    a = mapping(box(113.000001, -1.002001, 113.002001, -1.000001))
    b = mapping(box(113.001001, -1.002001, 113.003001, -1.000001))
    body = post(collection([a, b]))
    assert body["clear_count"] == 2 and body["overall"] == "review_needed"
    assert body["overlap_count"] == 1
    assert body["boundary_check"]["pairs"][0]["overlap_ha"] > 0
    assert all(p["boundary_warnings"] for p in body["plots"])
    assert body["readiness"][2]["status"] == "incomplete"
    # A DDS point export must never replace the polygon displayed on the result map.
    assert body["plot_map_geojson"]["features"][0]["geometry"]["type"] == "Polygon"


def test_shared_border_and_polygon_hole_are_not_overlaps():
    left = box(113.000001, -1.002001, 113.002001, -1.000001)
    right = box(113.002001, -1.002001, 113.004001, -1.000001)
    outer = box(113.010001, -1.010001, 113.020001, -1.000001)
    hole = box(113.012001, -1.008001, 113.018001, -1.002001)
    donut = Polygon(outer.exterior.coords, [hole.exterior.coords])
    inner = box(113.013001, -1.007001, 113.017001, -1.003001)
    vals = parse_plots(collection([mapping(g) for g in [left, right, donut, inner]]), "geojson")
    assert all(v.geometry_ok for v in vals)
    assert boundary_overlaps(vals)["pairs"] == []


def test_duplicate_polygons_overlap_and_points_remain_unassessed():
    a = mapping(box(113.000001, -1.002001, 113.002001, -1.000001))
    point = {"type": "Point", "coordinates": [113.001001, -1.001001]}
    vals = parse_plots(collection([a, a, point]), "geojson")
    result = boundary_overlaps(vals)
    assert len(result["pairs"]) == 1
    assert result["unassessed_plot_ids"] == ["S3"]


@pytest.mark.parametrize("forest,loss,jrc_note,loss_note,expected", [
    (None, 0, "JRC GFC2020 all-nodata over plot", "", "baseline_no_usable_pixels"),
    (True, None, "", "Plot crosses a Hansen tile; split the plot", "loss_tile_boundary"),
    (True, None, "", "Plot is below raster resolution or includes unavailable pixels", "loss_no_usable_pixels"),
])
def test_unavailable_measurement_has_specific_reason(monkeypatch, forest, loss, jrc_note, loss_note, expected):
    adapters(monkeypatch, forest=forest, loss=loss, jrc_note=jrc_note, loss_note=loss_note)
    p = post(collection([mapping(box(113.000001, -1.002001, 113.002001, -1.000001))]))["plots"][0]
    assert p["detection"] == "inconclusive" and expected in p["reason_codes"]
    assert "cloud" not in p["detail"]
    if loss is None:
        assert p["hansen_available"] is False and "Hansen reports zero" not in p["detail"]


@pytest.mark.parametrize("retain", ["true", "false"])
def test_original_source_including_invalid_shape_is_private_and_obeys_retention(monkeypatch, tmp_path, retain):
    path = _configure(monkeypatch, tmp_path, geometry=retain)
    adapters(monkeypatch)
    a = mapping(box(113.000001, -1.002001, 113.002001, -1.000001))
    bad = {"type": "Polygon", "coordinates": [[[113.000001, -1.000001], [113.002001, -1.002001],
            [113.000001, -1.002001], [113.002001, -1.000001], [113.000001, -1.000001]]]}
    source = " \n" + collection([a, bad]) + "\n "
    body = post(source)
    assert body["invalid_count"] == 1 and "_source_input" not in json.dumps(body)
    with sqlite3.connect(path) as conn:
        geometry, result = conn.execute("SELECT geometry_geojson,result_json FROM intake_submissions").fetchone()
    assert '"coordinates":' not in result and "_source_input" not in result
    if retain == "true":
        stored = json.loads(geometry)
        assert stored["features"][0]["geometry"]["type"] == "Polygon"
        assert base64.b64decode(stored["_source_input"]["content"]).decode() == source
        assert len(parse_plots(source, "geojson")) == 2  # invalid source is recoverable too
    else:
        assert geometry is None


def test_small_area_display_never_rounds_to_zero():
    assert format_area(0.2) == "0.20 ha"
    assert format_area(0.001) == "10.00 m²"
    assert format_area(0) == "area unavailable"
