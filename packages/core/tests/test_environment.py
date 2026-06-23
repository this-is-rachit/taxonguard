from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from taxonguard_core.engine.environment import (
    NORM_SCORE_COLUMN,
    RAW_SCORE_COLUMN,
    SCORED_COLUMN,
    fit_environmental_model,
    score_environmental_outliers,
)

# Two climate columns keep the fixtures small and easy to reason about.
_VARIABLES = (1, 2)
_COLUMNS = ["bio_1", "bio_2"]


def _cluster_frame(seed: int = 0, n: int = 40) -> pd.DataFrame:
    """A tight climate cluster around (10, 20) plus one extreme outlier.

    The outlier (bio_1=100, bio_2=200) sits far outside the cluster, so any
    sensible environmental model must rank it as the most outlying record.
    """
    rng = np.random.default_rng(seed)
    bio_1 = np.concatenate([rng.normal(10.0, 0.5, n), [100.0]])
    bio_2 = np.concatenate([rng.normal(20.0, 0.5, n), [200.0]])
    return pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 2)),
            "decimal_longitude": np.linspace(-5.0, 5.0, n + 1),
            "decimal_latitude": np.linspace(-5.0, 5.0, n + 1),
            "bio_1": bio_1,
            "bio_2": bio_2,
        }
    )


def test_score_adds_columns_and_flags_outlier() -> None:
    frame = score_environmental_outliers(_cluster_frame(), variables=_VARIABLES)

    for column in (RAW_SCORE_COLUMN, NORM_SCORE_COLUMN, SCORED_COLUMN):
        assert column in frame.columns

    # The injected extreme point is the last row and must score highest.
    outlier_index = frame.index[-1]
    assert frame.loc[outlier_index, RAW_SCORE_COLUMN] == frame[RAW_SCORE_COLUMN].max()
    assert frame.loc[outlier_index, NORM_SCORE_COLUMN] == pytest.approx(1.0)


def test_normalized_scores_within_unit_interval() -> None:
    frame = score_environmental_outliers(_cluster_frame(), variables=_VARIABLES)
    norm = frame[NORM_SCORE_COLUMN].to_numpy(dtype="float64")
    assert np.nanmin(norm) >= 0.0
    assert np.nanmax(norm) <= 1.0


def test_scoring_is_deterministic() -> None:
    frame = _cluster_frame()
    first = score_environmental_outliers(frame, variables=_VARIABLES, random_state=7)
    second = score_environmental_outliers(frame, variables=_VARIABLES, random_state=7)
    np.testing.assert_array_equal(
        first[RAW_SCORE_COLUMN].to_numpy(dtype="float64"),
        second[RAW_SCORE_COLUMN].to_numpy(dtype="float64"),
    )


def test_scored_column_is_nullable_boolean() -> None:
    frame = score_environmental_outliers(_cluster_frame(), variables=_VARIABLES)
    assert str(frame[SCORED_COLUMN].dtype) == "boolean"
    assert bool(frame[SCORED_COLUMN].all())


def test_ocean_rows_are_left_unscored() -> None:
    # Two land rows with climate, one ocean row with NaN climate (as the WorldClim
    # enrichment produces for points off the land mask).
    frame = pd.DataFrame(
        {
            "gbif_id": [1, 2, 3],
            "decimal_longitude": [0.0, 1.0, 2.0],
            "decimal_latitude": [0.0, 1.0, 2.0],
            "bio_1": [10.0, 11.0, np.nan],
            "bio_2": [20.0, 21.0, np.nan],
        }
    )
    out = score_environmental_outliers(frame, variables=_VARIABLES)

    scored = out[SCORED_COLUMN].fillna(False).tolist()
    assert scored == [True, True, False]
    assert np.isnan(out.loc[2, RAW_SCORE_COLUMN])
    assert np.isnan(out.loc[2, NORM_SCORE_COLUMN])
    assert not np.isnan(out.loc[0, RAW_SCORE_COLUMN])


def test_empty_frame_gets_columns() -> None:
    frame = pd.DataFrame(
        {
            "gbif_id": pd.Series([], dtype="Int64"),
            "bio_1": pd.Series([], dtype="float64"),
            "bio_2": pd.Series([], dtype="float64"),
        }
    )
    out = score_environmental_outliers(frame, variables=_VARIABLES)
    assert len(out) == 0
    for column in (RAW_SCORE_COLUMN, NORM_SCORE_COLUMN, SCORED_COLUMN):
        assert column in out.columns


def test_all_ocean_frame_is_unscored_not_an_error() -> None:
    frame = pd.DataFrame(
        {
            "gbif_id": [1, 2],
            "bio_1": [np.nan, np.nan],
            "bio_2": [np.nan, np.nan],
        }
    )
    out = score_environmental_outliers(frame, variables=_VARIABLES)
    assert not bool(out[SCORED_COLUMN].fillna(False).any())
    assert out[RAW_SCORE_COLUMN].isna().all()


def test_fit_raises_without_complete_rows() -> None:
    frame = pd.DataFrame({"gbif_id": [1], "bio_1": [np.nan], "bio_2": [np.nan]})
    with pytest.raises(ValueError):
        fit_environmental_model(frame, variables=_VARIABLES)


def test_missing_climate_columns_raises() -> None:
    frame = pd.DataFrame({"gbif_id": [1, 2], "bio_1": [10.0, 11.0]})  # bio_2 absent
    with pytest.raises(KeyError):
        score_environmental_outliers(frame, variables=_VARIABLES)


def test_model_reuse_on_a_separate_frame() -> None:
    # Fit on the taxon's own cluster, then score brand-new records: a point inside
    # the niche should look normal and a far point should look outlying.
    model = fit_environmental_model(_cluster_frame(), variables=_VARIABLES)

    new = pd.DataFrame(
        {
            "gbif_id": [101, 102],
            "bio_1": [10.0, 80.0],
            "bio_2": [20.0, 160.0],
        }
    )
    scored = model.score(new)
    inside = scored.loc[0, RAW_SCORE_COLUMN]
    far = scored.loc[1, RAW_SCORE_COLUMN]
    assert far > inside
    assert bool(scored[SCORED_COLUMN].all())
