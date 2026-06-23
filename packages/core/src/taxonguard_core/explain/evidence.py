"""Structured numeric evidence behind a flag.

A RecordEvidence captures everything the explanation layer is allowed to talk
about for one flagged record: the taxon, the suspicion score and confidence, the
reason codes, and the few supporting numbers (coordinates, expected realm, the
environmental outlier score). The explanation layer reads only this object, so it
can never refer to anything the engine did not compute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..engine.environment import NORM_SCORE_COLUMN, SCORED_COLUMN
from ..engine.fusion import (
    SUSPICION_CONFIDENCE_COLUMN,
    SUSPICION_REASONS_COLUMN,
    SUSPICION_SCORE_COLUMN,
)


@dataclass(frozen=True)
class RecordEvidence:
    """The numeric facts the explanation layer may use for one record."""

    taxon: str
    gbif_id: int | None
    latitude: float
    longitude: float
    suspicion_score: float
    confidence: float
    reasons: tuple[str, ...]
    expected_realm: str | None
    on_land: bool | None
    environmental_normalized: float | None


def _parse_reasons(value: object) -> tuple[str, ...]:
    if not isinstance(value, str) or not value.strip():
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _present(value: Any) -> bool:
    """True if a pandas scalar is neither None nor a missing value."""
    return value is not None and not bool(pd.isna(value))


def evidence_for_row(
    row: pd.Series,
    *,
    taxon: str,
    expected_realm: str | None = None,
) -> RecordEvidence:
    """Build a RecordEvidence from one row of a scored frame."""
    gbif_id: Any = row.get("gbif_id")
    on_land: Any = row.get("on_land")
    normalized: Any = row.get(NORM_SCORE_COLUMN) if row.get(SCORED_COLUMN) else None

    return RecordEvidence(
        taxon=taxon,
        gbif_id=int(gbif_id) if _present(gbif_id) else None,
        latitude=float(row["decimal_latitude"]),
        longitude=float(row["decimal_longitude"]),
        suspicion_score=float(row[SUSPICION_SCORE_COLUMN]),
        confidence=float(row[SUSPICION_CONFIDENCE_COLUMN]),
        reasons=_parse_reasons(row.get(SUSPICION_REASONS_COLUMN)),
        expected_realm=expected_realm,
        on_land=bool(on_land) if _present(on_land) else None,
        environmental_normalized=float(normalized) if _present(normalized) else None,
    )


def evidence_from_frame(
    frame: pd.DataFrame,
    *,
    taxon: str,
    expected_realm: str | None = None,
    min_score: float = 0.0,
) -> list[RecordEvidence]:
    """Build evidence objects for the flagged rows of a scored frame.

    Rows with a suspicion score at or above min_score are returned, most
    suspicious first.
    """
    flagged = frame[frame[SUSPICION_SCORE_COLUMN] >= min_score]
    flagged = flagged.sort_values(SUSPICION_SCORE_COLUMN, ascending=False)
    return [
        evidence_for_row(row, taxon=taxon, expected_realm=expected_realm)
        for _, row in flagged.iterrows()
    ]
