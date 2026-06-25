"""Split a labeled benchmark into a calibration fold and a held-out report fold.

Calibrating the fusion weights and reporting metrics on the same records makes the
at-threshold numbers optimistic: the weights are tuned to clear exactly those
records. (Ranking metrics such as ROC-AUC and average precision are scale
invariant to the weights and so are not affected, but the operating-threshold
recall is.) A record-level split removes that optimism: the weights are calibrated
on one fold and every metric is reported on the other, untouched fold.

The split is stratified by label and error type so each fold holds a
representative mix of plausible records and of every planted error type, and it is
deterministic given a seed. It operates on a prepared frame (the upstream signals
already computed), so the two folds can be fused with any weights at no cost.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .scoring import PreparedCase

# Columns that define a stratum. Records are split within each (label, error_type)
# group so both folds carry the same composition.
DEFAULT_STRATA: tuple[str, ...] = ("label", "error_type")

DEFAULT_HOLDOUT_FRAC = 0.5


def stratified_split(
    frame: pd.DataFrame,
    *,
    holdout_frac: float = DEFAULT_HOLDOUT_FRAC,
    seed: int = 0,
    strata: Sequence[str] = DEFAULT_STRATA,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a frame into (calibration, held-out) folds, stratified and seeded.

    Within each stratum the rows are shuffled deterministically and the first
    ``holdout_frac`` go to the held-out fold, the rest to calibration. At least one
    row from a stratum of size two or more is always kept in each fold, so no error
    type vanishes from a fold. Returns two frames with reset indices.
    """
    if not 0.0 < holdout_frac < 1.0:
        raise ValueError("holdout_frac must be strictly between 0 and 1")

    present = [column for column in strata if column in frame.columns]
    if not present:
        raise KeyError(f"frame has none of the strata columns {tuple(strata)}")

    rng = np.random.default_rng(seed)
    holdout_parts: list[pd.DataFrame] = []
    calib_parts: list[pd.DataFrame] = []

    for _, group in frame.groupby(list(present), sort=True, dropna=False):
        order = rng.permutation(len(group))
        shuffled = group.iloc[order]
        n_holdout = int(round(len(shuffled) * holdout_frac))
        # Keep both folds non-empty when the stratum has at least two members.
        if len(shuffled) >= 2:
            n_holdout = min(max(n_holdout, 1), len(shuffled) - 1)
        holdout_parts.append(shuffled.iloc[:n_holdout])
        calib_parts.append(shuffled.iloc[n_holdout:])

    calib = pd.concat(calib_parts, ignore_index=True) if calib_parts else frame.iloc[:0].copy()
    holdout = (
        pd.concat(holdout_parts, ignore_index=True) if holdout_parts else frame.iloc[:0].copy()
    )
    return calib, holdout


def split_prepared(
    case: PreparedCase,
    *,
    holdout_frac: float = DEFAULT_HOLDOUT_FRAC,
    seed: int = 0,
    strata: Sequence[str] = DEFAULT_STRATA,
) -> tuple[PreparedCase, PreparedCase]:
    """Split one prepared case's records into calibration and held-out cases.

    The taxon-level confidence is the same scalar in both folds, since it reflects
    the taxon's data sufficiency rather than the fold. Returns two PreparedCases
    ready to fuse and score.
    """
    calib_frame, holdout_frame = stratified_split(
        case.frame, holdout_frac=holdout_frac, seed=seed, strata=strata
    )
    calib = PreparedCase(name=f"{case.name}:calib", frame=calib_frame, confidence=case.confidence)
    holdout = PreparedCase(
        name=f"{case.name}:holdout", frame=holdout_frame, confidence=case.confidence
    )
    return calib, holdout
