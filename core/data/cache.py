"""core/data/cache.py — disk-cache wrapper for any DataAdapter.

Wraps any DataAdapter with a file-based cache keyed on (centroid_lat,
centroid_lon, area_ha). Committed fixture files in tests/fixtures/data_cache/
serve as the CI oracle — real API is never called in CI.

Cache key: SHA-256 of "lat:.4f,lon:.4f,area:.1f" → first 16 hex chars.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from core.contracts import Boundary, ForestData
from core.data.adapter import DataAdapter

_DEFAULT_CACHE_DIR = (
    Path(__file__).parent.parent.parent / "tests" / "fixtures" / "data_cache"
)


class CachedAdapter:
    """Wraps any DataAdapter with transparent file-based caching.

    On cache miss: calls the inner adapter and persists the result.
    On cache hit: deserialises from disk — no network call.
    Committed cache files make the test suite deterministic in CI.
    """

    def __init__(self, inner: DataAdapter, cache_dir: Path = _DEFAULT_CACHE_DIR):
        self._inner = inner
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, boundary: Boundary) -> str:
        raw = (
            f"{boundary.centroid_lat:.4f},"
            f"{boundary.centroid_lon:.4f},"
            f"{boundary.area_ha:.1f}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def query(self, boundary: Boundary) -> ForestData:
        key = self._key(boundary)
        cache_file = self._dir / f"{key}.json"
        if cache_file.exists():
            return ForestData(**json.loads(cache_file.read_text()))
        result = self._inner.query(boundary)
        cache_file.write_text(result.model_dump_json(indent=2))
        return result
