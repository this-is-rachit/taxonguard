"""Score fusion: combine every signal into one suspicion score with reasons.

The engine produces several signals: a graded environmental outlier score (an
isolation forest on climate), several deterministic coordinate flags, a local
sampling-effort weight, and a taxon-level low-data confidence. This module fuses
them into a single suspicion score in 0..1 with a transparent per-signal reason
breakdown and a per-record confidence.

The signals combine with a noisy-OR: each contributes an independent probability
that the record is suspicious, and the suspicion score is the probability that at
least one signal is right. The environmental signal is scaled down by sampling
effort and by low-data confidence, so a climate outlier in a sparsely sampled or
poorly recorded setting contributes little. The deterministic flags keep full
strength, because a record on null island or a land animal in the open ocean is
implausible regardless of how much data exists.

The environmental weight below is calibrated against a labeled evaluation
benchmark (see :mod:`taxonguard_core.eval` and docs/evaluation.md); on the
synthetic benchmark calibration raises it from a starting 0.8 to 0.93, which
recovers borderline climate outliers at the operating threshold without adding
false alarms. The deterministic rule confidences are fixed domain priors and are
not fit to the benchmark: each expresses how strongly a rule indicates an error
(an open-ocean freshwater record is strongly implausible regardless of dataset),
and fitting them to a small, imbalanced set would let any rule that fires on a few
real records be zeroed to chase precision. Only the environmental weight is
re-derived per dataset.

Score a cached taxon and print its most suspicious records:

    uv run python -m taxonguard_core.engine.fusion "Vulpes lagopus" --top 15
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.cache import load_cached
from ..data.worldclim import BIO_VARIABLES
from ..taxa import Realm
from .deterministic import (
    DET_REASONS_COLUMN,
    EQUAL_COORDINATES,
    GRIDDED_COORDINATES,
    INSTITUTION_COORDINATES,
    REALM_MISMATCH,
    ZERO_COORDINATES,
    add_deterministic_flags,
    realm_for,
)
from .effort import EFFORT_WEIGHT_COLUMN, add_sampling_effort
from .environment import (
    DEFAULT_RANDOM_STATE,
    NORM_SCORE_COLUMN,
    SCORED_COLUMN,
    score_environmental_outliers,
)
from .lowdata import DEFAULT_FULL_THRESHOLD, DEFAULT_LOW_THRESHOLD, assess_low_data

SUSPICION_SCORE_COLUMN = "suspicion_score"
SUSPICION_REASONS_COLUMN = "suspicion_reasons"
SUSPICION_CONFIDENCE_COLUMN = "suspicion_confidence"

ENVIRONMENTAL_REASON = "environmental_outlier"

# Normalized environmental score at or above which the environmental reason is
# named in the breakdown. The score is relative to the taxon, so this picks the
# clearly high outliers.
DEFAULT_REASON_THRESHOLD = 0.7


@dataclass(frozen=True)
class FusionWeights:
    """Per-signal probabilities used by the noisy-OR fusion.

    Each value is the probability of suspicion that the signal contributes at
    full strength. The defaults were calibrated against the labeled benchmark in
    :mod:`taxonguard_core.eval` (see docs/evaluation.md); the environmental
    weight is the one calibration moved (from 0.8 to 0.93).
    """

    environmental: float = 0.93
    realm_mismatch: float = 0.9
    zero_coordinates: float = 0.9
    equal_coordinates: float = 0.5
    gridded_coordinates: float = 0.5
    institution_coordinates: float = 0.7

    def deterministic_items(self) -> list[tuple[str, float]]:
        """Reason code to weight, in breakdown order."""
        return [
            (REALM_MISMATCH, self.realm_mismatch),
            (ZERO_COORDINATES, self.zero_coordinates),
            (EQUAL_COORDINATES, self.equal_coordinates),
            (GRIDDED_COORDINATES, self.gridded_coordinates),
            (INSTITUTION_COORDINATES, self.institution_coordinates),
        ]


def fuse_signals(
    frame: pd.DataFrame,
    *,
    weights: FusionWeights | None = None,
    confidence: float = 1.0,
    reason_threshold: float = DEFAULT_REASON_THRESHOLD,
) -> pd.DataFrame:
    """Return a copy of frame with the fused suspicion columns added.

    Expects the environmental columns (from the environmental model), the
    deterministic flag columns (from the deterministic checks), and the effort
    weight column (from the sampling-effort step). The confidence argument is the
    taxon-level low-data confidence applied to the environmental signal. Adds
    suspicion_score (0..1), suspicion_reasons (a comma separated breakdown), and
    suspicion_confidence (per record, 0..1).
    """
    weights = weights or FusionWeights()
    out = frame.copy()
    count = len(out)

    normalized = (
        out[NORM_SCORE_COLUMN].fillna(0.0).to_numpy(dtype="float64")
        if NORM_SCORE_COLUMN in out.columns
        else np.zeros(count, dtype="float64")
    )
    scored = (
        out[SCORED_COLUMN].fillna(False).to_numpy(dtype=bool)
        if SCORED_COLUMN in out.columns
        else np.zeros(count, dtype=bool)
    )
    effort = (
        out[EFFORT_WEIGHT_COLUMN].fillna(1.0).to_numpy(dtype="float64")
        if EFFORT_WEIGHT_COLUMN in out.columns
        else np.ones(count, dtype="float64")
    )

    p_env = weights.environmental * normalized * effort * float(confidence)

    keep = 1.0 - p_env
    any_deterministic = np.zeros(count, dtype=bool)
    flag_masks: dict[str, np.ndarray] = {}
    for code, weight in weights.deterministic_items():
        column = f"det_{code}"
        mask = (
            out[column].fillna(False).to_numpy(dtype=bool)
            if column in out.columns
            else np.zeros(count, dtype=bool)
        )
        flag_masks[code] = mask
        any_deterministic |= mask
        keep = keep * np.where(mask, 1.0 - weight, 1.0)

    suspicion = 1.0 - keep

    env_reliability = effort * float(confidence)
    record_confidence = np.where(any_deterministic, 1.0, env_reliability)

    base_reasons = (
        out[DET_REASONS_COLUMN].fillna("").astype("string").tolist()
        if DET_REASONS_COLUMN in out.columns
        else [""] * count
    )
    env_reason = scored & (normalized >= reason_threshold)
    reasons: list[str] = []
    for row in range(count):
        parts = [base_reasons[row]] if base_reasons[row] else []
        if bool(env_reason[row]):
            parts.append(ENVIRONMENTAL_REASON)
        reasons.append(", ".join(parts))

    out[SUSPICION_SCORE_COLUMN] = pd.Series(suspicion, index=out.index, dtype="float64")
    out[SUSPICION_CONFIDENCE_COLUMN] = pd.Series(
        record_confidence, index=out.index, dtype="float64"
    )
    out[SUSPICION_REASONS_COLUMN] = pd.Series(reasons, index=out.index, dtype="string")
    return out


def score_occurrences(
    frame: pd.DataFrame,
    *,
    expected_realm: Realm | None = None,
    institution_points: tuple[tuple[float, float], ...] = (),
    variables: tuple[int, ...] = BIO_VARIABLES,
    cell_size_deg: float | None = None,
    weights: FusionWeights | None = None,
    low_threshold: int = DEFAULT_LOW_THRESHOLD,
    full_threshold: int = DEFAULT_FULL_THRESHOLD,
    reason_threshold: float = DEFAULT_REASON_THRESHOLD,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> pd.DataFrame:
    """Run the whole engine for one taxon and return the scored frame.

    Runs, in order: the environmental outlier model, the deterministic checks,
    the sampling-effort weight, the low-data assessment, and the fusion. The
    input frame is a cached taxon dataset (tidy occurrences plus bio columns and
    on_land). Returns a copy with every signal column and the final
    suspicion_score, suspicion_reasons, and suspicion_confidence columns.
    """
    from .effort import DEFAULT_CELL_SIZE_DEG

    scored = score_environmental_outliers(frame, variables=variables, random_state=random_state)
    flagged = add_deterministic_flags(
        scored, expected_realm=expected_realm, institution_points=institution_points
    )
    with_effort = add_sampling_effort(
        flagged, cell_size_deg=cell_size_deg if cell_size_deg is not None else DEFAULT_CELL_SIZE_DEG
    )
    assessment = assess_low_data(
        with_effort, low_threshold=low_threshold, full_threshold=full_threshold
    )
    return fuse_signals(
        with_effort,
        weights=weights,
        confidence=assessment.confidence,
        reason_threshold=reason_threshold,
    )


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Score a cached taxon for suspicion by fusing every engine signal."
    )
    parser.add_argument("taxon", help="Scientific name of a cached taxon.")
    parser.add_argument("--top", type=int, default=15, help="How many top records to show.")
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE)
    args = parser.parse_args()

    frame = load_cached(args.taxon)
    if frame is None:
        raise SystemExit(
            f"No cached dataset for {args.taxon!r}. Build it first with: "
            f'uv run python -m taxonguard_core.data.cache "{args.taxon}"'
        )

    expected_realm = realm_for(args.taxon)
    scored = score_environmental_outliers(frame, random_state=args.random_state)
    assessment = assess_low_data(scored)
    result = score_occurrences(frame, expected_realm=expected_realm, random_state=args.random_state)

    realm_note = expected_realm or "unknown (realm check skipped)"
    low_note = "yes" if assessment.is_low_data else "no"
    print(
        f"{args.taxon}: {len(result)} records, {assessment.n_scored} climate-scored, "
        f"expected realm {realm_note}, low-data {low_note} "
        f"(confidence {assessment.confidence:.2f})"
    )

    ranked = result.sort_values(SUSPICION_SCORE_COLUMN, ascending=False).head(args.top)
    preferred = [
        "gbif_id",
        "decimal_latitude",
        "decimal_longitude",
        SUSPICION_SCORE_COLUMN,
        SUSPICION_CONFIDENCE_COLUMN,
        SUSPICION_REASONS_COLUMN,
    ]
    present = [column for column in preferred if column in ranked.columns]
    print(ranked.loc[:, present].to_string(index=False))


if __name__ == "__main__":
    _main()
