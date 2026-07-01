# 180Climate — Planning Batch 01
### The Brain's first hand-off to the Hands (Phase 0 → Phase 1)

**From:** Claude (Strategic Brain, Opus 4.8) · **To:** the Hands (Cowork orchestrator + Claude Code in VS Code) · **Date:** 21 Jun 2026
**Companions:** `180climate-MASTER-handover-spec.md` (the *what*), `180climate-build-and-orchestration-plan.md` (the *how*).

> **What this batch is.** Three things the Hands need before writing any feature code: **(1)** the methodology decision record (ADR‑0001) + the rest of the locked decisions, **(2)** the **typed contracts** — the "constitution" that lets parallel work proceed without colliding — and **(3)** the first two **Work Orders** (scaffold, then the vertical-slice spine).
>
> **How to use it.** Hand **WO‑000** to the Hands first. When it's green, John approves **Gate 0** (scaffold + contracts + ADR‑0001 correct). Then hand **WO‑001**. When the slice is green end-to-end, John approves **Gate 1**, and only then does Phase 2 (the carbon engine, parallel worktrees) begin. The Brain designs and reviews; the Hands write the code.

---

## Part 1 — Decision records (ADRs)

### ADR-0001 — Carbon methodology stance
**Status:** Accepted · 21 Jun 2026 · **Deciders:** John (owner), Claude (architect)

**Context.** The Verra landscape is shifting. The unplanned-deforestation family (AUD) moved to **VM0048 v1.0 + VMD0055 v1.1 + VT0007**, with **jurisdictionally-set, third-party baselines**. Planned, foregone-legal-harvest baselines fit **APD** (for HTI clear-fell foregone) and **IFM (VM0010 / VM0045)** (for HA selective-logging foregone). **VM0007 and several legacy methods are deprecated / excluded from the ICVCM Core Carbon Principles** and must not anchor the product. A standalone tropical-peatland method is still in development. The tool will be scrutinised by rival developers and skeptical funders, so it must be **defensible, must not date itself to a sunsetting method, and must route correctly by permit type.**

**Decision.**
1. The **engine is methodology-agnostic**: it computes a **transparent avoided-emissions range** (deterministic), not a single false-precise number, and not hard-coded to any one method.
2. The **AI narrative cites the correct Verra family by permit type**, using the routing rule below.
3. The **foregone-legal-harvest baseline is PLANNED → APD / IFM — never the unplanned VM0048 / VMD0055 family.**
4. The app **never brands to VM0007** or any deprecated method.
5. The narrative **always states the additionality basis explicitly: "legal harvest right foregone."**
6. The exact Verra route is **confirmed with a methodology advisor for the commercial deal**; the app provides the indicative, non-binding read only.

**Routing rule (normative).**

| Permit / project type | Baseline class | Verra family cited in narrative |
|---|---|---|
| **HTI** (industrial timber plantation; legal right to clear-fell) | Planned clear-fell foregone | **APD route** (VM0009 / legacy — advisor-confirm) |
| **HA** (natural-forest logging; legal right to selectively log) | Planned selective-logging foregone | **IFM** (VM0010 / VM0045 v1.2) |
| **Peat** | Avoided drainage/subsidence | **VM0027 (interim)** — advisor-confirm; standalone peat method pending |
| (reference only) Unplanned / illegal loss (AUD) | — | VM0048 + VMD0055 + VT0007 — **NOT used for foregone-harvest baselines** |

**Consequences.** + Defensible, swappable, won't date; + correct routing by permit. − Requires the routing rule encoded in the `methodology` skill and covered by golden cases; the narrative layer must enforce the additionality wording. **Gate M:** John signs off on routing + numbers + disclaimers before any public release. Source of truth: `docs/methodology.md` + this ADR.

### ADR log — 0002 → 0008 (locked decisions)

