"""tests/test_eudr_geometry.py — Art-9 geometry validation (WO-EUDR-GEOMETRY-002)."""
import json

import pytest

from engines.eudr.geometry import (
    FIX_MESSAGE,
    PlotValidation,
    _all_have_min_precision,
    _all_have_min_precision_str,
    _decimal_places,
    _decimal_places_str,
    parse_plots,
)

# ── Shared geometry fixtures ──────────────────────────────────────────────────
# All coordinates use ≥6 decimal places (the Art-9 minimum).
# 0.01° square near Kalimantan equator ≈ 123 ha — clearly >4 ha.

_POLY_LARGE = {
    "type": "Polygon",
    "coordinates": [[
        [117.123456, -0.123456],
        [117.133456, -0.123456],
        [117.133456, -0.133456],
        [117.123456, -0.133456],
        [117.123456, -0.123456],
    ]],
}

# 4-decimal coords — fails precision check
_POLY_LOW_PREC = {
    "type": "Polygon",
    "coordinates": [[
        [117.1235, -0.1235],
        [117.1335, -0.1235],
        [117.1335, -0.1335],
        [117.1235, -0.1335],
        [117.1235, -0.1235],
    ]],
}

# Bowtie (self-intersecting): edges A→B and C→D cross in the middle
_POLY_BOWTIE = {
    "type": "Polygon",
    "coordinates": [[
        [117.123456, -0.123456],  # A
        [117.133456, -0.133456],  # B  (A→B diagonal)
        [117.133456, -0.123456],  # C
        [117.123456, -0.133456],  # D  (C→D diagonal crosses A→B)
        [117.123456, -0.123456],
    ]],
}

_POINT_6DEC = {"type": "Point", "coordinates": [117.123456, -0.123456]}
_POINT_4DEC = {"type": "Point", "coordinates": [117.1235, -0.1235]}


def _feature(plot_id: str, geom: dict, area_ha: float = 0.0) -> dict:
    return {
        "type": "Feature",
        "properties": {"plot_id": plot_id, "area_ha": area_ha},
        "geometry": geom,
    }


def _fc(*features) -> str:
    return json.dumps({"type": "FeatureCollection", "features": list(features)})


# ── Precision helpers ─────────────────────────────────────────────────────────

def test_decimal_places_unit():
    assert _decimal_places(0.5) == 1
    assert _decimal_places(117.1235) == 4
    assert _decimal_places(117.12345) == 5
    assert _decimal_places(117.123456) == 6
    assert _decimal_places(117.1234567) == 7
    assert _decimal_places(1e-7) == 0  # scientific notation → treated as 0


def test_all_have_min_precision():
    assert _all_have_min_precision([117.123456, -0.123456]) is True
    assert _all_have_min_precision([117.1235, -0.123456]) is False
    assert _all_have_min_precision([117.0, -0.123456]) is False


def test_decimal_places_str_unit():
    """_decimal_places_str counts from the raw string, preserving trailing zeros."""
    # Trailing zeros preserved (the fix: repr() would drop these)
    assert _decimal_places_str("117.152340") == 6    # trailing 0 — repr gives 5
    assert _decimal_places_str("-1.000000") == 6     # all zeros after decimal
    assert _decimal_places_str("117.1234567") == 7
    assert _decimal_places_str("117.123456") == 6
    assert _decimal_places_str("117.1235") == 4
    assert _decimal_places_str("117") == 0           # no decimal
    assert _decimal_places_str("1e-7") == 0          # scientific notation → 0
    # Float fallback (SHP path) — still works via repr
    assert _decimal_places_str(117.123456) == 6
    assert _decimal_places_str(117.1235) == 4


def test_all_have_min_precision_str_accepts_trailing_zeros():
    """String-aware check: 6dp ending in 0 passes; 4dp fails."""
    assert _all_have_min_precision_str(["117.152340", "-1.000000"]) is True
    assert _all_have_min_precision_str(["117.1235", "-1.000000"]) is False   # 4dp
    assert _all_have_min_precision_str(["117.123456", "-1.000000"]) is True


# ── Trailing-zero coordinate acceptance (WO-EUDR-PRECISION-018) ───────────────

# Raw GeoJSON strings with trailing zeros — json.dumps() would drop the trailing 0,
# so these must be hand-written string literals to exercise the parse_float=str path.
_GJ_TRAILING_ZERO_POLYGON = (
    '{"type":"FeatureCollection","features":[{"type":"Feature",'
    '"properties":{"plot_id":"T1"},"geometry":{"type":"Polygon",'
    '"coordinates":[[[117.152340,-1.000000],[117.162340,-1.000000],'
    '[117.162340,-1.010000],[117.152340,-1.010000],[117.152340,-1.000000]]]}}]}'
)

_GJ_TRAILING_ZERO_POINT = (
    '{"type":"Feature","properties":{},'
    '"geometry":{"type":"Point","coordinates":[117.152340,-1.000000]}}'
)

