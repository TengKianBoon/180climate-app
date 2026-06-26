"""reports/generator.py — PDF + DOCX report generation for WO-CARBON-008.

Generates both formats from a CarbonEstimate + metadata.
Filename base: YYMMDDHHMM (UTC), shared between PDF and DOCX.

ADR-0009 invariants enforced here:
- Always a range — never a single bare tCO2e number.
- No "% accuracy" or "% confidence" strings.
- IPCC Tier label present.
- "baseline is the dominant uncertainty" stated explicitly.
- Ends with "Engage 180Climate" CTA.
"""
from __future__ import annotations
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_LOGO_PATH = Path(__file__).parent.parent / "brand" / "180climate-logo.png"
# Logo dimensions: 314×282 px → aspect ratio ≈ 1.113
_LOGO_ASPECT = 314 / 282


def make_filename() -> str:
    """YYMMDDHHMM UTC timestamp — shared base for .pdf and .docx."""
    return datetime.now(timezone.utc).strftime("%y%m%d%H%M")


@dataclass
class ReportData:
    iup_name: str
    iup_address: str
    permit_type: str
    permit_years_remaining: int
    project_type: str
    contact_name: str
    contact_email: str
    contact_mobile: Optional[str]
    contact_company: Optional[str]
    verdict: str                      # "eligible" | "flagged" | "hard_no"
    verdict_label: str
    quantity_low_tco2e: Optional[float]
    quantity_high_tco2e: Optional[float]
    baseline_class: str               # "planned_clearfell" | "planned_selective" | "peat"
    verra_family: str
    additionality_basis: str
    uncertainty: str
    area_ha: float
    filename_base: str = field(default_factory=make_filename)
    # Comprehensive report additions (WO-REPORT-001)
    quality: Optional[Any] = field(default=None)
    narrative: str = field(default="")
    forest_baseline_cover_pct: Optional[float] = field(default=None)
    forest_annual_loss_ha: dict = field(default_factory=dict)
    forest_loss_after_2020_ha: Optional[float] = field(default=None)
    forest_peat_present: Optional[bool] = field(default=None)
    forest_biomass_tco2_per_ha: Optional[float] = field(default=None)
    data_sources: list = field(default_factory=list)
    derivation: Optional[Any] = field(default=None)   # ADR-0014 CalculationTrace; None for peat

    # --- derived helpers ---

    def range_str(self) -> str:
        if self.quantity_low_tco2e is None or self.quantity_high_tco2e is None:
            return "Not shown — resolve eligibility issues before estimate."
        return (
            f"{self.quantity_low_tco2e:,.0f} – {self.quantity_high_tco2e:,.0f} tCO2e"
        )

    def methodology_short(self) -> str:
        bc = self.baseline_class
        if bc == "planned_clearfell":
            return "APD (Avoided Planned Deforestation) — VM0009"
        if bc == "planned_selective":
            return "IFM (Improved Forest Management) — VM0045 / VM0010"
        if bc == "peat":
            return "PEAT — no settled active Verra method as of 2026 (ADR-0012)"
        return self.verra_family


_DISCLAIMER = (
    "Indicative Tier 1 screening only — not registry-grade, not financial advice. "
    "This figure uses IPCC default values and a proxy loss rate; it is not a verified "
    "avoided-emissions claim. Confirm with a full feasibility study — registry-grade "
    "methodology application and independent third-party verification — before any "
    "financial or crediting claim."
)

_ENGAGE_CTA = (
    "This free screening already identifies the applicable Verra methodology family "
    "(subject to advisor confirmation and Verra's evolving rules), at an indicative "
    "IPCC Tier 1 level — a first read that a paid pre-feasibility study (service fee "
    "~SGD 12K; separate from any carbon credit value) would otherwise begin.\n\n"
    "To take it to a bankable, registry-grade carbon project — field validation, full "
    "methodology application, a financial model, independent third-party verification, "
    "Verra registration, and market access — talk to 180Climate.\n\n"
    "Contact: info@180climate.net\n"
    "Website: www.180climate.net"
)

