# core/contracts/__init__.py — the shared constitution. Change ONLY via ADR + Gate C.
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, model_validator

# ---------- Shared ----------
class ContactInfo(BaseModel):
    name: str
    email: str
    mobile: Optional[str] = None
    company: Optional[str] = None

class GeoInput(BaseModel):
    """Raw geometry as the user supplies it."""
    fmt: Literal["coords", "geojson", "shapefile"]
    payload: str            # coordinate string, GeoJSON, or a reference to an uploaded file
    crs: str = "EPSG:4326"

class Boundary(BaseModel):
    """Parsed, validated geometry."""
    geojson: dict           # normalised GeoJSON geometry
    area_ha: float
    centroid_lat: float
    centroid_lon: float
    is_valid: bool
    within_indonesia: bool
    source_fmt: Literal["coords", "geojson", "shapefile"]

class ForestData(BaseModel):
    """Output of the shared geospatial core (free-tier sources, swappable)."""
    annual_loss_ha: dict[int, float]          # year -> hectares lost
    baseline_cover_pct: float
    loss_after_2020_ha: float                 # used by the EUDR cutoff verdict
    data_sources: list[str]                   # e.g. ["GFW/Hansen", "JRC GFC2020", "RADD"]
    uncertainty_band: str                     # human-readable, never field-grade precision
    peat_present: Optional[bool] = None
    peat_depth_proxy_m: Optional[float] = None
    biomass_tco2_per_ha: Optional[float] = None
    # ADR-0015-C1: forest-origin gate — natural vs established plantation (KLHK Penutupan Lahan)
    forest_origin: Literal["natural", "plantation", "mixed", "unknown"] = "unknown"

class Disclaimer(BaseModel):
    text: str
    kind: Literal["carbon_non_binding", "eudr_decision_support"]

class MapOverlay(BaseModel):
    base_tiles: str
    boundary_geojson: dict
    loss_overlay: dict
    plots_geojson: Optional[dict] = None

class EngineResult(BaseModel):
    """The shared output envelope rendered by the frontend."""
    engine: Literal["carbon", "eudr"]
    verdict: str
    summary: str
    map: MapOverlay
    narrative: str
    disclaimer: Disclaimer
    carrot: str
    data_sources: list[str]

# ---------- Carbon ----------
class CarbonInput(BaseModel):
    contact: ContactInfo
    iup_name: str
    iup_address: str
    permit_type: Literal["HTI", "HA"]
    permit_years_remaining: int
    project_type: Literal["REDD", "PEAT", "IFM", "other"]  # IFM + other added (ADR-0013)
    project_type_description: Optional[str] = None          # used when project_type="other"
    geo: GeoInput

class GateResult(BaseModel):
    status: Literal["pass", "flag", "fail"]
    detail: str

class EligibilityResult(BaseModel):
    gates: dict[str, GateResult]              # keys: permit_type, permit_years, area, inside_iup
    verdict: Literal["eligible", "flagged", "hard_no"]
    reasons: list[str]

class MethodologyRoute(BaseModel):
    baseline_class: Literal["planned_clearfell", "planned_selective", "ifm_selective_logging", "peat"]
    verra_family: str                         # e.g. "APD (VM0009/legacy — advisor-confirm)"
    cited_methods: list[str]
    additionality_basis: str = "legal harvest right foregone"
    is_planned: bool                          # MUST be True for HTI/HA foregone-harvest baselines
    notes: str = ""

class QualityFactors(BaseModel):
    additionality: str
    permanence: str
    leakage: str
    methodology_fit: str

# ---------- ADR-0013 overlay + classification types ----------

class OverlayIntersection(BaseModel):
    """Result of one spatial overlay query (KHG, PIPPIB, WorldCover, JRC TMF)."""
    intersects: Optional[bool] = None   # None = data unavailable; not a negative result
    area_ha: Optional[float] = None
    source: str = ""
    note: str = ""

class LegalOverlayResult(BaseModel):
    """Two-overlay peat legal status evaluated independently (ADR-0013-peatland)."""
    overlay_a_khg: OverlayIntersection       # PP57/2016 ecosystem function / fungsi lindung
    overlay_b_pippib: OverlayIntersection    # Inpres5/2019 moratorium / PIPPIB
    peat_additionality_status: str           # see ADR-0013 outcome strings; never a tonnage
    note: str = ""

class ForestPresenceGate(BaseModel):
    """Forest presence + condition gate — required before any REDD/IFM number (ADR-0013-auto-routing)."""
    forest_confirmed: Optional[bool] = None
    canopy_cover_pct: Optional[float] = None
    condition: Literal["intact", "light_degradation", "heavy_degradation", "cleared", "unknown"] = "unknown"
    gate_result: Literal["pass", "flag", "fail"] = "flag"
    note: str = ""

