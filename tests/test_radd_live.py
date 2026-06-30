"""tests/test_radd_live.py — mocked tests for the RADD live-query path (WO-EUDR-RADD-LIVE-005B).

All tests are offline: httpx.post is monkeypatched so no real network calls are made and
the RADD_API_KEY never appears in logs, responses, or fixtures.

Coverage:
  - Alert present          → alert_after_cutoff=True  + datasets_version from live source
  - No alerts found        → alert_after_cutoff=False (genuine negative, queried OK)
  - HTTP error             → alert_after_cutoff=None  (unavailable, never fabricated False)
  - Non-200 status         → alert_after_cutoff=None
  - Malformed body (non-dict) → alert_after_cutoff=None
  - Malformed body (data not list) → alert_after_cutoff=None
  - Key missing            → stub (None) without any live call
  - RADD_DISABLE_LIVE=true → stub (None) even when key is present
  - Default URL constant   → points to wur_radd_alerts dataset
  - Key is NEVER logged    (scan captured log output)
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from core.contracts import Boundary
from core.overlays.radd import (
    RADDResult,
    _DEFAULT_RADD_URL,
    _DATASETS_VERSION,
    _DATASETS_VERSION_STUB,
    _EUDR_CUTOFF_DATE,
    _query_live,
    query_radd,
)

# ── Minimal boundary (no real geometry needed for live-path unit tests) ────────

_BOUNDARY = Boundary(
    geojson={"type": "Polygon", "coordinates": [[[113.0, -1.0], [113.1, -1.0],
             [113.1, -0.9], [113.0, -0.9], [113.0, -1.0]]]},
    area_ha=490.0,
    centroid_lat=-1.0,
    centroid_lon=113.0,
    is_valid=True,
    within_indonesia=True,
    source_fmt="geojson",
)

_FAKE_API_URL = "https://data-api.globalforestwatch.org/dataset/wur_radd_alerts/latest/query"
_FAKE_KEY = "test-key-never-logged"


def _mock_resp(json_body: object, status: int = 200) -> MagicMock:
    """Build a fake httpx.Response-like mock."""
    m = MagicMock()
    m.json.return_value = json_body
    m.status_code = status
    if status >= 400:
        from httpx import HTTPStatusError, Request, Response
        # raise_for_status must actually raise for the error path to trigger
        req = MagicMock(spec=Request)
        resp = MagicMock(spec=Response)
        resp.status_code = status
        m.raise_for_status.side_effect = HTTPStatusError(
            f"HTTP {status}", request=req, response=resp
        )
    else:
        m.raise_for_status.return_value = None
    return m


# ── Default URL ────────────────────────────────────────────────────────────────

def test_default_url_points_to_wur_radd_alerts():
    assert "wur_radd_alerts" in _DEFAULT_RADD_URL
    assert "data-api.globalforestwatch.org" in _DEFAULT_RADD_URL


# ── Live path: alert present ──────────────────────────────────────────────────

def test_live_alert_present():
    """GFW returns n>0 → alert_after_cutoff=True with the live datasets_version."""
    resp = _mock_resp({"status": "success", "data": [{"latest": "2023-08-14", "n": 5}]})
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is True
    assert result.latest_alert_date == "2023-08-14"
    assert result.datasets_version == _DATASETS_VERSION


def test_live_alert_present_high_count():
    resp = _mock_resp({"status": "success", "data": [{"latest": "2024-01-01", "n": 128}]})
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is True
    assert result.datasets_version == _DATASETS_VERSION


# ── Live path: no alerts (genuine negative) ───────────────────────────────────

def test_live_no_alerts_empty_data():
    """GFW returns empty data list → alert_after_cutoff=False (genuinely queried, none found)."""
    resp = _mock_resp({"status": "success", "data": []})
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is False
    assert result.latest_alert_date is None
    assert result.datasets_version == _DATASETS_VERSION


def test_live_no_alerts_n_zero():
    """Row returned but n==0 → alert_after_cutoff=False."""
    resp = _mock_resp({"status": "success", "data": [{"latest": None, "n": 0}]})
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is False


# ── Live path: failures → None (never fabricated False) ──────────────────────

def test_live_connection_error_returns_none():
    """Network error → alert_after_cutoff=None (never a fabricated False)."""
    import httpx
    with patch("httpx.post", side_effect=httpx.ConnectError("timeout")):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is None


def test_live_http_4xx_returns_none():
    """Non-200 HTTP status → alert_after_cutoff=None."""
    resp = _mock_resp({}, status=403)
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is None


def test_live_malformed_body_non_dict_returns_none():
    """Response body is not a dict → alert_after_cutoff=None."""
    resp = _mock_resp(["unexpected", "list"])
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is None


def test_live_malformed_body_data_not_list_returns_none():
    """'data' field is not a list → alert_after_cutoff=None."""
    resp = _mock_resp({"status": "success", "data": "unexpected_string"})
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is None


def test_live_missing_data_field_returns_none():
    """Response dict has no 'data' key → alert_after_cutoff=None."""
    resp = _mock_resp({"status": "success"})
    with patch("httpx.post", return_value=resp):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert result.alert_after_cutoff is None


# ── query_radd public API: key missing → stub ─────────────────────────────────

_NO_FIXTURE_BOUNDARY = Boundary(
    geojson={"type": "Polygon", "coordinates": [[[120.0, 5.0], [120.1, 5.0],
             [120.1, 5.1], [120.0, 5.1], [120.0, 5.0]]]},
    area_ha=100.0, centroid_lat=5.05, centroid_lon=120.05,
    is_valid=True, within_indonesia=True, source_fmt="geojson",
)


def test_no_key_returns_stub(monkeypatch):
    """Without RADD_API_KEY, returns alert_after_cutoff=None without any live call.

    Uses a coordinate with no committed fixture so the fixture path is bypassed.
    """
    monkeypatch.delenv("RADD_API_KEY", raising=False)
    monkeypatch.delenv("RADD_DISABLE_LIVE", raising=False)

    called = []
    with patch("httpx.post", side_effect=lambda *a, **kw: called.append(1)):
        result = query_radd(_NO_FIXTURE_BOUNDARY)

    assert result.alert_after_cutoff is None
    assert not called, "httpx.post must NOT be called when RADD_API_KEY is missing"


# ── query_radd public API: RADD_DISABLE_LIVE ─────────────────────────────────

def test_disable_live_skips_live_call(monkeypatch):
    """RADD_DISABLE_LIVE=true skips live even when key is present."""
    monkeypatch.setenv("RADD_API_KEY", _FAKE_KEY)
    monkeypatch.setenv("RADD_DISABLE_LIVE", "true")
    # Use a coordinate with no committed fixture so the live path would normally run.
    no_fixture_boundary = Boundary(
        geojson={"type": "Polygon", "coordinates": [[[120.0, 5.0], [120.1, 5.0],
                 [120.1, 5.1], [120.0, 5.1], [120.0, 5.0]]]},
        area_ha=100.0, centroid_lat=5.05, centroid_lon=120.05,
        is_valid=True, within_indonesia=True, source_fmt="geojson",
    )
    called = []
    with patch("httpx.post", side_effect=lambda *a, **kw: called.append(1)):
        result = query_radd(no_fixture_boundary)

    assert result.alert_after_cutoff is None
    assert not called, "httpx.post must NOT be called when RADD_DISABLE_LIVE=true"


def test_disable_live_uses_stub_datasets_version(monkeypatch):
    monkeypatch.setenv("RADD_API_KEY", _FAKE_KEY)
    monkeypatch.setenv("RADD_DISABLE_LIVE", "true")
    no_fixture_boundary = Boundary(
        geojson={"type": "Polygon", "coordinates": [[[120.0, 5.0], [120.1, 5.0],
                 [120.1, 5.1], [120.0, 5.1], [120.0, 5.0]]]},
        area_ha=100.0, centroid_lat=5.05, centroid_lon=120.05,
        is_valid=True, within_indonesia=True, source_fmt="geojson",
    )
    with patch("httpx.post", side_effect=AssertionError("must not call")):
        result = query_radd(no_fixture_boundary)
    assert result.datasets_version == _DATASETS_VERSION_STUB


# ── Key is NEVER logged ────────────────────────────────────────────────────────

def test_key_never_appears_in_log_output(caplog):
    """The RADD API key must never appear in any log message."""
    import httpx
    with caplog.at_level(logging.WARNING, logger="core.overlays.radd"):
        with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
            _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)

    full_log = " ".join(r.getMessage() for r in caplog.records)
    assert _FAKE_KEY not in full_log, (
        f"RADD API key appeared in log output: {full_log!r}"
    )


def test_key_never_appears_in_result_note():
    """The RADD API key must not leak into result.note."""
    import httpx
    with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
        result = _query_live(_BOUNDARY, _FAKE_API_URL, _FAKE_KEY, _EUDR_CUTOFF_DATE)
    assert _FAKE_KEY not in (result.note or "")


# ── URL override ──────────────────────────────────────────────────────────────

def test_radd_gfw_api_url_env_override(monkeypatch):
    """RADD_GFW_API_URL overrides the default endpoint."""
    custom_url = "https://custom.example.com/radd/query"
    monkeypatch.setenv("RADD_API_KEY", _FAKE_KEY)
    monkeypatch.setenv("RADD_GFW_API_URL", custom_url)
    monkeypatch.delenv("RADD_DISABLE_LIVE", raising=False)

    no_fixture_boundary = Boundary(
        geojson={"type": "Polygon", "coordinates": [[[120.0, 5.0], [120.1, 5.0],
                 [120.1, 5.1], [120.0, 5.1], [120.0, 5.0]]]},
        area_ha=100.0, centroid_lat=5.05, centroid_lon=120.05,
        is_valid=True, within_indonesia=True, source_fmt="geojson",
    )
    captured_urls = []

    def _capture(url, **kw):
        captured_urls.append(url)
        m = _mock_resp({"status": "success", "data": []})
        return m

    with patch("httpx.post", side_effect=_capture):
        query_radd(no_fixture_boundary)

    assert captured_urls == [custom_url], f"Expected {custom_url!r}, got {captured_urls}"
