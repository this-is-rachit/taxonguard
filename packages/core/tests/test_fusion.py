from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from taxonguard_core.engine.deterministic import REALM_MISMATCH, ZERO_COORDINATES
from taxonguard_core.engine.effort import EFFORT_WEIGHT_COLUMN
from taxonguard_core.engine.environment import NORM_SCORE_COLUMN, SCORED_COLUMN
from taxonguard_core.engine.fusion import (
    ENVIRONMENTAL_REASON,
    SUSPICION_CONFIDENCE_COLUMN,
    SUSPICION_REASONS_COLUMN,
    SUSPICION_SCORE_COLUMN,
    FusionWeights,
    fuse_signals,
    score_occurrences,
)


def _signal_frame() -> pd.DataFrame:
    """A small frame carrying the columns fuse_signals expects.

    Row 0: clean. Row 1: strong environmental outlier in a well-sampled cell.
    Row 2: a deterministic realm mismatch with no environmental score.
    """
    frame = pd.DataFrame(
        {
            "gbif_id": [1, 2, 3],
            NORM_SCORE_COLUMN: [0.1, 0.95, np.nan],
            SCORED_COLUMN: pd.array([True, True, False], dtype="boolean"),
            EFFORT_WEIGHT_COLUMN: [0.9, 0.9, 0.5],
            f"det_{REALM_MISMATCH}": pd.array([False, False, True], dtype="boolean"),
            f"det_{ZERO_COORDINATES}": pd.array([False, False, False], dtype="boolean"),
            "det_equal_coordinates": pd.array([False, False, False], dtype="boolean"),
            "det_gridded_coordinates": pd.array([False, False, False], dtype="boolean"),
            "det_institution_coordinates": pd.array([False, False, False], dtype="boolean"),
            "det_reasons": pd.array(["", "", REALM_MISMATCH], dtype="string"),
        }
    )
    return frame


def test_suspicion_scores_are_within_unit_interval() -> None:
    out = fuse_signals(_signal_frame())
    scores = out[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64")
    assert (scores >= 0.0).all()
    assert (scores <= 1.0).all()


def test_clean_record_scores_low_outlier_scores_high() -> None:
    out = fuse_signals(_signal_frame())
    assert out.loc[0, SUSPICION_SCORE_COLUMN] < out.loc[1, SUSPICION_SCORE_COLUMN]


def test_deterministic_flag_drives_score_and_reason() -> None:
    out = fuse_signals(_signal_frame())
    weights = FusionWeights()
    # Row 2 fires only the realm mismatch, so its score equals that weight.
    assert out.loc[2, SUSPICION_SCORE_COLUMN] == pytest.approx(weights.realm_mismatch)
    assert REALM_MISMATCH in out.loc[2, SUSPICION_REASONS_COLUMN]


def test_environmental_reason_named_for_high_outliers() -> None:
    out = fuse_signals(_signal_frame(), reason_threshold=0.7)
    assert ENVIRONMENTAL_REASON in out.loc[1, SUSPICION_REASONS_COLUMN]
    assert out.loc[0, SUSPICION_REASONS_COLUMN] == ""  # 0.1 is below threshold


def test_confidence_is_full_for_deterministic_low_for_environmental() -> None:
    out = fuse_signals(_signal_frame(), confidence=0.5)
    # Row 2 fires a deterministic flag -> full confidence.
    assert out.loc[2, SUSPICION_CONFIDENCE_COLUMN] == pytest.approx(1.0)
    # Row 1 is environmental only -> effort_weight * confidence.
    assert out.loc[1, SUSPICION_CONFIDENCE_COLUMN] == pytest.approx(0.9 * 0.5)


def test_low_data_confidence_shrinks_environmental_score() -> None:
    full = fuse_signals(_signal_frame(), confidence=1.0)
    low = fuse_signals(_signal_frame(), confidence=0.2)
    assert low.loc[1, SUSPICION_SCORE_COLUMN] < full.loc[1, SUSPICION_SCORE_COLUMN]
    # The deterministic row is unaffected by the low-data confidence.
    assert low.loc[2, SUSPICION_SCORE_COLUMN] == pytest.approx(full.loc[2, SUSPICION_SCORE_COLUMN])


def _cached_like_frame() -> pd.DataFrame:
    """A cached-style frame for two bio variables, with one injected ocean error."""
    rng = np.random.default_rng(0)
    n = 60
    bio_1 = np.r_[rng.normal(10.0, 0.5, n), [90.0]]
    bio_2 = np.r_[rng.normal(20.0, 0.5, n), [180.0]]
    on_land = [True] * n + [False]  # the injected record is in the sea
    return pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 2)),
            "scientific_name": ["Test species"] * (n + 1),
            "decimal_latitude": np.r_[rng.uniform(40, 50, n), [3.0]],
            "decimal_longitude": np.r_[rng.uniform(0, 10, n), [-40.0]],
            "bio_1": bio_1,
            "bio_2": bio_2,
            "on_land": pd.array(on_land, dtype="boolean"),
        }
    )


def test_score_occurrences_end_to_end() -> None:
    frame = _cached_like_frame()
    out = score_occurrences(frame, expected_realm="terrestrial", variables=(1, 2))

    for column in (
        SUSPICION_SCORE_COLUMN,
        SUSPICION_REASONS_COLUMN,
        SUSPICION_CONFIDENCE_COLUMN,
    ):
        assert column in out.columns

    scores = out[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64")
    assert (scores >= 0.0).all()
    assert (scores <= 1.0).all()

    # The injected ocean record (climate outlier and realm mismatch) must be the
    # single most suspicious record.
    assert int(out[SUSPICION_SCORE_COLUMN].idxmax()) == out.index[-1]
    assert REALM_MISMATCH in out.loc[out.index[-1], SUSPICION_REASONS_COLUMN]


def test_score_occurrences_is_deterministic() -> None:
    frame = _cached_like_frame()
    first = score_occurrences(frame, expected_realm="terrestrial", variables=(1, 2))
    second = score_occurrences(frame, expected_realm="terrestrial", variables=(1, 2))
    np.testing.assert_array_equal(
        first[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64"),
        second[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64"),
    )
