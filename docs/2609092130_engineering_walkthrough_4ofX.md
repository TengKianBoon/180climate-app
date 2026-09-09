# Engineering walkthrough — 180Climate

I use this five-minute walkthrough to connect the product choices, architecture and verification in the implementation at [`b4ac414`](https://github.com/TengKianBoon/180climate-app/commit/b4ac414789659bfbb56f19599a87cbe72a01a2d2).

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

I required the report to expose the engine's real inputs and intermediate values. [ADR-0014](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0014-derivation-trace.md) records that request.

The engineering choice was to add a typed `CalculationTrace` populated by the engine. A report can then display those values instead of reconstructing an estimate from a partial result.

The [trace model](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/core/contracts/__init__.py#L158-L189) is visible in the public contracts. [ADR-0016](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/adr/ADR-0016-uncertainty-propagation.md) records a later change to uncertainty propagation. Read the earlier formula as design history, not as a substitute for the final implementation.

## Where AI is used

The development records describe AI-assisted planning, coding and review. Within the inspected runtime, the optional [free-text classifier](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/classifier/intake.py#L58-L118) makes an external model call. [The API](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/api/main.py#L267-L336) uses its category to route a carbon request.

The [narrator](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/narrative/narrator.py#L83-L105) builds template text from a typed payload. The EUDR decision function itself does not call a model.

This distinction matters when discussing the project: AI can influence the optional category-selection route, while the numerical calculations and detection rules execute as code.

## Development orchestration: Cowork and VS Code

I used Claude Cowork for planning alongside Claude Code in VS Code for execution and audit work. I customised the context, background instructions and responsibilities assigned to subagents, with checks across the build. This gave planning, implementation and verification distinct working contexts within one coordinated development process.

The published [Writer](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/writer.md), [Reviewer](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/reviewer.md), [Verifier](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/verifier.md) and [Test-writer](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/.claude/agents/test-writer.md) instructions show differentiated permissions, inputs and expected outputs. In particular, the Reviewer and Verifier are instructed not to edit files: a failed check should be reported to the builder rather than silently repaired by the checker.

I used the shared repository and work-order records to coordinate handoffs. The [original orchestration proposal](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/orchestration-v2.md) explains the file-based coordination design; the role instructions and [recorded work orders](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/coordination/INBOX.md) show the assigned responsibilities and acceptance criteria.

My focus was on making the work controllable: clear scope for each agent, the context needed for its role, defined handoffs, preserved failure evidence and explicit acceptance gates. I combined model review with deterministic tests and human decisions at the key boundaries.

I chose subscription-based AI development tools to manage spend and completed the build within the timeline and budget I had set. Reusing one geospatial foundation across two applications also kept the delivery scope focused while serving two user needs.

## Versioned releases and recovery

The published [carbon release v1.0.0](https://github.com/TengKianBoon/180climate-app/releases/tag/v1.0.0) points through an annotated tag to source commit `ceb8b1df560d47499af27c20d2af819bf8b9997b`. The [EUDR release v1.1.0](https://github.com/TengKianBoon/180climate-app/releases/tag/v1.1.0) points to `f2a447b8759be80535b74c59e22b500df4ea17ae`. These are distinct source revisions; the later CI result cited in this tour belongs to `b4ac414`.

I included GitHub versioning and rollback/recovery decisions in my delivery responsibilities. The release records preserve named milestones and their source revisions, making the development history inspectable.

A source-recovery procedure should record the unwanted change and the recovery target, create a revert commit that preserves history, then run the relevant checks on the resulting revision. GitHub Desktop supports this through History → Revert Changes in Commit. [GitHub's documentation](https://docs.github.com/en/desktop/managing-commits/reverting-a-commit-in-github-desktop?platform=windows) explains that the original commit remains in history.

For production recovery, source is one part of the system: deployment configuration, dependencies, credentials and any persistent state also matter. A useful recovery record captures the deployed revision before and after, the reason for recovery, the observed service checks and the elapsed recovery time. My next hardening work is guided by the [production roadmap](https://github.com/TengKianBoon/180climate-app/blob/b4ac414789659bfbb56f19599a87cbe72a01a2d2/docs/production-roadmap.md), including staging, post-deployment smoke tests and the service rollback path.

## Verification

- The linked code and design records exist in the reviewed public snapshot.
- [The linked CI job](https://github.com/TengKianBoon/180climate-app/actions/runs/28553478682/job/84655746161) records 461 passed, 2 skipped and 1 warning on 1 July 2026.
- The local example exercises one pure function against the repository's existing examples and invariant.

## Explore the decisions

1. Open the product screenshot and describe the user problem.
2. Show the architecture and separate the application runtime from AI-assisted development.
3. Change the discussion from “zero” to “unavailable” in the decision table.
4. Open the function and its tests.
5. Follow my calculation-trace request, the uncertainty refinement and the recorded approvals.
6. Discuss one remaining hardening task and the conditions that would justify it.
