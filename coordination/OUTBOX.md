# OUTBOX — Builder → Cowork · WO-REPORT-001 · 2026-06-26

## Status: CI GREEN ✅ — STOPPED for Cowork + advisor wording review

---

## What was delivered

Content/wording improvements per `docs/report-improvement-spec.md`. No engine/number/contract change.

### Fix "accredited methodology" trust risk (spec §1)
- `narrative/narrator.py` `_DISCLAIMER` + `_ENGAGE_CTA`: reframed; no "accredited methodology" without context
- `narrative/narrator.py` line ~180: "accredited methodology selection" → "full (registry-grade) methodology application"
- `reports/generator.py` `_DISCLAIMER` + `_ENGAGE_CTA`: same reframe
- `api/main.py` `_CARROT`: new copy (spec §2); `_DISCLAIMER_TEXT`: expanded no-% version (spec §3)

### New "Engage 180Climate" CTA copy (spec §2)
"This free screening already routes your concession to the appropriate **accredited Verra methodology**, at an indicative **IPCC Tier 1** level — a first read that a paid pre-feasibility study (~SGD 12K) would otherwise begin. To take it to a **bankable, registry-grade** carbon project — talk to 180Climate at **info@180climate.net**."

### Clearer disclaimer — NO % (spec §3, ADR-0009 preserved)
Disclaimer now explains: range-not-point-estimate, IPCC Tier, and the dominant uncertainties that make a % indefensible. No numeric confidence/accuracy % anywhere.

### Comprehensive PDF + DOCX (spec §4)
New sections added to both formats, mirroring the results page:
- **Quality Factors** — additionality, permanence, leakage, methodology fit (from `QualityFactors`)
- **Forest Data Summary** — baseline canopy cover, annual-loss trend, loss after 2020, peat presence/proxy, biomass density
- **Assessment Narrative** — full generated narrative text (same as on screen)
- **Data Sources** — GFW/Hansen, ESA CCI, KHG, PIPPIB, etc.

`ReportData` extended with new optional fields (all backward-compatible defaults).  
`/api/report` and `/api/lead` now generate the narrative before building report data.

---

## Verification

| Check | Result |
|---|---|
| `pytest tests/` | ✅ **259 passed** (was 246; 13 new assertions) |
| Quality Factors in PDF | ✅ present |
| Forest Data Summary in PDF | ✅ present (canopy cover 82.5%, biomass 266.5 tCO2/ha) |
| Assessment Narrative in PDF | ✅ present |
| Data Sources in PDF | ✅ present (Hansen visible) |
| "registry-grade" in PDF | ✅ present |
| "accredited Verra methodology" in PDF | ✅ present |
| "accredited methodology selection" in PDF | ✅ absent (trust-risk phrase removed) |
| No "% confidence" / "% accuracy" | ✅ confirmed |
| No engine/number/contract change | ✅ confirmed |

---

## Cowork + advisor review checklist
1. Re-render a sample PDF + DOCX (run a screening → Download PDF / DOCX)
2. Confirm: Quality Factors section present with additionality/permanence/leakage/methodology-fit
3. Confirm: Forest Data Summary present with canopy cover, loss rate, biomass density
4. Confirm: Assessment Narrative section present (same text as on-screen)
5. Confirm: Data Sources section present
6. Confirm: Engage CTA uses "would otherwise begin" (not "replaces"); ~SGD 12K present
7. Confirm: No % confidence anywhere in PDF/DOCX
8. **Advisor wording pressure-test** — final copy review before go-live
9. If pass → deploy-time items → Gate L
