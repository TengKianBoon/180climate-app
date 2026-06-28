"""tests/test_overlay_adapters.py — Unit tests for KHG + PIPPIB live/snapshot adapters.

All tests are deterministic (no real network calls):
- KHG tests monkeypatch httpx.post
- PIPPIB tests use a temp GeoJSON file
- The @pytest.mark.network test is skipped unless --run-network is passed
"""
from __future__ import annotations
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from core.contracts import Boundary, OverlayIntersection
from core.overlays.khg import query_khg, _geojson_to_esri, _query_live
from core.overlays.pippib import query_pippib, _query_snapshot, _load_snapshot, _query_live as _pippib_query_live


# ── shared fixture ────────────────────────────────────────────────────────────

@pytest.fixture
def kalimantan_mineral_boundary():
    """A small mineral forest polygon in East Kalimantan — no overlay fixture committed."""
    # centroid ~(-0.300, 117.200) — chosen to NOT match any committed fixture
    geojson = {
        "type": "Polygon",
        "coordinates": [[[117.10, -0.25], [117.30, -0.25], [117.30, -0.35], [117.10, -0.35], [117.10, -0.25]]]
    }
    return Boundary(
        geojson=geojson,
        area_ha=20000.0,
        centroid_lat=-0.300,
        centroid_lon=117.200,
        is_valid=True,
        within_indonesia=True,
        source_fmt="geojson",
    )


# ── KHG tests ─────────────────────────────────────────────────────────────────

def test_khg_geojson_to_esri_polygon():
    """Polygon GeoJSON converts to Esri rings format."""
    geojson = {"type": "Polygon", "coordinates": [[[100.0, -1.0], [101.0, -1.0], [101.0, -2.0], [100.0, -1.0]]]}
    esri = _geojson_to_esri(geojson)
    assert "rings" in esri
    assert esri["spatialReference"]["wkid"] == 4326
    assert esri["rings"] == geojson["coordinates"]


def test_khg_geojson_to_esri_multipolygon():
    """MultiPolygon GeoJSON flattens all rings."""
    geojson = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[100.0, -1.0], [101.0, -1.0], [100.0, -1.0]]],
            [[[102.0, -2.0], [103.0, -2.0], [102.0, -2.0]]],
        ]
    }
    esri = _geojson_to_esri(geojson)
    assert len(esri["rings"]) == 2


def test_khg_fixture_used_over_live(kalimantan_mineral_boundary, tmp_path, monkeypatch):
    """When a fixture exists, the live query is never called."""
    # Write a temporary fixture
    fixture_dir = tmp_path / "overlays"
    fixture_dir.mkdir()
    lat, lon = kalimantan_mineral_boundary.centroid_lat, kalimantan_mineral_boundary.centroid_lon
    fname = fixture_dir / f"khg_{lat:.3f}_{lon:.3f}.json"
    fname.write_text(json.dumps({"intersects": False, "area_ha": None}), encoding="utf-8")

    monkeypatch.setattr("core.overlays._cache._FIXTURE_DIR", fixture_dir)
    called = []
    monkeypatch.setattr("core.overlays.khg._query_live", lambda b, u: called.append(True) or OverlayIntersection(intersects=None, source="test"))
    result = query_khg(kalimantan_mineral_boundary)
    assert result.intersects is False
    assert not called, "Live query should NOT be called when fixture exists"


def test_khg_live_no_features_returns_false(kalimantan_mineral_boundary):
    """Live query with no features returned → intersects=False."""
    import httpx as httpx_mod
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"features": []}
    with patch.object(httpx_mod, "post", lambda *a, **kw: mock_resp):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is False


def test_khg_live_with_feature_returns_true(kalimantan_mineral_boundary):
    """Live query with a feature returned → intersects=True."""
    import httpx as httpx_mod
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "features": [{"attributes": {"kode_khg": "KHG-KAL-001", "peat_thick": ">3m", "feg_50k": "Fungsi Lindung E.G."}}]
    }
    with patch.object(httpx_mod, "post", lambda *a, **kw: mock_resp):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is True
    assert "KHG-KAL-001" in result.note


