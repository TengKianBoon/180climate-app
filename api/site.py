"""Public methodology, crawl metadata and satellite-source health."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html import escape
import os
import ssl
from pathlib import Path
import time
from threading import Lock

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from core.data.gfw import GFWHTTPAdapter, _HANSEN_BASE
from core.overlays import jrc_gfc2020, hansen_loss

router = APIRouter()
_cached: tuple[float, dict] | None = None
_lock = Lock()
_PUBLIC_HOSTS = {"carbon.180climate.net", "eudr.180climate.net"}


def _public_origin(request: Request) -> str:
    host = request.url.hostname or ""
    return "https://" + (host if host in _PUBLIC_HOSTS else "eudr.180climate.net")


def _probe(item: tuple[str, str]) -> tuple[str, dict]:
    name, url = item
    try:
        response = httpx.head(url, timeout=12, follow_redirects=True, verify=ssl.create_default_context())
        return name, {"available": response.status_code == 200,
                      "http_status": response.status_code}
    except httpx.HTTPError as exc:
        return name, {"available": False, "error": type(exc).__name__}


def dataset_health() -> dict:
    global _cached
    with _lock:
        if _cached and time.monotonic() - _cached[0] < 60:
            return _cached[1]
        version = hansen_loss._version()
        tile = "00N_110E"  # public Indonesia coverage tile; no user plot is transmitted
        urls = {
            "jrc_gfc2020": jrc_gfc2020._jrc_url(-1, 113),
            "eudr_lossyear": f"{hansen_loss._HANSEN_BUCKET}/{version}/Hansen_{version}_lossyear_{tile}.tif",
            "carbon_lossyear": GFWHTTPAdapter()._hansen_url(-1, 113),
            "carbon_treecover2000": f"{_HANSEN_BASE}/Hansen_GFC-2025-v1.13_treecover2000_{tile}.tif",
        }
        with ThreadPoolExecutor(max_workers=4) as pool:
            checks = dict(pool.map(_probe, urls.items()))
        for dataset, disabled_key in (("jrc_gfc2020", "JRC_GFC2020_DISABLE_LIVE"), ("eudr_lossyear", "HANSEN_LOSS_DISABLE_LIVE")):
            if os.environ.get(disabled_key) == "true":
                checks[dataset]["available"] = False
                checks[dataset]["error"] = "Live read disabled"
        try:
            hansen_loss._last_loss_year(version)
        except ValueError:
            checks["eudr_lossyear"]["available"] = False
            checks["eudr_lossyear"]["error"] = "Outdated or invalid release"
        warnings = []
        if not os.environ.get("RADD_API_KEY") or os.environ.get("RADD_DISABLE_LIVE") == "true":
            warnings.append("RADD radar enrichment unavailable; results rely on JRC and Hansen.")
        if os.environ.get("SCREENING_USE_TEST_FIXTURES") == "true":
            warnings.append("Test fixtures enabled: unsuitable for production screening.")
        healthy = all(c["available"] for c in checks.values()) and os.environ.get("SCREENING_USE_TEST_FIXTURES") != "true"
        payload = {
            "status": "ok" if healthy else "degraded",
            "checks": checks, "warnings": warnings,
            "scope": "HTTP source reachability; plot coverage and pixel reads are checked on each screening.",
            "datasets": {"jrc": jrc_gfc2020.version_label(urls["jrc_gfc2020"]), "eudr_hansen": version, "carbon_hansen": "GFC-2025-v1.13"},
            "release": os.environ.get("RENDER_GIT_COMMIT", "local"),
        }
        _cached = (time.monotonic(), payload)
        return payload


@router.get("/health/data", operation_id="getDataHealth", tags=["discovery"])
def health_data() -> JSONResponse:
    payload = dataset_health()
    return JSONResponse(payload, status_code=200 if payload["status"] == "ok" else 503,
                        headers={"Cache-Control": "no-store"})


@router.get("/methodology", response_class=HTMLResponse, include_in_schema=False)
def methodology() -> HTMLResponse:
    return HTMLResponse((Path(__file__).resolve().parents[1] / "frontend/methodology.html").read_text(encoding="utf-8"))


@router.get("/robots.txt", include_in_schema=False)
def robots(request: Request) -> Response:
    origin = _public_origin(request)
    return Response("User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /fieldwork/status\nDisallow: /fieldwork/operator\n"
                    f"Sitemap: {origin}/sitemap.xml\n", media_type="text/plain")


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request) -> Response:
    origin = escape(_public_origin(request))
    urls = "".join(f"<url><loc>{origin}{path}</loc></url>" for path in ("/", "/methodology", "/fieldwork"))
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', media_type="application/xml")
