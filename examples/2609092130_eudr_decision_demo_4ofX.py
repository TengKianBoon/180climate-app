"""Offline EUDR decision example using this checkout's existing code and tests.

Run from a checkout with Python 3.10+:
    python examples/2609092130_eudr_decision_demo_4ofX.py
    python examples/2609092130_eudr_decision_demo_4ofX.py --json

No network calls, API keys, third-party dependencies or imports of the app.
Created for the September 2026 showcase; this is not an original build artifact.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Optional


def load_function(tree: ast.Module, name: str, namespace: dict, filename: str):
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    if node.decorator_list:
        raise ValueError(f"Unexpected decorators on {name}")
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, filename, "exec"), namespace)
    return namespace[name]


def run(repo_root: Path) -> dict:
    source = repo_root / "engines/eudr/triage.py"
    tests = repo_root / "tests/test_eudr_triage.py"
    source_bytes, test_bytes = source.read_bytes(), tests.read_bytes()
    source_tree = ast.parse(source_bytes.decode("utf-8-sig"))
    test_tree = ast.parse(test_bytes.decode("utf-8-sig"))
    namespace = {"Optional": Optional, "Detection": str}
    decide = load_function(source_tree, "_decide_detection", namespace, str(source))

    test_node = next(
        n for n in test_tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "test_decide_detection_truth_table"
    )
    decorator = test_node.decorator_list[0]
    if not isinstance(decorator, ast.Call) or len(decorator.args) < 2:
        raise ValueError("Existing truth-table test format has changed")
    cases = ast.literal_eval(decorator.args[1])
    results = []
    for forest, loss, radar, expected in cases:
        actual = decide(forest, loss, radar)
        if actual != expected:
            raise AssertionError(f"Existing case failed: {(forest, loss, radar)}: {actual} != {expected}")
        results.append({
            "forest_2020": forest, "hansen_loss_ha": loss,
            "radd_alert_after_cutoff": radar,
            "expected": expected, "actual": actual,
        })

    invariant = load_function(
        test_tree, "test_honesty_rule_never_clear_when_in_doubt", namespace, str(tests)
    )
    invariant()
    return {
        "scope": "Isolated decision function; synthetic inputs; no live integrations",
        "source": "engines/eudr/triage.py",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "tests_source_sha256": hashlib.sha256(test_bytes).hexdigest(),
        "truth_table_cases_passed": len(cases),
        "existing_invariant_passed": True,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not __debug__:
        raise SystemExit("Run without -O: the existing invariant uses assertions.")
    report = run(args.repo_root.resolve())
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print("EUDR decision example | actual checkout function | no network")
    print("Synthetic inputs; this is not a property screening or compliance determination.")
    print()
    print(f"{'Forest baseline':<17} {'Loss ha':<12} {'Radar alert':<13} Decision")
    print("-" * 66)
    for row in report["results"]:
        print(f'{str(row["forest_2020"]):<17} {str(row["hansen_loss_ha"]):<12} '
              f'{str(row["radd_alert_after_cutoff"]):<13} {row["actual"]}')
    print()
    print(f'PASS: {report["truth_table_cases_passed"]} existing truth-table cases.')
    print("PASS: existing no-false-clear invariant.")
    print("Scope: decision function only; geospatial adapters and app not executed.")


if __name__ == "__main__":
    main()

