"""core/overlays — Swappable spatial overlay adapters (ADR-0013).

Public API:
    query_khg(boundary)      -> OverlayIntersection  (Overlay A: KHG fungsi lindung)
    query_pippib(boundary)   -> OverlayIntersection  (Overlay B: PIPPIB moratorium)
    query_worldcover(boundary) -> WorldCoverResult
    query_jrc_tmf(boundary)  -> JRCTMFResult

All adapters are cached for offline CI via JSON fixtures in
tests/fixtures/overlays/{adapter}_{lat:.3f}_{lon:.3f}.json.
Real-data URLs are set via env vars KHG_URL, PIPPIB_URL, WORLDCOVER_TILE_URL,
JRC_TMF_URL — absent in CI, the fixture (or safe default) is used.
"""
from core.overlays.khg import query_khg
from core.overlays.pippib import query_pippib
from core.overlays.worldcover import query_worldcover, WorldCoverResult
from core.overlays.jrc_tmf import query_jrc_tmf, JRCTMFResult

__all__ = [
    "query_khg",
    "query_pippib",
    "query_worldcover",
    "WorldCoverResult",
    "query_jrc_tmf",
    "JRCTMFResult",
]
