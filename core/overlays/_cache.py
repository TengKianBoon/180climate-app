"""core/overlays/_cache.py — Fixture-based cache for overlay adapters.

Cache key: f"{adapter_name}_{lat:.3f}_{lon:.3f}.json"
Resolution: 0.001° (~100 m) — same KHG/PIPPIB polygon applies across nearby points.
Fixture directory: tests/fixtures/overlays/ (committed; CI-safe).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

_FIXTURE_DIR = (
    Path(__file__).parent.parent.parent / "tests" / "fixtures" / "overlays"
)


def load_fixture(adapter_name: str, lat: float, lon: float) -> Optional[dict]:
    """Return the cached overlay dict, or None if no fixture exists."""
    fname = f"{adapter_name}_{lat:.3f}_{lon:.3f}.json"
    path = _FIXTURE_DIR / fname
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None
