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
from typing import Optional

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
    "avoided-emissions claim. Confirm with a full feasibility study, accredited "
    "methodology, and independent third-party verification before any financial or "
    "crediting claim."
)

_ENGAGE_CTA = (
    "If this concession is a candidate for a carbon project, the next step is a "
    "structured feasibility scoping with 180Climate: site visit, accredited methodology "
    "selection and baseline, financial model, Verra registration, and market access.\n\n"
    "Contact: info@180climate.net\n"
    "Website: www.180climate.net"
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

    # ── Peat additionality flag (shown only for peat concessions) ─────────────
    if data.baseline_class == "peat":
        story.append(Paragraph(_PEAT_FLAG_HEADING, H2))
        story.append(Paragraph(_PEAT_FLAG_LEGAL, BODY))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Overlay screening result:</b>", BODY))
        unc_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
        story.append(Paragraph(unc_clean, SMALL))
        story.append(Spacer(1, 4))
        story.append(Paragraph(_PEAT_FLAG_PATHWAY, BODY))
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
    story.append(Paragraph(
        "<i>Methodology confirmation requires a qualified methodology advisor. "
        "All cited methods must be verified as active at the time of registration.</i>",
        SMALL))
    story.append(hr())

    # ── Uncertainty ───────────────────────────────────────────────────────────
    story.append(Paragraph("Uncertainty Band", H2))
    # Strip any markdown artifacts before rendering in PDF
    unc_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
    story.append(Paragraph(unc_clean, BODY))
    story.append(hr())

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Paragraph("Disclaimer", H2))
    story.append(Paragraph(_DISCLAIMER, SMALL))
    story.append(hr())

    # ── Engage 180Climate CTA ────────────────────────────────────────────────
    story.append(Paragraph("Engage 180Climate", H2))
    for line in _ENGAGE_CTA.split("\n"):
        story.append(Paragraph(line or "&nbsp;", BODY))

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

    # ── Peat additionality flag (shown only for peat concessions) ─────────────
    if data.baseline_class == "peat":
        _h2(_PEAT_FLAG_HEADING)
        _body(_PEAT_FLAG_LEGAL)
        _body("Overlay screening result:", bold=True)
        unc_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
        _body(unc_clean, italic=True, colour=(136, 136, 136), size=9)
        _body(_PEAT_FLAG_PATHWAY)
        _hr()

    # ── Methodology ───────────────────────────────────────────────────────────
    _h2("Methodology (Indicative)")
    for k, v in [
        ("Methodology family", data.methodology_short()),
        ("Additionality basis", data.additionality_basis),
        ("Baseline class", data.baseline_class.replace("_", " ").title()),
    ]:
        _kv(k, v)
    _body(
        "Methodology confirmation requires a qualified methodology advisor. "
        "All cited methods must be verified as active at the time of registration.",
        italic=True, colour=(136, 136, 136), size=9,
    )
    _hr()

    # ── Uncertainty ───────────────────────────────────────────────────────────
    _h2("Uncertainty Band")
    unc_clean = re.sub(r"\*\*(.*?)\*\*", r"\1", data.uncertainty)
    _body(unc_clean)
    _hr()

    # ── Disclaimer ────────────────────────────────────────────────────────────
    _h2("Disclaimer")
    _body(_DISCLAIMER, italic=True, colour=(136, 136, 136), size=9)
    _hr()

    # ── Engage 180Climate CTA ────────────────────────────────────────────────
    _h2("Engage 180Climate")
    for line in _ENGAGE_CTA.split("\n"):
        _body(line) if line else doc.add_paragraph()

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
