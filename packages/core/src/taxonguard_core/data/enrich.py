"""Enrich occurrence records with WorldClim climate values.

For each record, the 19 bioclimatic variables are sampled from the rasters at the
record's coordinate and added as columns bio_1 to bio_19. Points with no land
data (for example a terrestrial record that falls in the ocean) get NaN, which is
itself a useful signal for the detection engine.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from .worldclim import BIO_VARIABLES, bio_raster_path

# WorldClim ocean and missing cells use a large negative sentinel. Anything below
# this threshold is treated as no data.
_NODATA_THRESHOLD = -1e30


def _sample(path: str, coordinates: list[tuple[float, float]]) -> np.ndarray:
    """Sample a single-band raster at (lon, lat) coordinates, nodata -> NaN."""
    with rasterio.open(path) as src:
        nodata = src.nodata
        values = np.array([record[0] for record in src.sample(coordinates)], dtype="float64")
    if nodata is not None:
        values = np.where(values == nodata, np.nan, values)
    return np.where(values < _NODATA_THRESHOLD, np.nan, values)


def enrich_with_climate(
    frame: pd.DataFrame,
    *,
    data_dir: Path | None = None,
    variables: tuple[int, ...] = BIO_VARIABLES,
) -> pd.DataFrame:
    """Add bio_1 to bio_19 columns sampled from WorldClim rasters.

    Raises FileNotFoundError if the rasters have not been downloaded. The
    coordinate columns decimal_longitude and decimal_latitude must be present.
    """
    out = frame.copy()

    if out.empty:
        for variable in variables:
            out[f"bio_{variable}"] = pd.Series(dtype="float64")
        return out

    coordinates = list(zip(out["decimal_longitude"], out["decimal_latitude"], strict=True))

    for variable in variables:
        path = bio_raster_path(variable, data_dir)
        if not path.exists():
            raise FileNotFoundError(
                f"WorldClim raster not found: {path}. Download it first with: "
                "uv run python -m taxonguard_core.data.worldclim --download"
            )
        out[f"bio_{variable}"] = _sample(str(path), coordinates)

    return out
