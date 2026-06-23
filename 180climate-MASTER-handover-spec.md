# 180Climate — Master Handover Specification
### Forest Carbon Pre-FS + EUDR Export Readiness Platform

**Owner:** John (180climate) · **Architect of record:** Claude · **Compiled:** 21 Jun 2026
**Source docs consolidated:** `180climate-preFS-scope.md`, `180climate-EUDR-and-combined-build-plan.md`
**Build window:** now → ~5 Jul 2026 (Claude Max higher session limits) · **Runtime:** deterministic engine + AI narrative · **Build method:** multi-agent (Sonnet + Haiku)

---

## 0. How to use this document

This is the single source of truth for two downstream consumers:

- **Claude AI Project (planning):** use Sections 1–11 to produce the project plan, task breakdown, ADRs, and resolve the open decisions in Section 19. Treat Section 19 `[CONFIRM]` items as the first planning gate.
- **Cowork Claude (programming):** use Sections 7–18 to build. Section 15 (Acceptance Criteria) and Section 20 (First Vertical Slice) are your definition of done. Respect the module boundaries in Section 12 so parallel agents do not collide.

If anything here conflicts with an older note, **this document and the repo's `docs/methodology.md` + ADRs win.** Methodology facts were verified against Verra/EU sources in June 2026 (Section 9).

---

## 1. Executive summary

180Climate is building a public web platform with **two domain engines on one shared geospatial core**:

1. **Carbon Pre-FS Engine** — a forest owner/developer enters minimal contact details + a concession location (coordinates or shapefile) and receives a free, ~80%-confidence "gut-feel" pre-feasibility estimate of carbon-credit **quantity and quality**, a deforestation verdict, and a map — replacing a ~SGD 12K paid pre-feasibility study.
2. **EUDR Export Readiness Engine** — an Indonesian commodity exporter enters plot(s) and commodity and receives a deforestation-free verdict against the **31 Dec 2020** cutoff, an Indonesia risk-tier read, a legality **gap checklist**, and a **DDS-ready GeoJSON data pack**.

**The product is a lead-generation + data-collection funnel.** The free estimate/verdict is the carrot; 180Climate's real value is the captured lead + concession data and the warm path to a paid follow-up (financial model, face-to-face, fundraising / full DDS preparation). The build doubles as John's **public FDE / solutions-architect portfolio** (GitHub + 180climate site).

**Key architectural decisions (locked):**
- Runtime is a **deterministic calculator + AI narrative** — NOT a live multi-agent show for visitors.
- **Multi-agent is the build method** (parallel Sonnet agents, Haiku for boilerplate/narrative/tests).
- The carbon engine is **methodology-agnostic** (transparent avoided-emissions range), with the narrative citing the correct Verra family by permit/project type — it does NOT hard-code a single (now-sunsetting) method.
- **Shared core + two verticals** = build once, branch the calc (cost + speed lever).

---

## 2. Glossary (read first — domain terms the coding agent will not know)

| Term | Meaning |
|---|---|
| **Pre-FS** | Pre-Feasibility Study — an early, indicative go/no-go assessment before a full feasibility study (FS). |
| **FS** | Feasibility Study — the paid, detailed study (site visit, ground sampling, drone LiDAR) that 180Climate sells as the follow-up. |
| **REDD+** | Reducing Emissions from Deforestation and forest Degradation — carbon crediting for keeping existing forest standing. |
| **ARR** | Afforestation, Reforestation, Revegetation — planting/restoring forest (a *later* project type here). |
| **IFM** | Improved Forest Management — e.g. converting a logging concession to protection ("logged-to-protected"). |
| **APD** | Avoiding Planned Deforestation — avoiding *legally permitted* clearing (relevant to HTI/HA baselines). |
| **AUD** | Avoiding Unplanned Deforestation — the VM0048/VMD0055 family (illegal/encroachment-driven loss). |
| **HTI** | *Hutan Tanaman Industri* — Indonesian industrial timber **plantation** concession (legal right to clear-fell). |
| **HA** | *Hutan Alam* / natural-forest logging concession (legal right to **selectively** log). |
| **IUP** | *Izin Usaha Pertambangan/Perkebunan* — the land-use business permit; here, the forestry concession permit. |
| **Concession** | The licensed land area governed by the permit (the unit the Carbon engine assesses). |
| **Additionality** | Proof the carbon benefit would NOT have happened anyway. Here: holder has the legal right to log but forgoes it. |
| **Permanence / Leakage / Buffer** | Carbon-quality factors: durability of storage / displacement of emissions elsewhere / risk reserve deduction. |
| **Verra / VCS** | The carbon-standard body (Verified Carbon Standard) and registry; "VM####" = a methodology, "VMD####" = a module, "VT####" = a tool. |
| **ICVCM / CCP** | Integrity Council for the Voluntary Carbon Market / its Core Carbon Principles quality label. |
| **EUDR** | EU Deforestation Regulation — bans import of listed commodities tied to post-2020 deforestation. |
| **DDS** | Due Diligence Statement — the filing an EU operator submits (geolocation + risk assessment) via EU TRACES/Information System. |
| **Operator / Trader** | EUDR roles: operator first places goods on the EU market; trader makes them available downstream. Different obligations/deadlines. |
| **GFW / Hansen / RADD / JRC GFC2020** | Free satellite forest datasets (Global Forest Watch, Hansen loss, RADD alerts, EU JRC Global Forest Cover 2020 reference layer). |

