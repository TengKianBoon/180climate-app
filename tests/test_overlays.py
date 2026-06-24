"""Tests for WO-AUTOROUTE-001: overlay adapters + new contract types.

All tests are offline-only (no network) — overlays load from CI fixture cache.
Acceptance: contracts type-check; adapters return cached overlays deterministically;
existing 116 tests still green; no secrets.
"""
import pytest
from core.contracts import (
    Boundary,
    OverlayIntersection,
    LegalOverlayResult,
    ForestPresenceGate,
    Stratum,
    ProjectClassification,
    MethodologyRoute,
    CarbonEstimate,
    CarbonInput,
    ContactInfo,
    GeoInput,
    EligibilityResult,
    GateResult,
    ForestData,
    QualityFactors,
)
from core.overlays import (
    query_khg,
    query_pippib,
    query_worldcover,
    query_jrc_tmf,
    WorldCoverResult,
    JRCTMFResult,
)

# Golden mineral-forest concession centroid (East Kalimantan)
_MINERAL_LAT, _MINERAL_LON = -0.500, 117.500
# Golden peat-dome concession centroid (Kalimantan Tengah PEAT fixture)
_PEAT_LAT, _PEAT_LON = 0.900, 117.150


def _make_boundary(lat: float, lon: float) -> Boundary:
    return Boundary(
        geojson={"type": "Point", "coordinates": [lon, lat]},
        area_ha=50_000.0,
        centroid_lat=lat,
        centroid_lon=lon,
        is_valid=True,
        within_indonesia=True,
        source_fmt="coords",
    )


# ── New contract types round-trip ──────────────────────────────────────────────

