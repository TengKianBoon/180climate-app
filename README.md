# 180Climate App

**A defensible carbon + EUDR pre-feasibility platform built with enterprise-grade multi-agent AI orchestration.**

Two diagnostic engines on one shared geospatial core — designed as a professional lead-generation and data-collection funnel for 180Climate's consulting business.

---

## What it does

### Carbon Pre-Feasibility Engine
A concession holder enters contact details and a concession location (coordinates or shapefile) and receives a free, ~80% screening pre-feasibility read: carbon-credit **quantity range + quality band**, a deforestation/condition verdict, a forest-loss map overlay, and a defensible AI rationale. Replaces a ~SGD 12K paid pre-feasibility study with a free screening tool.

### EUDR Export Readiness Engine
An Indonesian commodity exporter enters plot(s) + commodity and receives a **deforestation-free verdict vs the 31 Dec 2020 cutoff** (JRC GFC2020), an Indonesia risk-tier read, a legality gap checklist, and a **DDS-ready GeoJSON pack** aligned to EU TRACES + a readiness score (0–100).

The **non-negotiable spine:** the runtime is a deterministic calculator — AI only writes the explanation. Numbers and verdicts are reproducible, testable, and cheap to run.

---

## Architecture

```
docs/         methodology.md · ADRs (0001–0011) · spec · application-plan · orchestration-v2
core/         shared geospatial core · core/contracts/ (the typed constitution)
engines/      carbon/  (eligibility · methodology routing · estimate range + quality)
              eudr/    (cutoff verdict · risk tier · legality checklist · DDS pack)
narrative/    AI rationale — the ONLY place an LLM is called
frontend/     map UI + funnel form (React + MapLibre/Leaflet)
api/          FastAPI routes
tests/        golden-case fixtures + unit tests
coordination/ agent mailbox + board (board.html — open with a double-click)
```

**Stack:** Python 3.13 · FastAPI · Pydantic v2 · geopandas / rasterio / shapely · React + MapLibre/Leaflet · Claude (narrative only)

**Module-boundary rule:** `core/contracts/` is the typed constitution — all engines and the API consume it; a shared-type change requires an ADR + Gate C (enforced by the contract-guard hook).

---

## Multi-agent orchestration (the build method)

This project is built using a **multi-agent AI development pipeline** as a deliberate engineering practice — not a prototype pattern, but the production build method:

| Agent | Role |
|---|---|
| **Builder** (VS Code Claude Code) | Writes, runs, tests, and commits code; inner Writer → Reviewer → Verifier → Test-writer loop per Work Order |
| **Reviewer** | White-box review of every diff against the typed contracts + invariants; never edits |
| **Verifier** | Black-box execution of acceptance criteria; screenshots UI; MUST NOT edit files |
| **Test-writer** | Golden-case fixtures + determinism assertions committed to the repo |

**Quality control layers:**
1. Automated: lint · type-check · golden cases · contract-guard hook · secret-scan hook
2. Agentic: Reviewer (diff vs contracts) + Verifier (product vs spec)
3. Self-improving: Chain-of-Verification (CoV) loop on the number-path work orders (1 rewrite budget)
4. Human gates: Gate 0 (scaffold) · Gate 1 (slice) · Gate M (numbers + methodology) · Gate C (contract change) · Gate P (lead flow) · Gate E (EUDR verdict) · Gate L (go-live)

**Dreaming / memory consolidation:** at each gate boundary, the orchestrator distills episodic lessons from `coordination/journal.md` into `memory/` — the system learns and stops repeating itself.

**Coordination:** `coordination/board.html` (self-contained, double-click) is regenerated after every step and shows phase, active Work Order, status, last commit, open questions, and gate readiness.

---

## Reproducible free-tier setup

```bash
git clone https://github.com/TengKianBoon/180climate-app
cd 180climate-app
pip install pydantic mypy pytest
mypy core/contracts/__init__.py --ignore-missing-imports
pytest tests/ -v
```

**Data sources (free tier, swappable behind a single interface):**
- Forest loss: GFW/Hansen annual loss tiles
- EUDR baseline: JRC Global Forest Cover 2020
- Biomass proxy: ESA CCI Biomass / JAXA
- Land cover: ESA WorldCover
- Peat maps: CIFOR/Wetlands International
- DEM: SRTM

> ⚠️ **GEE (Google Earth Engine) non-commercial caveat (ADR-0007):** GEE APIs are non-commercial only. This project uses free, self-hostable COG sources for production deployments. A commercial GEE licence is required if GEE is used in a paid engagement.

---

## Methodology defensibility

The carbon engine is **methodology-agnostic** — it computes a transparent avoided-emissions range. The AI narrative cites the correct Verra family by permit type:

| Permit type | Verra family cited |
|---|---|
| HTI (planned clear-fell foregone) | APD route (VM0009/legacy — advisor-confirm) |
| HA (planned selective-logging foregone) | IFM (VM0010 / VM0045 v1.2) |
| Peat (avoided drainage/subsidence) | VM0027 (interim) — advisor-confirm |

**Critical rule:** HTI/HA foregone-legal-harvest is a **planned** baseline — never the unplanned VM0048 family. VM0007 is deprecated and never cited. Additionality is always stated as: *"legal harvest right foregone."* (ADR-0001)

---

## Uncertainty communication

Carbon outputs always carry:
- A **range** (low–high tCO₂e) — never a single false-precise number
- An **uncertainty band** string
- An **IPCC Tier label** (free satellite = Tier 1 screening; hi-res/LiDAR = toward Tier 2; field + accredited + verification = Tier 3)
- A plain-language note that **the baseline/counterfactual — not satellite resolution — is the dominant uncertainty**

(ADR-0009)

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
