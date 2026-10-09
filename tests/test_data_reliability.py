"""Behavior checks for current data, real polygon reads and production isolation."""
from unittest.mock import Mock

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from fastapi.testclient import TestClient

from core.contracts import Boundary, CarbonInput, ContactInfo, GeoInput, ForestData
from core.data.gfw import GFWHTTPAdapter
from core.data.cache import CachedAdapter
from core.overlays.hansen_loss import _query_live
from core.overlays.jrc_gfc2020 import _read_forest_share
from core.overlays._cache import load_fixture
from engines.carbon.engine import run_carbon_engine
from api.main import app
from api import site


def boundary():
    return Boundary(geojson={"type": "Polygon", "coordinates": [[[113., -1.], [113.0006, -1.], [113.0006, -1.0012], [113., -1.0012], [113., -1.]]]},
                    area_ha=1, centroid_lat=-1.0006, centroid_lon=113.0003,
                    is_valid=True, within_indonesia=True, source_fmt="geojson")


def raster(monkeypatch, values, nodata=255):
    mem = MemoryFile()
    with mem.open(driver="GTiff", height=4, width=4, count=1, dtype="uint8", crs="EPSG:4326", transform=from_origin(113., -1., .0003, .0003), nodata=nodata) as src:
        src.write(np.array(values, dtype="uint8"), 1)
    monkeypatch.setattr(rasterio, "open", lambda *a, **kw: mem.open())
    return mem


def test_current_hansen_finds_2024_2025_and_excludes_neighbours(monkeypatch):
    mem = raster(monkeypatch, [[24,0,25,25], [0,25,24,24], [0,0,23,23], [0,0,23,23]])
    result = _query_live(boundary(), 2020)
    assert result.available and result.loss_after_2020_ha > 0
    assert "2024, 2025" in result.note
    annual, sources, _ = GFWHTTPAdapter()._query_annual_loss(boundary())
    assert annual[2023] == 0 and annual[2024] > 0 and annual[2025] > 0
    assert result.loss_after_2020_ha == pytest.approx(annual[2024] + annual[2025], abs=.01)
    assert "GFC-2025-v1.13" in sources[0]
    mem.close()


def test_nodata_inside_plot_never_becomes_zero_loss(monkeypatch):
    mem = raster(monkeypatch, [[255,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,0]])
    assert _query_live(boundary(), 2020).loss_after_2020_ha is None
    assert GFWHTTPAdapter()._query_annual_loss(boundary())[0] == {}
    mem.close()


def test_jrc_excludes_forest_outside_polygon(monkeypatch):
    mem = raster(monkeypatch, [[0,0,1,1]] * 4)
    result = _read_forest_share(boundary(), (113., -1.0012, 113.0006, -1.), "JRC_GFC2020_V4_COG.tif")
    assert result.forest_2020 is False and result.forest_pct == 0
    mem.close()


def test_production_does_not_load_committed_overlay_samples(monkeypatch):
    monkeypatch.delenv("SCREENING_USE_TEST_FIXTURES")
    assert load_fixture("jrc_gfc2020", -1., 113.) is None


def test_production_cache_distinguishes_shapes_and_current_release(monkeypatch, tmp_path):
    monkeypatch.delenv("SCREENING_USE_TEST_FIXTURES")
    adapter = CachedAdapter(Mock(), cache_dir=tmp_path)
    a = boundary()
    b = a.model_copy(update={"geojson": {"type": "Point", "coordinates": [113.0003, -1.0006]}})
    assert adapter._key(a) != adapter._key(b)


def test_carbon_missing_live_data_has_no_quantity():
    inp = CarbonInput(contact=ContactInfo(name="Synthetic QA", email="qa@example.test"), iup_name="Synthetic", iup_address="Indonesia", permit_type="HTI", permit_years_remaining=20, project_type="REDD", geo=GeoInput(fmt="coords", payload="-1,113"))
    forest = ForestData(annual_loss_ha={}, baseline_cover_pct=0, loss_after_2020_ha=0, data_sources=["Hansen loss data unavailable"], uncertainty_band="unavailable")
    result = run_carbon_engine(inp, boundary().model_copy(update={"area_ha": 30000}), forest)
    assert result.eligibility.verdict == "flagged"
    assert result.quantity_low_tco2e is None and result.quantity_high_tco2e is None


def test_data_health_reports_failure_even_when_process_is_up(monkeypatch):
    monkeypatch.delenv("SCREENING_USE_TEST_FIXTURES")
    monkeypatch.setattr(site, "_cached", None)
    monkeypatch.setattr(site.httpx, "head", lambda url, **kw: Mock(status_code=404 if "JRC" in url else 200))
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    response = client.get("/health/data")
    assert response.status_code == 503 and response.json()["status"] == "degraded"
    monkeypatch.setattr(site, "_cached", None)


def test_public_methodology_and_safe_crawl_urls():
    client = TestClient(app)
    assert client.get("/methodology").status_code == 200
    assert "30-year illustrative" in client.get("/methodology").text
    assert "evil.example" not in client.get("/sitemap.xml", headers={"host": "evil.example"}).text
    assert "Disallow: /fieldwork/status" in client.get("/robots.txt").text


def test_invalid_or_unread_plots_never_get_complete_screening_readiness():
    from api.main import _build_readiness
    for invalid, inconclusive in ((1, 0), (0, 1)):
        readiness = _build_readiness(invalid, 0, inconclusive)
        assert readiness[1]["status"] == "incomplete"
        assert readiness[2]["status"] == "incomplete"


def test_small_loss_finding_does_not_claim_zero_or_radar_detection():
    from api.main import _eudr_finding_detail
    verdict = Mock(detection="loss_detected", loss_after_2020_ha=1.32)
    finding = _eudr_finding_detail(verdict, 492.3)
    assert "0.3%" in finding and "2026" in finding
    assert "RADD radar" not in finding
