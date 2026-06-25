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


def test_sea_buffer_absorbs_coastal_rounding(tmp_path: Path) -> None:
    """A near-shore point counts as on land with a buffer, but a pelagic one does not."""
    import json

    from taxonguard_core.data.naturalearth import land_geojson_path

    land = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]],
                },
            }
        ],
    }
    path = land_geojson_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(land))

    frame = pd.DataFrame(
        {
            "decimal_latitude": [50.5, 50.5, 50.5],
            "decimal_longitude": [0.5, 1.03, 6.0],  # inside, ~3 km offshore, far out
        }
    )
    no_buffer = add_land_sea_flag(frame, data_dir=tmp_path)["on_land"].tolist()
    buffered = add_land_sea_flag(frame, data_dir=tmp_path, sea_buffer_deg=0.05)["on_land"].tolist()
    assert no_buffer == [True, False, False]
    # The coastal point flips to on-land; the pelagic point stays off-land.
    assert buffered == [True, True, False]
