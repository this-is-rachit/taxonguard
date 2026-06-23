"""Cluster and decision endpoints.

Read endpoints list taxa and flagged clusters and fetch one cluster with its
records, explanation, and draft rule. The decision endpoint records an expert's
confirm, reject, or refine. The service is provided by dependency injection so it
can be swapped in tests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from .models import (
    ClusterDetail,
    ClusterSummary,
    DecisionRequest,
    DecisionResponse,
    TaxonSummary,
)
from .service import (
    ClusterNotFoundError,
    ClusterService,
    InvalidDecisionError,
    build_default_service,
)


@lru_cache(maxsize=1)
def get_service() -> ClusterService:
    """Return the process-wide cluster service, built once from local caches."""
    return build_default_service()


ServiceDep = Annotated[ClusterService, Depends(get_service)]

router = APIRouter()


@router.get("/taxa", response_model=list[TaxonSummary])
def list_taxa(service: ServiceDep) -> list[TaxonSummary]:
    return service.list_taxa()


@router.get("/clusters", response_model=list[ClusterSummary])
def list_clusters(service: ServiceDep, taxon: str | None = None) -> list[ClusterSummary]:
    return service.list_clusters(taxon=taxon)


@router.get("/clusters/{cluster_id}", response_model=ClusterDetail)
def get_cluster(cluster_id: str, service: ServiceDep) -> ClusterDetail:
    try:
        return service.get_cluster(cluster_id)
    except ClusterNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Unknown cluster: {cluster_id}") from error


@router.post("/clusters/{cluster_id}/decision", response_model=DecisionResponse)
def decide(cluster_id: str, request: DecisionRequest, service: ServiceDep) -> DecisionResponse:
    try:
        return service.decide(cluster_id, request)
    except ClusterNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Unknown cluster: {cluster_id}") from error
    except InvalidDecisionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
