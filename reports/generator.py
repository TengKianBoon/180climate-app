"""reports/generator.py — Value-first PDF + DOCX report (WO-VALUEFIRST-001).

Section order (per docs/design/value-first-report-mockup.html):
  1. Header  (logo + concession + date)
  2. Hero    (range + per-year + indicative $)
  3. Why qualifies  (APD / IFM / peat pathway)
  4. Strengths  (quality factors as strengths)
  5. How built  (derivation table)
  6. What we found  (forest data + flags as opportunities)
  7. How to grow  (RKU/RKT upload)
  8. CTA  (Engage 180Climate)
  9. Footer  (ONE line only — no body disclaimers anywhere)

ADR-0009 invariants:
- Always a range; never a single bare tCO2e number.
- No "% accuracy" or "% confidence" strings.
- IPCC Tier label present.
"""
from __future__ import annotations
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_LOGO_PATH = Path(__file__).parent.parent / "brand" / "180climate-logo.png"
_LOGO_ASPECT = 314 / 282

# Presentation-layer config — never in contracts (no Gate C required)
INDICATIVE_PRICE_USD_PER_TCO2E = 8


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
    baseline_class: str
    verra_family: str
    additionality_basis: str
    uncertainty: str
    area_ha: float
    filename_base: str = field(default_factory=make_filename)
    quality: Optional[Any] = field(default=None)
    narrative: str = field(default="")
    forest_baseline_cover_pct: Optional[float] = field(default=None)
    forest_annual_loss_ha: dict = field(default_factory=dict)
    forest_loss_after_2020_ha: Optional[float] = field(default=None)
    forest_peat_present: Optional[bool] = field(default=None)
    forest_biomass_tco2_per_ha: Optional[float] = field(default=None)
    data_sources: list = field(default_factory=list)
    derivation: Optional[Any] = field(default=None)
    quantity_low_per_yr_tco2e: Optional[float] = field(default=None)   # ADR-0017
    quantity_high_per_yr_tco2e: Optional[float] = field(default=None)  # ADR-0017

    # --- derived helpers ---

    def range_str(self) -> str:
        if self.quantity_low_tco2e is None or self.quantity_high_tco2e is None:
            return "Carbon restoration pathway — see below"
        return (
            f"{self.quantity_low_tco2e:,.0f} – {self.quantity_high_tco2e:,.0f} tCO2e"
        )

    def per_yr_str(self) -> str:
        if self.quantity_low_per_yr_tco2e is None or self.quantity_high_per_yr_tco2e is None:
            return ""
        return (
            f"≈ {self.quantity_low_per_yr_tco2e:,.0f} – "
            f"{self.quantity_high_per_yr_tco2e:,.0f} tonnes per year"
        )

    def worth_str(self) -> str:
        if self.quantity_low_tco2e is None or self.quantity_high_tco2e is None:
            return ""
        p = INDICATIVE_PRICE_USD_PER_TCO2E
        lo = int(self.quantity_low_tco2e * p)
        hi = int(self.quantity_high_tco2e * p)

        def _fmt_m(n: int) -> str:
            if n >= 1_000_000:
                return f"US${n/1_000_000:.0f}M"
            return f"US${n:,.0f}"

        return (
            f"At indicative voluntary-carbon prices (~US${p}/tonne), "
            f"roughly {_fmt_m(lo)} – {_fmt_m(hi)} across the project. "
            f"(Indicative market range, not a quote.)"
        )

    def methodology_short(self) -> str:
        bc = self.baseline_class
        if bc == "planned_clearfell":
            return "APD (Avoided Planned Deforestation) — VM0009"
        if bc == "planned_selective":
            return "IFM (Improved Forest Management) — VM0045 / VM0010"
        if bc == "peat":
            return "PEAT — no settled active Verra method as of 2026"
        return self.verra_family

    def why_qualifies(self) -> str:
        """Substantive copy for 'Why your forest qualifies' per permit type."""
        bc = self.baseline_class
        pt = self.permit_type
        if bc == "planned_clearfell":
            return (
                f"Avoided Planned Deforestation (APD). Your {pt} permit is a legal right "
                "to clear-fell this natural forest. A carbon project earns by foregoing that "
                "clearance — the forest stays standing and the avoided emissions become credits. "
                "That is the right Verra pathway for a timber concession holding standing natural "
                "forest, and it is why this opportunity exists for you specifically."
            )
        if bc == "planned_selective":
            return (
                f"Improved Forest Management (IFM). Your {pt} permit authorises selective "
                "logging. A carbon project earns by reducing the harvest intensity below the "
                "permitted baseline — the unharvested trees continue growing and sequestering "
                "carbon. This is the correct Verra pathway for a selective-logging concession, "
                "and it is why your concession qualifies."
            )
        if bc == "peat":
            return (
                "Peat Restoration Pathway. While direct avoided-deforestation carbon credits "
                "are not available for legally protected peat (the without-project baseline "
                "is already no-clearance), a peat-rewetting or restoration approach may qualify "
                "where the without-project scenario is continued oxidation and fire of "
                "already-drained peat. That pathway — which can also pay — requires a site "
                "visit, hydrology survey, and a qualified methodology advisor. "
                "Contact 180Climate to explore the restoration pathway."
            )
        return (
            f"Your {pt} concession holds standing forest that qualifies for a "
            "voluntary carbon project under the applicable Verra methodology family. "
            "A pre-feasibility study will confirm the route."
        )

    def quality_cards(self) -> list[tuple[str, str]]:
        """Return quality factors as strength statements."""
        if self.quality is None:
            return []
        return [
            ("Additionality", self.quality.additionality),
            ("Permanence",    self.quality.permanence),
            ("Leakage",       self.quality.leakage),
            ("Methodology fit", self.quality.methodology_fit),
        ]


