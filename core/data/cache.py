"""core/data/cache.py — disk-cache wrapper for any DataAdapter.

Production cache keys include the full geometry, adapter and release, with a 24-hour TTL.
Explicit test mode uses the historical coordinate keys and committed test fixtures.

Production data is stored only beneath the ignored runtime cache directory.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
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

    def __init__(self, inner: DataAdapter, cache_dir: Path | None = None):
        self._inner = inner
        self._fixtures = os.environ.get('SCREENING_USE_TEST_FIXTURES') == 'true'
        self._dir = cache_dir or (_DEFAULT_CACHE_DIR if self._fixtures else Path(os.environ.get('SCREENING_CACHE_DIR', '.runtime/screening_cache')))
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, boundary: Boundary) -> str:
        if not self._fixtures:
            raw = json.dumps({'geometry': boundary.geojson, 'adapter': type(self._inner).__name__, 'release': '20261009-GFC2025-v1.13'}, sort_keys=True)
            return hashlib.sha256(raw.encode()).hexdigest()[:32]
        raw = (
            f"{boundary.centroid_lat:.4f},"
            f"{boundary.centroid_lon:.4f},"
            f"{boundary.area_ha:.1f}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def query(self, boundary: Boundary) -> ForestData:
        key = self._key(boundary)
        cache_file = self._dir / f"{key}.json"
        if cache_file.exists() and (self._fixtures or time.time() - cache_file.stat().st_mtime < 86400):
            return ForestData(**json.loads(cache_file.read_text(encoding="utf-8")))
        result = self._inner.query(boundary)
        if result.annual_loss_ha and not any('unavailable' in source.lower() for source in result.data_sources):
            cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result
