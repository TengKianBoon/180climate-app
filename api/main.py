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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from core.contracts import (
    CarbonInput, EngineResult, Disclaimer, GeoInput, MapOverlay,
    LeadCapture, ContactInfo, NarrativeRequest,
)
from core.geo import parse_geo
from core.forest import query_forest_data
from engines.carbon.engine import run_carbon_engine, run_mixed_stratification
from narrative.narrator import generate_narrative
from api.email import send_lead_email
from api.sheets import append_lead
from reports.generator import generate_pdf, generate_docx, ReportData, make_filename

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
    "This free screening already routes your concession to the appropriate "
    "accredited Verra methodology, at an indicative IPCC Tier 1 level — "
    "a first read that a paid pre-feasibility study (~SGD 12K) would otherwise begin. "
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
        **({"filename_base": filename_base} if filename_base else {}),
    )


def _build_form_data(
    inp: CarbonInput,
    boundary,           # type: ignore[no-untyped-def]
    estimate,           # type: ignore[no-untyped-def]
    ts: str,
    payload_summary: str,
) -> dict:
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
        "quantity_low_tco2e": estimate.quantity_low_tco2e,   # None for peat (ADR-0013)
        "quantity_high_tco2e": estimate.quantity_high_tco2e,
        "payload_summary": payload_summary,
    }


def _deliver(
    form_data: dict,
    docx_bytes: bytes,
    filename_base: str,
) -> None:
    """Fire-and-forget: email + Sheet append. Errors are logged, never raised."""
    send_lead_email(
        iup_name=form_data.get("iup_name", "Lead"),
        filename_base=filename_base,
        form_data=form_data,
        docx_bytes=docx_bytes,
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

    docx_bytes: bytes | None = None
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
            docx_bytes = generate_docx(rdata)
        except Exception:
            pass  # best-effort DOCX; email still sent without attachment

    _deliver(form_data, docx_bytes or b"", filename_base)
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

    # Always generate DOCX for the email attachment (regardless of download format)
    docx_bytes = generate_docx(rdata)
    _deliver(form_data, docx_bytes, filename_base)

    if fmt == "pdf":
        content = generate_pdf(rdata)
        media   = "application/pdf"
        fname   = f"{filename_base}.pdf"
    else:
        content = docx_bytes
        media   = ("application/vnd.openxmlformats-officedocument"
                   ".wordprocessingml.document")
        fname   = f"{filename_base}.docx"

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