_FOOTER_LINE = (
    "Indicative satellite screening — not a verified credit issuance or legal advice. "
    "IPCC Tier 1 approach. How this is calculated & legal notes: 180climate.net/methodology."
)

_CTA_BODY = (
    "Your next step — engage 180Climate. "
    "A Pre-Feasibility Study (site visit, field sampling, financial model, "
    "methodology lock-in, market access) turns this screening into a bankable, "
    "verified number.\n\n"
    "info@180climate.net   ·   www.180climate.net"
)

_GROW_TEXT = (
    "Upload your harvest plan (RKU/RKT) — it tightens this estimate and proves "
    "the project counts, moving you from 'opportunity' to 'fundable.'"
)

_PEAT_FOUND_TEXT = (
    "Your land includes areas mapped under the national peat moratorium (PIPPIB) or "
    "peat ecosystem function zones (KHG). This means avoided-deforestation credits are "
    "not available there — but a peat rewetting or restoration project, which can also "
    "pay, may qualify. We caught this for you before any field spend."
)


def _derivation_rows(d: Any) -> list[tuple[str, str]]:
    """Convert a CalculationTrace into an ordered list of label/value pairs."""
    if d is None:
        return []
    rows: list[tuple[str, str]] = []
    rows.append(("Eligible forest area", f"{d.eligible_area_ha:,.0f} ha"))
    if d.basis == "redd":
        if d.baseline_loss_rate_yr is not None:
            rows.append(("Observed forest-loss rate", f"{d.baseline_loss_rate_yr*100:.4f}%/yr (satellite baseline)"))
        if d.carbon_density_tco2_ha is not None:
            src = f" [{d.carbon_density_source}]" if d.carbon_density_source else ""
            rows.append(("Carbon density", f"{d.carbon_density_tco2_ha:,.0f} tCO2/ha{src}"))
        if d.sigma_combined_pct is not None:
            rows.append(("Uncertainty band (sigma)", f"±{d.sigma_combined_pct:.1f}% (quadrature, ADR-0016-M1)"))
    elif d.basis == "ifm":
        if d.harvested_area_ha is not None:
            rows.append(("Harvest-eligible area (one TPTI cycle)", f"{d.harvested_area_ha:,.0f} ha"))
        if d.ef_central_tco2_ha is not None:
            rows.append(("Emission factor (Pearson-2014)", f"{d.ef_central_tco2_ha:.2f} tCO2/ha"))
        if d.sigma_ifm_pct is not None:
            rows.append(("Uncertainty band (sigma)", f"±{d.sigma_ifm_pct:.1f}% (quadrature, ADR-0016-M1)"))
    rows.append(("Project period", f"{d.project_years} years"))
    if d.gross_low_tco2e is not None and d.gross_high_tco2e is not None:
        rows.append(("Gross band (pre-buffer)",
                     f"{d.gross_low_tco2e:,.0f} – {d.gross_high_tco2e:,.0f} tCO2e"))
    rows.append(("VCS permanence buffer",
                 f"{int(d.buffer_low*100)}–{int(d.buffer_high*100)}% (risk-pooled, deducted separately)"))
    rows.append(("Estimated avoided emissions",
                 f"{d.net_low_tco2e:,.0f} – {d.net_high_tco2e:,.0f} tCO2e"))
    return rows