| ADR | Decision | Status |
|---|---|---|
| **0002 — Hosting / platform** | Site is **Wix**, which can't host a custom app → build a **standalone app on a subdomain** (`app.180climate.net`), **linked from the Wix nav** + optional iframe embed. John adds the DNS/subdomain in Wix. | Accepted |
| **0003 — Funnel gating** | **Light capture up front** (name + email to see the headline verdict + map); **detailed report + financial-model carrot gated** behind the full lead form. | Accepted |
| **0004 — Lead store** | **Email to `info@180climate.net`** (primary) **+ Google Sheet append** (durable backup). App runtime uses its own credentials, not Claude's connectors. | Accepted |
| **0005 — Build order / public scope** | **Carbon vertical first → ship → EUDR fast-follow** reusing the shared core. Carbon-only is a valid public v1 if the window tightens. | Accepted |
| **0006 — Peat methodology** | **Agnostic + advisor-confirm** — peat presented as a transparent range, **never branded to VM0027**; advisor confirms for the commercial deal. | Accepted |
| **0007 — Data sources & licensing** | Free-tier sources **behind a swappable interface**; **GEE is non-commercial only** → flag in README + this ADR; ship MVP on free APIs / self-hosted COGs where possible; reserve paid hi-res for flagged plots only. | Accepted |
| **0008 — Execution surfaces & models** | **Brain** = Opus 4.8 (this Project + Claude Code **plan mode**). **Hands** = **Claude Code in VS Code**, default **Sonnet 4.6**, `/model opus` for the number path + reviews, or `opusplan`. **Cowork** = orchestrator window (Sonnet 4.6). **Runtime is deterministic** (no model in the number path). | Accepted |
| **0009 — Uncertainty &amp; confidence communication** | The engine **always outputs a range (low/high) + an uncertainty band**, **never a single value and never a "% accuracy."** The narrative uses **IPCC Tier language** (free = Tier 1 screening; hi-res/LiDAR = toward Tier 2; field + accredited methodology + verification = Tier 3 / registry-grade) and states that the **baseline — not the satellite — is the dominant uncertainty**. Full rationale: `docs/carbon-confidence-report.pdf`; rules: `docs/uncertainty.md`. **Gate M** verifies compliance. | Accepted |
| **0010 — Report generation &amp; lead delivery** | Each user's carbon pre-feasibility report is generated in **both PDF (user download) and DOCX**. Filenames = a creation **timestamp `YYMMDDHHMM`** (same base for the PDF and DOCX, using the earlier of the two). **On download**, the app emails **info@180climate.net** with the **DOCX attached + the user's full lead-form details**, subject = **"{concession name} — {filename}"**, and appends the lead to the **Google Sheet** (ADR-0004). The report **ends with the 180Climate engagement call-to-action** (value-adds). **Single inbox: `info@180climate.net`** for record and download notification. | Accepted |

---

### Report generation &amp; lead-delivery spec (extends WO for lead capture; the coding agent implements this)

```
ON detailed-report request (after the full lead form is submitted):
1. Render the per-user report from the EngineResult in TWO formats: PDF (served to the user for
   download) and DOCX (for the internal email). Same content, same CTA section.
2. Filename base = creation timestamp in YYMMDDHHMM (year, month, day, hour, minute), e.g.
   "2606231423"; PDF = <base>.pdf, DOCX = <base>.docx. Use the EARLIER of the two creation times
   as the shared base so both files share one name.
3. The report content MUST end with the "Engage 180Climate" section (full feasibility study, field
   validation, methodology/baseline advisory, hi-res/LiDAR, EUDR compliance, project development /
   verification / market access) + contact: info@180climate.net, www.180climate.net.
4. The report MUST carry the uncertainty rules from ADR-0009 (range + band + screening qualifier +
   IPCC Tier label + "baseline is the dominant uncertainty"; never a single number or "% accuracy").
5. ON the user clicking download, send an email to info@180climate.net:
     - Subject: "{concession_name} — {filename}"
     - Attachment: the DOCX (<base>.docx)
     - Body: the full lead-capture form (name, email, mobile, company, concession name, permit type,
       project type, area, geometry summary) + timestamp.
6. ALSO append the lead to the Google Sheet (ADR-0004). All email goes to the single inbox
   info@180climate.net.
SECRETS: email + Sheets credentials live in host environment config, never in the repo.
HITL: Gate P (PII / lead flow) verifies the email + attachment + form capture end-to-end before go-live.
```

