"""core/forest.py — forest data query facade.

Uses the active DataAdapter (swappable per ADR-0007).
Override adapter via the CARBON_DATA_ADAPTER env var:
  'stub'     → deterministic offline stub (default in CI)
  'gfw_http' → GFW/Hansen HTTP adapter + IPCC biomass
  'cached'   → CachedAdapter wrapping gfw_http (staging/production)

The public API is unchanged: query_forest_data(boundary) → ForestData.
Callers (engine, API) never need to know which adapter is active.
"""
from __future__ import annotations
from core.contracts import Boundary, ForestData
from core.data.adapter import get_adapter
from core.data.cache import CachedAdapter


def query_forest_data(boundary: Boundary) -> ForestData:
    """Query forest + biomass data using the active adapter (cached by default)."""
    inner = get_adapter()
    cached = CachedAdapter(inner)
    return cached.query(boundary)
