# Engineering walkthrough — 180Climate

A five-minute tour of the public implementation at [`b4ac414`](https://github.com/TengKianBoon/180climate-app/commit/b4ac414789659bfbb56f19599a87cbe72a01a2d2). This page explains code and recorded design decisions; it is not a fresh geospatial or regulatory validation.

## One distinction that changes the result

A missing dataset response and a measured zero must not mean the same thing.

The EUDR decision function receives three values: whether a 2020 forest baseline is confirmed, optical loss in hectares, and whether radar reports an alert after the cutoff. Its [current logic](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/engines/eudr/triage.py#L45-L79) is:

1. A confirmed baseline plus either positive optical loss or a radar alert returns `loss_detected`.
2. A confirmed baseline plus zero optical loss and no positive radar alert returns `clear_in_screen`.
3. The remaining combinations return `inconclusive`.

A missing radar result is permitted in the second branch. Missing optical-loss data or a missing baseline is not. This is the implementation's explicit policy, and the existing tests capture it.

### Decision → implementation → check

| Layer | What to inspect |
|---|---|
| Design decision | [ADR-0018](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0018-eudr-contracts.md) replaces a boolean with explicit detection states. |
| Contract | [`PlotVerdict`](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/core/contracts/__init__.py#L247-L276) includes `geometry_invalid`; geometry validation occurs before the three-state detection function. |
| Logic | [`_decide_detection`](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/engines/eudr/triage.py#L45-L79) implements the three branches above. |
| Existing checks | [15 truth-table cases and a 27-combination invariant sweep](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/tests/test_eudr_triage.py#L50-L90). |
| Local reproduction | [Run the isolated function](../examples/2609092130_eudr_decision_demo_4ofX.py) against the existing cases with the Python standard library. |

The reproduction script parses the checked-out source and loads only the inspected function. It does not import the application or fetch satellite data. It also extracts the existing test cases rather than maintaining a second copy of the decision algorithm.

## A second example: showing the actual calculation

[ADR-0014](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0014-derivation-trace.md) records John's request for a report that exposes the engine's real inputs and intermediate values.

The engineering choice was to add a typed `CalculationTrace` populated by the engine. A report can then display those values instead of reconstructing an estimate from a partial result.

The [trace model](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/core/contracts/__init__.py#L158-L189) is visible in the public contracts. [ADR-0016](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0016-uncertainty-propagation.md) records a later change to uncertainty propagation. Read the earlier formula as design history, not as a substitute for the final implementation.

## Where AI is used

The development records describe AI-assisted planning, coding and review. Within the inspected runtime, the optional [free-text classifier](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/classifier/intake.py#L58-L118) makes an external model call. [The API](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/api/main.py#L267-L336) uses its category to route a carbon request.

The [narrator](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/narrative/narrator.py#L83-L105) builds template text from a typed payload. The EUDR decision function itself does not call a model.

This distinction matters when discussing the project: AI can influence the optional category-selection route, while the numerical calculations and detection rules execute as code.

## Versioned releases and recovery

The published [carbon release v1.0.0](https://github.com/TengKianBoon/180climate-app/releases/tag/v1.0.0) points through an annotated tag to source commit `ceb8b1df560d47499af27c20d2af819bf8b9997b`. The [EUDR release v1.1.0](https://github.com/TengKianBoon/180climate-app/releases/tag/v1.1.0) points to `f2a447b8759be80535b74c59e22b500df4ea17ae`. These are distinct source revisions; the later CI result cited in this tour belongs to `b4ac414`.

John confirms that GitHub versioning and rollback/recovery decisions were part of his delivery responsibilities. Release records provide direct evidence of versioning. They do not, by themselves, prove that a service was successfully rolled back.

A source-recovery procedure should record the unwanted change and the recovery target, create a revert commit that preserves history, then run the relevant checks on the resulting revision. GitHub Desktop supports this through History → Revert Changes in Commit. [GitHub's documentation](https://docs.github.com/en/desktop/managing-commits/reverting-a-commit-in-github-desktop?platform=windows) explains that the original commit remains in history.

For production recovery, source is one part of the system: deployment configuration, dependencies, credentials and any persistent state also matter. A useful recovery record would show the deployed revision before and after, the reason for recovery, the observed service checks, and the elapsed recovery time. The reviewed [production roadmap](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/production-roadmap.md) identifies staging, post-deployment smoke tests and a rollback path as further work. No successful production recovery drill is claimed in this showcase.

## What the evidence proves

- The linked code and design records exist in the reviewed public snapshot.
- [The linked CI job](https://github.com/TengKianBoon/180climate-app/actions/runs/28553478682/job/84655746161) records 461 passed, 2 skipped and 1 warning on 1 July 2026.
- The local example exercises one pure function against the repository's existing examples and invariant.

It does not establish field accuracy, current email or Sheet delivery, full TRACES interoperability, enterprise scale, or independent confirmation of each historical human action. Those require their own evidence.

## A two-minute interview route

1. Open the product screenshot and describe the user problem.
2. Show the architecture and separate the application runtime from AI-assisted development.
3. Change the discussion from “zero” to “unavailable” in the decision table.
4. Open the function and its tests.
5. Explain the calculation-trace request, the advisor's uncertainty finding and John's recorded approvals.
6. Discuss one remaining hardening task and the conditions that would justify it.

Use the contribution wording only to the extent it matches your own recollection and supporting records.
