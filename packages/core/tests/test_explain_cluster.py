from __future__ import annotations

import numpy as np
import pandas as pd

from taxonguard_core.engine.fusion import score_occurrences
from taxonguard_core.explain.cluster import cluster_records


def _scored_frame() -> pd.DataFrame:
    """A scored frame with a clean cluster plus two errors in distant regions."""
    rng = np.random.default_rng(0)
    n = 70
    frame = pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 3)),
            "scientific_name": ["Test fox"] * (n + 2),
            "decimal_latitude": np.r_[rng.uniform(60, 68, n), [3.0, 4.0]],
            "decimal_longitude": np.r_[rng.uniform(10, 20, n), [-35.0, -36.0]],
            "bio_1": np.r_[rng.normal(-40, 6, n), [285.0, 286.0]],
            "bio_2": np.r_[rng.normal(30, 3, n), [140.0, 141.0]],
            "on_land": pd.array([True] * n + [False, False], dtype="boolean"),
        }
    )
    return score_occurrences(frame, expected_realm="terrestrial", variables=(1, 2))


def test_flagged_errors_form_a_cluster() -> None:
    clusters = cluster_records(_scored_frame(), taxon="Test fox", expected_realm="terrestrial")
    assert len(clusters) >= 1
    # The two ocean errors sit in one 10-degree cell, so they cluster together.
    biggest = clusters[0]
    assert biggest.count >= 2
    assert biggest.taxon == "Test fox"
    assert "realm_mismatch" in biggest.reason_counts
    assert len(biggest.records) == biggest.count


def test_cluster_has_rule_and_representative() -> None:
    clusters = cluster_records(_scored_frame(), taxon="Test fox", expected_realm="terrestrial")
    cluster = clusters[0]
    assert cluster.rule.taxon == "Test fox"
    assert cluster.rule.value == "suspicious"
    assert cluster.representative.taxon == "Test fox"
    assert cluster.representative.suspicion_score >= 0.5
    assert cluster.cluster_id.startswith("test_fox:")


def test_no_flagged_records_returns_empty() -> None:
    rng = np.random.default_rng(1)
    n = 60
    frame = pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 1)),
            "scientific_name": ["Test fox"] * n,
            "decimal_latitude": list(rng.uniform(60, 68, n)),
            "decimal_longitude": list(rng.uniform(10, 20, n)),
            "bio_1": list(rng.normal(-40, 6, n)),
            "bio_2": list(rng.normal(30, 3, n)),
            "on_land": pd.array([True] * n, dtype="boolean"),
        }
    )
    scored = score_occurrences(frame, expected_realm="terrestrial", variables=(1, 2))
    assert cluster_records(scored, taxon="Test fox") == []


def test_clusters_sorted_by_severity() -> None:
    clusters = cluster_records(_scored_frame(), taxon="Test fox", expected_realm="terrestrial")
    scores = [cluster.max_score for cluster in clusters]
    assert scores == sorted(scores, reverse=True)
