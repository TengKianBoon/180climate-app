# Skill: self-improving-code

Chain-of-Verification (CoV) loop for high-stakes code outputs. Use on the carbon engine, EUDR verdict logic, and the report generator.

## When to apply
- **HIGH effort** (number-path WOs: WO-CARBON-003, WO-CARBON-004, EUDR verdict): run full CoV — 1 rewrite.
- **MEDIUM effort** (narrative, golden cases): verify only — no rewrite unless a hard invariant fails.
- **LOW effort** (scaffold, plumbing, stubs): skip.

## The loop (budget: 1 rewrite)

### Step 1 — Draft
Writer produces the initial implementation.

### Step 2 — Adversarial verify
Reviewer and Verifier independently check:
- Does the output satisfy all acceptance criteria?
- Are all invariants upheld (determinism, no single carbon number, correct methodology routing)?
- Are there any edge cases that break the contract types?

If both PASS → done (no rewrite needed).

### Step 3 — Rewrite (if FAIL)
Writer rewrites, targeting the specific failures. **One rewrite only** — if it still fails after the rewrite, STOP and write `coordination/QUESTIONS.md`.

## Anti-patterns to catch in CoV
- A single bare carbon number returned as the answer (must be a range).
- `"% accuracy"` or `"% confidence"` in any output string.
- `is_planned = False` for an HTI or HA route.
- VM0048 cited for a foregone-harvest baseline.
- LLM call outside `narrative/` module.
- Hardcoded config values that should come from `CarbonGates` or `EUDRConfig`.
