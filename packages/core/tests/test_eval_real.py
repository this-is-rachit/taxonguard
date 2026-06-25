"""Tests for the real-data evaluation path (planting, split, held-out report).

The real-data benchmark plants the six error types into a real per-taxon frame and
reports on a held-out split. To keep CI network-free, these tests stand in a tiny
synthetic frame for the "real base population": it has the same shape the data
pipeline produces (tidy occurrences plus bio_* columns and on_land), so the
planting, the stratified split, and the held-out report all run with no GBIF
download and no rasters.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from taxonguard_core.eval.benchmark import (
    DEFAULT_ERRORS_PER_TYPE,
    build_real_case,
    plant_labeled_errors,
)
from taxonguard_core.eval.run import build_real_report
from taxonguard_core.eval.scoring import prepare_case
from taxonguard_core.eval.split import split_prepared, stratified_split

VARIABLES = (1, 2)
ERROR_TYPES = ("ocean", "null_island", "equal", "gridded", "institution", "climate")


def _base_frame(n: int = 150, seed: int = 7) -> pd.DataFrame:
    """A synthetic stand-in for an enriched real download (one cold-ish taxon)."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 1)),
            "scientific_name": "Rana temporaria",
            "decimal_latitude": rng.uniform(50.0, 60.0, n),
            "decimal_longitude": rng.uniform(-8.0, 2.0, n),
            "bio_1": rng.normal(90.0, 12.0, n),
            "bio_2": rng.normal(60.0, 8.0, n),
            "on_land": pd.array([True] * n, dtype="boolean"),
        }
    )


# --- planting -------------------------------------------------------------


def test_plant_labeled_errors_adds_every_type() -> None:
    planted = plant_labeled_errors(_base_frame(), variables=VARIABLES, seed=0)
    counts = planted["error_type"].value_counts()
    for kind in ERROR_TYPES:
        assert counts.get(kind, 0) == DEFAULT_ERRORS_PER_TYPE
    n_plausible = int((planted["label"] == "plausible").sum())
    n_suspicious = int((planted["label"] == "suspicious").sum())
    assert n_plausible == 150
    assert n_suspicious == len(ERROR_TYPES) * DEFAULT_ERRORS_PER_TYPE


def test_plant_labeled_errors_is_deterministic() -> None:
    first = plant_labeled_errors(_base_frame(), variables=VARIABLES, seed=0)
    second = plant_labeled_errors(_base_frame(), variables=VARIABLES, seed=0)
    pd.testing.assert_frame_equal(first, second)


def test_planted_ocean_errors_are_off_land() -> None:
    planted = plant_labeled_errors(_base_frame(), variables=VARIABLES, seed=0)
    ocean = planted[planted["error_type"] == "ocean"]
    assert not ocean["on_land"].fillna(True).any()


# --- split ----------------------------------------------------------------


def test_stratified_split_preserves_every_stratum() -> None:
    planted = plant_labeled_errors(_base_frame(), variables=VARIABLES, seed=0)
    calib, holdout = stratified_split(planted, holdout_frac=0.5, seed=0)
    # No record is lost or duplicated across the two folds.
    assert len(calib) + len(holdout) == len(planted)
    # Every error type appears in both folds (each has 4 members, so 2 and 2).
    for kind in ERROR_TYPES:
        assert int((calib["error_type"] == kind).sum()) >= 1
        assert int((holdout["error_type"] == kind).sum()) >= 1


def test_stratified_split_is_deterministic() -> None:
    planted = plant_labeled_errors(_base_frame(), variables=VARIABLES, seed=0)
    a1, b1 = stratified_split(planted, seed=3)
    a2, b2 = stratified_split(planted, seed=3)
    pd.testing.assert_frame_equal(a1, a2)
    pd.testing.assert_frame_equal(b1, b2)


def test_split_prepared_keeps_confidence_and_labels() -> None:
    case = build_real_case(
        _base_frame(), name="Rana temporaria", expected_realm="freshwater", variables=VARIABLES
    )
    prepared = prepare_case(case, variables=VARIABLES)
    calib, holdout = split_prepared(prepared, holdout_frac=0.5, seed=0)
    assert calib.confidence == prepared.confidence
    assert holdout.confidence == prepared.confidence
    assert "label" in calib.frame.columns
    assert len(calib.frame) + len(holdout.frame) == len(prepared.frame)


# --- held-out report ------------------------------------------------------


def test_real_report_reports_held_out_metrics() -> None:
    report = build_real_report(
        _base_frame(),
        name="Rana temporaria",
        expected_realm="freshwater",
        doi="10.15468/dl.demo",
        variables=VARIABLES,
        grid_steps=30,
        seed=0,
    )
    assert report["mode"] == "real"
    assert report["doi"] == "10.15468/dl.demo"
    # Both folds are non-empty and carry planted errors.
    assert report["fold_counts"]["holdout"]["suspicious"] > 0
    assert report["fold_counts"]["calibration"]["suspicious"] > 0
    # Held-out precision stays perfect on this clean stand-in; recall is reported.
    held = report["holdout"]["at_operating_threshold"]
    assert 0.0 <= held["recall"] <= 1.0
    assert held["false_positive_rate"] <= 0.05


def test_real_report_calibration_does_not_worsen_objective() -> None:
    report = build_real_report(
        _base_frame(),
        name="Rana temporaria",
        expected_realm="freshwater",
        variables=VARIABLES,
        grid_steps=30,
        seed=0,
    )
    assert report["calibration"]["improvement"] >= 0.0
    assert (
        report["calibration"]["calibrated_weights"]["environmental"]
        >= report["calibration"]["starting_weights"]["environmental"]
    )


def test_real_report_is_deterministic() -> None:
    kwargs = dict(
        name="Rana temporaria",
        expected_realm="freshwater",
        variables=VARIABLES,
        grid_steps=30,
        seed=0,
    )
    first = build_real_report(_base_frame(), **kwargs)
    second = build_real_report(_base_frame(), **kwargs)
    assert first["holdout"]["at_operating_threshold"] == second["holdout"]["at_operating_threshold"]
    assert first["calibration"]["calibrated_weights"] == second["calibration"]["calibrated_weights"]