def test_khg_live_network_failure_returns_none(kalimantan_mineral_boundary):
    """Network failure → intersects=None (ADR-0013: failure must not return False)."""
    import httpx as httpx_mod

    def raise_connect_error(*a, **kw):
        raise httpx_mod.ConnectError("timeout")

    with patch.object(httpx_mod, "post", raise_connect_error):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is None, "INVARIANT: network failure must return None, not False"


def test_khg_live_server_error_returns_none(kalimantan_mineral_boundary):
    """Server-side error JSON → intersects=None."""
    import httpx as httpx_mod
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"error": {"code": 400, "message": "Bad request"}}
    with patch.object(httpx_mod, "post", lambda *a, **kw: mock_resp):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is None


def test_khg_disable_live_returns_none(kalimantan_mineral_boundary, monkeypatch):
    """KHG_DISABLE_LIVE=true → intersects=None without making any HTTP call."""
    monkeypatch.setenv("KHG_DISABLE_LIVE", "true")
    with patch("core.overlays._cache.load_fixture", return_value=None):
        result = query_khg(kalimantan_mineral_boundary)
    assert result.intersects is None


# ── PIPPIB tests ──────────────────────────────────────────────────────────────

@pytest.fixture
def pippib_snapshot_path(tmp_path):
    """A small PIPPIB GeoJSON snapshot with one 'PIPPIB GAMBUT' polygon over Kalimantan peat."""
    fc = {
        "type": "FeatureCollection",
        "name": "PIPPIB_2026_I_AR_250K",
        "features": [
            {
                "type": "Feature",
                "properties": {"PIPPIB": "PIPPIB GAMBUT", "NAMOBJ": "Test Peat Area"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[111.0, -2.0], [114.0, -2.0], [114.0, -4.0], [111.0, -4.0], [111.0, -2.0]]]
                }
            }
        ]
    }
    path = tmp_path / "PIPPIB_2026_I.geojson"
    path.write_text(json.dumps(fc), encoding="utf-8")
    return str(path)


@pytest.fixture
def peat_boundary_hits_snapshot():
    """A small polygon inside the snapshot polygon — should return intersects=True."""
    geojson = {
        "type": "Polygon",
        "coordinates": [[[111.5, -2.5], [112.0, -2.5], [112.0, -3.0], [111.5, -3.0], [111.5, -2.5]]]
    }
    return Boundary(
        geojson=geojson,
        area_ha=20000.0,
        centroid_lat=-2.750,
        centroid_lon=111.750,
        is_valid=True,
        within_indonesia=True,
        source_fmt="geojson",
    )


@pytest.fixture
def mineral_boundary_misses_snapshot():
    """A polygon outside the snapshot polygon — should return intersects=False."""
    geojson = {
        "type": "Polygon",
        "coordinates": [[[117.0, -0.5], [117.5, -0.5], [117.5, -1.0], [117.0, -1.0], [117.0, -0.5]]]
    }
    return Boundary(
        geojson=geojson,
        area_ha=20000.0,
        centroid_lat=-0.750,
        centroid_lon=117.250,
        is_valid=True,
        within_indonesia=True,
        source_fmt="geojson",
    )


def test_pippib_snapshot_hit(pippib_snapshot_path, peat_boundary_hits_snapshot):
    """Concession inside PIPPIB GAMBUT area → intersects=True + category captured."""
    # Clear the module-level cache first
    from core.overlays import pippib as pmod
    pmod._snapshot_cache.clear()
    result = _query_snapshot(peat_boundary_hits_snapshot, pippib_snapshot_path)
    assert result.intersects is True
    assert "PIPPIB GAMBUT" in result.note


def test_pippib_snapshot_miss(pippib_snapshot_path, mineral_boundary_misses_snapshot):
    """Concession outside all PIPPIB polygons → intersects=False."""
    from core.overlays import pippib as pmod
    pmod._snapshot_cache.clear()
    result = _query_snapshot(mineral_boundary_misses_snapshot, pippib_snapshot_path)
    assert result.intersects is False


def test_pippib_snapshot_missing_file(peat_boundary_hits_snapshot):
    """Non-existent snapshot file → intersects=None (safe failure)."""
    from core.overlays import pippib as pmod
    pmod._snapshot_cache.clear()
    result = _query_snapshot(peat_boundary_hits_snapshot, "/nonexistent/path/PIPPIB.geojson")
    assert result.intersects is None, "Missing snapshot file must return None, not False"


