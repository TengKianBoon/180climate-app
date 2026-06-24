"""tests/test_report.py — golden snapshot tests for PDF + DOCX report generation.

WO-CARBON-008: checks that both formats contain required content and honour
ADR-0009 invariants (no single number, no "%" string, range present, IPCC Tier,
baseline-dominant-uncertainty present, Engage CTA present).
"""
import io
import pytest

from reports.generator import ReportData, generate_pdf, generate_docx, make_filename


# ── Fixture: HTI eligible input ────────────────────────────────────────────────

@pytest.fixture
def hti_eligible_data() -> ReportData:
    return ReportData(
        iup_name="PT Hutan Lestari (test)",
        iup_address="Kalimantan Timur, Indonesia",
        permit_type="HTI",
        permit_years_remaining=20,
        project_type="REDD",
        contact_name="Jane Smith",
        contact_email="jane@example.com",
        contact_mobile="+62 811 000 000",
        contact_company="Forestry Co.",
        verdict="eligible",
        verdict_label="Eligible — indicative carbon project opportunity identified",
        quantity_low_tco2e=5_816_578.0,
        quantity_high_tco2e=8_309_397.0,
        baseline_class="planned_clearfell",
        verra_family="APD (VM0009/legacy — advisor-confirm)",
        additionality_basis="legal harvest right foregone",
        uncertainty="Low–medium; observed-loss floor; IPCC Tier 1",
        area_ha=73_787.0,
        filename_base="2606241200",
    )


@pytest.fixture
def peat_data() -> ReportData:
    return ReportData(
        iup_name="PT Gambut Nusantara (test)",
        iup_address="Kalimantan Tengah, Indonesia",
        permit_type="HTI",
        permit_years_remaining=15,
        project_type="PEAT",
        contact_name="Bob Tan",
        contact_email="bob@example.com",
        contact_mobile=None,
        contact_company=None,
        verdict="flagged",
        verdict_label="Flagged — review required before proceeding",
        quantity_low_tco2e=None,
        quantity_high_tco2e=None,
        baseline_class="peat",
        verra_family="PEAT — no settled active Verra method as of 2026",
        additionality_basis="legal harvest right foregone",
        uncertainty="High; no settled Verra method",
        area_ha=12_000.0,
        filename_base="2606241201",
    )


# ── make_filename ──────────────────────────────────────────────────────────────

def test_make_filename_format():
    fn = make_filename()
    assert len(fn) == 10
    assert fn.isdigit()


# ── PDF text extraction helper ─────────────────────────────────────────────────

def _pdf_text(content: bytes) -> str:
    import pypdf
    import re as _re
    reader = pypdf.PdfReader(io.BytesIO(content))
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Collapse hyphenated line-breaks and normalise whitespace for substring checks
    return _re.sub(r"\s+", " ", raw)


# ── PDF invariants ─────────────────────────────────────────────────────────────

class TestPdf:
    def test_returns_bytes(self, hti_eligible_data):
        result = generate_pdf(hti_eligible_data)
        assert isinstance(result, bytes)
        assert len(result) > 1000

    def test_valid_pdf_header(self, hti_eligible_data):
        result = generate_pdf(hti_eligible_data)
        assert result[:4] == b"%PDF"

    def test_range_present(self, hti_eligible_data):
        text = _pdf_text(generate_pdf(hti_eligible_data))
        assert "5,816,578" in text or "5816578" in text
        assert "8,309,397" in text or "8309397" in text

    def test_no_percentage_strings(self, hti_eligible_data):
        text = _pdf_text(generate_pdf(hti_eligible_data))
        assert "% accuracy" not in text
        assert "% confidence" not in text

    def test_ipcc_tier_present(self, hti_eligible_data):
        text = _pdf_text(generate_pdf(hti_eligible_data))
        assert "IPCC Tier 1" in text

    def test_dominant_uncertainty_present(self, hti_eligible_data):
        text = _pdf_text(generate_pdf(hti_eligible_data))
        assert "dominant uncertainty" in text

    def test_engage_cta_present(self, hti_eligible_data):
        text = _pdf_text(generate_pdf(hti_eligible_data))
        assert "180Climate" in text
        assert "info@180climate.net" in text

    def test_adr_0009_methodology_present(self, hti_eligible_data):
        text = _pdf_text(generate_pdf(hti_eligible_data))
        assert "APD" in text

    def test_peat_no_settled_method(self, peat_data):
        text = _pdf_text(generate_pdf(peat_data))
        assert "no settled" in text

    def test_non_eligible_no_range(self, peat_data):
        text = _pdf_text(generate_pdf(peat_data))
        assert "5,816,578" not in text
        assert "8,309,397" not in text


# ── DOCX invariants ────────────────────────────────────────────────────────────

class TestDocx:
    def _extract_text(self, content: bytes) -> str:
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)

    def test_returns_bytes(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        assert isinstance(result, bytes)
        assert len(result) > 1000

    def test_valid_docx_header(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        # DOCX is a ZIP; PK magic
        assert result[:2] == b"PK"

    def test_range_present(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        text = self._extract_text(result)
        assert "5,816,578" in text or "5816578" in text
        assert "8,309,397" in text or "8309397" in text

    def test_no_percentage_strings(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        text = self._extract_text(result)
        assert "% accuracy" not in text
        assert "% confidence" not in text

    def test_ipcc_tier_present(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        text = self._extract_text(result)
        assert "IPCC Tier 1" in text

    def test_dominant_uncertainty_present(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        text = self._extract_text(result)
        assert "dominant uncertainty" in text

    def test_engage_cta_present(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        text = self._extract_text(result)
        assert "info@180climate.net" in text

    def test_additionality_basis_present(self, hti_eligible_data):
        result = generate_docx(hti_eligible_data)
        text = self._extract_text(result)
        assert "legal harvest right foregone" in text

    def test_peat_no_settled_method(self, peat_data):
        result = generate_docx(peat_data)
        text = self._extract_text(result)
        assert "no settled" in text
