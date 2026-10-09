"""Read public raster data for a synthetic test plot; does not submit a lead."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.contracts import Boundary
from core.data.gfw import GFWHTTPAdapter
from core.overlays.jrc_gfc2020 import query_jrc_gfc2020
from core.overlays.hansen_loss import query_hansen_loss
from api.site import dataset_health

# Synthetic QA geometry; no claim of ownership or supplier identity.
plot = Boundary(geojson={"type": "Polygon", "coordinates": [[[113.121111, -1.121111], [113.141111, -1.121111], [113.141111, -1.141111], [113.121111, -1.141111], [113.121111, -1.121111]]]}, area_ha=494, centroid_lat=-1.131111, centroid_lon=113.131111, is_valid=True, within_indonesia=True, source_fmt="geojson")

for name, call in (("health", dataset_health), ("jrc", lambda: query_jrc_gfc2020(plot).__dict__), ("hansen", lambda: query_hansen_loss(plot).__dict__), ("carbon", lambda: GFWHTTPAdapter().query(plot).model_dump())):
    started = time.monotonic()
    print(json.dumps({"check": name, "result": call(), "seconds": round(time.monotonic() - started, 2)}), flush=True)