def _what_we_found(data: "ReportData") -> list[str]:
    """Build bullet-point 'what we found' items — flags as opportunities, not hedges."""
    items: list[str] = []
    if data.forest_baseline_cover_pct is not None:
        items.append(
            f"{data.area_ha:,.0f} ha of forest ({data.forest_baseline_cover_pct:.0f}% "
            "canopy cover) — the basis of your number."
        )
    if data.forest_annual_loss_ha:
        win = {y: v for y, v in data.forest_annual_loss_ha.items() if 2016 <= y <= 2022}
        if win:
            avg = sum(win.values()) / len(win)
            items.append(
                f"Measurable clearing trend ({avg:,.0f} ha/yr observed, 2016–2022) "
                "that a project would avoid — a real, bankable baseline."
            )
    if data.forest_peat_present:
        items.append(
            "Peat areas on your land: these qualify for a restoration project (which can "
            "also pay) — nearly all your land has a credit pathway."
        )
    if data.forest_biomass_tco2_per_ha is not None:
        items.append(
            f"Satellite biomass estimate: {data.forest_biomass_tco2_per_ha:,.0f} tCO2/ha "
            "(used in this screening; a field study locks in a project-specific figure)."
        )
    if data.baseline_class == "peat":
        items.append(_PEAT_FOUND_TEXT)
    return items


# ── PDF ───────────────────────────────────────────────────────────────────────

