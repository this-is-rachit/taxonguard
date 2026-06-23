"""Sampling-effort correction: down-weight outliers in sparsely sampled areas.

An outlier flag is less trustworthy where few records exist, because sparse data
can look anomalous without being wrong. This module measures local sampling
effort with a simple geographic grid over a taxon's records and turns it into a
per-record weight in 0..1: low where a cell holds few records, high where a cell
is well sampled. The fusion step multiplies the environmental outlier signal by
this weight, so that sparse is not treated as wrong.

The grid uses the taxon's own records as an effort proxy. A fuller measure would
count all GBIF records of any species per cell, from a full download; that is a
documented future enhancement and would not change this interface.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EFFORT_CELL_COLUMN = "effort_cell"
EFFORT_COUNT_COLUMN = "effort_count"
EFFORT_WEIGHT_COLUMN = "effort_weight"

# Grid cell size in degrees. One degree is a reasonable default at global scale.
DEFAULT_CELL_SIZE_DEG = 1.0

# Record count at which a cell reaches an effort weight of 0.5. Larger values
# demand more records before a cell is treated as well sampled.
DEFAULT_HALF_SATURATION = 5.0


def add_sampling_effort(
    frame: pd.DataFrame,
    *,
    cell_size_deg: float = DEFAULT_CELL_SIZE_DEG,
    half_saturation: float = DEFAULT_HALF_SATURATION,
) -> pd.DataFrame:
    """Return a copy of frame with sampling-effort columns added.

    Adds effort_cell (the grid cell id), effort_count (records in that cell), and
    effort_weight (count / (count + half_saturation), in 0..1). Coordinate
    columns must be present. An empty frame gets the columns with no rows.
    """
    if cell_size_deg <= 0.0:
        raise ValueError("cell_size_deg must be positive")

    out = frame.copy()
    for column in ("decimal_latitude", "decimal_longitude"):
        if column not in out.columns:
            raise KeyError(f"frame is missing coordinate column: {column!r}")

    if out.empty:
        out[EFFORT_CELL_COLUMN] = pd.Series([], dtype="string")
        out[EFFORT_COUNT_COLUMN] = pd.Series([], dtype="Int64")
        out[EFFORT_WEIGHT_COLUMN] = pd.Series([], dtype="float64")
        return out

    latitude = out["decimal_latitude"].to_numpy(dtype="float64")
    longitude = out["decimal_longitude"].to_numpy(dtype="float64")
    ix = np.floor(longitude / cell_size_deg).astype("int64")
    iy = np.floor(latitude / cell_size_deg).astype("int64")
    cell_ids = [f"{x}_{y}" for x, y in zip(ix, iy, strict=True)]

    out[EFFORT_CELL_COLUMN] = pd.Series(cell_ids, index=out.index, dtype="string")
    counts = out.groupby(EFFORT_CELL_COLUMN)[EFFORT_CELL_COLUMN].transform("size")
    count_values = counts.to_numpy(dtype="float64")

    out[EFFORT_COUNT_COLUMN] = pd.Series(
        count_values.astype("int64"), index=out.index, dtype="Int64"
    )
    weight = count_values / (count_values + half_saturation)
    out[EFFORT_WEIGHT_COLUMN] = pd.Series(weight, index=out.index, dtype="float64")
    return out
