"""Independent checks between valid uploaded boundaries; no satellite or legal verdict."""
from pyproj import Geod
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

_GEOD = Geod(ellps="WGS84")


def _area_ha(geometry) -> float:
    if geometry.geom_type == "Polygon":
        return abs(_GEOD.geometry_area_perimeter(orient(geometry, sign=1.0))[0]) / 10000
    if hasattr(geometry, "geoms"):
        return sum(_area_ha(part) for part in geometry.geoms)
    return 0.0


def boundary_overlaps(validations) -> dict:
    polygons = [(i, v, shape(v.geojson)) for i, v in enumerate(validations)
                if v.geometry_ok and v.geojson and v.geometry_type == "polygon"]
    unassessed = [v.plot_id for v in validations
                  if not v.geometry_ok or not v.geojson or v.geometry_type != "polygon"]
    pairs = []
    shapes = [entry[2] for entry in polygons]
    if shapes:
        tree = STRtree(shapes)
        for i, (index_a, a, geom) in enumerate(polygons):
            for candidate in sorted(tree.query(geom)):
                j = int(candidate)
                if j <= i:
                    continue
                index_b, b, other = polygons[j]
                intersection = geom.intersection(other)
                # Shared borders and points have no overlapping interior area.
                if intersection.area <= 0:
                    continue
                area = _area_ha(intersection)
                if area <= 0.000001:  # ignore numerical slivers below 0.01 m²
                    continue
                pairs.append({"plot_a": a.plot_id, "plot_b": b.plot_id,
                              "index_a": index_a, "index_b": index_b,
                              "overlap_ha": round(area, 8)})
    return {"pairs": pairs, "unassessed_plot_ids": unassessed,
            "scope": "Overlapping interiors among valid polygons in this upload only. "
                     "Shared borders are allowed. Points, invalid shapes, ownership and other submissions are not assessed."}


def format_area(area_ha: float) -> str:
    if area_ha <= 0:
        return "area unavailable"
    if area_ha < 0.01:
        return f"{area_ha * 10000:,.2f} m²"
    return f"{area_ha:,.2f} ha"
