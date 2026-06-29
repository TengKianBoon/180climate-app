"""engines/eudr/geometry.py — EUDR Art-9 geometry validation (E2).

Parses GeoJSON / KML / SHP files → list[PlotValidation].

Art-9 rules (EU Regulation 2023/1115):
  • Plots >4 ha must submit a polygon; a point with declared area >4 ha → geometry_invalid.
  • All coordinate values must carry ≥6 decimal places (shortest repr of the parsed float).
  • Empty / self-intersecting / unparseable geometry → geometry_invalid.
  • geometry_ok is ALWAYS derived: geometry_ok == (detection != "geometry_invalid").

Output detection per plot:
  Valid:   detection="inconclusive"    (pending satellite triage, E3)
  Invalid: detection="geometry_invalid", fix_message = FIX_MESSAGE

Deps: shapely ≥2.0, pyproj ≥3.0 (already in requirements.txt), pyshp (added).
No network calls. Deterministic.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Literal

from pyproj import Geod
from shapely.geometry import shape as _shapely_shape

_GEOD = Geod(ellps="WGS84")
_KML_NS = "http://www.opengis.net/kml/2.2"

FIX_MESSAGE = (
    "EUDR Art 9 needs a polygon for plots over 4 ha and coordinates to at least "
    "6 decimals. Fix it and we'll re-screen."
)


@dataclass
class PlotValidation:
    """Per-plot geometry validation result.

    Invariant: geometry_ok == (detection != "geometry_invalid").
    """

    plot_id: str
    geometry_ok: bool
    detection: Literal["geometry_invalid", "inconclusive"]
    area_ha: float
    geometry_type: Literal["polygon", "point", "unknown"]
    fix_message: str | None
    geojson: dict | None  # normalised GeoJSON geometry dict for E3; None if invalid

    def __post_init__(self) -> None:
        if self.geometry_ok != (self.detection != "geometry_invalid"):
            raise AssertionError(
                f"PlotValidation invariant violated for {self.plot_id!r}: "
                "geometry_ok must equal (detection != 'geometry_invalid'). "
                f"Got geometry_ok={self.geometry_ok}, detection={self.detection!r}."
            )


# ── Public API ────────────────────────────────────────────────────────────────

def parse_plots(
    content: str | bytes,
    fmt: Literal["geojson", "kml", "shapefile"],
    commodity: str = "manual_review",
) -> list[PlotValidation]:
    """Parse an uploaded geometry file and validate each plot for Art-9.

    Args:
        content: Raw file content (str for GeoJSON / KML; bytes for SHP).
        fmt:     File format.
        commodity: Commodity label (passed through for caller context; not stored here).

    Returns:
        One PlotValidation per detected plot, in input order.
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8", errors="replace")
    else:
        text = content

    if fmt == "geojson":
        return _parse_geojson(text)
    if fmt == "kml":
        return _parse_kml(text)
    if fmt == "shapefile":
        return _parse_shp(content if isinstance(content, bytes) else content.encode())
    raise ValueError(f"Unsupported format: {fmt!r}. Expected 'geojson', 'kml', or 'shapefile'.")


# ── GeoJSON ───────────────────────────────────────────────────────────────────

def _parse_geojson(content: str) -> list[PlotValidation]:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError) as exc:
        return [_invalid("plot_1", "unknown", f"GeoJSON parse error: {exc}")]

    geom_type = data.get("type", "")
    if geom_type == "FeatureCollection":
        features = data.get("features") or []
    elif geom_type == "Feature":
        features = [data]
    elif geom_type in ("Point", "Polygon", "MultiPolygon", "MultiPoint", "GeometryCollection"):
        features = [{"type": "Feature", "properties": {}, "geometry": data}]
    else:
        return [_invalid("plot_1", "unknown", f"Unrecognised GeoJSON type: {geom_type!r}")]

    results: list[PlotValidation] = []
    for i, feat in enumerate(features):
        props = feat.get("properties") or {}
        plot_id = str(
            props.get("plot_id")
            or props.get("id")
            or props.get("name")
            or f"plot_{i + 1}"
        )
        declared_ha = _float_or_zero(props.get("area_ha") or props.get("hectares"))
        geom = feat.get("geometry") or {}
        results.append(_validate_geom(plot_id, geom, declared_ha))
    return results