---

### Uncertainty &amp; confidence spec (`docs/uncertainty.md`) — the coding agent must implement this

```
RULES (enforced by tests + Gate M):
1. CarbonEstimate MUST expose quantity_low_tco2e and quantity_high_tco2e (a RANGE), plus an
   `uncertainty` band string. The UI MUST render the range + band + a screening-grade qualifier.
2. NEVER render or return a single point carbon figure as "the" answer, and NEVER a "% accurate"
   or "% confident" number anywhere in output, narrative, or report.
3. The narrative MUST classify the estimate by IPCC Tier:
     - free/open satellite data  -> "Tier 1 — indicative screening estimate"
     - higher-res / LiDAR         -> "toward Tier 2 — improved pre-feasibility"
     - field + accredited method + independent verification -> "Tier 3 — registry-grade"
4. The narrative MUST state, in plain language, that the BASELINE/counterfactual (not satellite
   resolution) is the dominant uncertainty, and that field validation + accredited methodology +
   third-party verification are required before any creditable/financial claim.
5. Every carbon output MUST carry the screening disclaimer: indicative only, not registry-grade,
   not financial advice, confirm with a full feasibility study.
6. The data-source label (e.g. "GFW/Hansen + ESA CCI Biomass, free tier") MUST be shown so the
   confidence tier is traceable to the inputs.
GATE M CHECK: golden cases assert (1)-(4); a lint/test fails the build if a single bare carbon
number or any "%accuracy/%confidence" string appears in engine or narrative output.
```

---

## Part 2 — The typed contracts (the "constitution")

These are the interface definitions for `core/contracts/`. **The Hands implement the behaviour behind these; they do not change a shared type without an ADR + Gate C** (the contract-guard hook enforces this). Expressed as Python / Pydantic for the chosen stack; semantics are the binding part.

```python
# core/contracts/__init__.py — the shared constitution. Change ONLY via ADR + Gate C.
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel

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
    project_type: Literal["REDD", "PEAT"]
    geo: GeoInput

class GateResult(BaseModel):
    status: Literal["pass", "flag", "fail"]
    detail: str

class EligibilityResult(BaseModel):
    gates: dict[str, GateResult]              # keys: permit_type, permit_years, area, inside_iup
    verdict: Literal["eligible", "flagged", "hard_no"]
    reasons: list[str]

class MethodologyRoute(BaseModel):
    baseline_class: Literal["planned_clearfell", "planned_selective", "peat"]
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

class CarbonEstimate(BaseModel):
    eligibility: EligibilityResult
    methodology: MethodologyRoute
    forest: ForestData
    quantity_low_tco2e: float
    quantity_high_tco2e: float                # a RANGE, never a single false-precise number
    uncertainty: str
    quality: QualityFactors

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
```

**Determinism invariant (applies to every engine):** the number/verdict path is computed by these models and pure functions; the only place a model (LLM) is called is `NarrativeResult`. The contract-guard hook + golden cases enforce this.

---

## Part 3 — Phase 1 Work Orders

### WO-000 · Repo scaffold + contracts + harness + CI
**Phase:** P0→P1   **Model:** haiku-4.5 (scaffold) / sonnet-4.6 (contracts + CI)   **Worktree:** `feat/scaffold`
**Depends on:** none
**Objective:** Stand up the monorepo, the typed contracts, the `.claude/` harness, and a green CI on a placeholder test — the foundation everything else is built behind.

**Repo location (operational — important):** Create the repo in a **plain local folder, NOT inside a cloud-synced folder** (Google Drive / OneDrive / Dropbox) — background sync corrupts `.git` and causes lock/conflict errors mid-build. Prefer a path **without spaces**, e.g. `C:\dev\180climate-app`. Use **GitHub** for backup and versioning, not the synced drive. Reference docs may stay in Drive, but the live repo is local.

