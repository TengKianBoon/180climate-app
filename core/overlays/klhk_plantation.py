"""core/overlays/klhk_plantation.py — KLHK Penutupan Lahan plantation detector (ADR-0015-C1).

Source: KLHK (Kementerian Lingkungan Hidup dan Kehutanan) official land-cover maps.
Purpose: Forest-origin gate — distinguish hutan tanaman (established plantation) from
         hutan alam (natural forest) before any APD/IFM carbon number is computed.

ADR-0015 decision:
  - Primary discriminator: KLHK Penutupan Lahan (administrative ground truth; the user
    already declares the permit type = HTI, so KLHK provides the land-cover class).
  - Secondary: JRC TMF / Hansen rotational-harvest temporal pattern (~5–7 yr clear-and-replant
    return interval; natural forest is NOT stand-replaced on a 5–7 yr grid).
  - ESA WorldCover explicitly DEMOTED — cannot distinguish Acacia plantation from dipterocarp
    natural forest at the required resolution.
  - Oil-palm maps (e.g. Descals) not applicable — HTI is timber, not palm.

  Established plantation → FLAG: "no standing natural forest at risk — not an APD/IFM candidate;
    rotational-harvest loss is not avoidable deforestation."
  Natural → APD (HTI) or IFM (HA) as appropriate.
  Mixed → stratify: plantation area excluded; natural-forest baseline loss-rate must mask
    plantation rotational-harvest pixels.
  Unknown → proceed with caveat (KLHK data unavailable; advisor-confirm required pre-submission).

Pre-launch backlog: real KLHK Penutupan Lahan API / shapefile integration (parallel to KHG/PIPPIB).
Env var KLHK_PLANTATION_URL: REST endpoint for live query (unset → CI fixture only).
CI uses fixture cache: tests/fixtures/overlays/klhk_plantation_{lat:.3f}_{lon:.3f}.json.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Literal
from core.contracts import Boundary
from core.overlays._cache import load_fixture

_ADAPTER = "klhk_plantation"
_SOURCE = "KLHK Penutupan Lahan (official land-cover classification map, KLHK/MENLHK)"

_ORIGIN_LABELS: dict[str, str] = {
    "natural": "Hutan alam (natural forest) — eligible APD/IFM candidate",
    "plantation": (
        "Hutan tanaman (established plantation) — NOT an APD/IFM candidate; "
        "rotational-harvest loss is not avoidable deforestation (ADR-0015-C1)"
    ),
    "mixed": "Mixed natural + plantation — stratification required (plantation area excluded)",
    "unknown": (
        "Forest origin undetermined — KLHK Penutupan Lahan data unavailable; "
        "advisor-confirm required before any crediting claim"
    ),
}


@dataclass
class PlantationOriginResult:
    """Forest-origin classification from KLHK Penutupan Lahan maps (ADR-0015-C1)."""
    forest_origin: Literal["natural", "plantation", "mixed", "unknown"]
    source: str = _SOURCE
    note: str = ""

    @property
    def label(self) -> str:
        return _ORIGIN_LABELS.get(self.forest_origin, "Unknown")


_UNKNOWN = PlantationOriginResult(
    forest_origin="unknown",
    source=_SOURCE,
    note=(
        "KLHK Penutupan Lahan data unavailable; forest origin undetermined (ADR-0015-C1). "
        "Engine proceeds; advisor-confirm required before any crediting claim."
    ),
)


def query_klhk_plantation(boundary: Boundary) -> PlantationOriginResult:
    """Return forest-origin classification for the boundary from KLHK Penutupan Lahan maps.

    Load from CI fixture cache if available.
    Fall back to live API query if KLHK_PLANTATION_URL is set.
    Return _UNKNOWN (forest_origin="unknown") when data is unavailable — engine
    flags with a caveat note but does NOT hard-block (restoration/natural-forest
    distinction requires field confirmation).
    """
    lat = boundary.centroid_lat
    lon = boundary.centroid_lon

    cached = load_fixture(_ADAPTER, lat, lon)
    if cached is not None:
        return PlantationOriginResult(
            forest_origin=cached.get("forest_origin", "unknown"),
            source=_SOURCE,
            note=cached.get("note", ""),
        )

    url = os.environ.get("KLHK_PLANTATION_URL")
    if url:
        return _query_live(boundary, url)

    return _UNKNOWN


def _query_live(boundary: Boundary, url: str) -> PlantationOriginResult:
    """Placeholder for live KLHK Penutupan Lahan API/WFS query — pre-launch backlog."""
    return PlantationOriginResult(
        forest_origin="unknown",
        source=_SOURCE,
        note=f"KLHK Penutupan Lahan live query not yet implemented (url={url!r})",
    )
