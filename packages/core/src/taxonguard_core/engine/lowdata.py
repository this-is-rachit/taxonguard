"""Low-data fallback: reduce confidence when a taxon has too few records.

An environmental niche model needs a reasonable number of records to be
trustworthy. For a sparsely recorded taxon the model is unreliable, so the engine
should lean on the deterministic checks and report lower confidence rather than
trusting the climate score. This module turns the count of climate-scoreable
records into a confidence value in 0..1 that the fusion step applies to the
environmental signal only; the deterministic checks keep full strength.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .environment import SCORED_COLUMN

# Below this many scored records the niche model is treated as unreliable and the
# environmental signal is switched off. At or above the full threshold it is
# trusted completely; in between, confidence ramps linearly.
DEFAULT_LOW_THRESHOLD = 30
DEFAULT_FULL_THRESHOLD = 100


@dataclass(frozen=True)
class LowDataAssessment:
    """The data-sufficiency verdict for one taxon."""

    n_records: int
    n_scored: int
    is_low_data: bool
    confidence: float


def assess_low_data(
    frame: pd.DataFrame,
    *,
    low_threshold: int = DEFAULT_LOW_THRESHOLD,
    full_threshold: int = DEFAULT_FULL_THRESHOLD,
) -> LowDataAssessment:
    """Assess whether a scored frame has enough data to trust the niche model.

    Counts records that carry an environmental score (env_scored True) and maps
    that count to a confidence in 0..1: zero at or below low_threshold, one at or
    above full_threshold, ramping linearly between. Requires the env_scored
    column produced by the environmental model.
    """
    if SCORED_COLUMN not in frame.columns:
        raise KeyError(
            f"frame is missing the {SCORED_COLUMN!r} column; "
            "run the environmental model before assessing low data"
        )
    if full_threshold <= low_threshold:
        raise ValueError("full_threshold must be greater than low_threshold")

    n_records = len(frame)
    n_scored = int(frame[SCORED_COLUMN].fillna(False).sum())

    span = full_threshold - low_threshold
    confidence = (n_scored - low_threshold) / span
    confidence = max(0.0, min(1.0, confidence))

    return LowDataAssessment(
        n_records=n_records,
        n_scored=n_scored,
        is_low_data=n_scored < low_threshold,
        confidence=confidence,
    )