_GJ_TWO_DECIMAL = (
    '{"type":"FeatureCollection","features":[{"type":"Feature",'
    '"properties":{"plot_id":"Bad"},"geometry":{"type":"Polygon",'
    '"coordinates":[[[117.15,-1.00],[117.16,-1.00],'
    '[117.16,-1.01],[117.15,-1.01],[117.15,-1.00]]]}}]}'
)

_KML_TRAILING_ZERO = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>K1</name>
    <Polygon>
      <outerBoundaryIs><LinearRing>
        <coordinates>
          117.152340,-1.000000 117.162340,-1.000000
          117.162340,-1.010000 117.152340,-1.010000
          117.152340,-1.000000
        </coordinates>
      </LinearRing></outerBoundaryIs>
    </Polygon>
  </Placemark>
</kml>"""


def test_geojson_trailing_zero_polygon_accepted():
    """GeoJSON polygon with 6 dp ending in 0 must validate, not be rejected (false-reject fix)."""
    results = parse_plots(_GJ_TRAILING_ZERO_POLYGON, "geojson")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is True, f"Trailing-zero coords falsely rejected: {r.fix_message}"
    assert r.detection == "inconclusive"
    assert r.area_ha > 0


def test_geojson_trailing_zero_point_accepted():
    """GeoJSON point with 6 dp trailing zeros must validate."""
    results = parse_plots(_GJ_TRAILING_ZERO_POINT, "geojson")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is True, f"Trailing-zero point coords falsely rejected: {r.fix_message}"
    assert r.detection == "inconclusive"


def test_geojson_two_decimal_still_rejected():
    """2-dp coords must still be rejected (existing guard must not be broken)."""
    results = parse_plots(_GJ_TWO_DECIMAL, "geojson")
    assert len(results) == 1
    assert results[0].detection == "geometry_invalid"


def test_kml_trailing_zero_polygon_accepted():
    """KML polygon with 6 dp ending in 0 must validate (coord-text path fix)."""
    results = parse_plots(_KML_TRAILING_ZERO, "kml")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is True, f"KML trailing-zero coords falsely rejected: {r.fix_message}"
    assert r.detection == "inconclusive"


# ── Valid polygon (>4 ha, ≥6 dec) ────────────────────────────────────────────

def test_valid_large_polygon():
    """Valid polygon ≥6 decimal coords and >4 ha → geometry_ok, detection=inconclusive."""
    results = parse_plots(json.dumps(_POLY_LARGE), "geojson")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is True
    assert r.detection == "inconclusive"
    assert r.area_ha > 4.0
    assert r.geometry_type == "polygon"
    assert r.fix_message is None
    assert r.geojson is not None


def test_valid_polygon_via_feature():
    """GeoJSON Feature wrapping a valid polygon is parsed correctly."""
    results = parse_plots(json.dumps(_feature("P1", _POLY_LARGE)), "geojson")
    assert len(results) == 1
    assert results[0].plot_id == "P1"
    assert results[0].geometry_ok is True


# ── Point for >4 ha → invalid ─────────────────────────────────────────────────

def test_point_for_large_plot_is_invalid():
    """A point with declared area >4 ha violates Art-9 (polygon required)."""
    results = parse_plots(json.dumps(_feature("P_large", _POINT_6DEC, area_ha=10.5)), "geojson")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is False
    assert r.detection == "geometry_invalid"
    assert r.fix_message == FIX_MESSAGE


def test_point_for_small_plot_is_valid():
    """A point with declared area ≤4 ha is acceptable under Art-9."""
    results = parse_plots(json.dumps(_feature("P_small", _POINT_6DEC, area_ha=2.0)), "geojson")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is True
    assert r.detection == "inconclusive"
    assert r.geometry_type == "point"


def test_point_no_declared_area_is_valid():
    """A point with no declared area is treated as ≤4 ha (best-effort, Art-9 allows)."""
    results = parse_plots(json.dumps(_POINT_6DEC), "geojson")
    assert len(results) == 1
    assert results[0].geometry_ok is True


# ── <6-decimal coords → invalid ───────────────────────────────────────────────

def test_polygon_low_precision_coords_invalid():
    """Polygon with <6 decimal coords violates Art-9 precision requirement."""
    results = parse_plots(json.dumps(_POLY_LOW_PREC), "geojson")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is False
    assert r.detection == "geometry_invalid"
    assert r.fix_message == FIX_MESSAGE


def test_point_low_precision_coords_invalid():
    """Point with <6 decimal coords violates Art-9 precision requirement."""
    results = parse_plots(json.dumps(_POINT_4DEC), "geojson")
    assert len(results) == 1
    assert results[0].geometry_ok is False
    assert results[0].detection == "geometry_invalid"


# ── Self-intersecting → invalid ───────────────────────────────────────────────

def test_self_intersecting_polygon_invalid():
    """Bowtie (self-intersecting) polygon → geometry_invalid."""
    results = parse_plots(json.dumps(_POLY_BOWTIE), "geojson")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is False
    assert r.detection == "geometry_invalid"
    assert r.fix_message == FIX_MESSAGE


# ── Empty / degenerate ────────────────────────────────────────────────────────

def test_empty_geometry_invalid():
    """Missing geometry field → geometry_invalid."""
    feat = {"type": "Feature", "properties": {"plot_id": "X"}, "geometry": None}
    results = parse_plots(json.dumps(feat), "geojson")
    assert results[0].geometry_ok is False
    assert results[0].detection == "geometry_invalid"


def test_polygon_too_few_points_invalid():
    """A polygon ring with <4 points (degenerate) → geometry_invalid."""
    geom = {"type": "Polygon", "coordinates": [[[117.123456, -0.123456], [117.133456, -0.133456]]]}
    results = parse_plots(json.dumps(geom), "geojson")
    assert results[0].geometry_ok is False
    assert results[0].detection == "geometry_invalid"


# ── Multi-plot FeatureCollection ──────────────────────────────────────────────

def test_multi_plot_feature_collection_parses_all():
    """FeatureCollection with N features → N PlotValidation results, in order."""
    fc = _fc(
        _feature("A", _POLY_LARGE),
        _feature("B", _POLY_LARGE),
        _feature("C", _POLY_LOW_PREC),  # invalid
    )
    results = parse_plots(fc, "geojson")
    assert len(results) == 3
    assert results[0].plot_id == "A"
    assert results[0].geometry_ok is True
    assert results[1].plot_id == "B"
    assert results[1].geometry_ok is True
    assert results[2].plot_id == "C"
    assert results[2].geometry_ok is False


# ── geometry_ok / detection consistency ──────────────────────────────────────

def test_geometry_ok_and_detection_always_consistent_via_parse():
    """Every PlotValidation from parse_plots satisfies geometry_ok == (detection != 'geometry_invalid')."""
    geoms = [
        _feature("V", _POLY_LARGE),
        _feature("I", _POLY_LOW_PREC),
        _feature("S", _POLY_BOWTIE),
        _feature("P", _POINT_6DEC, area_ha=0.5),
        _feature("PL", _POINT_6DEC, area_ha=10.0),
    ]
    results = parse_plots(_fc(*geoms), "geojson")
    for r in results:
        assert r.geometry_ok == (r.detection != "geometry_invalid"), (
            f"Inconsistency for {r.plot_id}: geometry_ok={r.geometry_ok}, detection={r.detection!r}"
        )


def test_plot_validation_invariant_enforced_at_construction():
    """PlotValidation.__post_init__ raises AssertionError on geometry_ok/detection mismatch."""
    # Valid combinations — no error
    PlotValidation("P1", True, "inconclusive", 100.0, "polygon", None, {})
    PlotValidation("P2", False, "geometry_invalid", 0.0, "unknown", FIX_MESSAGE, None)

    # Invalid combination — geometry_ok=True with detection=geometry_invalid
    with pytest.raises(AssertionError):
        PlotValidation("bad1", True, "geometry_invalid", 0.0, "polygon", None, {})

    # Invalid combination — geometry_ok=False with detection=inconclusive
    with pytest.raises(AssertionError):
        PlotValidation("bad2", False, "inconclusive", 100.0, "polygon", None, {})


# ── KML ───────────────────────────────────────────────────────────────────────

_KML_VALID = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Plot KML 1</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              117.123456,-0.123456,0
              117.133456,-0.123456,0
              117.133456,-0.133456,0
              117.123456,-0.133456,0
              117.123456,-0.123456,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Plot KML 2</name>
      <Point>
        <coordinates>117.123456,-0.123456,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""

_KML_LOW_PREC = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Bad Plot</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              117.1235,-0.1235,0
              117.1335,-0.1235,0
              117.1335,-0.1335,0
              117.1235,-0.1335,0
              117.1235,-0.1235,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""


def test_kml_valid_polygon_parses_ok():
    """KML Polygon with ≥6 decimal coords → geometry_ok, plot_id from <name>."""
    results = parse_plots(_KML_VALID, "kml")
    assert len(results) == 2
    assert results[0].plot_id == "Plot KML 1"
    assert results[0].geometry_ok is True
    assert results[0].detection == "inconclusive"
    assert results[0].geometry_type == "polygon"


def test_kml_valid_point_parses_ok():
    """KML Point (second Placemark in _KML_VALID) → geometry_ok, point type."""
    results = parse_plots(_KML_VALID, "kml")
    assert results[1].plot_id == "Plot KML 2"
    assert results[1].geometry_ok is True
    assert results[1].geometry_type == "point"


def test_kml_low_precision_coords_invalid():
    """KML with <6 decimal coords → geometry_invalid."""
    results = parse_plots(_KML_LOW_PREC, "kml")
    assert len(results) == 1
    assert results[0].geometry_ok is False
    assert results[0].detection == "geometry_invalid"


# ── SHP (import-guard) ────────────────────────────────────────────────────────

def test_shp_without_pyshp_returns_helpful_message(monkeypatch):
    """If pyshp is not installed, SHP parse returns a geometry_invalid with an install hint."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "shapefile":
            raise ImportError("No module named 'shapefile'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    results = parse_plots(b"fake shp bytes", "shapefile")
    assert len(results) == 1
    r = results[0]
    assert r.geometry_ok is False
    assert r.detection == "geometry_invalid"
    assert "pyshp" in (r.fix_message or "").lower() or "shapefile" in (r.fix_message or "").lower()