class Stratum(BaseModel):
    """One classified land-area unit; soil-first stratification (ADR-0013)."""
    stratum_id: str
    area_ha: float
    soil_type: Literal["mineral", "peat", "unknown"] = "unknown"
    methodology: Optional[MethodologyRoute] = None
    legal_overlay: Optional[LegalOverlayResult] = None
    forest_gate: Optional[ForestPresenceGate] = None
    eligibility_verdict: Literal["eligible", "flagged", "hard_no"] = "flagged"
    eligibility_reasons: list[str] = []
    quantity_low_tco2e: Optional[float] = None
    quantity_high_tco2e: Optional[float] = None

    @model_validator(mode="after")
    def _peat_must_have_no_tonnage(self) -> "Stratum":
        """ADR-0013: peat stratum must never carry a tonnage — by construction."""
        if self.soil_type == "peat":
            if self.quantity_low_tco2e is not None or self.quantity_high_tco2e is not None:
                raise ValueError(
                    "ADR-0013 invariant violated: peat stratum must never carry a "
                    "tonnage (quantity_low_tco2e and quantity_high_tco2e must be None). "
                    "Peat routes to a flag, not a number."
                )
        return self

class ProjectClassification(BaseModel):
    """Per-stratum project classification; replaces single project_type (ADR-0013)."""
    strata: list[Stratum]
    dominant_soil: Literal["mineral", "peat", "mixed", "unknown"] = "unknown"
    auto_determined: bool = True
    user_project_type_override: Optional[str] = None   # for project_type="other" free-text
    note: str = ""

class CarbonEstimate(BaseModel):
    eligibility: EligibilityResult
    methodology: MethodologyRoute
    forest: ForestData
    quantity_low_tco2e: Optional[float]       # None for peat (ADR-0013: peat=flag, never a tonnage)
    quantity_high_tco2e: Optional[float]      # a RANGE for non-peat; None for peat
    uncertainty: str
    quality: QualityFactors
    classification: Optional[ProjectClassification] = None  # ADR-0013; None = not yet classified

# ---------- EUDR ----------
class Plot(BaseModel):
    plot_id: str
    geo: GeoInput
    commodity: Literal["palm", "rubber", "timber", "cocoa", "coffee"]
    geometry_type: Literal["polygon", "point"]   # polygon required >4 ha; point allowed <=4 ha

class EUDRInput(BaseModel):
    contact: ContactInfo
    role: Literal["operator", "trader"]
    plots: list[Plot]

class ChecklistItem(BaseModel):
    item: str
    status: Literal["present", "missing", "attest"]
    note: str = ""

class PlotVerdict(BaseModel):
    plot_id: str
    deforestation_free: bool                  # vs 31 Dec 2020
    loss_after_2020_ha: float
    commodity: str
    geometry_ok: bool

class EUDRVerdict(BaseModel):
    overall: Literal["compliant", "non_compliant", "needs_review"]
    plots: list[PlotVerdict]
    indonesia_risk_tier: Literal["low", "standard", "high"]
    legality_checklist: list[ChecklistItem]
    dds_pack: dict                            # GeoJSON FeatureCollection, TRACES-aligned schema
    readiness_score: int                      # 0-100
    applicable_deadline: str                  # from config

# ---------- Narrative ----------
class NarrativeRequest(BaseModel):
    engine: Literal["carbon", "eudr"]
    payload: dict                             # the estimate / verdict
    must_state: list[str]                     # e.g. ["legal harvest right foregone"]

class NarrativeResult(BaseModel):
    text: str
    citations: list[str]

# ---------- Lead ----------
class LeadCapture(BaseModel):
    contact: ContactInfo
    engine: Literal["carbon", "eudr"]
    payload_summary: str
    timestamp: str
    delivery_status: Literal["pending", "emailed", "sheet_appended", "failed"]

# ---------- Config (config-driven; one edit, no code change) ----------
class CarbonGates(BaseModel):
    min_area_ha: int = 20_000
    min_years_remaining: int = 5
    valid_permit_types: tuple[str, ...] = ("HTI", "HA")

class EUDRConfig(BaseModel):
    cutoff_date: str = "2020-12-31"
    operator_deadline: str = "2026-12-30"
    sme_deadline: str = "2027-06-30"
    as_of: str = "2026-06"
    commodities: tuple[str, ...] = ("palm", "rubber", "timber", "cocoa", "coffee")
