"""api/main.py — FastAPI application for the WO-001 vertical slice.

Routes:
  GET  /               → serves frontend/index.html
  GET  /health         → {"status": "ok"}
  POST /api/carbon     → CarbonInput → EngineResult
  POST /api/lead       → LeadCapture payload → send email, return status

Run locally:
  uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.contracts import (
    CarbonInput, EngineResult, Disclaimer, MapOverlay,
    LeadCapture, ContactInfo, NarrativeRequest,
)
from core.geo import parse_geo
from core.forest import query_forest_data
from engines.carbon.engine import run_carbon_engine
from narrative.narrator import generate_narrative
from api.email import send_lead_email

app = FastAPI(title="180Climate Pre-FS API", version="0.1.0-slice")

_FRONTEND = Path(__file__).parent.parent / "frontend"
_DISCLAIMER_TEXT = (
    "Indicative screening estimate only. Not registry-grade, not financial advice. "
    "Confirm with a full feasibility study before any financial or crediting claim."
)
_CARROT = (
    "This free screening replaces a ~SGD 12K paid pre-feasibility study. "
    "For a bankable feasibility — site visit, accredited methodology, financial model, "
    "Verra registration, and market access — contact info@180climate.net."
)


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


# ── Carbon API ────────────────────────────────────────────────────────────────

@app.post("/api/carbon", response_model=None)
def carbon(inp: CarbonInput) -> JSONResponse:
    # 1 — parse geometry
    try:
        boundary = parse_geo(inp.geo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 2 — forest data (deterministic stub)
    forest = query_forest_data(boundary)

    # 3 — carbon engine
    estimate = run_carbon_engine(inp, boundary, forest)

    # 4 — narrative (template in the slice; LLM in WO-CARBON-005)
    narr_req = NarrativeRequest(
        engine="carbon",
        payload=estimate.model_dump(),
        must_state=["legal harvest right foregone"],
    )
    narr = generate_narrative(narr_req)

    # 5 — build EngineResult
    verdict_labels = {
        "eligible": "Eligible — indicative carbon project opportunity identified",
        "flagged": "Flagged — review required before proceeding",
        "hard_no": "Not Eligible — does not meet minimum screening criteria",
    }
    result = EngineResult(
        engine="carbon",
        verdict=verdict_labels.get(estimate.eligibility.verdict, estimate.eligibility.verdict),
        summary=(
            f"Preliminary estimate: {estimate.quantity_low_tco2e:,.0f}–"
            f"{estimate.quantity_high_tco2e:,.0f} tCO₂e [PLACEHOLDER]. "
            f"Methodology: {estimate.methodology.verra_family}."
        ),
        map=MapOverlay(
            base_tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            boundary_geojson=boundary.geojson,
            loss_overlay={
                "type": "annual_loss_series",
                "data": forest.annual_loss_ha,
                "note": "GFW/Hansen stub — real tiles in WO-CARBON-001",
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
    permit_type: str = ""
    payload_summary: str = ""


@app.post("/api/lead")
def lead(req: LeadRequest) -> dict[str, Any]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    lead_obj = LeadCapture(
        contact=ContactInfo(
            name=req.name,
            email=req.email,
            mobile=req.mobile or None,
            company=req.company or None,
        ),
        engine="carbon",
        payload_summary=(
            req.payload_summary
            or f"IUP: {req.iup_name or '—'} | Permit: {req.permit_type or '—'}"
        ),
        timestamp=ts,
        delivery_status="pending",
    )
    subject_prefix = f"{req.iup_name or 'Lead'} ({req.permit_type or '?'})"
    ok = send_lead_email(lead_obj, subject_prefix=subject_prefix)
    status = "emailed" if ok else "failed"
    lead_obj.delivery_status = status  # type: ignore[assignment]
    return {"status": status, "timestamp": ts}
