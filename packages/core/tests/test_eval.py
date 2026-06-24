"""Tests for the Phase 7 evaluation harness (benchmark, metrics, calibration).

The assertions are deliberately robust to small numerical differences between
library versions: the benchmark's separation is large, so detection is asserted
with margin rather than on exact scores. The benchmark construction itself is
pure NumPy and so is exact and deterministic.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
import pytest

from taxonguard_core.engine.fusion import FusionWeights
from taxonguard_core.eval.benchmark import (
    DEFAULT_ERRORS_PER_TYPE,
    benchmark_label_counts,
    build_benchmark,
)
from taxonguard_core.eval.calibrate import calibrate, f1_at_threshold_objective
from taxonguard_core.eval.metrics import (
    average_precision,
    best_f1,
    confusion_at,
    metrics_at,
    recall_at_max_fpr,
    roc_auc,
    sweep,
)
from taxonguard_core.eval.scoring import (
    PreparedCase,
    fuse_prepared,
    labels_are_suspicious,
    prepare_benchmark,
    suspicion_scores,
)

ERROR_TYPES = ("ocean", "null_island", "equal", "gridded", "institution", "climate")
OPERATING = 0.5


@lru_cache(maxsize=1)
def _prepared() -> tuple[PreparedCase, ...]:
    return tuple(prepare_benchmark(build_benchmark(0)))


# --- benchmark ------------------------------------------------------------


def test_benchmark_label_counts_are_as_designed() -> None:
    cases = build_benchmark(0)
    counts = benchmark_label_counts(cases)
    # 3 niches; per niche: plausible + sampled population, then 5 deterministic
    # error types and 1 climate type, each planted DEFAULT_ERRORS_PER_TYPE times.
    expected_suspicious = 3 * 6 * DEFAULT_ERRORS_PER_TYPE
    assert counts["suspicious"] == expected_suspicious
    assert counts["plausible"] + counts["suspicious"] == counts["total"]


def test_benchmark_is_deterministic() -> None:
    first = build_benchmark(0)[0].frame
    second = build_benchmark(0)[0].frame
    pd.testing.assert_frame_equal(first, second)


def test_each_error_type_is_caught_with_margin() -> None:
    frame = fuse_prepared(_prepared(), FusionWeights())
    scores = suspicion_scores(frame)
    # A low threshold with comfortable margin below every planted error, so the
    # check is robust across library versions.
    flagged = scores >= 0.3
    for kind in ERROR_TYPES:
        mask = (frame["error_type"] == kind).to_numpy(dtype=bool)
        caught = int(np.sum(flagged & mask))
        assert caught == int(mask.sum()), f"{kind} not fully caught"


def test_plausible_records_stay_well_below_threshold() -> None:
    frame = fuse_prepared(_prepared(), FusionWeights())
    plausible = frame.loc[frame["label"] == "plausible", "suspicion_score"]
    assert float(plausible.max()) < OPERATING


# --- metrics --------------------------------------------------------------


def test_confusion_and_metrics_on_known_arrays() -> None:
    scores = np.array([0.9, 0.8, 0.2, 0.1])
    is_bad = np.array([True, False, True, False])
    c = confusion_at(scores, is_bad, 0.5)
    assert (c.tp, c.fp, c.tn, c.fn) == (1, 1, 1, 1)
    m = metrics_at(scores, is_bad, 0.5)
    assert m.precision == pytest.approx(0.5)
    assert m.recall == pytest.approx(0.5)
    assert m.false_positive_rate == pytest.approx(0.5)
    assert m.f1 == pytest.approx(0.5)


def test_roc_auc_is_one_for_separable_and_zero_for_reversed() -> None:
    scores = np.array([0.9, 0.8, 0.2, 0.1])
    is_bad = np.array([True, True, False, False])
    assert roc_auc(scores, is_bad) == pytest.approx(1.0)
    assert roc_auc(scores, ~is_bad) == pytest.approx(0.0)


def test_average_precision_is_one_when_all_positives_rank_first() -> None:
    scores = np.array([0.9, 0.8, 0.2, 0.1])
    is_bad = np.array([True, True, False, False])
    assert average_precision(scores, is_bad) == pytest.approx(1.0)


def test_best_f1_finds_the_perfect_split() -> None:
    scores = np.array([0.9, 0.8, 0.2, 0.1])
    is_bad = np.array([True, True, False, False])
    best = best_f1(scores, is_bad)
    assert best.f1 == pytest.approx(1.0)


def test_recall_at_max_fpr_respects_the_cap() -> None:
    frame = fuse_prepared(_prepared(), FusionWeights())
    scores = suspicion_scores(frame)
    y = labels_are_suspicious(frame)
    result = recall_at_max_fpr(scores, y, 0.01)
    assert result.false_positive_rate <= 0.01 + 1e-9
    assert result.recall > 0.5


def test_sweep_spans_from_all_flagged_to_none_flagged() -> None:
    scores = np.array([0.1, 0.4, 0.6, 0.9])
    is_bad = np.array([False, False, True, True])
    points = sweep(scores, is_bad)
    recalls = [m.recall for m in points]
    assert max(recalls) == pytest.approx(1.0)
    assert min(m.false_positive_rate for m in points) == pytest.approx(0.0)


# --- calibration ----------------------------------------------------------


def test_calibration_improves_recall_at_the_operating_threshold() -> None:
    prepared = _prepared()
    start = FusionWeights(environmental=0.8)
    starting = metrics_at(
        suspicion_scores(fuse_prepared(prepared, start)),
        labels_are_suspicious(fuse_prepared(prepared, start)),
        OPERATING,
    )
    result = calibrate(
        prepared,
        objective=f1_at_threshold_objective(OPERATING),
        start=start,
        grid_steps=11,
    )
    calibrated_frame = fuse_prepared(prepared, result.weights)
    calibrated = metrics_at(
        suspicion_scores(calibrated_frame), labels_are_suspicious(calibrated_frame), OPERATING
    )
    # Calibration never makes the objective worse, raises the environmental
    # weight, and recovers at least as many errors at the threshold.
    assert result.improvement >= 0.0
    assert result.weights.environmental >= start.environmental
    assert calibrated.recall >= starting.recall


def test_calibration_is_deterministic() -> None:
    prepared = _prepared()
    objective = f1_at_threshold_objective(OPERATING)
    first = calibrate(prepared, objective=objective, grid_steps=11)
    second = calibrate(prepared, objective=objective, grid_steps=11)
    assert vars(first.weights) == vars(second.weights)
    assert first.objective_value == pytest.approx(second.objective_value)