_ADDITIONALITY_CAVEAT = (
    "Note: 'legal harvest right foregone' is necessary but not sufficient for "
    "additionality. It must also be accompanied by demonstrated genuine harvest intent — "
    "an approved management plan with confirmed financing and operational viability "
    "(not satellite-derivable at screening stage). Additionally, the PIPPIB moratorium "
    "(Inpres 5/2019), if applicable, can negate the legal right and make "
    "avoided-conversion non-additional (regulatory surplus fails); the KHG overlay "
    "screens for this."
)

_DOMINANT_UNC = (
    "The baseline harvest rate — the legally-permitted extraction rate from the IUP "
    "permit — is the dominant uncertainty, not the satellite data. The carbon density "
    "is co-dominant. This estimate is a conservative observed-loss floor, not the "
    "registry-grade planned-harvest baseline established at project design."
)

_PEAT_FLAG_HEADING = "Peat Additionality Flag"

_PEAT_FLAG_INTRO = (
    "No indicative carbon tonnage is shown for this concession. Peat parcels route to "
    "a qualitative flag under 180Climate's methodology (ADR-0013), not an indicative number."
)

_PEAT_FLAG_LEGAL = (
    "Why: on legally protected Indonesian peat, the avoided-conversion baseline fails the "
    "Verra VCS regulatory-surplus test. Clearing is already legally prohibited under "
    "PP 57/2016 (ecosystem function / fungsi lindung) and Inpres 5/2019 (PIPPIB moratorium); "
    '"not clearing" is the mandated legal baseline, not an additional action. '
    "Crediting the avoidance of an illegal act is not permissible under Verra AFOLU rules."
)

_PEAT_FLAG_PATHWAY = (
    "This does not mean the concession is ineligible for carbon finance. A restoration or "
    "peat rewetting (WRC) approach — where the without-project scenario is continued "
    "oxidation and fire of already-drained peat — may be additionally claimable under a "
    "methodology such as VM0007 (WRC component). That determination requires a site visit, "
    "hydrology survey, and qualified methodology advisor. "
    "Contact 180Climate to explore the restoration pathway."
)


def _derivation_rows(d: Any) -> list[tuple[str, str]]:
    """Convert a CalculationTrace into an ordered list of label/value pairs for the report."""
    if d is None:
        return []
    rows: list[tuple[str, str]] = []
    rows.append(("Eligible area", f"{d.eligible_area_ha:,.0f} ha"))
    rows.append(("Project crediting period", f"{d.project_years} yr"))
    if d.basis == "redd":
        if d.baseline_loss_rate_yr is not None:
            rows.append(("Baseline loss rate (mean)", f"{d.baseline_loss_rate_yr*100:.4f}%/yr"))
        if d.loss_rate_sem_pct is not None:
            rows.append(("Loss-rate uncertainty (SEM)", f"{d.loss_rate_sem_pct:.1f}% (ADR-0016-M1)"))
        if d.carbon_density_tco2_ha is not None:
            src = f" [{d.carbon_density_source}]" if d.carbon_density_source else ""
            rows.append(("Carbon density", f"{d.carbon_density_tco2_ha:,.1f} tCO2/ha{src}"))
        if d.carbon_density_cv_pct is not None:
            rows.append(("Density CV (relative SE)", f"{d.carbon_density_cv_pct:.0f}%"))
        if d.sigma_combined_pct is not None:
            rows.append(("Combined sigma (quadrature)", f"{d.sigma_combined_pct:.1f}%"))
    elif d.basis == "ifm":
        if d.harvested_area_ha is not None:
            rows.append(("Harvested area (one entry)", f"{d.harvested_area_ha:,.0f} ha"))
        if d.ef_central_tco2_ha is not None:
            rows.append(("EF_central (Pearson-2014)", f"{d.ef_central_tco2_ha:.2f} tCO2/ha"))
        if d.sigma_ifm_pct is not None:
            rows.append(("Combined sigma (quadrature)", f"{d.sigma_ifm_pct:.1f}% (TPTI intensity + TEF)"))
    if d.central_tco2e is not None:
        rows.append(("Central estimate", f"{d.central_tco2e:,.0f} tCO2e"))
    if d.gross_low_tco2e is not None and d.gross_high_tco2e is not None:
        rows.append(("Pre-buffer band",
                     f"[{d.gross_low_tco2e:,.0f} – {d.gross_high_tco2e:,.0f}] tCO2e"))
    rows.append(("VCS buffer deducted",
                 f"{int(d.buffer_low*100)}–{int(d.buffer_high*100)}% (separately labelled)"))
    rows.append(("Net range (reproduced)",
                 f"{d.net_low_tco2e:,.0f} – {d.net_high_tco2e:,.0f} tCO2e"))
    return rows


