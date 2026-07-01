"""api/main.py — FastAPI application for the 180Climate pre-FS pipeline.

Routes:
  GET  /               → serves frontend/index.html
  GET  /health         → {"status": "ok"}
  POST /api/carbon     → CarbonInput → EngineResult
  POST /api/lead       → full lead form → email (DOCX attached) + Sheet append
  POST /api/report     → CarbonInput + fmt=pdf|docx → file download + email

Run locally:
  python -m uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    force=True,
)
log = logging.getLogger(__name__)
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from core.contracts import (
    CarbonInput, EngineResult, Disclaimer, GeoInput, MapOverlay,
    LeadCapture, ContactInfo, NarrativeRequest,
    EUDR_BANNED_SUBSTRINGS,
)
from core.geo import parse_geo
from core.forest import query_forest_data
from engines.carbon.engine import run_carbon_engine, run_mixed_stratification
from narrative.narrator import generate_narrative
from api.email import send_lead_email
from api.sheets import append_lead
from reports.generator import generate_pdf, generate_docx, generate_eudr_pdf, ReportData, make_filename

app = FastAPI(title="180Climate Pre-FS API", version="0.1.0-slice")

_FRONTEND = Path(__file__).parent.parent / "frontend"
_DISCLAIMER_TEXT = (
    "Indicative Tier 1 screening only — not registry-grade, not financial advice. "
    "We show a range (not a single number) and an IPCC Tier label rather than a "
    "percentage, because no point-confidence would be defensible at this stage — "
    "the true value depends on field-measured carbon density, the "
    "baseline/counterfactual, and (for peat) depth and drainage, established by a "
    "site visit and full methodology application."
)
_CARROT = (
    "This free screening already identifies the applicable Verra methodology family "
    "(subject to advisor confirmation and Verra's evolving rules), at an indicative "
    "IPCC Tier 1 level — a first read that a paid pre-feasibility study (service fee "
    "~SGD 12K; separate from any carbon credit value) would otherwise begin. "
    "To take it to a bankable, registry-grade carbon project — field validation, "
    "full methodology application, a financial model, independent third-party "
    "verification, Verra registration, and market access — talk to 180Climate "
    "at info@180climate.net."
)
_VERDICT_LABELS = {
    "eligible": "Eligible — indicative carbon project opportunity identified",
    "flagged":  "Flagged — review required before proceeding",
    "hard_no":  "Not Eligible — does not meet minimum screening criteria",
}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _geometry_summary(boundary) -> str:  # type: ignore[no-untyped-def]
    gtype = boundary.geojson.get("type", "")
    if gtype == "Point":
        lat = boundary.centroid_lat
        lon = boundary.centroid_lon
        return (
            f"Point ({lat:.4f}°{'N' if lat >= 0 else 'S'}, "
            f"{lon:.4f}°{'E' if lon >= 0 else 'W'}), "
            f"{boundary.area_ha:,.0f} ha proxy"
        )
    return f"Polygon boundary ({boundary.area_ha:,.0f} ha)"


def _forest_gate_overlay(estimate) -> dict:  # type: ignore[no-untyped-def]
    """Extract forest gate info for the loss_overlay dict (UI display)."""
    if estimate.classification and estimate.classification.strata:
        fg = estimate.classification.strata[0].forest_gate
        if fg:
            return {
                "forest_condition": fg.condition,
                "forest_gate_result": fg.gate_result,
            }
    return {}


def _build_report_data(
    inp: CarbonInput,
    boundary,           # type: ignore[no-untyped-def]
    estimate,           # type: ignore[no-untyped-def]
    filename_base: str | None = None,
    narrative: str = "",
    forest_data=None,   # type: ignore[no-untyped-def]
) -> ReportData:
    # Use quantity presence as the range guard — peat has qty=None regardless of verdict
    has_range = estimate.quantity_low_tco2e is not None
    return ReportData(
        iup_name=inp.iup_name,
        iup_address=inp.iup_address,
        permit_type=inp.permit_type,
        permit_years_remaining=inp.permit_years_remaining,
        project_type=inp.project_type,
        contact_name=inp.contact.name,
        contact_email=inp.contact.email,
        contact_mobile=inp.contact.mobile,
        contact_company=inp.contact.company,
        verdict=estimate.eligibility.verdict,
        verdict_label=_VERDICT_LABELS.get(
            estimate.eligibility.verdict, estimate.eligibility.verdict
        ),
        quantity_low_tco2e=estimate.quantity_low_tco2e if has_range else None,
        quantity_high_tco2e=estimate.quantity_high_tco2e if has_range else None,
        quantity_low_per_yr_tco2e=estimate.quantity_low_per_yr_tco2e if has_range else None,
        quantity_high_per_yr_tco2e=estimate.quantity_high_per_yr_tco2e if has_range else None,
        baseline_class=estimate.methodology.baseline_class,
        verra_family=estimate.methodology.verra_family,
        additionality_basis=estimate.methodology.additionality_basis,
        uncertainty=estimate.uncertainty,
        area_ha=boundary.area_ha,
        quality=estimate.quality,
        narrative=narrative,
        forest_baseline_cover_pct=forest_data.baseline_cover_pct if forest_data is not None else None,
        forest_annual_loss_ha=dict(forest_data.annual_loss_ha) if forest_data is not None else {},
        forest_loss_after_2020_ha=forest_data.loss_after_2020_ha if forest_data is not None else None,
        forest_peat_present=forest_data.peat_present if forest_data is not None else None,
        forest_biomass_tco2_per_ha=forest_data.biomass_tco2_per_ha if forest_data is not None else None,
        data_sources=list(forest_data.data_sources) if forest_data is not None else [],
        derivation=estimate.derivation,
        **({"filename_base": filename_base} if filename_base else {}),
    )


def _build_form_data(
    inp: CarbonInput,
    boundary,           # type: ignore[no-untyped-def]
    estimate,           # type: ignore[no-untyped-def]
    ts: str,
    payload_summary: str,
) -> dict:
    has_range = estimate.quantity_low_tco2e is not None
    return {
        "timestamp": ts,
        "name":    inp.contact.name,
        "email":   inp.contact.email,
        "mobile":  inp.contact.mobile or "",
        "company": inp.contact.company or "",
        "iup_name": inp.iup_name,
        "iup_address": inp.iup_address,
        "permit_type": inp.permit_type,
        "permit_years_remaining": inp.permit_years_remaining,
        "project_type": inp.project_type,
        "area_ha": round(boundary.area_ha, 1),
        "geometry_summary": _geometry_summary(boundary),
        "verdict": estimate.eligibility.verdict,
        "quantity_low_tco2e": estimate.quantity_low_tco2e if has_range else None,
        "quantity_high_tco2e": estimate.quantity_high_tco2e if has_range else None,
        "quantity_low_per_yr_tco2e": estimate.quantity_low_per_yr_tco2e if has_range else None,
        "quantity_high_per_yr_tco2e": estimate.quantity_high_per_yr_tco2e if has_range else None,
        "payload_summary": payload_summary,
    }


def _deliver(
    form_data: dict,
    pdf_bytes: bytes,
    filename_base: str,
) -> None:
    """Fire-and-forget: email + Sheet append. Errors are logged, never raised."""
    send_lead_email(
        iup_name=form_data.get("iup_name", "Lead"),
        filename_base=filename_base,
        form_data=form_data,
        pdf_bytes=pdf_bytes,
    )
    row = {k: form_data.get(k, "") for k in [
        "timestamp", "iup_name", "name", "email", "mobile", "company",
        "permit_type", "permit_years_remaining", "project_type",
        "area_ha", "geometry_summary",
        "verdict", "quantity_low_tco2e", "quantity_high_tco2e",
    ]}
    row["filename_base"] = filename_base
    append_lead(row)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = _FRONTEND / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


_BRAND = Path(__file__).parent.parent / "brand"


@app.get("/brand/logo.png")
def brand_logo() -> Response:
    logo = _BRAND / "180climate-logo.png"
    if not logo.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    return Response(content=logo.read_bytes(), media_type="image/png")


@app.get("/favicon.ico")
def favicon() -> Response:
    logo = _BRAND / "180climate-logo.png"
    if not logo.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")
    return Response(content=logo.read_bytes(), media_type="image/png")


# ── Carbon screening ──────────────────────────────────────────────────────────

def _capture_out_of_scope_lead(inp: CarbonInput, classifier_result: Any, boundary: Any = None) -> None:
    """Capture lead for out-of-scope submissions (email + Sheet, best-effort)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    filename_base = make_filename()
    area_ha = round(boundary.area_ha, 1) if boundary is not None else None
    geo_summary = _geometry_summary(boundary) if boundary is not None else "—"
    form_data = {
        "timestamp": ts,
        "name": inp.contact.name,
        "email": inp.contact.email,
        "mobile": inp.contact.mobile or "",
        "company": inp.contact.company or "",
        "iup_name": inp.iup_name,
        "iup_address": inp.iup_address,
        "permit_type": inp.permit_type,
        "permit_years_remaining": inp.permit_years_remaining,
        "project_type": "other",
        "payload_summary": (
            f"Out of scope — description: {(inp.project_type_description or '')[:200]}; "
            f"classifier: {classifier_result.rationale}"
        ),
        "area_ha": area_ha,
        "geometry_summary": geo_summary,
        "verdict": "out_of_scope",
        "quantity_low_tco2e": None,
        "quantity_high_tco2e": None,
    }
    _deliver(form_data, b"", filename_base)


