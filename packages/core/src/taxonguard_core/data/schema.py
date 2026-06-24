"""The tidy occurrence schema and basic validation.

The tidy frame is the contract between the data pipeline and the detection
engine. Validation at this stage is deliberately minimal: it drops records
without usable coordinates and clearly invalid coordinates, and removes
duplicates. Geometric checks such as country centroids and the null-island
point, and ecological checks, belong to the detection engine (Phase 2), not
here.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

# Tidy column name -> pandas dtype. Nullable dtypes are used so missing values
# survive without coercing integer columns to float.
TIDY_COLUMNS: dict[str, str] = {
    "gbif_id": "Int64",
    "scientific_name": "string",
    "decimal_latitude": "float64",
    "decimal_longitude": "float64",
    "year": "Int64",
    "basis_of_record": "string",
    "country_code": "string",
    "coordinate_uncertainty_m": "float64",
}

# Tidy column name -> raw GBIF field name.
_SOURCE_FIELDS: dict[str, str] = {
    "gbif_id": "key",
    "scientific_name": "scientificName",
    "decimal_latitude": "decimalLatitude",
    "decimal_longitude": "decimalLongitude",
    "year": "year",
    "basis_of_record": "basisOfRecord",
    "country_code": "countryCode",
    "coordinate_uncertainty_m": "coordinateUncertaintyInMeters",
}


def to_tidy_frame(records: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Map raw GBIF occurrence records to the tidy schema, untouched otherwise."""
    rows = [
        {tidy: record.get(source) for tidy, source in _SOURCE_FIELDS.items()} for record in records
    ]
    frame = pd.DataFrame(rows, columns=list(TIDY_COLUMNS))
    return frame.astype(TIDY_COLUMNS)


def validate(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop records without usable coordinates and duplicates.

    Removes rows with a missing latitude or longitude, rows with coordinates
    outside the valid range, and duplicate GBIF ids. Returns a new frame with a
    reset index.
    """
    out = frame.dropna(subset=["decimal_latitude", "decimal_longitude"])

    in_range = out["decimal_latitude"].between(-90.0, 90.0) & out["decimal_longitude"].between(
        -180.0, 180.0
    )
    out = out[in_range]

    out = out.dropna(subset=["gbif_id"]).drop_duplicates(subset=["gbif_id"])
    return out.reset_index(drop=True)
