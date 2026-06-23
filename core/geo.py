"""core/geo.py — parse user-supplied geometry to a validated Boundary.

Supports:
  - coords: "lat,lng" or "lat lng" or "lng,lat" (auto-detected via within_indonesia check)
  - geojson: a GeoJSON dict (Polygon or Point)

Shapefile parsing is out of scope for the WO-001 slice (added in a later WO).
"""
from __future__ import annotations
import json
from typing import Union
from shapely.geometry import shape, Point, Polygon, mapping
from shapely.ops import transform
import pyproj
from core.contracts import GeoInput, Boundary


# Indonesia bounding box (rough): lon 95–141 E, lat 6 N – 11 S
_INDO_LON_MIN, _INDO_LON_MAX = 95.0, 141.0
_INDO_LAT_MIN, _INDO_LAT_MAX = -11.0, 6.0


def _within_indonesia(lon: float, lat: float) -> bool:
    return _INDO_LON_MIN <= lon <= _INDO_LON_MAX and _INDO_LAT_MIN <= lat <= _INDO_LAT_MAX


def _area_ha(geom: Union[Polygon, Point]) -> float:
    """Return area in hectares using a local UTM projection for accuracy."""
    if isinstance(geom, Point):
        return 0.0
    centroid = geom.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = "north" if centroid.y >= 0 else "south"
    utm_crs = pyproj.CRS(f"EPSG:{32600 + utm_zone if hemisphere == 'north' else 32700 + utm_zone}")
    wgs84 = pyproj.CRS("EPSG:4326")
    project = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True).transform
    projected = transform(project, geom)
    return projected.area / 10_000  # m² → ha


def _parse_coords(payload: str) -> tuple[float, float]:
    """Parse 'lat,lng' or 'lat lng' to (lon, lat). Raises ValueError on bad input."""
    payload = payload.strip().replace(",", " ")
    parts = payload.split()
    if len(parts) != 2:
        raise ValueError(
            f"Expected 'lat,lng' or 'lat lng' — got {payload!r}. "
            "Example: '-0.5,117.5' or '-0.5 117.5'"
        )
    try:
        a, b = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"Coordinates must be numbers — got {payload!r}")
    # If both could be lat/lon, prefer the ordering that puts the point in Indonesia
    if _within_indonesia(b, a):  # b=lon, a=lat
        return b, a
    if _within_indonesia(a, b):  # a=lon, b=lat
        return a, b
    # Default to treating as lat,lon
    return b, a


def parse_geo(geo: GeoInput) -> Boundary:
    """Parse a GeoInput into a validated Boundary. Raises ValueError on bad input."""
    if geo.fmt == "shapefile":
        raise ValueError(
            "Shapefile parsing is not yet implemented in this slice. "
            "Please supply coordinates or GeoJSON."
        )

    if geo.fmt == "coords":
        lon, lat = _parse_coords(geo.payload)
        # Represent a point as a small ~0 ha boundary; UI prompts for full polygon later
        geom = Point(lon, lat)
        geojson_dict = mapping(geom)
        return Boundary(
            geojson=dict(geojson_dict),
            area_ha=0.0,
            centroid_lat=lat,
            centroid_lon=lon,
            is_valid=True,
            within_indonesia=_within_indonesia(lon, lat),
            source_fmt="coords",
        )

    if geo.fmt == "geojson":
        try:
            raw = json.loads(geo.payload) if isinstance(geo.payload, str) else geo.payload
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid GeoJSON: {exc}") from exc

        # Accept a bare geometry or a Feature wrapper
        if raw.get("type") == "Feature":
            raw = raw["geometry"]

        try:
            geom = shape(raw)
        except Exception as exc:
            raise ValueError(f"Could not parse GeoJSON geometry: {exc}") from exc

        if not geom.is_valid:
            raise ValueError("GeoJSON geometry is invalid (self-intersecting or degenerate).")

        centroid = geom.centroid
        area_ha = _area_ha(geom)
        return Boundary(
            geojson=dict(mapping(geom)),
            area_ha=area_ha,
            centroid_lat=centroid.y,
            centroid_lon=centroid.x,
            is_valid=True,
            within_indonesia=_within_indonesia(centroid.x, centroid.y),
            source_fmt="geojson",
        )

    raise ValueError(f"Unsupported geo format: {geo.fmt!r}")