def generate_pdf(data: ReportData) -> bytes:
    """Return PDF bytes for the value-first pre-feasibility report."""
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
    navy     = colors.HexColor("#13212E")
    green    = colors.HexColor("#15913A")
    gdeep    = colors.HexColor("#0E7A30")
    grey     = colors.HexColor("#475463")
    ltgrey   = colors.HexColor("#8A97A3")
    lime     = colors.HexColor("#8FC71B")
    white    = colors.HexColor("#FFFFFF")
    hero_bg  = colors.HexColor("#0E7A30")
    cta_bg   = colors.HexColor("#0E7A30")
    worth_bg = colors.HexColor("#F3FAF5")
    worth_bd = colors.HexColor("#CDEBD5")
    card_bd  = colors.HexColor("#E7ECF0")

    H2 = ParagraphStyle("H2", parent=styles["Heading2"],
                         textColor=gdeep, fontSize=11, leading=14,
                         spaceBefore=18, spaceAfter=5, fontName="Helvetica-Bold")
    BODY = ParagraphStyle("Body", parent=styles["Normal"],
                           fontSize=9.5, leading=14, spaceAfter=6, textColor=navy)
    SMALL = ParagraphStyle("Small", parent=styles["Normal"],
                            fontSize=8, leading=12, textColor=grey)
    FOOT = ParagraphStyle("Foot", parent=styles["Normal"],
                           fontSize=7.5, leading=11, textColor=ltgrey)
    META = ParagraphStyle("Meta", parent=styles["Normal"],
                           fontSize=8.5, textColor=grey, leading=13)
    LABEL = ParagraphStyle("Label", parent=styles["Normal"],
                            fontSize=8, textColor=colors.HexColor("#CDEBD5"),
                            fontName="Helvetica-Bold", spaceAfter=2)
    HERO_NUM = ParagraphStyle("HeroNum", parent=styles["Normal"],
                               fontSize=22, leading=26, textColor=white,
                               fontName="Helvetica-Bold", spaceAfter=2)
    HERO_SUB = ParagraphStyle("HeroSub", parent=styles["Normal"],
                               fontSize=10, leading=13, textColor=white, spaceAfter=4)
    HERO_CHIP = ParagraphStyle("HeroChip", parent=styles["Normal"],
                                fontSize=7.5, leading=11, textColor=white)
    CTA_H = ParagraphStyle("CtaH", parent=styles["Normal"],
                            fontSize=11, leading=14, textColor=white,
                            fontName="Helvetica-Bold", spaceAfter=4)
    CTA_B = ParagraphStyle("CtaB", parent=styles["Normal"],
                            fontSize=9.5, leading=14, textColor=white, spaceAfter=4)

    def hr():
        return HRFlowable(width="100%", thickness=0.5,
                           color=colors.HexColor("#E7ECF0"),
                           spaceAfter=6, spaceBefore=2)

    def sec_hr():
        return HRFlowable(width="100%", thickness=1.5,
                           color=colors.HexColor("#EDF4EE"),
                           spaceAfter=4, spaceBefore=2)

    story = []

    # ── 1. Header (2-col: left = title+meta, right = logo top-right) ────────
    from reportlab.platypus import Image as RLImage, Table as RLTable, TableStyle as RLTS
    SUB = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=13, textColor=navy,
                         fontName="Helvetica-Bold", spaceBefore=0, spaceAfter=4)
    meta_rows = [
        ("Concession", data.iup_name),
        ("Region", data.iup_address or "—"),
        ("Permit", f"{data.permit_type} · {data.permit_years_remaining} years remaining"),
        ("Prepared for", data.contact_name + (f", {data.contact_company}" if data.contact_company else "")),
        ("Reference", data.filename_base),
        ("Date (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    ]
    left_col = [Paragraph("Carbon Pre-Feasibility Report", SUB)]
    left_col += [Paragraph(f"<b>{k}:</b> {v}", META) for k, v in meta_rows]

    logo_h = 1.6 * cm
    logo_w = logo_h * _LOGO_ASPECT
    if _LOGO_PATH.exists():
        right_col = [RLImage(str(_LOGO_PATH), width=logo_w, height=logo_h)]
    else:
        right_col = [Paragraph("180Climate", ParagraphStyle(
            "Brand", parent=styles["Normal"], fontSize=16, textColor=green,
            fontName="Helvetica-Bold"))]

    hdr_tbl = RLTable([[left_col, right_col]],
                      colWidths=[doc.width - logo_w - 0.4 * cm, logo_w + 0.4 * cm])
    hdr_tbl.setStyle(RLTS([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("ALIGN",       (1, 0), (1, 0),   "RIGHT"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    story.append(hdr_tbl)
    story.append(hr())

    # ── 2. Hero — range + per-year + worth ───────────────────────────────────
    hero_rows_data = []
    has_range = data.quantity_low_tco2e is not None
    if has_range:
        hero_inner = [
            Paragraph("Your forest could generate an estimated", LABEL),
            Paragraph(data.range_str(), HERO_NUM),
            Paragraph(f"over a 30-year project  ·  {data.per_yr_str()}", HERO_SUB),
        ]
    else:
        hero_inner = [
            Paragraph("Your land has a carbon pathway", LABEL),
            Paragraph("Restoration project opportunity", HERO_NUM),
            Paragraph("Peat rewetting / WRC may qualify — see 'What we found'", HERO_SUB),
        ]
    # Hero as green table cell
    from reportlab.platypus import Table as RLTable, TableStyle as RLTS
    hero_tbl = RLTable([[hero_inner]], colWidths=["100%"])
    hero_tbl.setStyle(RLTS([
        ("BACKGROUND",  (0, 0), (-1, -1), hero_bg),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",  (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(hero_tbl)
    story.append(Spacer(1, 6))

    # Worth box
    if has_range and data.worth_str():
        worth_inner = [Paragraph(
            f"<b>What that's worth:</b> {data.worth_str()}", BODY)]
        worth_tbl = RLTable([[worth_inner]], colWidths=["100%"])
        worth_tbl.setStyle(RLTS([
            ("BACKGROUND",  (0, 0), (-1, -1), worth_bg),
            ("BOX",         (0, 0), (-1, -1), 0.75, worth_bd),
            ("ROUNDEDCORNERS", [6]),
            ("TOPPADDING",  (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(worth_tbl)
        story.append(Spacer(1, 4))

    # ── 3. Why your forest qualifies ─────────────────────────────────────────
    story.append(sec_hr())
    story.append(Paragraph("Why Your Forest Qualifies", H2))
    story.append(Paragraph(data.why_qualifies(), BODY))

    # ── 4. How strong is your project (quality as strengths) ─────────────────
    if data.quality_cards():
        story.append(sec_hr())
        story.append(Paragraph("How Strong Is Your Project", H2))
        cards = data.quality_cards()
        # 2-column card grid
        col_w = (doc.width / 2) - 4
        for i in range(0, len(cards), 2):
            pair = cards[i:i+2]
            row_cells = []
            for label, value in pair:
                inner = [
                    Paragraph(label.upper(), ParagraphStyle(
                        "CardH", parent=styles["Normal"],
                        fontSize=7, fontName="Helvetica-Bold",
                        textColor=gdeep, spaceBefore=0, spaceAfter=2)),
                    Paragraph(value, ParagraphStyle(
                        "CardV", parent=styles["Normal"],
                        fontSize=8.5, textColor=navy, leading=12)),
                ]
                row_cells.append(inner)
            # Pad to 2 if odd number
            while len(row_cells) < 2:
                row_cells.append([Paragraph("", BODY)])
            card_tbl = RLTable([row_cells], colWidths=[col_w, col_w])
            card_tbl.setStyle(RLTS([
                ("BOX",         (0, 0), (0, 0), 0.5, card_bd),
                ("BOX",         (1, 0), (1, 0), 0.5, card_bd),
                ("ROUNDEDCORNERS", [6]),
                ("TOPPADDING",  (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(card_tbl)
            story.append(Spacer(1, 6))

    # ── 5. How your number is built ───────────────────────────────────────────
    if data.derivation is not None:
        story.append(sec_hr())
        story.append(Paragraph("How Your Number Is Built", H2))
        drv_rows = _derivation_rows(data.derivation)
        if drv_rows:
            tbl_data = [[Paragraph(k, ParagraphStyle("TK", parent=BODY, spaceAfter=0)),
                         Paragraph(v, ParagraphStyle("TV", parent=BODY, spaceAfter=0,
                                                     fontName="Helvetica-Bold"))]
                        for k, v in drv_rows]
            # Last row bold green (total)
            tbl_data[-1] = [
                Paragraph(drv_rows[-1][0], ParagraphStyle(
                    "TKLast", parent=BODY, spaceAfter=0, fontName="Helvetica-Bold",
                    textColor=gdeep)),
                Paragraph(drv_rows[-1][1], ParagraphStyle(
                    "TVLast", parent=BODY, spaceAfter=0, fontName="Helvetica-Bold",
                    textColor=gdeep)),
            ]
            t = RLTable(tbl_data, colWidths=[doc.width * 0.55, doc.width * 0.45])
            t.setStyle(RLTS([
                ("INNERGRID",   (0, 0), (-1, -1), 0.3, colors.HexColor("#F1F4F7")),
                ("LINEABOVE",   (0, -1), (-1, -1), 1.5, colors.HexColor("#E3EAF0")),
                ("TOPPADDING",  (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
            ]))
            story.append(t)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "Grounded in satellite forest-loss data (Hansen/GFW), ESA CCI biomass and "
            "IPCC factors. It's a range because it's a free screening — "
            "<b>a field study narrows it into a bankable number. That's the upgrade.</b>",
            SMALL))
    elif data.baseline_class == "peat":
        story.append(sec_hr())
        story.append(Paragraph("How Your Number Is Built", H2))
        story.append(Paragraph(
            "No avoided-deforestation tonnage is shown for this concession — "
            "no settled Verra method exists for peat carbon credits as of 2026. "
            "Peat parcels route to a qualitative flag under 180Climate's methodology (ADR-0013). "
            "The restoration pathway may produce carbon revenue; that determination "
            "requires a site visit and hydrology survey.",
            BODY))

    # ── 6. What we found on your land ────────────────────────────────────────
    found_items = _what_we_found(data)
    if found_items:
        story.append(sec_hr())
        story.append(Paragraph("What We Found on Your Land", H2))
        for item in found_items:
            story.append(Paragraph(f"• {item}", BODY))

    # Forest data summary (fine detail — stays as bullet lines, no disclaimer)
    if data.forest_annual_loss_ha:
        story.append(Spacer(1, 4))
        _yrs = sorted(data.forest_annual_loss_ha.keys())
        _tot = sum(data.forest_annual_loss_ha.values())
        _avg = _tot / len(_yrs) if _yrs else 0
        story.append(Paragraph(
            f"<b>Annual loss (all years avg):</b> {_avg:,.0f} ha/yr "
            f"({_yrs[0]}–{_yrs[-1]})", SMALL))
        _win = [y for y in _yrs if 2016 <= y <= 2022]
        if _win:
            _wa = sum(data.forest_annual_loss_ha[y] for y in _win) / len(_win)
            story.append(Paragraph(
                f"<b>Loss rate (2016–2022 avg, used in estimate):</b> "
                f"{_wa:,.0f} ha/yr", SMALL))

    # Data sources credit (always shown if data_sources present)
    if data.data_sources:
        story.append(Paragraph(
            "<b>Data sources:</b> " + " · ".join(data.data_sources), SMALL))

    # ── 7. How to grow this number ────────────────────────────────────────────
    story.append(sec_hr())
    story.append(Paragraph("How to Grow This Number", H2))
    story.append(Paragraph(_GROW_TEXT, BODY))

    # ── 8. CTA ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    cta_inner = []
    for line in _CTA_BODY.split("\n"):
        if line.strip():
            style = CTA_H if line.startswith("Your next step") else CTA_B
            cta_inner.append(Paragraph(line, style))
        else:
            cta_inner.append(Spacer(1, 4))
    cta_tbl = RLTable([[cta_inner]], colWidths=["100%"])
    cta_tbl.setStyle(RLTS([
        ("BACKGROUND",  (0, 0), (-1, -1), cta_bg),
        ("ROUNDEDCORNERS", [10]),
        ("TOPPADDING",  (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(cta_tbl)

    # ── 9. Footer — ONE line only ─────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(hr())
    story.append(Paragraph(
        f"{_FOOTER_LINE}  Report ref: {data.filename_base}.", FOOT))

    doc.build(story)
    return buf.getvalue()


# ── DOCX ──────────────────────────────────────────────────────────────────────

def generate_docx(data: ReportData) -> bytes:
    """Return DOCX bytes for the value-first pre-feasibility report."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.0)
        section.right_margin  = Inches(1.0)

    # Colour palette
    _GREEN = (21, 145, 58)
    _GDEEP = (14, 122, 48)
    _NAVY  = (19, 33, 46)
    _GREY  = (71, 84, 99)
    _LGREY = (138, 151, 163)

    def _h1(text: str, colour: tuple = _NAVY) -> None:
        p = doc.add_heading(text, level=1)
        run = p.runs[0] if p.runs else p.add_run(text)
        run.font.color.rgb = RGBColor(*colour)

    def _h2(text: str) -> None:
        p = doc.add_heading(text, level=2)
        for run in p.runs:
            run.font.color.rgb = RGBColor(*_GDEEP)

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

    # ── 1. Header ─────────────────────────────────────────────────────────────
    if _LOGO_PATH.exists():
        from docx.shared import Inches as _Inches
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run()
        run.add_picture(str(_LOGO_PATH), height=_Inches(0.55))
    else:
        _h1("180Climate", colour=_GREEN)
    _h1("Carbon Pre-Feasibility Report", colour=_NAVY)
    for key, val in [
        ("Concession", data.iup_name),
        ("Region", data.iup_address or "—"),
        ("Permit", f"{data.permit_type} · {data.permit_years_remaining} years remaining"),
        ("Prepared for", data.contact_name + (f", {data.contact_company}" if data.contact_company else "")),
        ("Reference", data.filename_base),
        ("Date (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    ]:
        _kv(key, val)
    _hr()

    # ── 2. Hero ───────────────────────────────────────────────────────────────
    has_range = data.quantity_low_tco2e is not None
    if has_range:
        _body("Your forest could generate an estimated", colour=_GDEEP, size=9, bold=True)
        p = doc.add_paragraph()
        run = p.add_run(data.range_str())
        run.font.size = Pt(20)
        run.bold = True
        run.font.color.rgb = RGBColor(*_GREEN)
        _body(f"over a 30-year project  ·  {data.per_yr_str()}",
              italic=True, colour=_GREY, size=10)
        if data.worth_str():
            _body(f"What that's worth: {data.worth_str()}", colour=_GDEEP, size=9)
    else:
        _body("Your land has a carbon pathway", colour=_GDEEP, size=9, bold=True)
        _body("Peat rewetting / restoration project may qualify", bold=True,
              colour=_GREEN, size=14)
    _hr()

    # ── 3. Why your forest qualifies ─────────────────────────────────────────
    _h2("Why Your Forest Qualifies")
    _body(data.why_qualifies())
    _hr()

    # ── 4. Strengths ─────────────────────────────────────────────────────────
    if data.quality_cards():
        _h2("How Strong Is Your Project")
        for label, value in data.quality_cards():
            _kv(label, value)
        _hr()

    # ── 5. How built ─────────────────────────────────────────────────────────
    _h2("How Your Number Is Built")
    if data.derivation is not None:
        drv_rows = _derivation_rows(data.derivation)
        for k, v in drv_rows:
            _kv(k, v)
        _body(
            "Grounded in satellite forest-loss data (Hansen/GFW), ESA CCI biomass and "
            "IPCC factors. It's a range because it's a free screening — "
            "a field study narrows it into a bankable number. That's the upgrade.",
            colour=_GREY, size=9,
        )
    elif data.baseline_class == "peat":
        _body(
            "No avoided-deforestation tonnage shown — "
            "no settled Verra method exists for peat carbon credits as of 2026. "
            "Peat parcels route to a qualitative flag under 180Climate's methodology (ADR-0013). "
            "The restoration pathway may produce carbon revenue; that determination "
            "requires a site visit and hydrology survey.",
            colour=_GREY, size=9,
        )
    else:
        _body("Derivation detail not available for this estimate variant.",
              italic=True, colour=_LGREY, size=9)
    _hr()

    # ── 6. What we found ─────────────────────────────────────────────────────
    found_items = _what_we_found(data)
    if found_items:
        _h2("What We Found on Your Land")
        for item in found_items:
            _body(f"• {item}")
        if data.forest_annual_loss_ha:
            _yrs = sorted(data.forest_annual_loss_ha.keys())
            _tot = sum(data.forest_annual_loss_ha.values())
            _avg = _tot / len(_yrs) if _yrs else 0
            _kv("Annual loss (all years avg)",
                f"{_avg:,.0f} ha/yr ({_yrs[0]}–{_yrs[-1]})")
            _win = [y for y in _yrs if 2016 <= y <= 2022]
            if _win:
                _wa = sum(data.forest_annual_loss_ha[y] for y in _win) / len(_win)
                _kv("Loss rate (2016–2022 avg, used in estimate)", f"{_wa:,.0f} ha/yr")
        _hr()

    # Data sources credit
    if data.data_sources:
        _body("Data sources: " + " · ".join(data.data_sources), colour=_LGREY, size=8)
    _hr()

    # ── 7. How to grow ────────────────────────────────────────────────────────
    _h2("How to Grow This Number")
    _body(_GROW_TEXT)
    _hr()

    # ── 8. CTA ────────────────────────────────────────────────────────────────
    _h2("Engage 180Climate — Your Next Step")
    for line in _CTA_BODY.split("\n"):
        _body(line) if line.strip() else doc.add_paragraph()
    _hr()

    # ── 9. Footer — ONE line ──────────────────────────────────────────────────
    _body(f"{_FOOTER_LINE}  Report ref: {data.filename_base}.",
          italic=True, colour=_LGREY, size=8)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
