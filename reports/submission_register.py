"""Private Excel projection of the saved Carbon/EUDR intake registry.

The styled template is authored with Artifact Tool. Production fills its three
tables with standard-library OOXML, preserving the template's Excel styles.
User text is always an inline string, never a spreadsheet formula.
"""
from __future__ import annotations

import io
import json
import math
import re
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from engines.carbon.engine import _MAX_CREDITING_YR

TEMPLATE = Path(__file__).parent / "templates" / "submission_register.xlsx"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", NS)
TAG = lambda name: f"{{{NS}}}{name}"
_INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _geometry_rows(reference: str, geometry: dict[str, Any], plot_id: str):
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if kind == "FeatureCollection":
        for index, feature in enumerate(geometry.get("features", []), 1):
            props = feature.get("properties") or {}
            name = str(props.get("plot_id") or props.get("id") or feature.get("id") or index)
            yield from _geometry_rows(reference, feature.get("geometry") or {}, name)
        return
    if kind == "Feature":
        yield from _geometry_rows(reference, geometry.get("geometry") or {}, plot_id)
        return
    if kind == "GeometryCollection":
        for index, child in enumerate(geometry.get("geometries", []), 1):
            yield from _geometry_rows(reference, child, f"{plot_id}.{index}")
        return
    if kind == "Point":
        parts = [[[coords]]]
    elif kind in ("MultiPoint", "LineString"):
        parts = [[coords]]
    elif kind in ("Polygon", "MultiLineString"):
        parts = [coords]
    elif kind == "MultiPolygon":
        parts = coords
    else:
        return
    for part, rings in enumerate(parts, 1):
        for ring, points in enumerate(rings, 1):
            for vertex, point in enumerate(points, 1):
                if len(point) >= 2:
                    yield [reference, plot_id, kind, part, ring, vertex,
                           _number(point[0]), _number(point[1]),
                           _number(point[2]) if len(point) > 2 else None]


def register_tables(records: list[dict[str, Any]]) -> list[list[list[Any]]]:
    """One submission row per saved reference, newest first on all three tabs."""
    submissions, coordinates, answers = [], [], []
    # Equal-second records are supplied in descending database rowid order.
    records = sorted(records, key=lambda r: r["created_at"], reverse=True)
    for row in records:
        ref = row["reference"]
        form = json.loads(row["form_json"])
        result = json.loads(row["result_json"])
        carbon = row["application"] == "carbon"
        overlay = (result.get("map") or {}).get("loss_overlay") or {}
        low = _number(overlay.get("quantity_low_tco2e", result.get("quantity_low_tco2e"))) if carbon else None
        high = _number(overlay.get("quantity_high_tco2e", result.get("quantity_high_tco2e"))) if carbon else None
        if low is None or high is None or low < 0 or high < low:
            low = high = None
        plots = result.get("plots") or []
        areas = [_number(p.get("area_ha")) for p in plots]
        losses = [_number(p.get("loss_after_2020_ha")) for p in plots]
        area = _number(overlay.get("area_ha", result.get("area_ha"))) if carbon else (
            sum(v for v in areas if v is not None)
            if areas and all(v is not None for v in areas) else None
        )
        loss = (sum(v for v in losses if v is not None)
                if losses and all(v is not None for v in losses) else None)
        name = row["contact_name"]
        submissions.append([
            ref, _date(row["created_at"]), row["application"].upper(), row["status"],
            result.get("verdict", "") if carbon else result.get("overall", ""),
            low, high,
            _number(overlay.get("quantity_low_per_yr_tco2e")) if low is not None else None,
            _number(overlay.get("quantity_high_per_yr_tco2e")) if high is not None else None,
            _MAX_CREDITING_YR if low is not None else None,
            "Estimate only; issuance not verified" if carbon else "Not applicable",
            name, row["contact_email"], row["contact_mobile"], row["company"],
            form.get("iup_name", ""), form.get("iup_address", ""), form.get("permit_type", ""),
            form.get("permit_years_remaining"), form.get("project_type", "") if carbon else form.get("commodity", ""),
            area, result.get("plot_count") if not carbon else None, loss,
            overlay.get("verra_family", "") if carbon else result.get("datasets_version", ""),
            _date(row["retention_due_at"]), row["source_route"],
            "SYNTHETIC TEST" if name.upper().startswith("SYNTHETIC") else "User submission",
            result.get("summary", "") if carbon else result.get("overall_headline", ""),
        ])
        for key, value in form.items():
            answers.append([ref, row["application"].upper(), key,
                            json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])
        if row.get("geometry_geojson"):
            geometry = json.loads(row["geometry_geojson"])
            coordinates.extend(_geometry_rows(ref, geometry, "1"))
    return [submissions, coordinates, answers]


