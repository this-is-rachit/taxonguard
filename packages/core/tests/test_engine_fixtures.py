"""Engine test suite on labeled fixtures (Phase 2, step 24).

These tests check the whole engine end to end against a small, seeded, labeled
dataset rather than any single function. A realistic plausible population is
built for one taxon, then one error of each kind is planted with a known label:
a land animal in the sea, a null-island point, a gridded centroid, an
institution coordinate, and a climate outlier sitting in a well-sampled area. The
suite asserts that every planted error is flagged and that no plausible record
is, and it documents the deliberate sampling-effort behaviour: a climate outlier
that is also spatially isolated is down-weighted on purpose, so that sparse data
is not treated as wrong.

The fixture builder is intentionally self-contained and synthetic, with no
network. It mirrors the cached dataset shape (tidy occurrences plus bio columns
and on_land) and can seed the real labeled evaluation set built in Phase 7.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from taxonguard_core.engine.deterministic import (
    GRIDDED_COORDINATES,
    INSTITUTION_COORDINATES,
    REALM_MISMATCH,
    ZERO_COORDINATES,
)
from taxonguard_core.engine.fusion import (
    ENVIRONMENTAL_REASON,
    SUSPICION_REASONS_COLUMN,
    SUSPICION_SCORE_COLUMN,
    score_occurrences,
)

# A point standing in for a biodiversity institution (a museum).
INSTITUTION = (52.5200, 13.4050)
VARIABLES = (1, 2)

# Score at or above which a record counts as flagged. Chosen to sit in the gap
# between the plausible population and every planted error in the fixture.
FLAG_THRESHOLD = 0.4

# Expected reason code per planted error type.
EXPECTED_REASON = {
    "ocean": REALM_MISMATCH,
    "null_island": ZERO_COORDINATES,
    "gridded": GRIDDED_COORDINATES,
    "climate": ENVIRONMENTAL_REASON,
    "institution": INSTITUTION_COORDINATES,
}


def build_labeled_fixture(seed: int = 0) -> pd.DataFrame:
    """Build a labeled occurrence fixture for one cold-specialist taxon.

    Columns include label ('plausible' or 'suspicious') and error_type. The
    plausible population is a cold climate cluster on land, with a dense
    sub-cluster standing for a well-sampled locality. One error of each kind is
    appended.
    """
    rng = np.random.default_rng(seed)
    n = 120
    lat = list(rng.uniform(60.0, 70.0, n))
    lon = list(rng.uniform(10.0, 30.0, n))
    bio_1 = list(rng.normal(-40.0, 8.0, n))
    bio_2 = list(rng.normal(30.0, 4.0, n))
    label = ["plausible"] * n
    error_type = [""] * n
    on_land = [True] * n
    gbif_id = list(range(1, n + 1))

    # A well-sampled locality: 16 extra plausible records in one grid cell.
    m = 16
    lat += list(rng.uniform(64.0, 64.9, m))
    lon += list(rng.uniform(18.0, 18.9, m))
    bio_1 += list(rng.normal(-40.0, 6.0, m))
    bio_2 += list(rng.normal(30.0, 3.0, m))
    label += ["plausible"] * m
    error_type += [""] * m
    on_land += [True] * m
    gbif_id += list(range(n + 1, n + m + 1))

    def add(latitude: float, longitude: float, b1: float, b2: float, land: bool, kind: str) -> None:
        gbif_id.append(len(gbif_id) + 1)
        lat.append(latitude)
        lon.append(longitude)
        bio_1.append(b1)
        bio_2.append(b2)
        on_land.append(land)
        label.append("suspicious")
        error_type.append(kind)

    add(65.3, -30.0, -38.0, 31.0, False, "ocean")  # land animal in the sea
    add(0.0, 0.0, -40.0, 30.0, False, "null_island")  # (0, 0)
    add(66.0, 20.0, -39.0, 30.0, True, "gridded")  # integer-degree centroid
    add(64.55, 18.45, 285.0, 140.0, True, "climate")  # hot outlier in sampled cell
    add(INSTITUTION[0], INSTITUTION[1], -40.0, 30.0, True, "institution")  # museum point

    frame = pd.DataFrame(
        {
            "gbif_id": gbif_id,
            "scientific_name": "Test fox",
            "decimal_latitude": lat,
            "decimal_longitude": lon,
            "bio_1": bio_1,
            "bio_2": bio_2,
            "on_land": pd.array(on_land, dtype="boolean"),
            "label": label,
            "error_type": error_type,
        }
    )
    return frame


def _score(frame: pd.DataFrame) -> pd.DataFrame:
    return score_occurrences(
        frame,
        expected_realm="terrestrial",
        variables=VARIABLES,
        institution_points=(INSTITUTION,),
    )


def evaluate(scored: pd.DataFrame, threshold: float) -> tuple[float, float]:
    """Return (recall, false_positive_rate) against the label column."""
    flagged = scored[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64") >= threshold
    is_bad = (scored["label"] == "suspicious").to_numpy(dtype=bool)
    tp = int(np.sum(flagged & is_bad))
    fn = int(np.sum(~flagged & is_bad))
    fp = int(np.sum(flagged & ~is_bad))
    tn = int(np.sum(~flagged & ~is_bad))
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) else 0.0
    return recall, false_positive_rate


def test_engine_catches_every_planted_error_without_false_alarms() -> None:
    scored = _score(build_labeled_fixture())
    recall, false_positive_rate = evaluate(scored, FLAG_THRESHOLD)
    assert recall == 1.0
    assert false_positive_rate == 0.0


def test_plausible_population_scores_below_the_threshold() -> None:
    scored = _score(build_labeled_fixture())
    good = scored.loc[scored["label"] == "plausible", SUSPICION_SCORE_COLUMN]
    assert float(good.max()) < FLAG_THRESHOLD


def test_each_error_type_reports_its_expected_reason() -> None:
    scored = _score(build_labeled_fixture())
    for kind, code in EXPECTED_REASON.items():
        row = scored.loc[scored["error_type"] == kind].iloc[0]
        assert code in row[SUSPICION_REASONS_COLUMN], f"{kind} should report {code}"


def test_isolated_climate_outlier_is_downweighted_by_effort() -> None:
    # A cold population plus one hot outlier alone in a distant, unsampled cell.
    rng = np.random.default_rng(1)
    n = 80
    frame = pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 2)),
            "scientific_name": "Test fox",
            "decimal_latitude": list(rng.uniform(60.0, 70.0, n)) + [5.3],
            "decimal_longitude": list(rng.uniform(10.0, 30.0, n)) + [-50.4],
            "bio_1": list(rng.normal(-40.0, 8.0, n)) + [285.0],
            "bio_2": list(rng.normal(30.0, 4.0, n)) + [140.0],
            "on_land": pd.array([True] * (n + 1), dtype="boolean"),
        }
    )
    scored = score_occurrences(frame, expected_realm="terrestrial", variables=VARIABLES)
    isolated = scored.iloc[-1][SUSPICION_SCORE_COLUMN]
    # The isolated climate outlier is deliberately not strongly flagged.
    assert float(isolated) < FLAG_THRESHOLD


def test_scores_are_deterministic_across_runs() -> None:
    first = _score(build_labeled_fixture())
    second = _score(build_labeled_fixture())
    np.testing.assert_array_equal(
        first[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64"),
        second[SUSPICION_SCORE_COLUMN].to_numpy(dtype="float64"),
    )