# ── KML ───────────────────────────────────────────────────────────────────────

def _parse_kml(content: str) -> list[PlotValidation]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        return [_invalid("plot_1", "unknown", f"KML parse error: {exc}")]

    # Support both namespaced ("<kml xmlns=...>") and bare KML
    ns = f"{{{_KML_NS}}}" if root.tag.startswith(f"{{{_KML_NS}}}") else ""

    placemarks = root.findall(f".//{ns}Placemark")
    if not placemarks:
        return [_invalid("plot_1", "unknown", "No Placemark elements found in KML.")]

    results: list[PlotValidation] = []
    for i, pm in enumerate(placemarks):
        name_el = pm.find(f".//{ns}name")
        raw_name = (name_el.text or "").strip() if name_el is not None else ""
        plot_id = raw_name if raw_name else f"plot_{i + 1}"

        declared_ha = 0.0
        ext_el = pm.find(f".//{ns}ExtendedData")
        if ext_el is not None:
            for data_el in ext_el.iter(f"{ns}Data" if ns else "Data"):
                if data_el.get("name") in ("area_ha", "hectares"):
                    val_el = data_el.find(f".//{ns}value")
                    declared_ha = _float_or_zero(val_el.text if val_el is not None else None)

        poly_el = pm.find(f".//{ns}Polygon")
        point_el = pm.find(f".//{ns}Point")

        if poly_el is not None:
            geom = _kml_polygon_to_geojson(poly_el, ns)
        elif point_el is not None:
            geom = _kml_point_to_geojson(point_el, ns)
        else:
            geom = {}

        results.append(_validate_geom(plot_id, geom, declared_ha))
    return results


def _kml_polygon_to_geojson(poly_el: ET.Element, ns: str) -> dict:
    coords_el = poly_el.find(f".//{ns}coordinates")
    if coords_el is None or not coords_el.text:
        return {}
    ring = _parse_kml_coord_string(coords_el.text)
    if not ring:
        return {}
    return {"type": "Polygon", "coordinates": [ring]}


def _kml_point_to_geojson(point_el: ET.Element, ns: str) -> dict:
    coords_el = point_el.find(f".//{ns}coordinates")
    if coords_el is None or not coords_el.text:
        return {}
    ring = _parse_kml_coord_string(coords_el.text)
    if not ring:
        return {}
    return {"type": "Point", "coordinates": ring[0]}


def _parse_kml_coord_string(text: str) -> list[list[float]]:
    """Parse KML <coordinates> text (whitespace-separated 'lon,lat[,alt]') → [[lon, lat], ...]."""
    pairs: list[list[float]] = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) < 2:
            return []
        try:
            pairs.append([float(parts[0]), float(parts[1])])
        except ValueError:
            return []
    return pairs


# ── Shapefile ─────────────────────────────────────────────────────────────────

def _parse_shp(content: bytes) -> list[PlotValidation]:
    try:
        import io
        import shapefile  # pyshp — optional light dep
    except ImportError:
        return [_invalid(
            "plot_1",
            "unknown",
            "SHP upload requires pyshp (pip install pyshp). "
            "Please convert to GeoJSON or KML and re-upload.",
        )]

    try:
        sf = shapefile.Reader(shp=io.BytesIO(content))
    except Exception as exc:
        return [_invalid("plot_1", "unknown", f"SHP read error: {exc}")]

    results: list[PlotValidation] = []
    for i, shape_rec in enumerate(sf.shapeRecords()):
        # Attributes may not be available without .dbf; fall back to auto-IDs
        try:
            field_names = [f[0].lower() for f in sf.fields[1:]]
            rec_vals = list(shape_rec.record)
            rec = dict(zip(field_names, rec_vals))
            plot_id = str(rec.get("plot_id") or rec.get("id") or rec.get("name") or f"plot_{i + 1}")
            declared_ha = _float_or_zero(rec.get("area_ha") or rec.get("hectares"))
        except Exception:
            plot_id = f"plot_{i + 1}"
            declared_ha = 0.0

        try:
            geom = shape_rec.shape.__geo_interface__
        except Exception as exc:
            results.append(_invalid(plot_id, "unknown", f"SHP geometry error: {exc}"))
            continue

        results.append(_validate_geom(plot_id, geom, declared_ha))
    return results