class TestNewContractTypes:
    def test_overlay_intersection_defaults(self):
        oi = OverlayIntersection()
        assert oi.intersects is None
        assert oi.area_ha is None
        assert oi.source == ""
        assert oi.note == ""

    def test_overlay_intersection_with_data(self):
        oi = OverlayIntersection(intersects=True, area_ha=5000.0, source="KHG")
        assert oi.intersects is True
        assert oi.area_ha == 5000.0

    def test_legal_overlay_result_round_trip(self):
        a = OverlayIntersection(intersects=False)
        b = OverlayIntersection(intersects=True, area_ha=1000.0)
        lor = LegalOverlayResult(
            overlay_a_khg=a,
            overlay_b_pippib=b,
            peat_additionality_status="flag — manual methodological review required",
        )
        assert lor.overlay_a_khg.intersects is False
        assert lor.overlay_b_pippib.intersects is True
        assert "flag" in lor.peat_additionality_status

    def test_forest_presence_gate_defaults(self):
        gate = ForestPresenceGate()
        assert gate.forest_confirmed is None
        assert gate.condition == "unknown"
        assert gate.gate_result == "flag"

    def test_forest_presence_gate_pass(self):
        gate = ForestPresenceGate(
            forest_confirmed=True,
            canopy_cover_pct=78.0,
            condition="light_degradation",
            gate_result="pass",
        )
        assert gate.gate_result == "pass"
        assert gate.canopy_cover_pct == 78.0

    def test_stratum_mineral(self):
        route = MethodologyRoute(
            baseline_class="planned_clearfell",
            verra_family="APD (VM0009/legacy — advisor-confirm)",
            cited_methods=["VM0009"],
            is_planned=True,
        )
        s = Stratum(
            stratum_id="mineral_forest",
            area_ha=73_000.0,
            soil_type="mineral",
            methodology=route,
            eligibility_verdict="eligible",
            quantity_low_tco2e=5_000_000.0,
            quantity_high_tco2e=8_000_000.0,
        )
        assert s.soil_type == "mineral"
        assert s.methodology is not None
        assert s.quantity_low_tco2e < s.quantity_high_tco2e

    def test_stratum_peat_no_tonnage(self):
        """Peat stratum MUST NOT assert a tonnage (ADR-0013 invariant)."""
        s = Stratum(
            stratum_id="peat",
            area_ha=15_000.0,
            soil_type="peat",
            eligibility_verdict="flagged",
            eligibility_reasons=["peat: manual review required (ADR-0013)"],
            quantity_low_tco2e=None,
            quantity_high_tco2e=None,
        )
        assert s.quantity_low_tco2e is None
        assert s.quantity_high_tco2e is None

    def test_project_classification_single_stratum(self):
        s = Stratum(stratum_id="mineral_forest", area_ha=50_000.0, soil_type="mineral")
        pc = ProjectClassification(strata=[s], dominant_soil="mineral")
        assert len(pc.strata) == 1
        assert pc.auto_determined is True

    def test_project_classification_mixed(self):
        s1 = Stratum(stratum_id="mineral_forest", area_ha=40_000.0, soil_type="mineral")
        s2 = Stratum(stratum_id="peat", area_ha=10_000.0, soil_type="peat")
        pc = ProjectClassification(strata=[s1, s2], dominant_soil="mixed")
        assert len(pc.strata) == 2
        assert pc.dominant_soil == "mixed"

    def test_carbon_estimate_classification_optional(self):
        """CarbonEstimate still valid without classification (backward compat)."""
        est = CarbonEstimate(
            eligibility=EligibilityResult(
                gates={"permit_type": GateResult(status="pass", detail="")},
                verdict="eligible",
                reasons=[],
            ),
            methodology=MethodologyRoute(
                baseline_class="planned_clearfell",
                verra_family="APD",
                cited_methods=[],
                is_planned=True,
            ),
            forest=ForestData(
                annual_loss_ha={2021: 100.0},
                baseline_cover_pct=80.0,
                loss_after_2020_ha=100.0,
                data_sources=["GFW"],
                uncertainty_band="±20%",
            ),
            quality=QualityFactors(
                additionality="high",
                permanence="medium",
                leakage="low",
                methodology_fit="APD",
            ),
            quantity_low_tco2e=1_000_000.0,
            quantity_high_tco2e=1_500_000.0,
            uncertainty="±20%",
        )
        assert est.classification is None

    def test_carbon_input_ifm_project_type(self):
        inp = CarbonInput(
            contact=ContactInfo(name="Test", email="t@t.com"),
            iup_name="PT Test",
            iup_address="Kalimantan",
            permit_type="HA",
            permit_years_remaining=15,
            project_type="IFM",
            geo=GeoInput(fmt="coords", payload="-0.5,117.5"),
        )
        assert inp.project_type == "IFM"

    def test_carbon_input_other_project_type(self):
        inp = CarbonInput(
            contact=ContactInfo(name="Test", email="t@t.com"),
            iup_name="PT Test",
            iup_address="Kalimantan",
            permit_type="HA",
            permit_years_remaining=15,
            project_type="other",
            project_type_description="Mangrove restoration along coastal boundary",
            geo=GeoInput(fmt="coords", payload="-0.5,117.5"),
        )
        assert inp.project_type == "other"
        assert inp.project_type_description is not None

    def test_carbon_input_redd_peat_still_valid(self):
        """Existing REDD / PEAT values must still be accepted after expansion."""
        for pt in ("REDD", "PEAT"):
            inp = CarbonInput(
                contact=ContactInfo(name="Test", email="t@t.com"),
                iup_name="PT Test",
                iup_address="Kalimantan",
                permit_type="HTI",
                permit_years_remaining=20,
                project_type=pt,
                geo=GeoInput(fmt="coords", payload="-0.5,117.5"),
            )
            assert inp.project_type == pt


# ── KHG adapter ───────────────────────────────────────────────────────────────

