# Enterprise AI delivery case study — 180Climate

**Purpose:** an inspectable account of solution architecture, forward-deployed and full-stack engineering, business-process redesign, business-value discipline and adoption leadership.

**Evidence date:** 11 September 2026.

**Claim boundary:** this is project evidence, not an AIRI assessment, certification, enterprise-wide adoption result or claim that every planned control is operating in production.

## Executive view

180Climate uses one public engineering foundation to support Carbon Pre-Feasibility screening, EUDR plot screening and an invited Fieldwork pilot. The work demonstrates how a business problem is converted into a bounded human/AI workflow, a maintainable application architecture, deterministic controls, tests, deployment evidence and a practical adoption path.

The delivery principle is simple: use AI where it improves speed or clarity, use deterministic code where the result must be reproducible, and keep human authority at privacy, safety, professional, publication, contact-disclosure and commercial boundaries.

## From business process to working service

| Business need | Previous or manual friction | Implemented operating response | Evidence |
|---|---|---|---|
| Early carbon opportunity screening | Inputs and assumptions can be hard to compare or explain | Shared typed inputs, deterministic calculations and a visible derivation trace | [Carbon contracts](../core/contracts/__init__.py), [ADR-0014](adr/ADR-0014-derivation-trace.md), [report tests](../tests/test_report.py) |
| EUDR plot triage | Missing evidence can be mistaken for a clear result | Explicit `clear_in_screen`, `loss_detected` and `inconclusive` states; missing required evidence fails closed | [Decision logic](../engines/eudr/triage.py), [ADR-0018](adr/ADR-0018-eudr-contracts.md), [truth-table tests](../tests/test_eudr_triage.py) |
| Finding suitable field support | Requests, capabilities, authority and consent can arrive through loose messages | One invited-pilot explanation, one private Wix intake, operator review and consent-before-introduction policy | [Live pilot](https://one80climate-fieldwork-preview.onrender.com/fieldwork), [public service record](https://github.com/TengKianBoon/180climate-app/blob/d25d2c4/frontend/services.json), [Phase 1A boundary](fieldwork/phase-1a-foundation.md) |
| Scaling delivery with AI | Tool use can obscure responsibility or bypass checks | Role-specific build/review/verification instructions, deterministic tests and explicit human approval gates | [Agent instructions](../.claude/agents), [engineering walkthrough](2609092130_engineering_walkthrough_4ofX.md), [project controls](../AGENTS.md) |

## Solution architecture evidence

- **Reuse before expansion.** FastAPI, typed contracts, geospatial adapters and the existing Render deployment shape are extended rather than replaced with a second framework.
- **Separate runtime decisions from AI assistance.** Carbon and EUDR outcomes are computed in code. Optional AI classifies a free-text carbon description before routing; it does not replace the engines.
- **Fail closed at uncertain boundaries.** Missing required forest evidence yields `inconclusive`; incomplete native Fieldwork launch configuration rejects submissions.
- **Protect different data classes differently.** Public source, schemas and synthetic fixtures stay in GitHub; contacts, requests, status keys, operator secrets, logs and sensitive locations do not.
- **Design for recovery.** Source versioning, deployment revisions and database backup/restore are treated as different recovery layers with different completion checks.

Start with the [architecture view](assets/2609092130_architecture_4ofX.svg), then inspect the [API composition](../api/main.py), [typed contracts](../core/contracts/__init__.py), [Fieldwork boundary](fieldwork/phase-1a-foundation.md) and [deployment/recovery record](fieldwork/deployment-and-recovery.md).

## Forward-deployed and full-stack engineering evidence

The forward-deployed engineering (FDE) evidence is the connection between a live business workflow and the technical delivery: inspect the existing Wix/GitHub/Render environment, clarify the operator and user journey, reuse the existing stack, ship the smallest workable path, test it in the deployed context, and correct friction found in that real journey. The repository then links user interface, API, domain logic, persistence, tests and deployment instead of presenting disconnected code samples:

1. Responsive English/Bahasa browser flows and explicit empty, error, blocked and success states.
2. FastAPI routes, Pydantic contracts, deterministic engines and security/cache headers.
3. SQLite persistence and recovery utilities for the gated native Fieldwork workflow.
4. Unit, integration, truth-table, API/report, security-boundary and browser-path checks.
5. Git stage commits, CI evidence, Render deployment revisions and recovery instructions.

For the current Fieldwork checkpoint, the deterministic offline suite recorded **477 passed, two live-network checks deselected**; the focused Fieldwork suite recorded **16 passed**. When the two live BIG map checks were included, the external endpoints timed out and the adapters returned unavailable/manual-review outcomes. See the [dated stage receipt](fieldwork/stage-receipts.md) for the exact confidence boundary.

## Business-case discipline

The project treats AI and software investment as an operating decision:

- reuse one geospatial foundation across related revenue and compliance use cases;
- start Fieldwork as a free, invited, manually reviewed pilot before building marketplace automation or payments;
- use rules, schemas and templates before model calls, then route only ambiguous work to higher-cost reasoning;
- retain manual fallbacks for classification, matching and professional review;
- measure counts and elapsed work before claiming savings, conversion or adoption outcomes;
- stop excluded work—payments, public profiles, automated dispatch and regulated conclusions—until demand and controls justify it.

This creates a clearer benefits chain: **business problem → bounded use case → reusable capability → testable decision → operating feedback → investment decision**.

## Enterprise AI adoption leadership

The leadership evidence is in the operating design, not the number of AI tools used:

- product objectives and acceptance criteria are set before implementation;
- builder, reviewer, verifier and test-writer responsibilities are separated;
- people retain judgement over unsafe, regulated, privacy-sensitive and externally consequential actions;
- bilingual explanations and visible limitations reduce user uncertainty;
- failures are preserved for correction rather than hidden by the same agent that built the change;
- pilot targets focus on genuine providers, requesters, qualified cases, mutual introductions, operator effort and exceptions;
- wider rollout depends on observed value, user feedback, governance evidence and an explicit go/no-go decision.

No sustained-adoption result is claimed yet. The current public checkpoint establishes a usable pilot entry and an evidence-controlled way to learn.

## AIRI Level 4 direction

At the evidence date, [AIRI Framework v3.2](https://airi.foundation/) describes Level 4 as **AI Catalyst / Pioneer**, where AI agents can handle routine production while humans provide judgement, and where mature governance and ecosystem influence are evidenced. This repository is therefore described as **building evidence toward Level 4 capabilities**, not as Level 4 certified or assessed.

| AIRI evidence area | Evidence present here | Evidence still needed for a credible Level 4 case |
|---|---|---|
| Leadership and culture | Management-owned use cases, acceptance gates, role design and experimentation | Broader workforce participation, mentoring records and sustained adoption beyond the builder |
| Ethics and governance | Privacy boundary, consent, fail-closed rules, prohibited use and human accountability | Approved production governance, incident exercises, counsel-reviewed notices and operating audits |
| Business value | Reuse strategy, staged investment, pilot proof targets and honest exclusions | Baselines, repeated real use, measured benefits, correction cost and outcome coverage |
| Data foundation | Typed contracts, reference inputs, synthetic tests and unknown states | Production data-quality ownership, lifecycle evidence, deletion propagation and independent quality review |
| Infrastructure and standards | FastAPI/Render delivery, CI/test evidence, versioning and recovery design | Mature monitoring, protected production state, exercised service rollback and cross-team reuse |
| Ecosystem influence | Public code, walkthroughs, ADRs and reusable control patterns | External adoption, teaching/mentoring, independent review, contributions or standards influence |

## My contribution and AI assistance

I owned problem selection, requirements, scope, architecture and operating choices, delivery priorities, acceptance criteria, publication decisions and the connection between the tools and 180Climate's business workflows. I used AI agents to assist research, implementation, testing, review and documentation. Deterministic test results and deployment receipts are evidence of system behaviour; they do not convert AI-assisted implementation into a claim of unaided coding, nor do they prove business outcomes that have not yet been measured.

## Review path

For a five-minute technical review:

1. Open the [live services](../README.md#1-see-the-product).
2. Follow the [architecture](../README.md#2-understand-the-architecture).
3. Inspect the [EUDR decision and tests](../README.md#3-inspect-a-meaningful-piece-of-code).
4. Review the [test/CI record](../README.md#4-check-the-tests).
5. Read [My contribution](../README.md#5-my-contribution) and the remaining AIRI evidence gaps above.

That path is deliberately short: product → workflow → architecture → controls → code → tests → deployment → adoption evidence → contribution.
