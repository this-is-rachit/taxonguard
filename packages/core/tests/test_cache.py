from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import rasterio
from rasterio.transform import from_origin

from taxonguard_core.data.cache import (
    cache_path,
    cache_taxon,
    load_cached,
    metadata_path,
)
from taxonguard_core.data.naturalearth import land_geojson_path
from taxonguard_core.data.worldclim import bio_raster_path

_RAW: list[dict[str, Any]] = [
    {
        "key": 1,
        "scientificName": "Test species",
        "decimalLatitude": 1.5,
        "decimalLongitude": 0.5,
        "year": 2010,
        "basisOfRecord": "HUMAN_OBSERVATION",
        "countryCode": "XX",
    },
    {
        "key": 2,
        "scientificName": "Test species",
        "decimalLatitude": 0.5,
        "decimalLongitude": 1.5,
        "year": 2011,
        "basisOfRecord": "HUMAN_OBSERVATION",
        "countryCode": "XX",
    },
]


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/species/match"):
        return httpx.Response(200, json={"usageKey": 1, "matchType": "EXACT"})
    if request.url.path.endswith("/occurrence/search"):
        offset = int(request.url.params.get("offset", "0"))
        if offset == 0:
            return httpx.Response(200, json={"results": _RAW, "endOfRecords": True})
        return httpx.Response(200, json={"results": [], "endOfRecords": True})
    return httpx.Response(404, json={})


def _write_fixtures(data_dir: Path) -> None:
    # bio_1 raster: 2x2 grid, lon 0..2, lat 0..2, top-left origin.
    bio1 = bio_raster_path(1, data_dir)
    bio1.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(0.0, 2.0, 1.0, 1.0)
    data = np.array([[110.0, 120.0], [130.0, 20.0]], dtype="float32")
    with rasterio.open(
        bio1,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=-3.4e38,
    ) as dst:
        dst.write(data, 1)

    # Land polygon covering the whole 0..2 square.
    land = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
                },
            }
        ],
    }
    land_path = land_geojson_path(data_dir)
    land_path.parent.mkdir(parents=True, exist_ok=True)
    land_path.write_text(json.dumps(land))


def test_cache_taxon_round_trip(tmp_path: Path) -> None:
    _write_fixtures(tmp_path)
    client = httpx.Client(transport=httpx.MockTransport(_handler))

    path = cache_taxon("Test species", data_dir=tmp_path, variables=(1,), client=client)
    assert path == cache_path("Test species", tmp_path)
    assert path.exists()
    assert metadata_path("Test species", tmp_path).exists()

    loaded = load_cached("Test species", tmp_path)
    assert loaded is not None
    assert len(loaded) == 2
    assert "bio_1" in loaded.columns
    assert "on_land" in loaded.columns
    assert bool(loaded["on_land"].all())

    meta = json.loads(metadata_path("Test species", tmp_path).read_text())
    assert meta["record_count"] == 2
    assert meta["on_land_count"] == 2
    assert meta["schema_version"] == 1


def test_cache_taxon_skips_when_present(tmp_path: Path) -> None:
    _write_fixtures(tmp_path)
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    cache_taxon("Test species", data_dir=tmp_path, variables=(1,), client=client)
    mtime = cache_path("Test species", tmp_path).stat().st_mtime_ns

    # Second call without force should not rebuild the file.
    cache_taxon("Test species", data_dir=tmp_path, variables=(1,), client=client)
    assert cache_path("Test species", tmp_path).stat().st_mtime_ns == mtime
