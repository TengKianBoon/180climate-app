"""tests/test_eudr_triage.py — EUDR per-plot satellite triage engine (WO-EUDR-TRIAGE-003, E3).

Fully deterministic and offline:
- Detection-logic unit tests call the pure `_decide_detection` directly (no I/O).
- End-to-end tests drive committed fixtures in tests/fixtures/overlays/ (jrc_gfc2020_*,
  hansen_loss_*, radd_*) — the live HTTP path is never touched.
- *_DISABLE_LIVE switches are exercised to prove the CI kill-switches work.
"""
from __future__ import annotations

from datetime import date

import pytest

from core.contracts import Boundary, PlotVerdict
from core.overlays.hansen_loss import query_hansen_loss
from core.overlays.jrc_gfc2020 import query_jrc_gfc2020, _jrc_tile_name, _jrc_url
from core.overlays.radd import query_radd
from engines.eudr.triage import (
    EUDR_CUTOFF_DATE,
    EUDR_CUTOFF_YEAR,
    _boundary_from_geojson,
    _decide_detection,
    triage_plot,
    triage_validated_plots,
)

_RUN_DATE = date(2026, 6, 30)


# ── Test plot geometries (centroid rounds EXACTLY to a committed fixture coord) ──

def _square(center_lon: float, center_lat: float, half: float = 0.01) -> dict:
    """A symmetric square polygon centred on (center_lon, center_lat) — centroid is exact."""
    w, e = round(center_lon - half, 6), round(center_lon + half, 6)
    s, n = round(center_lat - half, 6), round(center_lat + half, 6)
    return {
        "type": "Polygon",
        "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    }


# Each centred so the shapely centroid → the fixture's {lat:.3f}_{lon:.3f} key.
_PLOT_LOSS = _square(113.000, -1.000)      # fixtures at -1.000_113.000
_PLOT_CLEAR = _square(114.000, -2.000)     # fixtures at -2.000_114.000
_PLOT_NO_BASELINE = _square(110.000, 1.500)   # fixtures at 1.500_110.000
_PLOT_HANSEN_GAP = _square(116.500, -0.750)   # fixtures at -0.750_116.500


# ── Pure detection-logic truth table ──────────────────────────────────────────

@pytest.mark.parametrize(
    "forest_2020, hansen_loss_ha, radd_alert, expected",
    [
        # loss_detected: forest baseline + a positive loss signal
        (True, 12.4, True, "loss_detected"),
        (True, 12.4, False, "loss_detected"),
        (True, 12.4, None, "loss_detected"),
        (True, 0.0, True, "loss_detected"),     # RADD caught loss Hansen missed
        (True, None, True, "loss_detected"),    # radar-only loss on a baseline
        # clear_in_screen: forest baseline + Hansen-confirmed zero loss + no RADD alert
        (True, 0.0, False, "clear_in_screen"),
        (True, 0.0, None, "clear_in_screen"),   # RADD None is allowed (enriches, not blocks)
        # inconclusive: Hansen unavailable on a baseline (cannot confirm no-loss)
        (True, None, False, "inconclusive"),
        (True, None, None, "inconclusive"),
        # inconclusive: no/unknown 2020 forest baseline — NEVER clear
        (False, 0.0, False, "inconclusive"),
        (False, 0.0, None, "inconclusive"),
        (None, 0.0, False, "inconclusive"),
        (None, None, None, "inconclusive"),
        # honesty: a positive loss signal but NO confirmed baseline → not loss_detected
        (None, 12.4, True, "inconclusive"),
        (False, 12.4, True, "inconclusive"),
    ],
)
def test_decide_detection_truth_table(forest_2020, hansen_loss_ha, radd_alert, expected):
    assert _decide_detection(forest_2020, hansen_loss_ha, radd_alert) == expected


def test_honesty_rule_never_clear_when_in_doubt():
    """Exhaustive sweep: clear_in_screen ONLY when forest_2020 is True AND Hansen==0."""
    for forest in (True, False, None):
        for loss in (None, 0.0, 5.0):
            for radd in (True, False, None):
                det = _decide_detection(forest, loss, radd)
                if det == "clear_in_screen":
                    assert forest is True and loss == 0.0 and radd is not True, (
                        f"clear_in_screen leaked for forest={forest}, loss={loss}, radd={radd}"
                    )


# ── End-to-end triage via fixtures ─────────────────────────────────────────────

def test_triage_loss_detected():
    """Forest cleared post-2020 → loss_detected (+ stamps)."""
    pv = triage_plot("P_loss", _PLOT_LOSS, "palm", area_ha=490.0, run_date=_RUN_DATE)
    assert isinstance(pv, PlotVerdict)
    assert pv.detection == "loss_detected"
    assert pv.loss_after_2020_ha == 12.4
    assert pv.commodity == "palm"
    # computed fields follow detection
    assert pv.geometry_ok is True
    assert pv.plot_satellite_risk == "high"


def test_triage_clear_in_screen():
    """Intact 2020 forest, no post-2020 loss → clear_in_screen."""
    pv = triage_plot("P_clear", _PLOT_CLEAR, "rubber", area_ha=490.0, run_date=_RUN_DATE)
    assert pv.detection == "clear_in_screen"
    assert pv.loss_after_2020_ha == 0.0
    assert pv.geometry_ok is True
    assert pv.plot_satellite_risk == "low"


def test_triage_inconclusive_no_baseline():
    """No 2020 forest baseline (cropland) → inconclusive, never clear."""
    pv = triage_plot("P_nobase", _PLOT_NO_BASELINE, "cocoa", area_ha=490.0, run_date=_RUN_DATE)
    assert pv.detection == "inconclusive"
    assert pv.plot_satellite_risk == "inconclusive"


def test_triage_inconclusive_hansen_unavailable():
    """Forest baseline present but Hansen unavailable → inconclusive (cannot confirm no-loss)."""
    pv = triage_plot("P_gap", _PLOT_HANSEN_GAP, "timber", area_ha=490.0, run_date=_RUN_DATE)
    assert pv.detection == "inconclusive"
    # Hansen None surfaces as 0.0 in the verdict, but detection is correctly inconclusive.
    assert pv.loss_after_2020_ha == 0.0


def test_triage_stamps_present():
    """Every verdict carries datasets_version (3 datasets) + run_date."""
    pv = triage_plot("P_loss", _PLOT_LOSS, "palm", area_ha=490.0, run_date=_RUN_DATE)
    assert pv.run_date == _RUN_DATE
    assert "JRC GFC2020" in pv.datasets_version
    assert "Hansen" in pv.datasets_version
    assert "RADD" in pv.datasets_version


def test_triage_deterministic():
    """Same plot twice → byte-identical verdict (determinism invariant)."""
    a = triage_plot("P_loss", _PLOT_LOSS, "palm", area_ha=490.0, run_date=_RUN_DATE)
    b = triage_plot("P_loss", _PLOT_LOSS, "palm", area_ha=490.0, run_date=_RUN_DATE)
    assert a.model_dump() == b.model_dump()


# ── Batch + geometry_invalid skip ──────────────────────────────────────────────

class _FakeValidation:
    """Stand-in for engines.eudr.geometry.PlotValidation (duck-typed for the batch API)."""

    def __init__(self, plot_id, detection, geometry_ok, geojson, area_ha=490.0):
        self.plot_id = plot_id
        self.detection = detection
        self.geometry_ok = geometry_ok
        self.geojson = geojson
        self.area_ha = area_ha


def test_batch_triage_mixed_with_geometry_invalid_skip(monkeypatch):
    """geometry_invalid plots are passed through WITHOUT any adapter call; valid ones screened."""
    # Trip-wire: if triage_plot's adapters run on the invalid plot, this fixture-less coord
    # would hit the (disabled) live path. We assert no adapter is called for the invalid plot
    # by counting triage_plot invocations.
    calls: list[str] = []
    import engines.eudr.triage as triage_mod

    real_triage_plot = triage_mod.triage_plot

    def _counting_triage_plot(plot_id, geojson, commodity, **kw):
        calls.append(plot_id)
        return real_triage_plot(plot_id, geojson, commodity, **kw)

    monkeypatch.setattr(triage_mod, "triage_plot", _counting_triage_plot)

    validations = [
        _FakeValidation("good", "inconclusive", True, _PLOT_LOSS),
        _FakeValidation("bad", "geometry_invalid", False, None),
    ]
    verdicts = triage_mod.triage_validated_plots(validations, "palm", run_date=_RUN_DATE)

    assert len(verdicts) == 2
    by_id = {v.plot_id: v for v in verdicts}
    assert by_id["good"].detection == "loss_detected"
    assert by_id["bad"].detection == "geometry_invalid"
    assert "geometry invalid" in by_id["bad"].datasets_version.lower()
    # the invalid plot must NOT have been screened
    assert calls == ["good"], f"adapters ran on a geometry_invalid plot: {calls}"


def test_batch_preserves_order_and_count():
    validations = [
        _FakeValidation("a", "inconclusive", True, _PLOT_LOSS),
        _FakeValidation("b", "inconclusive", True, _PLOT_CLEAR),
        _FakeValidation("c", "inconclusive", True, _PLOT_NO_BASELINE),
    ]
    verdicts = triage_validated_plots(validations, "palm", run_date=_RUN_DATE)
    assert [v.plot_id for v in verdicts] == ["a", "b", "c"]
    assert [v.detection for v in verdicts] == [
        "loss_detected",
        "clear_in_screen",
        "inconclusive",
    ]


# ── Adapter-level: fixture loading + DISABLE_LIVE kill-switches ─────────────────

def _boundary(plot_geojson) -> Boundary:
    return _boundary_from_geojson(plot_geojson, area_ha=490.0)


def test_jrc_adapter_reads_fixture():
    res = query_jrc_gfc2020(_boundary(_PLOT_LOSS))
    assert res.forest_2020 is True
    assert res.available is True
    assert res.datasets_version


def test_hansen_adapter_reads_fixture():
    res = query_hansen_loss(_boundary(_PLOT_LOSS), cutoff_year=EUDR_CUTOFF_YEAR)
    assert res.loss_after_2020_ha == 12.4
    assert res.has_post_cutoff_loss is True


def test_hansen_adapter_none_is_unavailable_not_zero():
    res = query_hansen_loss(_boundary(_PLOT_HANSEN_GAP))
    assert res.loss_after_2020_ha is None
    assert res.available is False
    assert res.has_post_cutoff_loss is None  # cannot assert no-loss


def test_radd_adapter_reads_fixture():
    res = query_radd(_boundary(_PLOT_LOSS), cutoff_date=EUDR_CUTOFF_DATE)
    assert res.alert_after_cutoff is True
    assert res.latest_alert_date == "2023-08-14"


def test_disable_live_switches_return_unavailable(monkeypatch):
    """With no fixture present and *_DISABLE_LIVE=true, adapters return unavailable (None)."""
    # A coordinate with NO committed fixture.
    nowhere = _square(120.000, 5.000)
    monkeypatch.setenv("JRC_GFC2020_DISABLE_LIVE", "true")
    monkeypatch.setenv("HANSEN_LOSS_DISABLE_LIVE", "true")
    monkeypatch.setenv("RADD_DISABLE_LIVE", "true")
    b = _boundary(nowhere)
    assert query_jrc_gfc2020(b).forest_2020 is None
    assert query_hansen_loss(b).loss_after_2020_ha is None
    assert query_radd(b).alert_after_cutoff is None
    # With everything unavailable, the engine must be inconclusive — never clear.
    pv = triage_plot("P_nowhere", nowhere, "palm", area_ha=490.0, run_date=_RUN_DATE)
    assert pv.detection == "inconclusive"


# ── JRC tile resolver (the bit Cowork must verify) ─────────────────────────────

def test_jrc_tile_name_nw_corner():
    """NW-corner 10° tile id — UNPADDED, matching the verified live naming (N0_E110)."""
    # lat -1.0, lon 113.0 → NW corner N0 / E110 (tile spans lat [-10,0], lon [110,120])
    assert _jrc_tile_name(-1.0, 113.0) == "N0_E110"
    assert _jrc_tile_name(5.0, 117.0) == "N10_E110"


def test_jrc_url_default_is_single_cog(monkeypatch):
    """Default URL is the verified global single-COG (no per-tile guesswork)."""
    monkeypatch.delenv("JRC_GFC2020_URL", raising=False)
    url = _jrc_url(-1.0, 113.0)
    assert url.endswith("single-cog/JRC_GFC2020_V3_COG.tif")
    assert "jeodpp.jrc.ec.europa.eu" in url


def test_jrc_url_override(monkeypatch):
    # tiles/ template override resolves the unpadded tile id
    monkeypatch.setenv("JRC_GFC2020_URL", "https://example.test/tiles/JRC_GFC2020_V3_{tile}.tif")
    assert _jrc_url(-1.0, 113.0) == "https://example.test/tiles/JRC_GFC2020_V3_N0_E110.tif"
    # single-COG override used verbatim
    monkeypatch.setenv("JRC_GFC2020_URL", "https://example.test/whole_aoi.tif")
    assert _jrc_url(-1.0, 113.0) == "https://example.test/whole_aoi.tif"


def test_boundary_centroid_matches_fixture_key():
    """Guard: the test squares' centroids round to the fixture coords (else fixtures miss)."""
    b = _boundary(_PLOT_LOSS)
    assert f"{b.centroid_lat:.3f}_{b.centroid_lon:.3f}" == "-1.000_113.000"
    b2 = _boundary(_PLOT_HANSEN_GAP)
    assert f"{b2.centroid_lat:.3f}_{b2.centroid_lon:.3f}" == "-0.750_116.500"
