# 180Climate — Carbon Screening, EUDR Plot Check & Fieldwork

The platform behind 180Climate's free controlled public beta: carbon pre-feasibility screening, EUDR plot checks against the EU's forest baseline and satellite loss data, and the Fieldwork Network. Built for Indonesian landholders, exporters and field practitioners.

**Python · FastAPI · Pydantic · geospatial data · deterministic engines · AI-assisted development**

[Open Carbon Screening](https://carbon.180climate.net) · [Open EUDR Plot Check](https://eudr.180climate.net) · [Open Fieldwork Network](https://eudr.180climate.net/fieldwork) · [Current beta status](docs/data-control/controlled-beta-status-2026-09-24.md) · [Read the code walkthrough](docs/2609092130_engineering_walkthrough_4ofX.md) · [Inspect CI](https://github.com/TengKianBoon/180climate-app/actions)

## 1. See the product

![180Climate EUDR Plot Check — actual public entry screen](docs/assets/2609092130_eudr_entry_4ofX.png)

*Public entry screen captured on 9 September 2026. The Carbon Screening view is [shown here](docs/assets/2609092130_carbon_entry_4ofX.png). These are entry screens; the reproducible example below demonstrates the decision logic separately.*

| App | Input | Output |
|---|---|---|
| Carbon Screening | Concession location, permit and project information | Indicative quantity range, calculation trace and report |
| EUDR Plot Check | Plot geometry, commodity and supplier role | Per-plot detection state, findings, preparation checklist and report |
| Fieldwork Network | Requester outcome or provider capability and contact details | Private review queue and consent-controlled introduction workflow |

### Fieldwork Network (free controlled public beta)

The public **180Climate Fieldwork Network** accepts requester and provider registrations through its native private intake. 180Climate reviews scope and fit before any introduction. Registration is free and does not create a booking or a payment obligation.

The repository implements requester/provider records, private operator review, non-enumerable status access and two-party consent. The current public entry is the native Fieldwork page above; older stage receipts describe the earlier Wix invitation route. Tests use generated synthetic records only; no user submission or runtime database belongs in this public repository. See the [current beta status](docs/data-control/controlled-beta-status-2026-09-24.md).

For a quick look without entering contact details, run the offline example below.

### Run one decision in under a minute

From the repository root, with Python 3.10 or later:

```bash
python examples/2609092130_eudr_decision_demo_4ofX.py
```

No API key or package installation is needed. The example reads the actual `_decide_detection` function from this checkout and reuses the existing truth-table test cases. It isolates that function to avoid importing geospatial libraries or starting external integrations.

| Confirmed 2020 forest baseline | Optical loss data | Radar alert | Function result |
|---|---|---|---|
| Yes | Zero loss | No | `clear_in_screen` |
| Yes | 12.4 hectares lost | No | `loss_detected` |
| Yes | Unavailable | No | `inconclusive` |
| Unknown | Zero loss | No | `inconclusive` |
| Yes | Zero loss | Yes | `loss_detected` |

Synthetic inputs, run through the production function.

## 2. Understand the architecture

![Architecture of the reviewed public implementation](docs/assets/2609092130_architecture_4ofX.svg)

- **Product runtime:** browser UI → FastAPI → typed contracts and geospatial adapters → carbon calculations or EUDR triage → results and reports.
- **Optional AI:** the carbon “describe your own” path uses an LLM classifier to select a project category before routing to an engine. The calculations and EUDR detection rules are implemented in code.
- **Narration:** `narrative/narrator.py` generates template text from the calculation results.
- **Development workflow:** AI agents assisted planning, implementation and review, with human decisions recorded separately. That build workflow is distinct from what runs when a user opens the app.

[API wiring](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/api/main.py#L267-L336) · [Contracts](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/core/contracts/__init__.py#L247-L276) · [Classifier](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/classifier/intake.py#L58-L118) · [Narration](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/narrative/narrator.py#L83-L105)

### How I orchestrated development

I worked hands-on with **Claude Cowork, Claude Code and Codex** to move from requirements through implementation, audit, browser QA and release correction. I customised agent roles with the relevant context, background instructions and checks for each responsibility. The shared repository and work-order records supported controlled handoffs between planning, implementation and verification.

| Role | Instruction a reviewer can inspect |
|---|---|
| [Writer](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/writer.md) | Implement the scoped work order, respect the contracts and hand off the change for review. |
| [Reviewer](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/reviewer.md) | Inspect the code and acceptance criteria; return PASS, FAIL or CLARIFY without editing files. |
| [Verifier](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/verifier.md) | Run the product and checks, preserve failure evidence and report observed versus expected results. |
| [Test writer](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/test-writer.md) | Turn acceptance criteria into deterministic tests and input/expected-output fixtures. |

I designed this workflow around task decomposition, role-specific context, evidence-based handoffs and human decision gates. The Reviewer and Verifier instructions keep checking separate from implementation and preserve failures for the next correction cycle. The [walkthrough](docs/2609092130_engineering_walkthrough_4ofX.md) connects those controls to the code and delivery decisions.

## 3. Inspect a meaningful piece of code

Start with [`_decide_detection`](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/engines/eudr/triage.py#L45-L79). It distinguishes a confirmed zero from unavailable data. That distinction prevents a missing optical-loss response from being treated as a clean result.

Then follow [the contract decision](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0018-eudr-contracts.md) → [the typed verdict](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/core/contracts/__init__.py#L247-L276) → [the truth-table tests](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/tests/test_eudr_triage.py#L50-L90).

The [engineering walkthrough](docs/2609092130_engineering_walkthrough_4ofX.md) explains this example and the separate carbon calculation-trace decision.

## 4. Check the tests

The [GitHub CI run from 1 July 2026](https://github.com/TengKianBoon/180climate-app/actions/runs/28553478682/job/84655746161), for commit [`b4ac414`](https://github.com/TengKianBoon/180climate-app/commit/b4ac414789659bfbb56f19599a87cbe72a01a2d2), records **463 collected: 461 passed, 2 skipped**, with one test warning. Contract type-checking also passed. The skipped checks were two live overlay smoke tests.

The offline example reproduces the decision checks; the CI workflow covers the broader application suite.

[CI definition](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.github/workflows/ci.yml) · [Triage tests](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/tests/test_eudr_triage.py) · [API and report tests](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/tests/test_eudr_api.py)

## 5. My contribution

I took the project from demand assessment and scope through an AI-assisted build, deployment, trial and launch.

- **Chose the problem and the shared approach.** I assessed demand and the available solutions, then chose to reuse satellite data and a common geospatial foundation across carbon screening and EUDR plot checks.
- **Set scope, timeline and budget.** I defined the first-release requirements and delivery constraints. I used subscription-based AI development tools to control spending and completed the build within the timeline and budget I had set.
- **Designed the development process before coding.** I divided planning and execution between Cowork and VS Code, customised the subagents' roles, context and instructions, and specified the skills, workflow graphs, bounded improvement loops, hooks, graders and checks used throughout the build.
- **Included versioning and recovery in delivery.** My responsibilities included GitHub version control and rollback/recovery decisions as part of the development and release process. The published releases and their exact source revisions are linked below.
- **Owned delivery and acceptance.** I directed decisions on UI, reports, security, usage and deployment to the 180Climate website, and took the apps through trial and launch. I worked against Verra- and EUDR-related screening requirements, with report quality, usability and practical value as acceptance criteria.
- **Connected the apps to origination and adoption.** I set the strategy for forest-data collection to support origination, and for messaging and promotion to encourage use.

**One decision you can inspect:** I required the carbon report to expose the actual calculation inputs and intermediate values. [ADR-0014](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0014-derivation-trace.md) records that request; the [typed calculation trace](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/core/contracts/__init__.py#L158-L189) shows the implementation approach. [ADR-0018](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0018-eudr-contracts.md) separately records my approval of explicit EUDR detection states.

### How the work was split

I designed and ran the agent harness that implemented, tested and reviewed this code against my specifications. Problem selection, the domain model, architecture, acceptance criteria and every release decision were mine; the commit history shows the AI co-authorship openly.

## 6. Inspect versioning and recovery

The project has two published releases, each connected to an annotated Git tag and a specific source revision. Both releases were published on 1 July 2026.

| Release | Scope | Tagged source |
|---|---|---|
| [v1.0.0](https://github.com/TengKianBoon/180climate-app/releases/tag/v1.0.0) | Carbon Pre-Feasibility Engine | [`ceb8b1d`](https://github.com/TengKianBoon/180climate-app/commit/ceb8b1df560d47499af27c20d2af819bf8b9997b) |
| [v1.1.0](https://github.com/TengKianBoon/180climate-app/releases/tag/v1.1.0) | EUDR Export Readiness Engine | [`f2a447b`](https://github.com/TengKianBoon/180climate-app/commit/f2a447b8759be80535b74c59e22b500df4ea17ae) |

These tags let a reviewer identify and retrieve the source associated with each release. The later [`b4ac414`](https://github.com/TengKianBoon/180climate-app/commit/b4ac414789659bfbb56f19599a87cbe72a01a2d2) snapshot is the basis for this walkthrough and its recorded CI result.

I included versioning and rollback/recovery decisions in delivery so changes could be traced to specific revisions. Git recovery and service recovery have different completion checks: source changes need tests, while a restored service also needs configuration, dependency and user-facing checks. The [recovery discussion](docs/2609092130_engineering_walkthrough_4ofX.md) connects the release history to the next hardening work.

## Scope and next work

Next on the public [hardening roadmap](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/production-roadmap.md): observability, abuse controls, staging, rollback automation and usage analytics. Source links in this tour are pinned to the reviewed commit.