class TestKHGAdapter:
    def test_mineral_concession_not_intersecting(self):
        b = _make_boundary(_MINERAL_LAT, _MINERAL_LON)
        result = query_khg(b)
        assert isinstance(result, OverlayIntersection)
        assert result.intersects is False
        assert result.source != ""

    def test_peat_concession_intersecting(self):
        b = _make_boundary(_PEAT_LAT, _PEAT_LON)
        result = query_khg(b)
        assert result.intersects is True
        assert result.area_ha is not None and result.area_ha > 0

    def test_deterministic(self):
        """Same boundary → same result (no randomness)."""
        b = _make_boundary(_MINERAL_LAT, _MINERAL_LON)
        r1 = query_khg(b)
        r2 = query_khg(b)
        assert r1.intersects == r2.intersects
        assert r1.area_ha == r2.area_ha

    def test_no_fixture_returns_none_intersects(self, monkeypatch):
        """Unknown location (no fixture, no env var) → intersects=None."""
        monkeypatch.delenv("KHG_URL", raising=False)
        b = _make_boundary(5.0, 100.0)  # no fixture for this centroid
        result = query_khg(b)
        assert result.intersects is None


# ── PIPPIB adapter ────────────────────────────────────────────────────────────

class TestPIPPIBAdapter:
    def test_mineral_concession_not_intersecting(self):
        b = _make_boundary(_MINERAL_LAT, _MINERAL_LON)
        result = query_pippib(b)
        assert isinstance(result, OverlayIntersection)
        assert result.intersects is False

    def test_peat_concession_intersecting(self):
        b = _make_boundary(_PEAT_LAT, _PEAT_LON)
        result = query_pippib(b)
        assert result.intersects is True

    def test_deterministic(self):
        b = _make_boundary(_PEAT_LAT, _PEAT_LON)
        r1 = query_pippib(b)
        r2 = query_pippib(b)
        assert r1.intersects == r2.intersects

    def test_no_fixture_returns_none_intersects(self, monkeypatch):
        monkeypatch.delenv("PIPPIB_URL", raising=False)
        b = _make_boundary(5.0, 100.0)
        result = query_pippib(b)
        assert result.intersects is None


# ── WorldCover adapter ────────────────────────────────────────────────────────

class TestWorldCoverAdapter:
    def test_mineral_concession_is_tree_cover(self):
        b = _make_boundary(_MINERAL_LAT, _MINERAL_LON)
        result = query_worldcover(b)
        assert isinstance(result, WorldCoverResult)
        assert result.is_tree_cover is True
        assert result.land_class == 10

    def test_peat_concession_not_tree_cover(self):
        b = _make_boundary(_PEAT_LAT, _PEAT_LON)
        result = query_worldcover(b)
        assert result.land_class != 10  # herbaceous wetland (class 90)
        assert result.is_tree_cover is False

    def test_deterministic(self):
        b = _make_boundary(_MINERAL_LAT, _MINERAL_LON)
        r1 = query_worldcover(b)
        r2 = query_worldcover(b)
        assert r1.land_class == r2.land_class

    def test_no_fixture_returns_unknown(self, monkeypatch):
        monkeypatch.delenv("WORLDCOVER_TILE_URL", raising=False)
        b = _make_boundary(5.0, 100.0)
        result = query_worldcover(b)
        assert result.land_class == 0


# ── JRC TMF adapter ───────────────────────────────────────────────────────────

class TestJRCTMFAdapter:
    def test_mineral_concession_undisturbed(self):
        b = _make_boundary(_MINERAL_LAT, _MINERAL_LON)
        result = query_jrc_tmf(b)
        assert isinstance(result, JRCTMFResult)
        assert result.disturbance_class == "undisturbed"
        assert result.is_forest is True

    def test_peat_concession_degraded(self):
        b = _make_boundary(_PEAT_LAT, _PEAT_LON)
        result = query_jrc_tmf(b)
        assert result.disturbance_class == "degraded"
        assert result.is_forest is True
        assert result.deforestation_year is not None

    def test_deterministic(self):
        b = _make_boundary(_MINERAL_LAT, _MINERAL_LON)
        r1 = query_jrc_tmf(b)
        r2 = query_jrc_tmf(b)
        assert r1.disturbance_class == r2.disturbance_class

    def test_no_fixture_returns_unknown(self, monkeypatch):
        monkeypatch.delenv("JRC_TMF_URL", raising=False)
        b = _make_boundary(5.0, 100.0)
        result = query_jrc_tmf(b)
        assert result.disturbance_class == "unknown"
        assert result.is_forest is False
