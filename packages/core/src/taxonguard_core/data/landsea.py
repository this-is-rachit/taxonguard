"""Flag whether each occurrence falls on land or in the sea.

A point-in-polygon test against the Natural Earth land polygons adds a boolean
on_land column. Combined later with a taxon's expected realm, this turns "a
terrestrial animal recorded in the open ocean" into an explicit, testable flag.
The test itself only records geography; it makes no judgement about a species.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely import STRtree
from shapely.geometry import shape

from .naturalearth import land_geojson_path


def _load_land_geometries(path: Path) -> list[shapely.Geometry]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return [shape(feature["geometry"]) for feature in data["features"]]


def add_land_sea_flag(
    frame: pd.DataFrame, *, data_dir: Path | None = None, sea_buffer_deg: float = 0.0
) -> pd.DataFrame:
    """Add a boolean on_land column. True if the point is on land.

    ``sea_buffer_deg`` widens "on land" to include points within that many degrees
    of the coast, so coordinates that fall just offshore through rounding (river
    mouths, tidal flats, the resolution of the coastline) are not misread as the
    open ocean. With the default 0.0 the test is an exact point-in-polygon, as
    before; the real-data pipeline passes a small buffer (about 5 km) so the realm
    check flags only genuinely pelagic points.

    Raises FileNotFoundError if the Natural Earth data has not been downloaded.
    """
    out = frame.copy()

    if out.empty:
        out["on_land"] = pd.array([], dtype="boolean")
        return out

    path = land_geojson_path(data_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"Natural Earth land data not found: {path}. Download it first with: "
            "uv run python -m taxonguard_core.data.naturalearth --download"
        )

    geometries = _load_land_geometries(path)
    tree = STRtree(geometries)
    points = shapely.points(
        out["decimal_longitude"].to_numpy(dtype="float64"),
        out["decimal_latitude"].to_numpy(dtype="float64"),
    )

    on_land = np.zeros(len(points), dtype=bool)
    if sea_buffer_deg > 0.0:
        hits = tree.query(points, predicate="dwithin", distance=sea_buffer_deg)
    else:
        hits = tree.query(points, predicate="intersects")
    if hits.size:
        on_land[np.unique(hits[0])] = True

    out["on_land"] = pd.array(on_land, dtype="boolean")
    return out
