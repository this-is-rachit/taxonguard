from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from taxonguard_core.data.landsea import add_land_sea_flag
from taxonguard_core.data.naturalearth import land_geojson_path

# A single land polygon covering the square lon 0..10, lat 0..10.
_LAND = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
            },
        }
    ],
}


def _write_land(data_dir: Path) -> None:
    path = land_geojson_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_LAND))


def test_add_land_sea_flag(tmp_path: Path) -> None:
    _write_land(tmp_path)
    frame = pd.DataFrame(
        {
            "gbif_id": [1, 2, 3],
            "decimal_longitude": [5.0, 50.0, 1.0],
            "decimal_latitude": [5.0, 50.0, 1.0],
        }
    )
    out = add_land_sea_flag(frame, data_dir=tmp_path)
    assert out.loc[0, "on_land"]  # inside the polygon
    assert not out.loc[1, "on_land"]  # far out in the "ocean"
    assert out.loc[2, "on_land"]  # inside the polygon


def test_add_land_sea_flag_missing_data_raises(tmp_path: Path) -> None:
    frame = pd.DataFrame({"gbif_id": [1], "decimal_longitude": [5.0], "decimal_latitude": [5.0]})
    with pytest.raises(FileNotFoundError):
        add_land_sea_flag(frame, data_dir=tmp_path)


def test_add_land_sea_flag_empty_frame(tmp_path: Path) -> None:
    _write_land(tmp_path)
    frame = pd.DataFrame({"gbif_id": [], "decimal_longitude": [], "decimal_latitude": []})
    out = add_land_sea_flag(frame, data_dir=tmp_path)
    assert "on_land" in out.columns
    assert len(out) == 0
