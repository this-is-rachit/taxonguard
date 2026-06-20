from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from taxonguard_core.data.enrich import enrich_with_climate
from taxonguard_core.data.worldclim import bio_raster_path


def _write_bio_raster(path: Path, nodata: float = -3.4e38) -> None:
    """Write a small 2x2 deg, 1-degree-cell raster covering lon 0..2, lat 0..2.

    Cell values encode their position so sampling is easy to check:
      value = round(lat) * 10 + round(lon). Bottom-left cell is set to nodata to
    represent ocean.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # 2x2 grid, 1-degree cells, top-left origin at (lon=0, lat=2).
    transform = from_origin(0.0, 2.0, 1.0, 1.0)
    data = np.array(
        [
            [11.0, 12.0],  # top row, lat ~1.5: lon 0.5 -> 11, lon 1.5 -> 12
            [nodata, 2.0],  # bottom row, lat ~0.5: lon 0.5 -> nodata, lon 1.5 -> 2
        ],
        dtype="float32",
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)


def _make_worldclim(tmp_path: Path) -> Path:
    """Create the expected bio_1 raster under a temp data dir; return data dir."""
    bio1 = bio_raster_path(1, tmp_path)
    _write_bio_raster(bio1)
    return tmp_path


def test_enrich_samples_raster_values(tmp_path: Path) -> None:
    data_dir = _make_worldclim(tmp_path)
    frame = pd.DataFrame(
        {
            "gbif_id": [1, 2],
            "decimal_longitude": [0.5, 1.5],
            "decimal_latitude": [1.5, 0.5],
        }
    )
    out = enrich_with_climate(frame, data_dir=data_dir, variables=(1,))
    assert out.loc[0, "bio_1"] == pytest.approx(11.0)
    assert out.loc[1, "bio_1"] == pytest.approx(2.0)


def test_enrich_marks_nodata_as_nan(tmp_path: Path) -> None:
    data_dir = _make_worldclim(tmp_path)
    # The bottom-left cell (lon 0.5, lat 0.5) is nodata, standing in for ocean.
    frame = pd.DataFrame({"gbif_id": [9], "decimal_longitude": [0.5], "decimal_latitude": [0.5]})
    out = enrich_with_climate(frame, data_dir=data_dir, variables=(1,))
    assert np.isnan(out.loc[0, "bio_1"])


def test_enrich_missing_raster_raises(tmp_path: Path) -> None:
    frame = pd.DataFrame({"gbif_id": [1], "decimal_longitude": [0.5], "decimal_latitude": [1.5]})
    with pytest.raises(FileNotFoundError):
        enrich_with_climate(frame, data_dir=tmp_path, variables=(1,))


def test_enrich_empty_frame_adds_columns(tmp_path: Path) -> None:
    frame = pd.DataFrame({"gbif_id": [], "decimal_longitude": [], "decimal_latitude": []})
    out = enrich_with_climate(frame, data_dir=tmp_path, variables=(1, 2))
    assert "bio_1" in out.columns
    assert "bio_2" in out.columns
    assert len(out) == 0