def test_pippib_disable_live_no_snapshot_returns_none(kalimantan_mineral_boundary, monkeypatch):
    """PIPPIB_DISABLE_LIVE=true + no snapshot + no fixture → intersects=None."""
    monkeypatch.setenv("PIPPIB_DISABLE_LIVE", "true")
    monkeypatch.delenv("PIPPIB_SNAPSHOT_PATH", raising=False)
    with patch("core.overlays._cache.load_fixture", return_value=None):
        result = query_pippib(kalimantan_mineral_boundary)
    assert result.intersects is None, "INVARIANT: live disabled + no snapshot → None"
    assert "PIPPIB_DISABLE_LIVE" in result.note


def test_pippib_snapshot_path_env_var_used(pippib_snapshot_path, peat_boundary_hits_snapshot, monkeypatch):
    """PIPPIB_DISABLE_LIVE=true + PIPPIB_SNAPSHOT_PATH → snapshot query (secondary fallback)."""
    monkeypatch.setenv("PIPPIB_DISABLE_LIVE", "true")
    monkeypatch.setenv("PIPPIB_SNAPSHOT_PATH", pippib_snapshot_path)
    from core.overlays import pippib as pmod
    pmod._snapshot_cache.clear()
    with patch("core.overlays._cache.load_fixture", return_value=None):
        result = query_pippib(peat_boundary_hits_snapshot)
    assert result.intersects is True


def test_pippib_strtree_loaded_once(pippib_snapshot_path, peat_boundary_hits_snapshot):
    """STRtree is loaded only once per path (in-memory cache)."""
    from core.overlays import pippib as pmod
    pmod._snapshot_cache.clear()
    _query_snapshot(peat_boundary_hits_snapshot, pippib_snapshot_path)
    _query_snapshot(peat_boundary_hits_snapshot, pippib_snapshot_path)
    assert len(pmod._snapshot_cache) == 1, "Snapshot should be cached after first load"


# ── PIPPIB live adapter tests (mirror KHG pattern) ───────────────────────────

def test_pippib_live_no_features_returns_false(kalimantan_mineral_boundary):
    """Live query with no features → intersects=False."""
    import httpx as httpx_mod
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"features": []}
    with patch.object(httpx_mod, "post", lambda *a, **kw: mock_resp):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _pippib_query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is False


def test_pippib_live_with_feature_returns_true_with_category(kalimantan_mineral_boundary):
    """Live query with a PIPPIB GAMBUT feature → intersects=True + category in note."""
    import httpx as httpx_mod
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "features": [{"attributes": {"pippib": "PIPPIB GAMBUT"}}]
    }
    with patch.object(httpx_mod, "post", lambda *a, **kw: mock_resp):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _pippib_query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is True
    assert "PIPPIB GAMBUT" in result.note


def test_pippib_live_network_failure_returns_none(kalimantan_mineral_boundary):
    """Network failure → intersects=None (ADR-0013: failure must not return False)."""
    import httpx as httpx_mod

    def raise_connect_error(*a, **kw):
        raise httpx_mod.ConnectError("timeout")

    with patch.object(httpx_mod, "post", raise_connect_error):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _pippib_query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is None, "INVARIANT: network failure must return None, not False"


def test_pippib_live_server_error_returns_none(kalimantan_mineral_boundary):
    """Server-side error JSON → intersects=None."""
    import httpx as httpx_mod
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"error": {"code": 400, "message": "Bad request"}}
    with patch.object(httpx_mod, "post", lambda *a, **kw: mock_resp):
        with patch("core.overlays._cache.load_fixture", return_value=None):
            result = _pippib_query_live(kalimantan_mineral_boundary, "https://example.com/MapServer")
    assert result.intersects is None


def test_pippib_disable_live_returns_none_no_http(kalimantan_mineral_boundary, monkeypatch):
    """PIPPIB_DISABLE_LIVE=true → intersects=None without any HTTP call."""
    monkeypatch.setenv("PIPPIB_DISABLE_LIVE", "true")
    monkeypatch.delenv("PIPPIB_SNAPSHOT_PATH", raising=False)
    with patch("core.overlays._cache.load_fixture", return_value=None):
        result = query_pippib(kalimantan_mineral_boundary)
    assert result.intersects is None


