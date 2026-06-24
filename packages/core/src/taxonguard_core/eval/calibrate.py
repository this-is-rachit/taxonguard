"""Calibrate the fusion weights against the labeled benchmark.

The six noisy-OR weights are tuned by coordinate descent: starting from the
principled defaults, each weight is swept over a bounded grid while the others
are held, the value that most improves the objective is kept, and the pass
repeats until it stops improving. The objective defaults to average precision
(area under the precision-recall curve), a threshold-independent measure of how
well the suspicion score separates planted errors from plausible records under
the benchmark's class imbalance. Calibration uses the prepared (cached) signals,
so each evaluation only re-runs the cheap fusion step.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

import numpy as np

from ..engine.fusion import FusionWeights
from .metrics import average_precision, best_f1, metrics_at
from .scoring import PreparedCase, fuse_prepared, labels_are_suspicious, suspicion_scores

# The weight fields tuned by the search, in fusion order.
WEIGHT_FIELDS: tuple[str, ...] = (
    "environmental",
    "realm_mismatch",
    "zero_coordinates",
    "equal_coordinates",
    "gridded_coordinates",
    "institution_coordinates",
)

Objective = Callable[[np.ndarray, np.ndarray], float]

DEFAULT_BOUNDS = (0.1, 0.99)
DEFAULT_GRID_STEPS = 11
DEFAULT_PASSES = 5


@dataclass(frozen=True)
class CalibrationResult:
    """The outcome of a weight search."""

    weights: FusionWeights
    objective_name: str
    objective_value: float
    baseline_weights: FusionWeights
    baseline_value: float

    @property
    def improvement(self) -> float:
        return self.objective_value - self.baseline_value


def average_precision_objective(scores: np.ndarray, is_bad: np.ndarray) -> float:
    return average_precision(scores, is_bad)


def best_f1_objective(scores: np.ndarray, is_bad: np.ndarray) -> float:
    return best_f1(scores, is_bad).f1


def f1_at_threshold_objective(threshold: float) -> Objective:
    """Objective that maximises F1 at a fixed operating threshold.

    The fusion weights set the absolute score scale, so this is what they
    genuinely affect: whether each error type clears the threshold the product
    decides at, while plausible records stay below it. Ranking objectives (AUC,
    average precision) are largely insensitive to the weights because the weights
    scale scores monotonically.
    """

    def objective(scores: np.ndarray, is_bad: np.ndarray) -> float:
        return metrics_at(scores, is_bad, threshold).f1

    return objective


def evaluate_weights(
    prepared: Sequence[PreparedCase],
    weights: FusionWeights,
    objective: Objective,
) -> float:
    """Objective value for one weight set over the prepared benchmark."""
    frame = fuse_prepared(prepared, weights)
    return objective(suspicion_scores(frame), labels_are_suspicious(frame))


def calibrate(
    prepared: Sequence[PreparedCase],
    *,
    objective: Objective = average_precision_objective,
    objective_name: str = "average_precision",
    start: FusionWeights | None = None,
    bounds: tuple[float, float] = DEFAULT_BOUNDS,
    grid_steps: int = DEFAULT_GRID_STEPS,
    passes: int = DEFAULT_PASSES,
) -> CalibrationResult:
    """Coordinate-descent search for the weights that maximise the objective.

    Deterministic: with the same prepared benchmark and parameters it always
    returns the same weights. The result records the baseline (starting) value
    so the gain from calibration is explicit.
    """
    start = start or FusionWeights()
    baseline_value = evaluate_weights(prepared, start, objective)

    grid = np.linspace(bounds[0], bounds[1], grid_steps)
    best = start
    best_value = baseline_value

    for _ in range(passes):
        improved = False
        for field_name in WEIGHT_FIELDS:
            current_best = best
            current_value = best_value
            for candidate in grid:
                trial = replace(best, **{field_name: float(candidate)})
                value = evaluate_weights(prepared, trial, objective)
                # Prefer a strict improvement; tie-break toward the smaller weight
                # so calibration does not inflate weights without cause.
                if value > current_value + 1e-12:
                    current_value = value
                    current_best = trial
            if current_best is not best:
                best = current_best
                best_value = current_value
                improved = True
        if not improved:
            break

    return CalibrationResult(
        weights=best,
        objective_name=objective_name,
        objective_value=best_value,
        baseline_weights=start,
        baseline_value=baseline_value,
    )