# ── Core Art-9 validation ─────────────────────────────────────────────────────

def _validate_geom(
    plot_id: str,
    geom: dict,
    declared_ha: float = 0.0,
) -> PlotValidation:
    """Validate one GeoJSON geometry dict per Art-9 rules."""
    geom_type = geom.get("type", "")
    coords = geom.get("coordinates")

    if not geom_type or coords is None:
        return _invalid(plot_id, "unknown", FIX_MESSAGE)

    if geom_type == "Point":
        return _validate_point(plot_id, geom, declared_ha)
    if geom_type == "Polygon":
        return _validate_polygon(plot_id, geom)
    return _invalid(
        plot_id,
        "unknown",
        f"Geometry type {geom_type!r} not supported. Submit a Polygon or Point.",
    )


def _validate_point(plot_id: str, geom: dict, declared_ha: float) -> PlotValidation:
    coords = geom["coordinates"]
    if len(coords) < 2:
        return _invalid(plot_id, "point", FIX_MESSAGE)

    lon, lat = coords[0], coords[1]
    if not _all_have_min_precision([lon, lat]):
        return _invalid(plot_id, "point", FIX_MESSAGE)

    # Art-9: points are acceptable only for plots ≤4 ha
    if declared_ha > 4.0:
        return _invalid(plot_id, "point", FIX_MESSAGE)

    return PlotValidation(
        plot_id=plot_id,
        geometry_ok=True,
        detection="inconclusive",
        area_ha=0.0,
        geometry_type="point",
        fix_message=None,
        geojson=geom,
    )


def _validate_polygon(plot_id: str, geom: dict) -> PlotValidation:
    rings = geom["coordinates"]
    if not rings or not rings[0] or len(rings[0]) < 4:
        return _invalid(plot_id, "polygon", FIX_MESSAGE)

    outer = rings[0]
    flat = [c for pt in outer for c in (pt[0], pt[1])]
    if not _all_have_min_precision(flat):
        return _invalid(plot_id, "polygon", FIX_MESSAGE)

    try:
        shp = _shapely_shape(geom)
        if not shp.is_valid:
            return _invalid(plot_id, "polygon", FIX_MESSAGE)
    except Exception:
        return _invalid(plot_id, "polygon", FIX_MESSAGE)

    area_ha = _area_ha(shp)
    return PlotValidation(
        plot_id=plot_id,
        geometry_ok=True,
        detection="inconclusive",
        area_ha=area_ha,
        geometry_type="polygon",
        fix_message=None,
        geojson=geom,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _invalid(
    plot_id: str,
    geometry_type: Literal["polygon", "point", "unknown"],
    message: str = FIX_MESSAGE,
) -> PlotValidation:
    return PlotValidation(
        plot_id=plot_id,
        geometry_ok=False,
        detection="geometry_invalid",
        area_ha=0.0,
        geometry_type=geometry_type,
        fix_message=message,
        geojson=None,
    )


def _decimal_places(val: float) -> int:
    """Count decimal places in Python's shortest round-trip repr of a float.

    repr() in Python 3.1+ uses the shortest decimal string that round-trips,
    so repr(0.123456) → '0.123456' (6 places). Scientific notation (rare for
    GPS coordinates) is treated as 0 places to be safe.
    """
    s = repr(val)
    if "e" in s or "E" in s:
        return 0
    if "." not in s:
        return 0
    return len(s.split(".")[1])


def _all_have_min_precision(values: list[float], min_places: int = 6) -> bool:
    """True iff every value has ≥min_places decimal places in its repr."""
    return all(_decimal_places(v) >= min_places for v in values)


def _area_ha(shp) -> float:  # shp: shapely geometry
    """Geodetic area in hectares (WGS84 ellipsoid via pyproj.Geod)."""
    try:
        area_m2, _ = _GEOD.geometry_area_perimeter(shp)
        return abs(area_m2) / 10_000.0
    except Exception:
        return 0.0


def _float_or_zero(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