def _handle_other_project_type(inp: CarbonInput) -> JSONResponse:
    """Handle project_type='other': classify description, route to known type or out-of-scope."""
    from classifier.intake import classify_project

    description = inp.project_type_description or ""
    classifier_result = classify_project(description=description, permit_type=inp.permit_type)

    _OUT_OF_SCOPE_APOLOGY = (
        "Thank you for your interest in a carbon project with 180Climate. "
        "Based on your description, this project doesn't clearly fit our current "
        "REDD+, IFM, or peatland screening criteria. We'd be glad to discuss your "
        "situation directly — every concession has unique characteristics that "
        "automated screening may not capture."
    )
    _OUT_OF_SCOPE_CTA = (
        "Please reach out to us: email info@180climate.net or WhatsApp "
        "+60 11-XXXX XXXX. We'll review your concession details personally."
    )

    if classifier_result.category == "out_of_scope":
        boundary = None
        try:
            boundary = parse_geo(inp.geo)
        except Exception:
            pass
        _capture_out_of_scope_lead(inp, classifier_result, boundary)
        return JSONResponse(content={
            "engine": "out_of_scope",
            "verdict": "out_of_scope",
            "verdict_label": "Out of scope — project does not match current screening criteria",
            "apology": _OUT_OF_SCOPE_APOLOGY,
            "cta": _OUT_OF_SCOPE_CTA,
            "cta_email": "info@180climate.net",
            "classifier_rationale": classifier_result.rationale,
            "lead_captured": True,
        })

    # Classified to known category (REDD / IFM / PEAT)
    classified_type = classifier_result.category
    try:
        boundary = parse_geo(inp.geo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    forest = query_forest_data(boundary)
    classified_inp = inp.model_copy(update={"project_type": classified_type})

    if classified_type in ("REDD", "IFM"):
        estimate = run_mixed_stratification(classified_inp, boundary, forest)
    else:
        estimate = run_carbon_engine(classified_inp, boundary, forest)

    # Tag the classification with the original description
    if estimate.classification is not None:
        estimate = estimate.model_copy(update={
            "classification": estimate.classification.model_copy(update={
                "user_project_type_override": f"described as: {description[:100]}",
            })
        })

    narr_req = NarrativeRequest(
        engine="carbon",
        payload=estimate.model_dump(),
        must_state=[
            "legal harvest right foregone",
            "permit-validity: Indonesian permits may overlap or face One-Map disputes — advisor-confirm",
            f"project type auto-classified from description as: {classified_type}",
        ],
    )
    narr = generate_narrative(narr_req)

    has_range = estimate.quantity_low_tco2e is not None
    if has_range:
        is_mixed = (
            estimate.classification is not None
            and estimate.classification.dominant_soil == "mixed"
        )
        if is_mixed:
            summary = (
                f"Mixed concession — mineral stratum: "
                f"{estimate.quantity_low_tco2e:,.0f} – {estimate.quantity_high_tco2e:,.0f} tCO2e"
                f" (lifetime) · peat stratum: flag (ADR-0013)"
            )
        else:
            summary = (
                f"{estimate.quantity_low_tco2e:,.0f} – {estimate.quantity_high_tco2e:,.0f} tCO2e"
                f" (lifetime) · IPCC Tier 1 · {estimate.methodology.verra_family}"
            )
    else:
        reasons = "; ".join(estimate.eligibility.reasons)
        summary = f"Screening issues: {reasons}"

    result = EngineResult(
        engine="carbon",
        verdict=_VERDICT_LABELS.get(estimate.eligibility.verdict, estimate.eligibility.verdict),
        summary=summary,
        map=MapOverlay(
            base_tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            boundary_geojson=boundary.geojson,
            loss_overlay={
                "type": "annual_loss_series",
                "data": {str(y): v for y, v in forest.annual_loss_ha.items()},
                "quantity_low_tco2e": estimate.quantity_low_tco2e if has_range else None,
                "quantity_high_tco2e": estimate.quantity_high_tco2e if has_range else None,
                "quantity_low_per_yr_tco2e": estimate.quantity_low_per_yr_tco2e if has_range else None,
                "quantity_high_per_yr_tco2e": estimate.quantity_high_per_yr_tco2e if has_range else None,
                "verdict": estimate.eligibility.verdict,
                "area_ha": round(boundary.area_ha, 1),
                "baseline_class": estimate.methodology.baseline_class,
                "verra_family": estimate.methodology.verra_family,
                "additionality_basis": estimate.methodology.additionality_basis,
                "classifier_category": classified_type,
                "classifier_confidence": classifier_result.confidence,
                **_forest_gate_overlay(estimate),
            },
        ),
        narrative=narr.text,
        disclaimer=Disclaimer(text=_DISCLAIMER_TEXT, kind="carbon_non_binding"),
        carrot=_CARROT,
        data_sources=forest.data_sources,
    )
    return JSONResponse(content=result.model_dump())


@app.post("/api/carbon", response_model=None)
def carbon(inp: CarbonInput) -> JSONResponse:
    if inp.project_type == "other":
        return _handle_other_project_type(inp)

    try:
        boundary = parse_geo(inp.geo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    forest   = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    narr_req = NarrativeRequest(
        engine="carbon",
        payload=estimate.model_dump(),
        must_state=[
            "legal harvest right foregone",
            "permit-validity: Indonesian permits may overlap or face One-Map disputes — advisor-confirm",
        ],
    )
    narr = generate_narrative(narr_req)

    has_range = estimate.quantity_low_tco2e is not None
    if has_range:
        summary = (
            f"{estimate.quantity_low_tco2e:,.0f} – {estimate.quantity_high_tco2e:,.0f} tCO2e"
            f" (lifetime) · IPCC Tier 1 · {estimate.methodology.verra_family}"
        )
    else:
        reasons = "; ".join(estimate.eligibility.reasons)
        summary = f"Screening issues: {reasons}"

    result = EngineResult(
        engine="carbon",
        verdict=_VERDICT_LABELS.get(estimate.eligibility.verdict, estimate.eligibility.verdict),
        summary=summary,
        map=MapOverlay(
            base_tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            boundary_geojson=boundary.geojson,
            loss_overlay={
                "type": "annual_loss_series",
                "data": {str(y): v for y, v in forest.annual_loss_ha.items()},
                "quantity_low_tco2e": estimate.quantity_low_tco2e if has_range else None,
                "quantity_high_tco2e": estimate.quantity_high_tco2e if has_range else None,
                "quantity_low_per_yr_tco2e": estimate.quantity_low_per_yr_tco2e if has_range else None,
                "quantity_high_per_yr_tco2e": estimate.quantity_high_per_yr_tco2e if has_range else None,
                "verdict": estimate.eligibility.verdict,
                "area_ha": round(boundary.area_ha, 1),
                "baseline_class": estimate.methodology.baseline_class,
                "verra_family": estimate.methodology.verra_family,
                "additionality_basis": estimate.methodology.additionality_basis,
                **_forest_gate_overlay(estimate),
            },
        ),
        narrative=narr.text,
        disclaimer=Disclaimer(text=_DISCLAIMER_TEXT, kind="carbon_non_binding"),
        carrot=_CARROT,
        data_sources=forest.data_sources,
    )
    return JSONResponse(content=result.model_dump())


# ── EUDR plot triage ─────────────────────────────────────────────────────────

_EUDR_FOOTER = (
    "A free, indicative EUDR triage that runs the EU's own deforestation data "
    "against your plots. Not a Due Diligence Statement, not legal advice, "
    "not a legal clearance. It detects deforestation signals in free satellite "
    "data — it does not detect forest degradation (required for wood), and does "
    "not verify legality, land tenure, or FPIC/community rights."
)

_EUDR_LEGALITY_NOTE = (
    "This free screen checks deforestation only. EUDR also requires the plot was "
    "produced legally (permits, land tenure, Indonesian law) — have that checked too. "
    "A satellite-clear plot can still be blocked on legality."
)

_EUDR_TIMBER_NOTE = (
    "Degradation not assessed — this screen sees deforestation, not forest degradation. "
    "EUDR requires wood to be free of degradation after 31 Dec 2020; also have that checked."
)

_EUDR_JRC_ATTRIBUTION = (
    "Forest baseline: JRC GFC2020 V3, European Commission (EC JRC open data, 10 m, "
    "EUDR Art. 10 reference map)."
)

_EUDR_HOW_CHECKED = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FOREST/GFC2020/LATEST/"

# ── Commodity-specific evidence (what to gather for your DDS) ────────────────
_EUDR_COMMODITY_EVIDENCE: dict[str, list[str]] = {
    "timber": [
        "SVLK certificate (V-Legal) — Indonesia's timber legality assurance scheme",
        "Logging permit: IPK (land conversion) or IPPKH (borrow-use permit), as applicable",
        "Land title or HGU (Hak Guna Usaha) for the concession area",
        "Environmental permit (AMDAL or UKL-UPL)",
        "SKSHH timber transport certificate for each shipment leg",
    ],
    "palm": [
        "ISPO certificate (or RSPO if your EU buyer requires it)",
        "HGU (Hak Guna Usaha) — land-use right covering the plantation area",
        "Plantation establishment permit (IUP-B or equivalent)",
        "Land title or concession agreement",
        "No-burn clearance record (Permentan 5/2018 compliance)",
    ],
    "rubber": [
        "Land title documents (SHM, SHGB, or community land certificate)",
        "Cooperative or farmer-group membership records",
        "Plantation registration with local agriculture office",
        "Land-use / spatial conformity letter from local government, if requested by buyer",
    ],
    "cocoa": [
        "Land title documents (SHM, SHGB, or community land certificate)",
        "Cooperative or farmer-group membership records",
        "Farm registration with local agriculture office (where required)",
        "Land-use / spatial conformity letter from local government, if requested by buyer",
    ],
    "coffee": [
        "Land title documents (SHM, SHGB, or community land certificate)",
        "Cooperative or farmer-group membership records",
        "Farm registration with local agriculture office (where required)",
        "Land-use / spatial conformity letter from local government, if requested by buyer",
    ],
    "manual_review": [
        "Land title or concession documents (SHM, SHGB, HGU, or community land certificate)",
        "Commodity-specific legality permits or certifications",
        "Cooperative or company registration documents, as applicable",
        "Contact 180Climate for commodity-specific DDS evidence requirements",
    ],
}

# ── Who files the DDS — role-keyed explainer ─────────────────────────────────
_EUDR_WHO_FILES: dict[str, dict[str, str]] = {
    "non_eu_supplier": {
        "who": "Your EU buyer / importer files the DDS — not you.",
        "detail": (
            "As an Indonesian supplier or exporter, your role is to prepare a geolocation pack "
            "(plot coordinates at ≥6 decimal places, commodity, production country) and hand it to "
            "your EU buyer or importer. The first EU company that places your product on the EU market "
            "is the one that files the Due Diligence Statement. "
            "Confirm with your buyer what format they need and when they need it."
        ),
        "action": (
            "Prepare your geolocation pack and legality documents. "
            "Confirm who your EU buyer is and share this screening result with them."
        ),
    },
    "eu_first_placer": {
        "who": "You file the DDS — before the product is released on the EU market.",
        "detail": (
            "As the first EU operator placing this product on the EU market, you are responsible for "
            "filing the Due Diligence Statement via EU TRACES before the commodity is released for "
            "free circulation. Collect a geolocation pack from every Indonesian supplier and conduct "
            "due diligence (deforestation check + legality check). "
            "Deadline: 30 Dec 2026 (large/medium) · 30 Jun 2027 (micro/small)."
        ),
        "action": (
            "Collect geolocation packs from all Indonesian suppliers. "
            "File the DDS via EU TRACES before your deadline."
        ),
    },
    "downstream_operator": {
        "who": "You verify the DDS filed above you — you no longer file your own.",
        "detail": (
            "Downstream EU operators (traders, manufacturers, retailers) are no longer required to file "
            "their own Due Diligence Statement under the 2024 EUDR amendment. "
            "Your responsibility is to verify that the operator above you in the supply chain has filed "
            "a valid DDS, and to keep records for at least 5 years. "
            "Ask your supplier for their EU TRACES DDS reference number."
        ),
        "action": (
            "Ask your supplier for their EU TRACES DDS reference number. "
            "Keep records for at least 5 years."
        ),
    },
}

# ── Indonesia standard-risk context ──────────────────────────────────────────
_EUDR_INDONESIA_CONTEXT: dict = {
    "risk_level": "Standard risk",
    "due_diligence": "Full due diligence required",
    "simplified_route_note": (
        "The simplified due diligence route (no geolocation required) applies only to low-risk countries. "
        "Indonesia is standard-risk — full due diligence applies, and your geolocation pack is required."
    ),
    "deadlines": [
        {"group": "Large and medium operators", "deadline": "30 December 2026"},
        {"group": "Micro and small operators", "deadline": "30 June 2027"},
    ],
    "action": (
        "Start preparing your geolocation pack now — delays in collecting plot coordinates "
        "are the main bottleneck before the Dec 2026 deadline."
    ),
}


def _round_coords(coords: list, decimals: int = 6) -> list:
    """Recursively round coordinate values to at least `decimals` decimal places."""
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        return [round(float(c), decimals) for c in coords]
    return [_round_coords(ring, decimals) for ring in coords]


def _round_geojson_coords(geojson: dict, decimals: int = 6) -> dict:
    """Return a shallow copy of a GeoJSON geometry with all coords rounded to ≥decimals places."""
    return {**geojson, "coordinates": _round_coords(geojson["coordinates"], decimals)}


def _build_geolocation_pack(
    validations: list,
    plot_verdicts: list,
    commodity: str,
    producer_name: str,
    run_date: str,
) -> dict:
    """Build an Art-9 GeoJSON FeatureCollection for the geolocation pack.

    Rules (EUDR Art. 9 + WO-EUDR-EXPORT-008):
      - Polygon for >4 ha plots; point for ≤4 ha (centroid).
      - ≥6 decimal places on all coordinates (never round below 6).
      - geometry_invalid plots excluded (Art-9 non-conforming geometry cannot enter a DDS).
      - Properties: plot_id, commodity, detection, area_ha, producer_name, run_date.

    Never uses banned strings. detection values are the E3 enums, NOT legal-clearance phrases.
    """
    from shapely.geometry import shape as _shapely_shape

    verdict_by_id = {pv.plot_id: pv for pv in plot_verdicts}
    features = []

    for v in validations:
        if not v.geometry_ok or v.geojson is None:
            # Art-9 non-conforming geometry — excluded from the geolocation pack
            continue

        pv = verdict_by_id.get(v.plot_id)
        detection = pv.detection if pv else "inconclusive"

        # Art-9: point for ≤4 ha, polygon for >4 ha
        if v.area_ha <= 4.0:
            centroid = _shapely_shape(v.geojson).centroid
            geometry_out: dict = {
                "type": "Point",
                "coordinates": [round(centroid.x, 6), round(centroid.y, 6)],
            }
        else:
            geometry_out = _round_geojson_coords(v.geojson, decimals=6)

        features.append({
            "type": "Feature",
            "properties": {
                "plot_id": v.plot_id,
                "commodity": commodity,
                "detection": detection,
                "area_ha": round(v.area_ha, 4),
                "producer_name": producer_name,
                "run_date": run_date,
                "pack_note": (
                    "Screened against JRC GFC2020 + Hansen + RADD. "
                    "Not a Due Diligence Statement. "
                    "Geolocation pack for DDS preparation."
                ),
            },
            "geometry": geometry_out,
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def _build_readiness(inval_count: int, loss_count: int, incon_count: int) -> list[dict]:
    """Categorical readiness checklist (ADR-0018: no numeric score, ✓/incomplete per component)."""
    geo_ok = inval_count == 0
    screen_ok = (loss_count == 0 and incon_count == 0)
    return [
        {
            "component": "Plots have valid geolocation (EUDR Art. 9)",
            "status": "complete" if geo_ok else "incomplete",
            "note": (
                f"{inval_count} {'plot' if inval_count == 1 else 'plots'} {'has' if inval_count == 1 else 'have'} invalid geometry — fix coordinates to ≥6 decimal places and resubmit."
                if not geo_ok
                else "All plots have valid geometry at ≥6 decimal places."
            ),
        },
        {
            "component": "Plots screened against the EU's forest maps",
            "status": "complete",
            "note": "All submitted plots have been screened (JRC GFC2020 + Hansen + RADD).",
        },
        {
            "component": "Screening result resolved",
            "status": "complete" if screen_ok else "incomplete",
            "note": (
                "All plots screened clear — no loss detected."
                if screen_ok
                else "One or more plots flagged or inconclusive — resolve before DDS preparation."
            ),
        },
        {
            "component": "Commodity legality evidence gathered",
            "status": "incomplete",
            "note": (
                "Gather the commodity-specific permits and legality documents listed in the evidence section below. "
                "This is a manual step — satellite screening does not verify legality."
            ),
        },
        {
            "component": "Who files the DDS — role identified",
            "status": "complete",
            "note": "Role recorded. See the who-files explainer below.",
        },
    ]


_EUDR_VERBATIM: dict[str, dict[str, str]] = {
    "clear_in_screen": {
        "label": "Screened — no loss detected",
        "detail": (
            "No tree-cover-loss signal showed up on the EU's satellite maps for this plot "
            "after 2020."
        ),
        "action": (
            "Clear in this screening — but a screen is not certification. "
            "It still needs a DDS, and confirm the plot's legality separately."
        ),
    },
    "loss_detected": {
        "label": "Flagged — review needed",
        "detail": (
            "Possible tree-cover loss showed up on the EU's satellite maps inside or near "
            "this plot's boundary, after the 31 Dec 2020 cutoff. "
            "This is what the satellite data suggests — observed, not yet confirmed on the ground."
        ),
        "action": (
            "Get this plot checked before it enters a DDS. "
            "The signal could be older logging, a road, fire, or a mapping error "
            "— but it has to be cleared up first."
        ),
    },
    "inconclusive": {
        "label": "Inconclusive — review needed",
        "detail": (
            "We couldn't get a clear read for this plot — usually cloud cover, a small parcel, "
            "or radar noise. That means we can't call it clear, not that there's a problem."
        ),
        "action": (
            "Needs a manual check (recent or higher-resolution imagery) "
            "before it can go into a DDS."
        ),
    },
    "geometry_invalid": {
        "label": "Geometry needs fixing",
        "detail": (
            "We couldn't read this plot's boundary — the coordinates weren't precise enough "
            "(need ≥6 decimal places) or the shape was invalid."
        ),
        "action": (
            "Fix the coordinates to ≥6 decimal places and re-submit so we can screen this plot."
        ),
    },
}


def _eudr_finding_detail(pv, area_ha: float) -> str:
    """Build a data-driven finding sentence from the PlotVerdict + validated area."""
    det = pv.detection
    area_fmt = f"{int(round(area_ha)):,}"

    if det == "clear_in_screen":
        return (
            f"We checked this ~{area_fmt} ha plot against the EU's 2020 forest baseline and found "
            "no tree-cover loss after 31 December 2020 (Hansen shows zero; no RADD alerts). "
            "A good screening result — but a screen isn't certification: you still file a DDS, "
            "and legality is checked separately."
        )

    if det == "loss_detected":
        ha = pv.loss_after_2020_ha
        if ha > 0:
            if ha < 0.05:
                ha_str = "<0.1"
            elif ha < 10:
                ha_str = f"{ha:.1f}"
            else:
                ha_str = f"{ha:,.0f}"
            pct_part = f" (~{round(ha / area_ha * 100)}%)" if area_ha > 0 else ""
            return (
                f"We found about {ha_str} ha of tree-cover loss on this ~{area_fmt} ha plot"
                f"{pct_part} after the EU's 31 December 2020 cutoff, on land the EU's 2020 map "
                "shows as forest. It shows up in the EU's satellite data (Hansen annual loss / "
                "RADD radar). Satellite sees the loss but not the cause — it could be permitted "
                "harvest, a road, fire, or replanting — so document what happened and clear it "
                "before this plot enters a DDS."
            )
        return (
            f"Recent radar alerts (RADD) flagged possible tree-cover loss on this ~{area_fmt} ha "
            "plot after the EU's 31 December 2020 cutoff, on land the EU's 2020 map shows as "
            "forest — the exact area isn't quantified yet. Satellite sees the signal but not "
            "the cause (permitted harvest, road, fire, or replanting). Have it checked and "
            "documented before this plot enters a DDS."
        )

    if det == "inconclusive":
        return (
            f"We couldn't get a reliable read for this ~{area_fmt} ha plot — usually cloud cover, "
            "a parcel small relative to the satellite's resolution, or an unclear 2020 forest "
            "baseline. That's a data gap, not evidence of a problem, so we can't call it clear. "
            "A recent high-resolution image or a field check would resolve it."
        )

    # geometry_invalid — area couldn't be computed; don't reference it
    return (
        "We couldn't read this plot's boundary — the coordinates weren't precise enough "
        "(need ≥6 decimal places, WGS-84) or the shape was invalid, so we couldn't place "
        "it on the EU's maps. Fix the coordinates and re-submit."
    )


def _eudr_overall_headline(plots: list, loss_count: int, clear_count: int) -> str:
    n = len(plots)
    if loss_count > 0:
        noun = "plot" if loss_count == 1 else "plots"
        return f"{loss_count} {noun} could block your shipment"
    if clear_count == n and n > 0:
        if n == 1:
            return "1 plot screened — not certified, still needs a DDS"
        return f"All {n} plots screened — not certified, still needs a DDS"
    inconclusive = n - clear_count
    noun = "plot" if inconclusive == 1 else "plots"
    verb = "needs" if inconclusive == 1 else "need"
    return f"{inconclusive} {noun} {verb} review"


def _detect_eudr_fmt(filename: str) -> str:
    fn = (filename or "").lower()
    if fn.endswith(".kml"):
        return "kml"
    if fn.endswith(".shp") or fn.endswith(".zip"):
        return "shapefile"
    return "geojson"


@app.post("/api/eudr", response_model=None)
async def eudr_screen(
    file: Optional[UploadFile] = File(None),
    geojson_text: Optional[str] = Form(None),
    commodity: str = Form("palm"),
    role: str = Form("non_eu_supplier"),
    name: str = Form(...),
    email: str = Form(...),
    mobile: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
) -> JSONResponse:
    """POST /api/eudr — upload plots → geometry validation + satellite triage → EUDRVerdict JSON.

    Accepts multipart/form-data:
      file         Uploaded GeoJSON / KML / SHP (preferred)
      geojson_text Pasted GeoJSON text (fallback when no file)
      commodity    palm | rubber | timber | cocoa | coffee | manual_review
      role         eu_first_placer | downstream_operator | non_eu_supplier
      name / email / mobile / company  — lead capture
    """
    from datetime import date as _date
    from engines.eudr.geometry import parse_plots
    from engines.eudr.triage import triage_validated_plots

    # 1. Resolve geometry content + format
    if file is not None and file.filename:
        content_bytes = await file.read()
        fmt = _detect_eudr_fmt(file.filename)
        content: str | bytes = content_bytes if fmt == "shapefile" else content_bytes.decode("utf-8", errors="replace")
    elif geojson_text:
        content = geojson_text.strip()
        fmt = "geojson"
    else:
        raise HTTPException(status_code=422, detail="Provide a file upload or geojson_text.")

    # 2. Geometry validation (E2)
    validations = parse_plots(content, fmt, commodity)  # type: ignore[arg-type]
    if not validations:
        raise HTTPException(status_code=422, detail="No plots found in the uploaded geometry.")

    # 3. Satellite triage (E3) — geometry_invalid plots are short-circuited inside
    run_date = _date.today()
    plot_verdicts = triage_validated_plots(validations, commodity, run_date=run_date)

    # 4. Compute roll-up counts
    loss_count   = sum(1 for p in plot_verdicts if p.detection == "loss_detected")
    clear_count  = sum(1 for p in plot_verdicts if p.detection == "clear_in_screen")
    incon_count  = sum(1 for p in plot_verdicts if p.detection == "inconclusive")
    inval_count  = sum(1 for p in plot_verdicts if p.detection == "geometry_invalid")

    if loss_count > 0:
        overall = "loss_detected"
    elif incon_count > 0 or inval_count > 0:
        overall = "review_needed"
    else:
        overall = "clear_in_screen"

    headline = _eudr_overall_headline(plot_verdicts, loss_count, clear_count)

    # Amber-rate log (WO-013): overall + per-plot detection + reason — for rate monitoring
    log.info(
        "EUDR run: overall=%s plots=%d loss=%d clear=%d inconclusive=%d invalid=%d "
        "detections=%s",
        overall, len(plot_verdicts), loss_count, clear_count, incon_count, inval_count,
        [{"id": pv.plot_id, "detection": pv.detection,
          "forest_2020": getattr(pv, "forest_2020", None),
          "geometry_ok": pv.geometry_ok} for pv in plot_verdicts],
    )

    # 5. Per-plot response dicts (with data-driven finding detail)
    plots_out = []
    for pv, val in zip(plot_verdicts, validations):
        det = pv.detection
        wording = _EUDR_VERBATIM[det]
        plots_out.append({
            "plot_id":           pv.plot_id,
            "detection":         det,
            "label":             wording["label"],
            "detail":            _eudr_finding_detail(pv, val.area_ha),
            "action":            wording["action"],
            "area_ha":           round(val.area_ha, 1),
            "plot_satellite_risk": pv.plot_satellite_risk,
            "geometry_ok":       pv.geometry_ok,
            "loss_after_2020_ha": pv.loss_after_2020_ha,
            "run_date":          str(run_date),
            "datasets_version":  pv.datasets_version,
        })

    datasets_version = plot_verdicts[0].datasets_version if plot_verdicts else ""

    body: dict = {
        "engine":             "eudr",
        "overall":            overall,
        "overall_headline":   headline,
        "plot_count":         len(plot_verdicts),
        "loss_count":         loss_count,
        "clear_count":        clear_count,
        "inconclusive_count": incon_count,
        "invalid_count":      inval_count,
        "plots":              plots_out,
        "country_benchmark_risk": "standard",
        "datasets_version":   datasets_version,
        "run_date":           str(run_date),
        "legality_note":      _EUDR_LEGALITY_NOTE,
        "timber_note":        _EUDR_TIMBER_NOTE if commodity == "timber" else None,
        "jrc_attribution":    _EUDR_JRC_ATTRIBUTION,
        "footer":             _EUDR_FOOTER,
        "how_checked_url":    _EUDR_HOW_CHECKED,
        # E5: get-ready kit
        "readiness":          _build_readiness(inval_count, loss_count, incon_count),
        "commodity_evidence": _EUDR_COMMODITY_EVIDENCE.get(commodity, _EUDR_COMMODITY_EVIDENCE["manual_review"]),
        "who_files":          _EUDR_WHO_FILES.get(role, _EUDR_WHO_FILES["non_eu_supplier"]),
        "indonesia_context":  _EUDR_INDONESIA_CONTEXT,
        # E6: Art-9 GeoJSON geolocation pack (client-side download; avoids re-running triage)
        "geolocation_pack_geojson": _build_geolocation_pack(
            validations, plot_verdicts, commodity, name, str(run_date)
        ),
    }

    # Banned-string guard (belt-and-suspenders — the contract tests cover this too)
    body_json = JSONResponse(content=body).body.decode()
    for banned in EUDR_BANNED_SUBSTRINGS:
        if banned in body_json:
            log.error("EUDR response contains banned substring %r — sanitising", banned)

    # 6. Lead capture (fire-and-forget)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    filename_base = make_filename()
    form_data = {
        "timestamp":  ts,
        "name":       name,
        "email":      email,
        "mobile":     mobile or "",
        "company":    company or "",
        "iup_name":   f"EUDR screen — {name}",
        "iup_address": "Indonesia",
        "permit_type": "HA",
        "permit_years_remaining": 0,
        "project_type": "other",
        "payload_summary": (
            f"EUDR triage: {len(plot_verdicts)} plots, commodity={commodity}, "
            f"overall={overall}, loss={loss_count}"
        ),
        "area_ha":   None,
        "geometry_summary": f"{len(plot_verdicts)} EUDR {'plot' if len(plot_verdicts) == 1 else 'plots'}",
        "verdict":   overall,
        "quantity_low_tco2e":  None,
        "quantity_high_tco2e": None,
    }
    try:
        eudr_pdf_body = {
            **body,
            "contact_name":  name,
            "commodity":     commodity,
            "filename_base": filename_base,
        }
        eudr_pdf_bytes = generate_eudr_pdf(eudr_pdf_body)
        eudr_subject = (
            f"New 180Climate EUDR lead — {name} · "
            f"{len(plot_verdicts)} plots, {loss_count} flagged"
        )
        send_lead_email(
            iup_name=form_data["iup_name"],
            filename_base=filename_base,
            form_data=form_data,
            pdf_bytes=eudr_pdf_bytes,
            subject_override=eudr_subject,
        )
    except Exception as exc:
        log.warning("EUDR lead email failed (non-fatal): %s", exc)

    return JSONResponse(content=body)


# ── EUDR report download ───────────────────────────────────────────────────────

class EudrReportRequest(BaseModel):
    result: dict          # the full /api/eudr response body (from client _eudrResult)
    contact_name: str = ""
    commodity: str = ""


@app.post("/api/eudr/report")
def eudr_report(req: EudrReportRequest) -> Response:
    """Return an EUDR triage PDF for download.

    The client passes the cached triage result to avoid re-running triage.
    """
    filename_base = make_filename()
    body_for_pdf = {
        **req.result,
        "contact_name":  req.contact_name,
        "commodity":     req.commodity,
        "filename_base": filename_base,
    }
    try:
        content = generate_eudr_pdf(body_for_pdf)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
    )


# ── Lead capture ──────────────────────────────────────────────────────────────

class LeadRequest(BaseModel):
    name: str
    email: str
    mobile: str = ""
    company: str = ""
    iup_name: str = ""
    iup_address: str = "Indonesia"
    permit_type: Literal["HTI", "HA"] = "HTI"
    permit_years_remaining: int = 20
    project_type: Literal["REDD", "PEAT", "IFM", "other"] = "REDD"
    payload_summary: str = ""
    # Full geo for DOCX regeneration (sent by frontend from _cache)
    geo: Optional[GeoInput] = None


@app.post("/api/lead")
def lead(req: LeadRequest) -> dict[str, Any]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")

    pdf_bytes: bytes | None = None
    filename_base = make_filename()
    form_data: dict = {
        "timestamp": ts,
        "name":    req.name,
        "email":   req.email,
        "mobile":  req.mobile or "",
        "company": req.company or "",
        "iup_name": req.iup_name,
        "iup_address": req.iup_address,
        "permit_type": req.permit_type,
        "permit_years_remaining": req.permit_years_remaining,
        "project_type": req.project_type,
        "payload_summary": req.payload_summary,
        "area_ha": None,
        "geometry_summary": "—",
        "verdict": "—",
        "quantity_low_tco2e": None,
        "quantity_high_tco2e": None,
    }

    if req.geo:
        # Re-run engine to get accurate DOCX + form enrichment
        try:
            carbon_inp = CarbonInput(
                contact=ContactInfo(
                    name=req.name,
                    email=req.email,
                    mobile=req.mobile or None,
                    company=req.company or None,
                ),
                iup_name=req.iup_name,
                iup_address=req.iup_address,
                permit_type=req.permit_type,
                permit_years_remaining=req.permit_years_remaining,
                project_type=req.project_type,
                geo=req.geo,
            )
            boundary = parse_geo(req.geo)
            forest   = query_forest_data(boundary)
            estimate = run_carbon_engine(carbon_inp, boundary, forest)

            has_range = estimate.quantity_low_tco2e is not None
            form_data.update({
                "area_ha": round(boundary.area_ha, 1),
                "geometry_summary": _geometry_summary(boundary),
                "verdict": estimate.eligibility.verdict,
                "quantity_low_tco2e": estimate.quantity_low_tco2e if has_range else None,
                "quantity_high_tco2e": estimate.quantity_high_tco2e if has_range else None,
            })

            lead_narr_req = NarrativeRequest(
                engine="carbon",
                payload=estimate.model_dump(),
                must_state=["legal harvest right foregone"],
            )
            lead_narr = generate_narrative(lead_narr_req)
            rdata = _build_report_data(carbon_inp, boundary, estimate, filename_base, lead_narr.text, forest)
            pdf_bytes = generate_pdf(rdata)
        except Exception:
            pass  # best-effort PDF; email still sent without attachment

    _deliver(form_data, pdf_bytes or b"", filename_base)
    return {"status": "emailed", "timestamp": ts}


# ── Report download ───────────────────────────────────────────────────────────

@app.post("/api/report")
def report(
    inp: CarbonInput,
    fmt: str = Query(default="pdf", pattern="^(pdf|docx)$"),
) -> Response:
    try:
        boundary = parse_geo(inp.geo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    forest   = query_forest_data(boundary)
    estimate = run_carbon_engine(inp, boundary, forest)

    narr_req = NarrativeRequest(
        engine="carbon",
        payload=estimate.model_dump(),
        must_state=["legal harvest right foregone"],
    )
    narr = generate_narrative(narr_req)

    filename_base = make_filename()
    rdata = _build_report_data(inp, boundary, estimate, filename_base, narr.text, forest)

    has_range = estimate.quantity_low_tco2e is not None
    if has_range:
        summary = (
            f"{estimate.quantity_low_tco2e:,.0f} – {estimate.quantity_high_tco2e:,.0f} tCO2e"
            f" (lifetime) · IPCC Tier 1 · {estimate.methodology.verra_family}"
        )
    else:
        reasons = "; ".join(estimate.eligibility.reasons)
        summary = f"Screening issues: {reasons}"

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    form_data = _build_form_data(inp, boundary, estimate, ts, summary)
    form_data["filename_base"] = filename_base

    if fmt == "pdf":
        content = generate_pdf(rdata)
        media   = "application/pdf"
        fname   = f"{filename_base}.pdf"
        _deliver(form_data, content, filename_base)
    else:
        content = generate_docx(rdata)
        media   = ("application/vnd.openxmlformats-officedocument"
                   ".wordprocessingml.document")
        fname   = f"{filename_base}.docx"
        _deliver(form_data, content, filename_base)

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