**In scope:**
- Repo tree per spec §12: `core/`, `engines/{carbon,eudr}/`, `narrative/`, `frontend/`, `api/`, `tests/`, `docs/`.
- `core/contracts/` exactly as Part 2 above (type-checks clean).
- `docs/`: commit `spec.md`, `plan.md`, `methodology.md` (reflecting ADR‑0001), and `adr/ADR-0001.md` … `adr/ADR-0008.md`.
- `.claude/`: `CLAUDE.md` (constitution, from plan §16.1), `settings.json` (permissions + hooks: secret-scan, dangerous-bash veto, contract-guard, Stop verification gate), `agents/` (`reviewer`, `explorer`, `test-writer`), `skills/` stubs (`methodology`, `geospatial`, `golden-case`, `brand-180climate`, `self-improving-code`).
- `.github/workflows/ci.yml`: run lint + tests on every PR; block merge on red.
- `LICENSE` (Apache-2.0), `README.md` skeleton (with the GEE non-commercial caveat), `.gitignore` (include `.claude/worktrees/`, secrets, `__pycache__`, build artifacts).

**Acceptance criteria (Definition of Done):**
- [ ] Tree matches spec §12; `core/contracts/` imports and type-checks clean (mypy/pydantic).
- [ ] CI runs and is **green** on a placeholder test.
- [ ] **No secrets** anywhere in the repo.
- [ ] README documents a reproducible free-tier setup.
- [ ] First commit made (Conventional Commits); pushed to a **new PRIVATE GitHub repo** (flip to public later for the portfolio); `main` protected.

**Self-improving loop:** EFFORT LOW.   **Retry budget:** 2 → STOP + Failure Report.
**HITL gate:** **Gate 0** — John approves scaffold + contracts + ADR‑0001 before WO‑001 starts.
**Evidence to return:** repo tree, CI green link, contracts type-check output, the `main`-protection confirmation.

### WO-001 · Vertical slice spine (end-to-end, ugly but real)
**Phase:** P1   **Model:** sonnet-4.6 (wiring); `/model opus` for the eligibility-stub design   **Worktree:** `feat/spine`
**Depends on:** WO-000
**Objective:** One sample concession flows end-to-end and renders a verdict + map + AI rationale, and a lead email is sent. Prove the whole pipe connects before anything is widened or parallelised.

**In scope:** `api/` one route; `core/` parse → boundary + area → one GFW forest-loss query; a **placeholder** carbon number; `frontend/` map + verdict + rationale render; lead capture → email to `info@180climate.net`. **Consume the contracts only.**
**Out of scope / do NOT touch:** real biomass/peat logic, methodology routing, the EUDR engine, parallel modules, `core/contracts/*` (consume only).

**Acceptance criteria (spec §15 + §20):**
- [ ] Sample concession parses from **coords AND shapefile/GeoJSON** to a boundary + area; malformed input → a clear error message.
- [ ] GFW forest-loss query returns and renders as a **map overlay**.
- [ ] Placeholder number + the **brief non-binding disclaimer** render in the report layout.
- [ ] Capture form submits → **email received** (test inbox).
- [ ] **One golden case** committed (input → expected output); CI green **end-to-end**.
- [ ] **Deterministic:** same input → same output; **no LLM in the number path** (only the rationale text is model-written).

**Self-improving loop:** EFFORT MED (run CoV; watch for UNHANDLED INPUT on geometry).   **Retry budget:** 2 → STOP.
**HITL gate:** **Gate 1** — slice green end-to-end.
**Evidence to return:** CI run link, a **screenshot of the rendered report**, the **test email**, the golden-case output.

> **What comes after Gate 1 (preview, not in this batch):** Phase 2 opens the carbon engine across parallel worktrees — `WO-CARBON-001` (data integration), `WO-CARBON-002` (golden cases from §15), `WO-CARBON-003` (eligibility gates + methodology routing — **`/model opus`**, the high-stakes one), `WO-CARBON-004` (estimate range + quality), `WO-CARBON-005` (narrative + Verra rationale). Those carry the **Gate M** sign-off where John reviews the numbers, the routing, and the disclaimers. I'll issue that batch once Gate 1 is approved.

---

*End of Planning Batch 01. Hand WO‑000 to the Hands; approve Gate 0; then WO‑001; approve Gate 1.*