def _column(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _cell(address: str, value: Any, style: str | None) -> ET.Element:
    attrs = {"r": address}
    if style:
        attrs["s"] = style
    cell = ET.Element(TAG("c"), attrs)
    if value is None:
        return cell
    if isinstance(value, datetime):
        value = (value.astimezone(timezone.utc).replace(tzinfo=None) - datetime(1899, 12, 30)).total_seconds() / 86400
    if isinstance(value, bool):
        cell.set("t", "b")
        ET.SubElement(cell, TAG("v")).text = "1" if value else "0"
    elif isinstance(value, (int, float)) and math.isfinite(value):
        cell.set("t", "n")
        ET.SubElement(cell, TAG("v")).text = str(value)
    else:
        cell.set("t", "inlineStr")
        text = _INVALID_XML.sub("", str(value))
        # Refuse an overlong field rather than silently truncating its contents.
        if len(text) > 32767:
            raise ValueError("Register field exceeds Excel's text-cell limit")
        t = ET.SubElement(ET.SubElement(cell, TAG("is")), TAG("t"))
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = text
    return cell


def build_register(records: list[dict[str, Any]]) -> bytes:
    tables = register_tables(records)
    result = io.BytesIO()
    with zipfile.ZipFile(TEMPLATE) as source, zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            data = source.read(name)
            match = re.fullmatch(r"xl/worksheets/sheet([123])\.xml", name)
            table_match = re.fullmatch(r"xl/tables/table([123])\.xml", name)
            if match:
                index = int(match[1]) - 1
                rows = tables[index]
                xml = ET.fromstring(data)
                sheet_data = xml.find(TAG("sheetData"))
                assert sheet_data is not None
                old_rows = list(sheet_data)
                header = deepcopy(old_rows[0])
                prototype = old_rows[1] if len(old_rows) > 1 else ET.Element(TAG("row"))
                styles = {re.sub(r"\d+$", "", c.get("r", "")): c.get("s") for c in prototype}
                sheet_data.clear()
                sheet_data.append(header)
                width = len(header)
                for number, values in enumerate(rows, 2):
                    line_count = max((math.ceil(len(str(v)) / (110 if index == 2 else 45)) for v in values if isinstance(v, str)), default=1)
                    attrs = {"r": str(number), "ht": str(min(409, max(30, line_count * 13))), "customHeight": "1"}
                    new_row = ET.SubElement(sheet_data, TAG("row"), attrs)
                    for col, value in enumerate(values, 1):
                        letter = _column(col)
                        new_row.append(_cell(f"{letter}{number}", value, styles.get(letter)))
                dimension = xml.find(TAG("dimension"))
                if dimension is not None:
                    dimension.set("ref", f"A1:{_column(width)}{max(2,len(rows)+1)}")
                data = ET.tostring(xml, encoding="utf-8", xml_declaration=True)
            elif table_match:
                index = int(table_match[1]) - 1
                xml = ET.fromstring(data)
                end_col = xml.get("ref", "A1:A2").split(":")[1].rstrip("0123456789")
                ref = f"A1:{end_col}{max(2,len(tables[index])+1)}"
                xml.set("ref", ref)
                auto_filter = xml.find(TAG("autoFilter"))
                if auto_filter is not None:
                    auto_filter.set("ref", ref)
                data = ET.tostring(xml, encoding="utf-8", xml_declaration=True)
            target.writestr(name, data)
    return result.getvalue()
