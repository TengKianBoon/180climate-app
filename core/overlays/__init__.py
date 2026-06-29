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
from core.overlays.klhk_plantation import query_klhk_plantation, PlantationOriginResult
# EUDR triage adapters (ADR-0018, E3)
from core.overlays.jrc_gfc2020 import query_jrc_gfc2020, JRCGFC2020Result
from core.overlays.hansen_loss import query_hansen_loss, HansenLossResult
from core.overlays.radd import query_radd, RADDResult

__all__ = [
    "query_khg",
    "query_pippib",
    "query_worldcover",
    "WorldCoverResult",
    "query_jrc_tmf",
    "JRCTMFResult",
    "query_klhk_plantation",
    "PlantationOriginResult",
    # EUDR triage adapters (ADR-0018, E3)
    "query_jrc_gfc2020",
    "JRCGFC2020Result",
    "query_hansen_loss",
    "HansenLossResult",
    "query_radd",
    "RADDResult",
]
