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
    latitude: float
    longitude: float
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
    # Set when a confirmed rule is written to GBIF's annotation system.
    annotation_id: int | None = None
    annotation_url: str | None = None
    # Set when write-back is not enabled, so a reviewer can create the rule by hand.
    manual_instructions: str | None = None


class DecisionResponse(BaseModel):
    cluster_id: str
    decision: DecisionState
    status: str = "recorded"


# Resolve the forward reference to DecisionState in ClusterSummary.
ClusterSummary.model_rebuild()


class CleanIssue(BaseModel):
    label: str
    count: int


class CleanRecord(BaseModel):
    gbif_id: int | None
    scientific_name: str | None
    latitude: float
    longitude: float
    flagged: bool
    suspicion_score: float
    confidence: float
    reasons: list[str]


class CleanSummaryOut(BaseModel):
    total_records: int
    flagged_records: int
    clean_records: int
    taxa: int
    checks_run: list[str] = Field(description="Which checks ran, given the available data.")
    issues: list[CleanIssue] = Field(description="Record counts per issue type.")


class CleanReport(BaseModel):
    clean_id: str
    summary: CleanSummaryOut
    flagged: list[CleanRecord]
    flagged_truncated: bool = Field(
        description="True when more records were flagged than are listed here."
    )
    download_url: str = Field(description="Path to download the annotated, cleaned CSV.")


class SpeciesSuggestion(BaseModel):
    key: int
    name: str
    rank: str | None = None
    kingdom: str | None = None


class SpeciesScoreReport(BaseModel):
    taxon: str
    summary: CleanSummaryOut
    records: list[CleanRecord] = Field(
        description="Every scored record, most suspicious first (capped)."
    )
    records_truncated: bool = Field(
        description="True when more records were scored than are listed here."
    )


class AnnotatePoint(BaseModel):
    latitude: float
    longitude: float


class AnnotateRequest(BaseModel):
    """A request to draft a rule over flagged records and write it back to GBIF.

    The points are the coordinates of the records the rule should cover (the
    currently filtered, suspicious records on the Explore screen). The server
    builds the rule polygon from them, so geometry construction stays in one
    tested place in the core.
    """

    taxon: str
    points: list[AnnotatePoint] = Field(
        description="Coordinates of the flagged records the rule should cover."
    )
    value: str = Field(
        default="suspicious",
        description="Controlled-vocabulary annotation value. Defaults to suspicious.",
    )


class AnnotateResponse(BaseModel):
    """The outcome of drafting a rule and attempting to write it back to GBIF."""

    submitted: bool
    rule: RuleOut
    written_to_gbif: bool = False
    annotation_id: int | None = None
    annotation_url: str | None = None
    # Set when write-back is not enabled, so the reviewer can create the rule by hand.
    manual_instructions: str | None = None
    detail: str | None = None
