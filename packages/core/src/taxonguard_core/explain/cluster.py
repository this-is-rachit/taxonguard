"""Group flagged records into reviewable clusters.

The review screen and the API work in clusters, not single records: a cluster is
a group of nearby flagged records of one taxon that share a region and map to one
annotation rule. This module groups the flagged rows of a scored frame onto a
coarse grid, and for each group builds the member points, the score summary, a
reason tally, a representative evidence object, and a draft rule. The explanation
sentence is left to the caller so it can choose the template or a language model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..engine.fusion import SUSPICION_REASONS_COLUMN, SUSPICION_SCORE_COLUMN
from .evidence import RecordEvidence, evidence_for_row
from .rule import AnnotationRule, build_rule

# A record counts as flagged for clustering at or above this suspicion score.
DEFAULT_MIN_SCORE = 0.5

# Cluster grid cell size in degrees. Coarser than the sampling-effort grid, so a
# cluster covers a region rather than a single locality.
DEFAULT_CLUSTER_CELL_DEG = 10.0


@dataclass(frozen=True)
class Cluster:
    """A group of flagged records of one taxon in one region."""

    cluster_id: str
    taxon: str
    record_ids: tuple[int, ...]
    points: tuple[tuple[float, float], ...]
    count: int
    max_score: float
    mean_score: float
    reason_counts: dict[str, int]
    representative: RecordEvidence
    records: tuple[RecordEvidence, ...]
    rule: AnnotationRule


def _slug(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _reason_counts(reasons: pd.Series) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for value in reasons.tolist():
        if isinstance(value, str) and value.strip():
            counter.update(part.strip() for part in value.split(",") if part.strip())
    return dict(counter)


def cluster_records(
    frame: pd.DataFrame,
    *,
    taxon: str,
    expected_realm: str | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
    cell_size_deg: float = DEFAULT_CLUSTER_CELL_DEG,
) -> list[Cluster]:
    """Group the flagged rows of a scored frame into clusters, most severe first.

    Requires the suspicion columns produced by the fusion step. Records with a
    suspicion score at or above min_score are grouped onto a grid of cell_size_deg
    cells; each non-empty cell becomes one cluster.
    """
    if cell_size_deg <= 0.0:
        raise ValueError("cell_size_deg must be positive")
    if SUSPICION_SCORE_COLUMN not in frame.columns:
        raise KeyError(f"frame is missing the {SUSPICION_SCORE_COLUMN!r} column")

    flagged = frame[frame[SUSPICION_SCORE_COLUMN] >= min_score].copy()
    if flagged.empty:
        return []

    latitude = flagged["decimal_latitude"].to_numpy(dtype="float64")
    longitude = flagged["decimal_longitude"].to_numpy(dtype="float64")
    ix = np.floor(longitude / cell_size_deg).astype("int64")
    iy = np.floor(latitude / cell_size_deg).astype("int64")
    flagged["_cluster_cell"] = [f"{x}_{y}" for x, y in zip(ix, iy, strict=True)]

    clusters: list[Cluster] = []
    for cell, group in flagged.groupby("_cluster_cell", sort=True):
        members = [
            evidence_for_row(row, taxon=taxon, expected_realm=expected_realm)
            for _, row in group.iterrows()
        ]
        members.sort(key=lambda evidence: evidence.suspicion_score, reverse=True)
        representative = members[0]

        record_ids = tuple(member.gbif_id for member in members if member.gbif_id is not None)
        points = tuple((member.latitude, member.longitude) for member in members)
        scores = [member.suspicion_score for member in members]
        rule = build_rule(taxon, list(points))

        clusters.append(
            Cluster(
                cluster_id=f"{_slug(taxon)}:{cell}",
                taxon=taxon,
                record_ids=record_ids,
                points=points,
                count=len(members),
                max_score=max(scores),
                mean_score=sum(scores) / len(scores),
                reason_counts=_reason_counts(group[SUSPICION_REASONS_COLUMN]),
                representative=representative,
                records=tuple(members),
                rule=rule,
            )
        )

    return sorted(clusters, key=lambda cluster: cluster.max_score, reverse=True)
