from __future__ import annotations

import pandas as pd
import pytest

from taxonguard_core.engine.effort import (
    DEFAULT_HALF_SATURATION,
    EFFORT_CELL_COLUMN,
    EFFORT_COUNT_COLUMN,
    EFFORT_WEIGHT_COLUMN,
    add_sampling_effort,
)


def _frame(lats: list[float], lons: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "gbif_id": list(range(1, len(lats) + 1)),
            "decimal_latitude": lats,
            "decimal_longitude": lons,
        }
    )


def test_dense_cell_outweighs_sparse_cell() -> None:
    # Four records in one 1-degree cell, one lone record in a far cell.
    frame = _frame(
        [10.1, 10.2, 10.3, 10.4, 80.0],
        [20.1, 20.2, 20.3, 20.4, 5.0],
    )
    out = add_sampling_effort(frame, cell_size_deg=1.0)
    dense_weight = out.loc[0, EFFORT_WEIGHT_COLUMN]
    sparse_weight = out.loc[4, EFFORT_WEIGHT_COLUMN]
    assert dense_weight > sparse_weight
    assert out.loc[0, EFFORT_COUNT_COLUMN] == 4
    assert out.loc[4, EFFORT_COUNT_COLUMN] == 1


def test_weights_are_within_unit_interval() -> None:
    out = add_sampling_effort(_frame([1.0, 1.1, 50.0], [1.0, 1.1, 50.0]))
    weights = out[EFFORT_WEIGHT_COLUMN].to_numpy(dtype="float64")
    assert (weights > 0.0).all()
    assert (weights < 1.0).all()


def test_single_record_weight_matches_formula() -> None:
    out = add_sampling_effort(_frame([5.0], [5.0]))
    expected = 1.0 / (1.0 + DEFAULT_HALF_SATURATION)
    assert out.loc[0, EFFORT_WEIGHT_COLUMN] == pytest.approx(expected)


def test_columns_and_dtypes() -> None:
    out = add_sampling_effort(_frame([1.0, 2.0], [1.0, 2.0]))
    assert str(out[EFFORT_CELL_COLUMN].dtype) == "string"
    assert str(out[EFFORT_COUNT_COLUMN].dtype) == "Int64"
    assert str(out[EFFORT_WEIGHT_COLUMN].dtype) == "float64"


def test_empty_frame_gets_columns() -> None:
    frame = pd.DataFrame(
        {
            "gbif_id": pd.Series([], dtype="Int64"),
            "decimal_latitude": pd.Series([], dtype="float64"),
            "decimal_longitude": pd.Series([], dtype="float64"),
        }
    )
    out = add_sampling_effort(frame)
    assert len(out) == 0
    for column in (EFFORT_CELL_COLUMN, EFFORT_COUNT_COLUMN, EFFORT_WEIGHT_COLUMN):
        assert column in out.columns


def test_non_positive_cell_size_raises() -> None:
    with pytest.raises(ValueError):
        add_sampling_effort(_frame([1.0], [1.0]), cell_size_deg=0.0)
