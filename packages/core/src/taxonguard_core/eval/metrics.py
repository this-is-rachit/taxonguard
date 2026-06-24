"""Detection metrics for the labeled benchmark.

Everything is computed from a score array and a boolean ground-truth array (True
= a planted error). The headline trade-off is caught errors (recall) against
false alarms (false positive rate and precision). Threshold-independent quality
of the ranking is summarised by ROC AUC and average precision (PR AUC). All
functions are pure NumPy so the suite runs anywhere with no extra dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class Confusion:
    """Counts at one operating threshold."""

    threshold: float
    tp: int
    fp: int
    tn: int
    fn: int


@dataclass(frozen=True)
class Metrics:
    """The standard metrics at one operating threshold."""

    threshold: float
    precision: float
    recall: float
    false_positive_rate: float
    f1: float
    accuracy: float
    tp: int
    fp: int
    tn: int
    fn: int

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def _as_arrays(scores: np.ndarray, is_bad: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    s = np.asarray(scores, dtype="float64")
    y = np.asarray(is_bad, dtype=bool)
    if s.shape != y.shape:
        raise ValueError("scores and labels must have the same shape")
    return s, y


def confusion_at(scores: np.ndarray, is_bad: np.ndarray, threshold: float) -> Confusion:
    """Confusion counts treating score >= threshold as a flag."""
    s, y = _as_arrays(scores, is_bad)
    flagged = s >= threshold
    tp = int(np.sum(flagged & y))
    fp = int(np.sum(flagged & ~y))
    tn = int(np.sum(~flagged & ~y))
    fn = int(np.sum(~flagged & y))
    return Confusion(threshold=threshold, tp=tp, fp=fp, tn=tn, fn=fn)


def metrics_at(scores: np.ndarray, is_bad: np.ndarray, threshold: float) -> Metrics:
    """Precision, recall, false positive rate, F1, and accuracy at a threshold."""
    c = confusion_at(scores, is_bad, threshold)
    precision = c.tp / (c.tp + c.fp) if (c.tp + c.fp) else 0.0
    recall = c.tp / (c.tp + c.fn) if (c.tp + c.fn) else 0.0
    fpr = c.fp / (c.fp + c.tn) if (c.fp + c.tn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (c.tp + c.tn) / (c.tp + c.fp + c.tn + c.fn) if len(np.asarray(scores)) else 0.0
    return Metrics(
        threshold=threshold,
        precision=precision,
        recall=recall,
        false_positive_rate=fpr,
        f1=f1,
        accuracy=accuracy,
        tp=c.tp,
        fp=c.fp,
        tn=c.tn,
        fn=c.fn,
    )


def candidate_thresholds(scores: np.ndarray) -> np.ndarray:
    """Sorted unique thresholds that can change the confusion counts.

    The midpoints between adjacent unique scores, plus endpoints just below the
    minimum and just above the maximum, so the sweep spans every distinct
    flag/no-flag partition.
    """
    s = np.unique(np.asarray(scores, dtype="float64"))
    if s.size == 0:
        return np.array([0.0])
    if s.size == 1:
        return np.array([s[0] - 1e-9, s[0] + 1e-9])
    mids = (s[:-1] + s[1:]) / 2.0
    return np.concatenate(([s[0] - 1e-9], mids, [s[-1] + 1e-9]))


def sweep(scores: np.ndarray, is_bad: np.ndarray) -> list[Metrics]:
    """Metrics at every distinct operating threshold, low threshold first."""
    return [metrics_at(scores, is_bad, float(t)) for t in candidate_thresholds(scores)]


def roc_curve(scores: np.ndarray, is_bad: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (false_positive_rate, true_positive_rate) for the ROC curve.

    Built the standard way: sort by descending score and accumulate true and
    false positives, emitting one point per distinct score and prepending the
    origin. The arrays are monotonic non-decreasing and run from (0, 0) to
    (1, 1).
    """
    s, y = _as_arrays(scores, is_bad)
    positives = int(y.sum())
    negatives = int((~y).sum())
    if positives == 0 or negatives == 0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0])
    order = np.argsort(-s, kind="stable")
    s_sorted = s[order]
    y_sorted = y[order]
    tps = np.cumsum(y_sorted.astype("float64"))
    fps = np.cumsum((~y_sorted).astype("float64"))
    distinct = np.where(np.diff(s_sorted) != 0.0)[0]
    idx = np.concatenate([distinct, [s_sorted.size - 1]])
    tpr = np.concatenate([[0.0], tps[idx] / positives])
    fpr = np.concatenate([[0.0], fps[idx] / negatives])
    return fpr, tpr


def roc_auc(scores: np.ndarray, is_bad: np.ndarray) -> float:
    """Area under the ROC curve (1.0 is perfect ranking, 0.5 is chance)."""
    _, y = _as_arrays(scores, is_bad)
    if not y.any() or y.all():
        return float("nan")
    fpr, tpr = roc_curve(scores, is_bad)
    return float(np.trapezoid(tpr, fpr))


def average_precision(scores: np.ndarray, is_bad: np.ndarray) -> float:
    """Average precision: the precision-weighted sum of recall increments.

    Walks thresholds from strict to permissive (so recall is non-decreasing) and
    adds the recall gain at each step times the precision at that step, which is
    the standard definition of the area under the precision-recall curve.
    """
    ap = 0.0
    prev_recall = 0.0
    for m in reversed(sweep(scores, is_bad)):
        if m.recall > prev_recall:
            ap += (m.recall - prev_recall) * m.precision
            prev_recall = m.recall
    return float(ap)


def best_f1(scores: np.ndarray, is_bad: np.ndarray) -> Metrics:
    """The operating point with the highest F1 over the threshold sweep."""
    return max(sweep(scores, is_bad), key=lambda m: (m.f1, m.recall))


def recall_at_max_fpr(scores: np.ndarray, is_bad: np.ndarray, max_fpr: float) -> Metrics:
    """The highest-recall operating point whose false positive rate is within a cap.

    The most product-relevant operating point: catch as many errors as possible
    while keeping false alarms on plausible records under ``max_fpr``.
    """
    feasible = [m for m in sweep(scores, is_bad) if m.false_positive_rate <= max_fpr]
    if not feasible:
        # No threshold meets the cap; fall back to the strictest point.
        return max(sweep(scores, is_bad), key=lambda m: -m.false_positive_rate)
    return max(feasible, key=lambda m: (m.recall, -m.false_positive_rate))
