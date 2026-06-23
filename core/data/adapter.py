"""core/data/adapter.py — DataAdapter Protocol + adapter registry (ADR-0007).

Swap implementations via the CARBON_DATA_ADAPTER env var:
  'stub'     → deterministic offline stub (CI default)
  'gfw_http' → GFW/Hansen HTTP adapter with IPCC biomass values
  'cached'   → wraps gfw_http with disk cache (use in production staging)

Any class satisfying DataAdapter can be registered and swapped without
touching core/contracts/ or the engine.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from core.contracts import Boundary, ForestData

_registry: dict[str, type] = {}


def register(name: str):
    """Decorator: register an adapter class under a short key."""
    def dec(cls):
        _registry[name] = cls
        return cls
    return dec


@runtime_checkable
class DataAdapter(Protocol):
    """Swappable interface for forest + biomass data (ADR-0007).

    Implement this Protocol to plug in GFW, GEE, paid hi-res, local fixtures,
    or any future data source without touching contracts or the engine.
    """
    def query(self, boundary: Boundary) -> ForestData: ...


def get_adapter(name: str | None = None) -> DataAdapter:
    """Return the active DataAdapter.

    Resolution order:
    1. Explicit ``name`` argument (tests / dependency injection)
    2. CARBON_DATA_ADAPTER environment variable
    3. Auto: GFWHTTPAdapter (tries real HTTP; falls back to stub internally)
    """
    import os
    key = name or os.environ.get("CARBON_DATA_ADAPTER", "auto")
    if key in _registry:
        return _registry[key]()
    # auto — lazy import to avoid circular dependencies at module load time
    from core.data.gfw import GFWHTTPAdapter
    return GFWHTTPAdapter()
