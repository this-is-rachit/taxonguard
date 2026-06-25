"""Score the benchmark, with a fast path for calibration.

The fusion weights only affect the final fusion step, not the upstream signals
(the environmental outlier score, the deterministic flags, the sampling-effort
weight, and the low-data confidence). So each case is *prepared* once -- the
upstream signals are computed and cached -- and then *fused* repeatedly with
different weights at low cost. This makes a weight search over the benchmark
practical while staying identical to the public scoring path.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..engine.deterministic import add_deterministic_flags
from ..engine.effort import DEFAULT_CELL_SIZE_DEG, add_sampling_effort
from ..engine.environment import DEFAULT_RANDOM_STATE, score_environmental_outliers
from ..engine.fusion import (
    DEFAULT_REASON_THRESHOLD,
    SUSPICION_SCORE_COLUMN,
    FusionWeights,
    fuse_signals,
)
from ..engine.lowdata import assess_low_data
from .benchmark import BENCHMARK_VARIABLES, BenchmarkCase


@dataclass
class PreparedCase:
    """A case with its upstream signals computed, ready to fuse with any weights."""

    name: str
    frame: pd.DataFrame
    confidence: float


def prepare_case(
    case: BenchmarkCase,
    *,
    variables: tuple[int, ...] = BENCHMARK_VARIABLES,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> PreparedCase:
    """Run every upstream signal for a case and cache the result.

    Returns the frame with the environmental, deterministic, and effort columns
    added (and the benchmark's label columns preserved), plus the taxon-level
    low-data confidence. Fusion is deliberately not applied here.
    """
    scored = score_environmental_outliers(
        case.frame, variables=variables, random_state=random_state
    )
    flagged = add_deterministic_flags(
        scored,
        expected_realm=case.expected_realm,
        institution_points=case.institution_points,
    )
    with_effort = add_sampling_effort(flagged, cell_size_deg=DEFAULT_CELL_SIZE_DEG)
    assessment = assess_low_data(with_effort)
    return PreparedCase(name=case.name, frame=with_effort, confidence=assessment.confidence)


def prepare_benchmark(
    cases: Sequence[BenchmarkCase],
    *,
    variables: tuple[int, ...] = BENCHMARK_VARIABLES,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> list[PreparedCase]:
    """Prepare every case once for repeated fusion."""
    return [prepare_case(case, variables=variables, random_state=random_state) for case in cases]


def fuse_prepared(
    prepared: Sequence[PreparedCase],
    weights: FusionWeights | None = None,
    *,
    reason_threshold: float = DEFAULT_REASON_THRESHOLD,
) -> pd.DataFrame:
    """Fuse every prepared case with the given weights and return one frame.

    The returned frame concatenates all cases and carries the suspicion columns
    plus the benchmark labels, ready for metrics.
    """
    frames = [
        fuse_signals(
            case.frame,
            weights=weights,
            confidence=case.confidence,
            reason_threshold=reason_threshold,
        )
        for case in prepared
    ]
    return pd.concat(frames, ignore_index=True)


def labels_are_suspicious(frame: pd.DataFrame) -> np.ndarray:
    """Boolean ground-truth array: True where the record is a planted error."""
    return (frame["label"] == "suspicious").to_numpy(dtype=bool)


def suspicion_scores(frame: pd.DataFrame) -> np.ndarray:
    """The fused suspicion score column as a float array."""
    return frame[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64")
