# Skill: golden-case

Golden-case fixture format and assertion patterns for 180climate-app tests.

## Format
Each golden case is a JSON file in `tests/fixtures/`:
```
tests/fixtures/<engine>/<case-name>.json
```

Structure:
```json
{
  "description": "one-line description of what this case tests",
  "input": { ... },
  "expected": { ... },
  "invariants": {
    "deterministic": true,
    "no_single_carbon_number": true,
    "methodology_route": "APD"
  }
}
```

## Required invariant checks (every carbon golden case)
1. `quantity_low_tco2e < quantity_high_tco2e` — always a range, never equal.
2. `methodology.is_planned == True` for HTI and HA.
3. `methodology.additionality_basis == "legal harvest right foregone"` for HTI and HA.
4. No `"% accuracy"` or `"% confidence"` string anywhere in narrative output.
5. Same input → same output on two consecutive runs (determinism).

## Required invariant checks (every EUDR golden case)
1. `overall` is one of `"compliant"`, `"non_compliant"`, `"needs_review"`.
2. `dds_pack` is a valid GeoJSON FeatureCollection.
3. `applicable_deadline` matches config (not hardcoded in engine logic).

## Pytest pattern
```python
import json, pytest
from pathlib import Path

FIXTURES = list((Path("tests/fixtures/carbon")).glob("*.json"))

@pytest.mark.parametrize("fixture_path", FIXTURES)
def test_golden_case(fixture_path):
    case = json.loads(fixture_path.read_text())
    # run engine with case["input"], assert against case["expected"]
```