def test_pippib_fixture_used_over_live(kalimantan_mineral_boundary, tmp_path, monkeypatch):
    """When a fixture exists, the live query is never called."""
    fixture_dir = tmp_path / "overlays"
    fixture_dir.mkdir()
    lat, lon = kalimantan_mineral_boundary.centroid_lat, kalimantan_mineral_boundary.centroid_lon
    fname = fixture_dir / f"pippib_{lat:.3f}_{lon:.3f}.json"
    fname.write_text(json.dumps({"intersects": False, "area_ha": None}), encoding="utf-8")

    monkeypatch.setattr("core.overlays._cache._FIXTURE_DIR", fixture_dir)
    called = []
    monkeypatch.setattr(
        "core.overlays.pippib._query_live",
        lambda b, u: called.append(True) or OverlayIntersection(intersects=None, source="test"),
    )
    result = query_pippib(kalimantan_mineral_boundary)
    assert result.intersects is False
    assert not called, "Live query should NOT be called when fixture exists"


# ── Network-marked live smoke tests (skipped in CI) ──────────────────────────

_SOURCE_KHG = "KHG fungsi-lindung (PP57/2016) — BIG One Map"


@pytest.mark.network
@pytest.mark.skipif(
    os.environ.get("CI", "").lower() == "true",
    reason="Live network test — skipped in CI (set CI=true to skip)"
)
def test_khg_live_smoke_mineral_land():
    """Live smoke test: BIG KHG query on East Kalimantan mineral land.

    Expects a real response (not None). Exact intersects value may be True or False
    depending on the polygon's position — we only assert it is NOT None (endpoint up + working).

    Run with: pytest tests/test_overlay_adapters.py::test_khg_live_smoke_mineral_land -m network
    """
    geojson = {
        "type": "Polygon",
        "coordinates": [[[117.10, -0.25], [117.30, -0.25], [117.30, -0.35], [117.10, -0.35], [117.10, -0.25]]]
    }
    boundary = Boundary(
        geojson=geojson,
        area_ha=20000.0,
        centroid_lat=-0.300,
        centroid_lon=117.200,
        is_valid=True,
        within_indonesia=True,
        source_fmt="geojson",
    )
    from core.overlays.khg import _query_live, _DEFAULT_BASE
    result = _query_live(boundary, _DEFAULT_BASE)
    assert result.intersects is not None, (
        f"Live KHG query returned None — endpoint may be down. Note: {result.note}"
    )
    assert result.source == _SOURCE_KHG


_SOURCE_PIPPIB = "PIPPIB moratorium (Inpres5/2019) — BIG One Map / Kementerian Kehutanan"


@pytest.mark.network
@pytest.mark.skipif(
    os.environ.get("CI", "").lower() == "true",
    reason="Live network test — skipped in CI (set CI=true to skip)"
)
def test_pippib_live_smoke_peat_point():
    """Live smoke test: BIG PIPPIB query on a known peat point (113.9, -2.6).

    Point 113.9,-2.6 (Central Kalimantan) was live-tested per INBOX and returned
    {"pippib":"PIPPIB KAWASAN"}. We assert intersects=True and category in note.

    Run with: pytest tests/test_overlay_adapters.py::test_pippib_live_smoke_peat_point -m network
    """
    geojson = {
        "type": "Polygon",
        "coordinates": [[[113.85, -2.55], [113.95, -2.55], [113.95, -2.65], [113.85, -2.65], [113.85, -2.55]]]
    }
    boundary = Boundary(
        geojson=geojson,
        area_ha=5000.0,
        centroid_lat=-2.600,
        centroid_lon=113.900,
        is_valid=True,
        within_indonesia=True,
        source_fmt="geojson",
    )
    from core.overlays.pippib import _query_live as pippib_live, _DEFAULT_BASE as PIPPIB_BASE
    result = pippib_live(boundary, PIPPIB_BASE)
    assert result.intersects is not None, (
        f"Live PIPPIB query returned None — endpoint may be down. Note: {result.note}"
    )
    assert result.source == _SOURCE_PIPPIB