# ── PDF ───────────────────────────────────────────────────────────────────────

def generate_pdf(data: ReportData) -> bytes:
    """Return PDF bytes for the pre-feasibility report."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=f"180Climate Carbon Pre-Feasibility Report — {data.iup_name}",
        author="180Climate",
    )

    styles = getSampleStyleSheet()
    navy   = colors.HexColor("#1a1a2e")
    green  = colors.HexColor("#15913A")
    grey   = colors.HexColor("#555555")
    ltgrey = colors.HexColor("#888888")

    H1 = ParagraphStyle("H1", parent=styles["Heading1"],
                         textColor=navy, fontSize=16, leading=20, spaceAfter=4)
    H2 = ParagraphStyle("H2", parent=styles["Heading2"],
                         textColor=green, fontSize=11, leading=14, spaceBefore=14, spaceAfter=4)
    BODY = ParagraphStyle("Body", parent=styles["Normal"],
                           fontSize=9.5, leading=14, spaceAfter=6, textColor=navy)
    SMALL = ParagraphStyle("Small", parent=styles["Normal"],
                            fontSize=8, leading=12, textColor=grey)
    RANGE = ParagraphStyle("Range", parent=styles["Normal"],
                            fontSize=20, leading=24, textColor=green, fontName="Helvetica-Bold")
    LABEL = ParagraphStyle("Label", parent=styles["Normal"],
                            fontSize=8, textColor=ltgrey, spaceAfter=2)
    META  = ParagraphStyle("Meta", parent=styles["Normal"],
                            fontSize=8.5, textColor=grey, leading=13)

    def hr():
        return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"),
                           spaceAfter=6, spaceBefore=2)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    if _LOGO_PATH.exists():
        from reportlab.platypus import Image as RLImage
        logo_h = 1.6 * cm
        logo_w = logo_h * _LOGO_ASPECT
        story.append(RLImage(str(_LOGO_PATH), width=logo_w, height=logo_h))
        story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("180Climate", ParagraphStyle(
            "Brand", parent=H1, fontSize=22, textColor=green, fontName="Helvetica-Bold")))
    story.append(Paragraph("Carbon Pre-Feasibility Report", ParagraphStyle(
        "Sub", parent=H1, fontSize=13, textColor=navy, spaceBefore=0)))
    story.append(Spacer(1, 6))

    meta_rows = [
        ("Concession", data.iup_name),
        ("Region", data.iup_address or "—"),
        ("Permit", f"{data.permit_type} · {data.permit_years_remaining} years remaining"),
        ("Prepared for", f"{data.contact_name}" + (f", {data.contact_company}" if data.contact_company else "")),
        ("Reference", data.filename_base),
        ("Date (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    ]
    for k, v in meta_rows:
        story.append(Paragraph(f"<b>{k}:</b> {v}", META))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Indicative screening only — not registry-grade, not financial advice.",
        SMALL))
    story.append(hr())

    # ── Eligibility verdict ───────────────────────────────────────────────────
    story.append(Paragraph("Eligibility Verdict", H2))
    verdict_colours = {
        "eligible": colors.HexColor("#15913A"),
        "flagged":  colors.HexColor("#78350f"),
        "hard_no":  colors.HexColor("#7f1d1d"),
    }
    vc = verdict_colours.get(data.verdict, navy)
    story.append(Paragraph(data.verdict_label, ParagraphStyle(
        "Verdict", parent=BODY, textColor=vc, fontName="Helvetica-Bold", fontSize=11)))
    story.append(hr())

    # ── Carbon estimate ───────────────────────────────────────────────────────
    story.append(Paragraph("Indicative Carbon Estimate", H2))
    if data.quantity_low_tco2e is not None:   # has range (non-peat eligible)
        story.append(Paragraph(data.range_str(), RANGE))
        story.append(Paragraph("Project lifetime · IPCC Tier 1 Screening", LABEL))
        story.append(Spacer(1, 4))

        detail_rows = [
            ("Concession area", f"{data.area_ha:,.0f} ha"),
            ("Permit duration", f"{min(data.permit_years_remaining, 30)} years (capped at 30)"),
            ("Screening tier", "IPCC Tier 1 — indicative, not registry-grade"),
        ]
        for k, v in detail_rows:
            story.append(Paragraph(f"<b>{k}:</b> {v}", BODY))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Dominant uncertainty</b>", BODY))
        story.append(Paragraph(_DOMINANT_UNC, BODY))
    elif data.baseline_class == "peat":
        story.append(Paragraph(_PEAT_FLAG_INTRO, BODY))
    else:
        story.append(Paragraph(
            "Carbon estimate not shown — resolve screening issues before proceeding.",
            BODY))
    story.append(hr())

    # ── How this estimate is derived (ADR-0014) ───────────────────────────────
    if data.baseline_class == "peat":
        story.append(Paragraph("How This Estimate Is Derived", H2))
        story.append(Paragraph(_PEAT_FLAG_HEADING, ParagraphStyle(
            "PeatSubH", parent=BODY, fontName="Helvetica-Bold")))
        story.append(Paragraph(_PEAT_FLAG_LEGAL, BODY))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Overlay screening result:</b>", BODY))
        unc_clean_peat = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
        story.append(Paragraph(unc_clean_peat, SMALL))
        story.append(Spacer(1, 4))
        story.append(Paragraph(_PEAT_FLAG_PATHWAY, BODY))
    elif data.derivation is not None:
        story.append(Paragraph("How This Estimate Is Derived", H2))
        d = data.derivation
        story.append(Paragraph(
            f"<i>Formula ({d.basis.upper()}): {d.formula}</i>", SMALL))
        story.append(Spacer(1, 4))
        for _k, _v in _derivation_rows(d):
            story.append(Paragraph(f"<b>{_k}:</b> {_v}", BODY))
        if d.notes:
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<i>{d.notes}</i>", SMALL))
    elif data.quantity_low_tco2e is not None:
        story.append(Paragraph("How This Estimate Is Derived", H2))
        story.append(Paragraph(
            "Derivation detail not available for this estimate variant.", SMALL))
    story.append(hr())

    # ── Methodology ───────────────────────────────────────────────────────────
    story.append(Paragraph("Methodology (Indicative)", H2))
    meth_rows = [
        ("Methodology family", data.methodology_short()),
        ("Additionality basis", data.additionality_basis),
        ("Baseline class", data.baseline_class.replace("_", " ").title()),
    ]
    for k, v in meth_rows:
        story.append(Paragraph(f"<b>{k}:</b> {v}", BODY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(_ADDITIONALITY_CAVEAT, SMALL))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<i>Methodology confirmation requires a qualified methodology advisor. "
        "All cited methods must be verified as active at the time of registration.</i>",
        SMALL))
    story.append(hr())

    # ── Quality factors ───────────────────────────────────────────────────────
    if data.quality:
        story.append(Paragraph("Quality Factors", H2))
        for label, value in [
            ("Additionality", data.quality.additionality),
            ("Permanence", data.quality.permanence),
            ("Leakage", data.quality.leakage),
            ("Methodology fit", data.quality.methodology_fit),
        ]:
            story.append(Paragraph(f"<b>{label}:</b> {value}", BODY))
        story.append(hr())

    # ── Engage 180Climate CTA ────────────────────────────────────────────────
    story.append(Paragraph("Engage 180Climate", H2))
    for line in _ENGAGE_CTA.split("\n"):
        story.append(Paragraph(line or "&nbsp;", BODY))
    story.append(hr())

    # ════════════════════════════════════════════════════════════════════════════
    # FINE PRINT — supporting detail; narrative, uncertainty, data, disclaimer
    # ════════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Notes &amp; Supporting Detail", ParagraphStyle(
        "FPHead", parent=H2, textColor=colors.HexColor("#888888"), fontSize=9)))

    # ── Forest data summary ───────────────────────────────────────────────────
    story.append(Paragraph("Forest Data Summary", H2))
    _forest_rows = []
    if data.forest_baseline_cover_pct is not None:
        _forest_rows.append(("Baseline canopy cover",
                             f"{data.forest_baseline_cover_pct:.1f}%"))
    if data.forest_annual_loss_ha:
        _yrs = sorted(data.forest_annual_loss_ha.keys())
        _tot = sum(data.forest_annual_loss_ha.values())
        _avg = _tot / len(_yrs) if _yrs else 0
        _forest_rows.append(("Annual loss rate (avg)",
                             f"{_avg:,.0f} ha/yr ({_yrs[0]}–{_yrs[-1]})"))
        _win = [y for y in _yrs if 2016 <= y <= 2022]
        if _win:
            _wa = sum(data.forest_annual_loss_ha[y] for y in _win) / len(_win)
            _forest_rows.append(("Loss rate (2016–2022 avg, used in estimate)",
                                f"{_wa:,.0f} ha/yr"))
    if data.forest_loss_after_2020_ha is not None:
        _forest_rows.append(("Loss after Dec 2020",
                             f"{data.forest_loss_after_2020_ha:,.0f} ha"))
    if data.forest_peat_present is not None:
        _forest_rows.append(("Peat presence (proxy)",
                             "Yes" if data.forest_peat_present else "No"))
    if data.forest_biomass_tco2_per_ha is not None:
        _forest_rows.append(("Biomass density",
                             f"{data.forest_biomass_tco2_per_ha:,.1f} tCO2/ha"))
    if not _forest_rows:
        story.append(Paragraph("Not available at screening stage.", SMALL))
    for _k, _v in _forest_rows:
        story.append(Paragraph(f"<b>{_k}:</b> {_v}", SMALL))
    story.append(hr())

    # ── Assessment narrative ──────────────────────────────────────────────────
    if data.narrative:
        story.append(Paragraph("Assessment Narrative", H2))
        _narr_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.narrative)
        _narr_clean = re.sub(r"^---$", "", _narr_clean, flags=re.MULTILINE)
        for _line in _narr_clean.split("\n"):
            _line = _line.strip()
            if _line:
                story.append(Paragraph(_line, SMALL))
            else:
                story.append(Spacer(1, 4))
        story.append(hr())

    # ── Uncertainty ───────────────────────────────────────────────────────────
    story.append(Paragraph("Uncertainty Band", H2))
    unc_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
    story.append(Paragraph(unc_clean, SMALL))
    story.append(hr())

    # ── Data sources ──────────────────────────────────────────────────────────
    if data.data_sources:
        story.append(Paragraph("Data Sources", H2))
        for _src in data.data_sources:
            story.append(Paragraph(f"• {_src}", SMALL))
        story.append(hr())

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Paragraph("Disclaimer", H2))
    story.append(Paragraph(_DISCLAIMER, SMALL))

    doc.build(story)
    return buf.getvalue()


# ── DOCX ──────────────────────────────────────────────────────────────────────

def generate_docx(data: ReportData) -> bytes:
    """Return DOCX bytes for the pre-feasibility report."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.0)
        section.right_margin  = Inches(1.0)

    def _h1(text: str, colour: tuple = (26, 26, 46)) -> None:
        p = doc.add_heading(text, level=1)
        run = p.runs[0] if p.runs else p.add_run(text)
        run.font.color.rgb = RGBColor(*colour)

    def _h2(text: str) -> None:
        p = doc.add_heading(text, level=2)
        for run in p.runs:
            run.font.color.rgb = RGBColor(21, 145, 58)  # brand green

    def _body(text: str, bold: bool = False, italic: bool = False,
              colour: tuple | None = None, size: int = 10) -> None:
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.bold   = bold
        run.italic = italic
        if colour:
            run.font.color.rgb = RGBColor(*colour)

    def _kv(key: str, value: str) -> None:
        p = doc.add_paragraph()
        r1 = p.add_run(key + ": ")
        r1.bold = True
        r1.font.size = Pt(10)
        r2 = p.add_run(value)
        r2.font.size = Pt(10)

    def _hr() -> None:
        p = doc.add_paragraph()
        p.paragraph_format.space_after  = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "cccccc")
        pBdr.append(bottom)
        pPr.append(pBdr)

    # ── Header ────────────────────────────────────────────────────────────────
    if _LOGO_PATH.exists():
        from docx.shared import Inches as _Inches
        p = doc.add_paragraph()
        run = p.add_run()
        run.add_picture(str(_LOGO_PATH), height=_Inches(0.55))
        doc.add_paragraph()  # spacer
    else:
        _h1("180Climate", colour=(45, 106, 79))
    _h1("Carbon Pre-Feasibility Report", colour=(26, 26, 46))

    for key, val in [
        ("Concession", data.iup_name),
        ("Region", data.iup_address or "—"),
        ("Permit", f"{data.permit_type} · {data.permit_years_remaining} years remaining"),
        ("Prepared for", f"{data.contact_name}" + (f", {data.contact_company}" if data.contact_company else "")),
        ("Reference", data.filename_base),
        ("Date (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    ]:
        _kv(key, val)

    _body("Indicative screening only — not registry-grade, not financial advice.",
          italic=True, colour=(136, 136, 136), size=9)
    _hr()

    # ── Eligibility ───────────────────────────────────────────────────────────
    _h2("Eligibility Verdict")
    verdict_colours = {
        "eligible": (21, 145, 58),
        "flagged":  (120, 53, 15),
        "hard_no":  (127, 29, 29),
    }
    _body(data.verdict_label, bold=True,
          colour=verdict_colours.get(data.verdict, (26, 26, 46)))
    _hr()

    # ── Carbon estimate ───────────────────────────────────────────────────────
    _h2("Indicative Carbon Estimate")
    if data.quantity_low_tco2e is not None:   # has range (non-peat eligible)
        p = doc.add_paragraph()
        run = p.add_run(data.range_str())
        run.font.size = Pt(18)
        run.bold = True
        run.font.color.rgb = RGBColor(21, 145, 58)

        _body("Project lifetime · IPCC Tier 1 Screening", italic=True,
              colour=(136, 136, 136), size=9)

        for k, v in [
            ("Concession area", f"{data.area_ha:,.0f} ha"),
            ("Permit duration", f"{min(data.permit_years_remaining, 30)} years (capped at 30)"),
            ("Screening tier", "IPCC Tier 1 — indicative, not registry-grade"),
        ]:
            _kv(k, v)

        _body("Dominant uncertainty", bold=True)
        _body(_DOMINANT_UNC)
    elif data.baseline_class == "peat":
        _body(_PEAT_FLAG_INTRO, italic=True)
    else:
        _body("Carbon estimate not shown — resolve screening issues before proceeding.",
              italic=True)
    _hr()

    # ── How this estimate is derived (ADR-0014) ───────────────────────────────
    _h2("How This Estimate Is Derived")
    if data.baseline_class == "peat":
        _body(_PEAT_FLAG_HEADING, bold=True)
        _body(_PEAT_FLAG_LEGAL)
        _body("Overlay screening result:", bold=True)
        unc_clean_peat = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
        _body(unc_clean_peat, italic=True, colour=(136, 136, 136), size=9)
        _body(_PEAT_FLAG_PATHWAY)
    elif data.derivation is not None:
        d = data.derivation
        _body(f"Formula ({d.basis.upper()}): {d.formula}",
              italic=True, colour=(136, 136, 136), size=9)
        doc.add_paragraph()
        for _k, _v in _derivation_rows(d):
            _kv(_k, _v)
        if d.notes:
            _body(d.notes, italic=True, colour=(136, 136, 136), size=9)
    elif data.quantity_low_tco2e is not None:
        _body("Derivation detail not available for this estimate variant.",
              italic=True, colour=(136, 136, 136), size=9)
    _hr()

    # ── Methodology ───────────────────────────────────────────────────────────
    _h2("Methodology (Indicative)")
    for k, v in [
        ("Methodology family", data.methodology_short()),
        ("Additionality basis", data.additionality_basis),
        ("Baseline class", data.baseline_class.replace("_", " ").title()),
    ]:
        _kv(k, v)
    _body(_ADDITIONALITY_CAVEAT, italic=True, colour=(136, 136, 136), size=9)
    _body(
        "Methodology confirmation requires a qualified methodology advisor. "
        "All cited methods must be verified as active at the time of registration.",
        italic=True, colour=(136, 136, 136), size=9,
    )
    _hr()

    # ── Quality factors ───────────────────────────────────────────────────────
    if data.quality:
        _h2("Quality Factors")
        for _label, _value in [
            ("Additionality", data.quality.additionality),
            ("Permanence", data.quality.permanence),
            ("Leakage", data.quality.leakage),
            ("Methodology fit", data.quality.methodology_fit),
        ]:
            _kv(_label, _value)
        _hr()

    # ── Engage 180Climate CTA ────────────────────────────────────────────────
    _h2("Engage 180Climate")
    for line in _ENGAGE_CTA.split("\n"):
        _body(line) if line else doc.add_paragraph()
    _hr()

    # ════════════════════════════════════════════════════════════════════════════
    # FINE PRINT — supporting detail; narrative, uncertainty, data, disclaimer
    # ════════════════════════════════════════════════════════════════════════════
    _body("Notes & Supporting Detail", bold=True, colour=(136, 136, 136), size=9)

    # ── Forest data summary ───────────────────────────────────────────────────
    _h2("Forest Data Summary")
    _has_fd = False
    if data.forest_baseline_cover_pct is not None:
        _kv("Baseline canopy cover", f"{data.forest_baseline_cover_pct:.1f}%")
        _has_fd = True
    if data.forest_annual_loss_ha:
        _yrs = sorted(data.forest_annual_loss_ha.keys())
        _tot = sum(data.forest_annual_loss_ha.values())
        _avg = _tot / len(_yrs) if _yrs else 0
        _kv("Annual loss rate (avg)", f"{_avg:,.0f} ha/yr ({_yrs[0]}–{_yrs[-1]})")
        _win = [y for y in _yrs if 2016 <= y <= 2022]
        if _win:
            _wa = sum(data.forest_annual_loss_ha[y] for y in _win) / len(_win)
            _kv("Loss rate (2016–2022 avg, used in estimate)", f"{_wa:,.0f} ha/yr")
        _has_fd = True
    if data.forest_loss_after_2020_ha is not None:
        _kv("Loss after Dec 2020", f"{data.forest_loss_after_2020_ha:,.0f} ha")
        _has_fd = True
    if data.forest_peat_present is not None:
        _kv("Peat presence (proxy)", "Yes" if data.forest_peat_present else "No")
        _has_fd = True
    if data.forest_biomass_tco2_per_ha is not None:
        _kv("Biomass density", f"{data.forest_biomass_tco2_per_ha:,.1f} tCO2/ha")
        _has_fd = True
    if not _has_fd:
        _body("Not available at screening stage.", italic=True, colour=(136, 136, 136), size=9)
    _hr()

    # ── Assessment narrative ──────────────────────────────────────────────────
    if data.narrative:
        _h2("Assessment Narrative")
        _narr_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.narrative)
        _narr_clean = re.sub(r"^---$", "", _narr_clean, flags=re.MULTILINE)
        for _line in _narr_clean.split("\n"):
            _line = _line.strip()
            if _line:
                _body(_line, size=9)
            else:
                doc.add_paragraph()
        _hr()

    # ── Uncertainty ───────────────────────────────────────────────────────────
    _h2("Uncertainty Band")
    unc_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
    _body(unc_clean, size=9)
    _hr()

    # ── Data sources ──────────────────────────────────────────────────────────
    if data.data_sources:
        _h2("Data Sources")
        for _src in data.data_sources:
            _body(f"• {_src}", size=9)
        _hr()

    # ── Disclaimer ────────────────────────────────────────────────────────────
    _h2("Disclaimer")
    _body(_DISCLAIMER, italic=True, colour=(136, 136, 136), size=9)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
