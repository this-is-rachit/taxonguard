"""Typed request and response models for the TaxonGuard API.

These models define the API contract and drive the automatic OpenAPI schema. They
mirror the core engine and explanation objects but keep the API decoupled from
pandas and the core dataclasses.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TaxonSummary(BaseModel):
    taxon: str
    cluster_count: int
    flagged_records: int


class RuleOut(BaseModel):
    taxon: str
    geometry: str = Field(description="The rule polygon as WKT.")
    value: str
    record_count: int


class RecordOut(BaseModel):
    gbif_id: int | None
    latitude: float
    longitude: float
    suspicion_score: float
    confidence: float
    reasons: list[str]


class ClusterSummary(BaseModel):
    cluster_id: str
    taxon: str
    count: int
    max_score: float
    mean_score: float
    reason_counts: dict[str, int]
    explanation: str
    decision: DecisionState | None = None


class ClusterDetail(ClusterSummary):
    records: list[RecordOut]
    rule: RuleOut


class DecisionRequest(BaseModel):
    action: Literal["confirm", "reject", "refine"]
    value: str | None = Field(
        default=None,
        description="Controlled-vocabulary value for a refined rule. Defaults to suspicious.",
    )
    note: str | None = None


class DecisionState(BaseModel):
    action: Literal["confirm", "reject", "refine"]
    value: str | None = None
    note: str | None = None
    written_to_gbif: bool = False


class DecisionResponse(BaseModel):
    cluster_id: str
    decision: DecisionState
    status: str = "recorded"


# Resolve the forward reference to DecisionState in ClusterSummary.
ClusterSummary.model_rebuild()