---

## 3. Product definition & business model

- **What:** two free diagnostic tools (carbon gut-feel; EUDR readiness) behind one funnel.
- **Why it wins the lead:** replaces an expensive/slow manual process with an instant, credible, defensible read.
- **Revenue/relationship path:** lead capture → consultation → paid FS / financial model / DDS preparation → fundraising for forest development (180Climate's core business).
- **Carrots (explicit upsells, NOT app features):** multi-methodology optimization, project management of timing/location to optimize carbon yield, site visit + sampling + drone LiDAR for higher-accuracy numbers, full financial model, full DDS preparation & remediation.
- **Trust bar:** must look professional and defensible — rival developers and skeptical funders will scrutinize it. ~80%+ "gut-feel" is consistent with market pre-FS positioning; output is explicitly **non-binding** with a brief (not legalistic) disclaimer.

---

## 4. Users & primary audience

| User | Goal | Engine |
|---|---|---|
| Forest owner / concession holder | "Is my land worth a carbon project?" | Carbon |
| Developer / originator | Screen candidate concessions fast | Carbon |
| Investor / funder | Gut-feel feasibility before diligence | Carbon |
| Indonesian commodity exporter to EU | "Can I prove my plots are deforestation-free for EUDR?" | EUDR |
| (meta) Recruiters / peers | See John's FDE/architect skill via the public build | Both |

**#1 audience = concession holders/developers** who become 180Climate deal leads. Tune trust, copy, and defensibility to them.

---

## 5. Scope — in / out / later

**In (v1):**
- Carbon Pre-FS Engine: REDD+ and **Peatland** project types.
- EUDR Export Readiness Engine: palm oil, rubber, timber (+ cocoa, coffee) for Indonesia.
- Shared geospatial core, map UI, funnel/lead capture, AI narrative, deterministic calc.
- Deploy to 180climate website + public GitHub.

**Out / later:**
- ARR and Mangrove project types (architect so they slot in, not bolt on).
- Multi-methodology optimization (consultation carrot).
- CRM integration, authenticated user dashboard, richer peat-depth modelling.

**Build order (recommended):** Carbon vertical first (shippable milestone), EUDR as fast-follow reusing the core. `[CONFIRM]` in Section 19.

---

## 6. The "60-second wow"

- **Carbon:** enter info + location → deforestation verdict + map + semi-detailed carbon estimate (quantity & quality, ~80%+) + defensible AI rationale → carrot to book paid FS/financial model.
- **EUDR:** enter plot(s) + commodity → deforestation-free verdict vs 2020 + Indonesia risk tier + legality gap checklist + DDS-ready GeoJSON pack + readiness score → carrot to 180Climate for full DDS prep.

---

## 7. Carbon Pre-FS Engine — functional spec

**Input:** name, mobile, email, company, IUP name & address, permit type (HTI/HA), permit years remaining, project type (REDD+/Peat), concession location (coordinates OR shapefile/GeoJSON).

**Core estimate logic:**
- **Quantity** ≈ eligible area × carbon density (biomass or peat-carbon per ha) × project-type factor × baseline loss-rate × risk/buffer deductions.
- **Quality** ≈ additionality + permanence + leakage risk + methodology fit.
- Output a **range**, not a false-precision single number (baselines under current methods are jurisdictionally set — see Section 9).

**Baseline branches by permit type (both supported):**
- **HTI → clear-fell logic** (full legally-permitted clearing avoided).
- **HA → selective-logging logic** (partial extraction avoided).
- Peat projects: carbon is dominated by **avoided drainage/subsidence emissions** (peat depth proxy), not just above-ground biomass.

**Additionality (the defensible centerpiece):** holder has the **legal right to harvest but forgoes it**; land-use conversion to "carbon development & conservation" happens **commercially after the deal**, not as a precondition. AI narrative must explicitly cite **"legal harvest right foregone"** as the additionality basis.

**Output to user:** deforestation/condition verdict + map overlay; carbon quantity range; quality read; AI rationale; brief non-binding disclaimer; carrot.

---

## 8. EUDR Export Readiness Engine — functional spec

~60% reuses the carbon core (geospatial input, forest-loss detection, maps, funnel, AI-narrative pattern). What is **new**:

1. **Reference cutoff = 31 Dec 2020.** Verdict = deforestation-free after that date or not (binary, opposite framing to carbon).
2. **Commodity scope.** EUDR covers cattle, cocoa, coffee, **oil palm, rubber, wood/timber**, soya + derived products. Indonesia focus: palm oil, rubber, timber, cocoa, coffee. Tag each plot's commodity.
3. **Per-plot geometry.** EUDR requires **polygons for plots > 4 ha**, points allowed ≤ 4 ha. Support **plot-list / batch** ingest (many small plots), not just one large concession. No minimum-size gate (unlike carbon's 20,000 ha).
4. **Legality dimension** (NOT satellite-derivable): land-use rights, environmental laws, third-party rights, labour, anti-corruption, trade/customs → render as a **gap-analysis checklist / attestation**, framed as the carrot to 180Climate's service.
5. **Risk classification.** State **Indonesia's country risk tier** (low/standard/high) and adjust required due-diligence depth.
6. **DDS readiness output:** a **geolocation data pack** (GeoJSON aligned to EU TRACES/Information System format) + a **"missing evidence" gap report** + a readiness score.
7. **Roles & deadlines:** Operator vs Trader; **large/medium operators 30 Dec 2026, SMEs 30 Jun 2027** (Reg (EU) 2025/2650). Tell the user which applies. Keep dates **config-driven** (EUDR has already been delayed twice).

---

## 9. Verified methodology registry (carbon) — critical accuracy

Verified Jun 2026; source of truth = repo `docs/methodology.md` + ADR-0001/0007/0008.

| Project / baseline type | Current Verra route | Notes |
|---|---|---|
| Avoiding **Unplanned** Deforestation (AUD) | **VM0048 v1.0 + VMD0055 v1.1 + VT0007** | New standard; baselines **jurisdictional & third-party-set** (project gets a "slice of the jurisdictional pie"); first credits ~Apr 2026. |
| ARR | **VM0047** | Later project type. |
| **IFM** (HA logged-to-protected) | **VM0010 / VM0045 v1.2** | Fits HA "selective logging foregone." |
| Planned conversion (**HTI** clear-fell foregone) | **APD route (VM0009 / legacy — advisor-confirm)** | Fits HTI "clear-fell foregone." |
| **Peat** | **VM0027 now**; standalone **Tropical Peatland Conservation & Restoration v1.0** in development | Confirm before quoting numbers. |
| ⚠️ Deprecated | **VM0007** (and VM0006/0009/0015/0037) | Excluded from ICVCM CCP; VM0007 v1.7 had to finish validation by Oct 2025. **Do not brand the app to it.** |

**Critical routing rule:** the HTI/HA **foregone-legal-harvest** baseline is **PLANNED** (→ APD / IFM), **NOT** the unplanned VM0048/VMD0055 family. The app **routes by permit type** and cites the matching family in the narrative. Engine stays **methodology-agnostic** (transparent avoided-emissions math); the exact Verra route is confirmed with a methodology advisor for the *commercial* deal. `[CONFIRM]` stance in Section 19.

---

## 10. Eligibility gates & verdict logic

**Carbon hard gates:**

| Filter | Rule | Fail result |
|---|---|---|
| Permit type | Valid **HTI or HA** | No permit → **hard NO** |
| Permit remaining | **> 5 years** (extensions handled commercially; deals aim ~40 yr) | Flag / soft-no |
| Area | **≥ 20,000 ha** | Below → not viable v1 |
| Location | Inside the IUP boundary | Outside → flag |

**Verdict logic differs by engine:**
- **Carbon:** recent forest-loss characterizes current standing forest / degradation (is there carbon to protect?) — NOT a disqualifier.
- **EUDR:** any deforestation **after 31 Dec 2020** within the plot = non-compliant (disqualifying). Keep the cutoff and logic **config-driven** so the two engines share code but differ by parameter.

---

## 11. Data sources (free tier)

State uncertainty clearly; never imply field-grade precision.

- **Global Forest Watch / Hansen** — forest cover & annual loss (both engines).
- **RADD alerts** — near-real-time deforestation alerts.
- **JRC Global Forest Cover 2020** — EUDR's reference baseline layer (EUDR engine).
- **ESA WorldCover** — land cover.
- **ESA CCI Biomass / JAXA** — above-ground biomass (carbon density proxy).
- **Global/Indonesian peat maps** — peat presence & depth proxy.
- **SRTM / DEM** — terrain.

**Honesty line (brief, carrot-bearing):** *"This estimate uses satellite data and is a non-binding pre-feasibility gut-feel. A full FS with site visit, ground sampling and drone LiDAR refines quantity, quality, risks and mitigations — contact us to discuss."*

**Licensing watch-out:** Google Earth Engine is free for **non-commercial** use only — a commercial launch needs GEE commercial or self-hosted Cloud-Optimized GeoTIFFs / direct free APIs. Flag in README and ADR.

---

## 12. Shared architecture, stack & repo structure

```
                 180climate.com (website host)
        ┌──────────────────────────────────────────┐
        │   Shared FRONTEND (map UI + funnel form)   │
        └──────────────────────────────────────────┘
                          │
        ┌──────────────────────────────────────────┐
        │   Shared GEOSPATIAL CORE (reusable ~60%)   │
        │  • input parse (coords/shapefile/GeoJSON)  │
        │  • boundary + area                         │
        │  • forest-loss / land-cover / peat queries │
        │  • map tiles + overlays                    │
        └──────────────────────────────────────────┘
              │                              │
   ┌───────────────────┐         ┌────────────────────────┐
   │ CARBON PRE-FS      │         │ EUDR EXPORT READINESS   │
   │ ENGINE             │         │ ENGINE                  │
   │ • eligibility gates│         │ • 2020 cutoff verdict   │
   │ • avoided-emission │         │ • commodity + risk tier │
   │   range + quality  │         │ • legality gap checklist│
   │ • methodology route│         │ • DDS GeoJSON pack      │
   │   + Verra narrative│         │ • readiness score       │
   └───────────────────┘         └────────────────────────┘
              │                              │
        ┌──────────────────────────────────────────┐
        │   Shared OUTPUT: AI narrative + report      │
        │   render + lead capture → email (+ Sheet)   │
        └──────────────────────────────────────────┘
```

**Recommended stack (free-tier friendly, portfolio-credible):**
- **Backend/calc:** Python (FastAPI) + geospatial libs (geopandas, rasterio, shapely).
- **Frontend:** lightweight SPA with a map (React + MapLibre/Leaflet). Embed strategy depends on the 180climate platform — `[CONFIRM]` (WordPress/Webflow/custom) decides embed vs iframe vs link-out.
- **AI narrative:** Claude — **Haiku** for routine narrative/boilerplate/tests (cost control), **Sonnet** for harder reasoning.
- **Lead store:** email → leoniches@gmail.com (v1); recommend also a Google Sheet append for a durable record.
- **Hosting:** static frontend on free tier (Vercel/Netlify/GitHub Pages); API on free/cheap tier (Render/Fly/Railway).

**Suggested monorepo (`180climate-app/`):**
```
180climate-app/
  docs/            methodology.md, ADR-000x, this spec
  core/            geospatial core (shared); typed interfaces/contracts
  engines/
    carbon/        eligibility, methodology routing, estimate
    eudr/          cutoff verdict, risk tier, legality checklist, DDS pack
  narrative/       AI rationale (prompt templates per engine)
  frontend/        map UI + funnel
  api/             FastAPI routes
  tests/           golden-case fixtures + unit tests
```

**Module-boundary rule (so parallel agents don't collide):** define the **typed contracts** between `core ↔ engines ↔ narrative ↔ api` FIRST (the "constitution"). Agents may only change code behind their own interface; shared types change only by explicit agreement / ADR.

---

## 13. Runtime vs build (do not confuse these)

- **Runtime = deterministic.** A reproducible engine computes the number/verdict; AI only *writes the explanation*. This keeps results defensible, testable, and cheap. **No live multi-agent reasoning shown to visitors.**
- **Build method = multi-agent.** Parallel Sonnet agents develop the app within Claude Max limits; Haiku handles boilerplate/narrative/tests. Contracts-first; iteration caps; verification gate before any merge; nothing to `main` unreviewed.

---

## 14. Development plan & phases

**Principle:** vertical slice first (one path that works end-to-end), then widen. Human checkpoint after each phase.

**Phase 0 — Foundations (no parallel agents yet):** resolve Section 19 `[CONFIRM]`s; lock methodology stance + registry; set up monorepo, typed contracts, ADRs; pick host/embed. *Gate: architecture approved.*

**Phase 1 — Vertical slice (the spine):** one sample concession → parse boundary → GFW forest-loss query → placeholder carbon number → map + verdict + AI rationale → capture form → email. *Gate: works end-to-end, ugly but real.*

**Phase 2 — Carbon engine (multi-agent):**
- *Data agent* — biomass + peat + forest-loss integration.
- *Calc agent* — eligibility gates (HTI/HA, ≥20k ha, >5yr), methodology routing, avoided-emission range + quality factors.
- *Narrative agent* — defensible Verra-family rationale + foregone-legal-harvest additionality.
- *Frontend agent* — polished map, report layout, funnel UX.
*Gate: Carbon Pre-FS demo-ready.*

**Phase 3 — EUDR engine (reuses core; multi-agent):**
- *Verdict agent* — 2020 cutoff logic + JRC 2020 layer.
- *Compliance agent* — commodity scope, Indonesia risk tier, legality gap checklist.
- *DDS agent* — GeoJSON/TRACES-aligned pack + readiness score.
- *Frontend agent* — EUDR vertical UI + funnel.
*Gate: EUDR Readiness demo-ready.*

**Phase 4 — Integrate, harden, ship:** verification harness (calc unit tests, input validation, golden-case outputs), README + architecture diagram + methodology notes + disclaimers, deploy to 180climate + GitHub, lead pipeline live. *Gate: public.*

**Cost/speed controls:** model tiering (Sonnet build / Haiku boilerplate); parallelize only genuinely independent tasks; shared spec/memory as single source of truth; caching of dataset queries.

---

## 15. Acceptance criteria (Definition of Done — testable targets for the coding agent)

**Carbon engine:**
- Accepts coordinates AND shapefile/GeoJSON; rejects malformed input with a clear message.
- Applies all four hard gates (HTI/HA, >5yr, ≥20,000 ha, inside-IUP) and returns a correct eligible/flagged/hard-NO result on golden test cases.
- Routes methodology by permit type (HTI→APD/clear-fell; HA→IFM/selective; Peat→peat method) and names the correct Verra family in output.
- Produces a carbon **range** (not a single false-precise number) with stated uncertainty.
- AI rationale explicitly states the "legal harvest right foregone" additionality basis.
- Renders a map with forest-loss overlay; shows the brief non-binding disclaimer.
- Lead is captured and delivered to email (+ Sheet if enabled).

**EUDR engine:**
- Accepts a plot list; supports polygons (>4 ha) and points (≤4 ha); no min-size gate.
- Returns a correct deforestation-free / non-compliant verdict against the **31 Dec 2020** cutoff using the JRC 2020 layer on golden cases.
- Tags commodity; states Indonesia risk tier; outputs the legality gap checklist.
- Exports a valid **GeoJSON DDS pack** (TRACES-aligned schema) + readiness score.
- States which deadline applies (operator 30 Dec 2026 / SME 30 Jun 2027) from config.

**Cross-cutting:**
- Deterministic: same input → same output (no LLM in the number path).
- Golden-case fixtures committed; unit tests pass in CI.
- README + architecture diagram + methodology notes + disclaimers present.
- No secrets in repo; free-tier deploy reproducible from README.

---

## 16. Non-functionals, deployment & cost

- **Host:** embedded in / linked from 180climate website (`[CONFIRM]` platform → embed/iframe/link-out).
- **Public GitHub repo** as portfolio artifact: clean README, architecture diagram, defensible methodology notes, ADRs.
- **Budget:** free / near-free tier preferred; flag GEE commercial-licensing caveat.
- **Trust/UX:** professional, credible; brief disclaimer (non-binding; not a legal letter).
- **Accuracy claim:** "~80%+ gut-feel," market-consistent.
- **Observability:** basic logging on calc inputs/outputs + lead delivery for debugging.

---

## 17. Disclaimers & positioning

- Output is an **indicative, non-binding pre-feasibility / readiness screen**, not certified verification, legal, or financial advice.
- EUDR readiness is **decision-support**, not a substitute for the operator's legal DDS obligation.
- Keep disclaimers **brief and to the point**; pair with the carrot to the paid follow-up.

---

## 18. Risks, what-ifs & contingencies

| What-if | Contingency |
|---|---|
| Methodology dispute (VM0048 vs APD/IFM for logging concessions) | Methodology-agnostic transparent calc + swappable module; route by permit; advisor-confirm for the commercial deal |
| VM0007 reliance dates the app | Anchor to verified registry (Section 9); never brand to VM0007 |
| EUDR deadlines shift again (already delayed twice) | Dates config-driven; label "as of Jun 2026" |
| Free data too coarse for a specific plot | State uncertainty bands; position FS/site-visit as the precision upgrade (carrot) |
| GEE non-commercial licensing trips commercial launch | Self-hosted COGs / free APIs; flag in README + ADR |
| Additionality challenged by a rival/funder | Lead with foregone-legal-harvest baseline; golden-case tests + visible sources |
| Legality not satellite-derivable (EUDR) | Render as gap checklist/attestation = service carrot, not a computed claim |
| Two verticals double the work | Shared core keeps net add ~40%; build Carbon first, EUDR reuses |
| Parallel agents collide at the seams | Contracts/types first; agents change only behind their interface; ADR for shared changes |
| Malformed / out-of-Indonesia geometry | Validate early; clear error + graceful fallback |
| Scope creep before ~5 Jul | Phase-gated; Carbon vertical alone is a shippable milestone |
| Lead data lost (email only) | Add Google Sheet/CRM backup |
| 180climate platform can't embed the app | Standalone hosted app + link/iframe |

---

## 19. Open decisions to resolve in planning (the `[CONFIRM]` gate)

1. **Methodology stance** — confirm the *methodology-agnostic engine + Verra-family-by-permit narrative* approach (vs hard-coding one method). *(Recommended: agnostic.)*
2. **180climate website platform** — WordPress / Webflow / custom → decides embed vs iframe vs link-out.
3. **Funnel gating** — show estimate first then capture, or capture-to-unlock the full/detailed report? *(Recommended: light capture up front, detailed report + financial-model carrot gated.)*
4. **Lead store** — email only, or email + Google Sheet? *(Recommended: email + Sheet.)*
5. **Build order / public scope** — Carbon first then EUDR fast-follow (recommended), or both in parallel; and whether v1 public scope includes EUDR.
6. **Peat methodology** — confirm VM0027 now vs waiting on the standalone peatland methodology for quoted numbers.

---

## 20. First vertical slice (the spine — start here)

One thin end-to-end path that works, before any widening or parallel agents:

`sample concession (coords/shapefile)` → `parse boundary + area` → `eligibility gate stub (permit type/area)` → `GFW forest-loss query` → `placeholder carbon number` → `render map + verdict + AI rationale` → `capture form → email`.

Prove the whole pipe connects; then widen each stage (real biomass, peat, methodology routing, polish) and assign the multi-agent build around the Phase-2/3 stages above.

---

## 21. Handover checklist

- [ ] Claude Project ingests this doc; resolves Section 19; produces task breakdown + ADRs.
- [ ] Repo `180climate-app/` scaffolded per Section 12 with typed contracts.
- [ ] Phase 1 vertical slice green (Section 20) before parallel agents start.
- [ ] Golden-case fixtures written from Section 15 before engine logic.
- [ ] Methodology registry (Section 9) reflected in `docs/methodology.md` + ADRs.
- [ ] Disclaimers + README + architecture diagram before public deploy.

*End of master handover specification.*
