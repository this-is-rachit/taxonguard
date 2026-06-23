from __future__ import annotations

import pandas as pd
import pytest

from taxonguard_core.engine.environment import SCORED_COLUMN
from taxonguard_core.engine.lowdata import assess_low_data


def _scored_frame(n_scored: int, n_unscored: int = 0) -> pd.DataFrame:
    flags = [True] * n_scored + [False] * n_unscored
    return pd.DataFrame(
        {
            "gbif_id": list(range(1, len(flags) + 1)),
            SCORED_COLUMN: pd.array(flags, dtype="boolean"),
        }
    )


def test_low_data_below_threshold() -> None:
    assessment = assess_low_data(_scored_frame(10), low_threshold=30, full_threshold=100)
    assert assessment.is_low_data
    assert assessment.confidence == 0.0
    assert assessment.n_scored == 10


def test_full_confidence_above_threshold() -> None:
    assessment = assess_low_data(_scored_frame(150), low_threshold=30, full_threshold=100)
    assert not assessment.is_low_data
    assert assessment.confidence == 1.0


def test_confidence_ramps_linearly() -> None:
    # Midpoint between 30 and 100 is 65 -> confidence 0.5.
    assessment = assess_low_data(_scored_frame(65), low_threshold=30, full_threshold=100)
    assert assessment.confidence == pytest.approx(0.5)


def test_counts_only_scored_records() -> None:
    assessment = assess_low_data(_scored_frame(40, n_unscored=60))
    assert assessment.n_records == 100
    assert assessment.n_scored == 40


def test_missing_scored_column_raises() -> None:
    with pytest.raises(KeyError):
        assess_low_data(pd.DataFrame({"gbif_id": [1, 2]}))


def test_bad_thresholds_raise() -> None:
    with pytest.raises(ValueError):
        assess_low_data(_scored_frame(10), low_threshold=100, full_threshold=100)
