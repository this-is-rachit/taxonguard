"""Phase 7 proof: a labeled benchmark, metrics, and weight calibration.

The detection engine is measured against a labeled occurrence set: how many real
errors it catches versus how many plausible records it falsely flags. Ground-truth
labels on occurrence data require either expert annotation or controlled error
injection, so this package builds a labeled benchmark by planting known errors of
each kind into realistic plausible populations (:mod:`benchmark`), scores it
through the real engine, reports the trade-off with standard metrics
(:mod:`metrics`), and calibrates the fusion weights against it
(:mod:`calibrate`). The benchmark builder accepts any base population, so a real
GBIF download can be dropped in without changing the harness.

Run the whole evaluation and write the results and figure:

    uv run python -m taxonguard_core.eval.run
"""
