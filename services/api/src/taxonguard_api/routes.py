"""Cluster and decision endpoints.

Read endpoints list taxa and flagged clusters and fetch one cluster with its
records, explanation, and draft rule. The decision endpoint records an expert's
confirm, reject, or refine. The service is provided by dependency injection so it
can be swapped in tests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from taxonguard_core.data.cache import build_taxon_dataset, cache_path

from .annotate_service import AnnotationSubmitService
from .clean_service import CleanNotFoundError, CleanService, UploadError
from .models import (
    AddTaxonRequest,
    AddTaxonResponse,
    AnnotateRequest,
    AnnotateResponse,
    CleanReport,
    ClusterDetail,
    ClusterSummary,
    DecisionRequest,
    DecisionResponse,
    SpeciesScoreReport,
    SpeciesSuggestion,
    TaxonSummary,
)
from .review_taxa import add_review_taxon
from .score_service import SpeciesScoreError, TaxonScoreService
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


@lru_cache(maxsize=1)
def get_clean_service() -> CleanService:
    """Return the process-wide clean service (holds uploaded results in memory)."""
    return CleanService()


@lru_cache(maxsize=1)
def get_score_service() -> TaxonScoreService:
    """Return the process-wide on-demand species scoring service."""
    return TaxonScoreService()


@lru_cache(maxsize=1)
def get_annotation_service() -> AnnotationSubmitService:
    """Return the process-wide annotation submit service (Explore write-back)."""
    return AnnotationSubmitService()


ServiceDep = Annotated[ClusterService, Depends(get_service)]
CleanServiceDep = Annotated[CleanService, Depends(get_clean_service)]
ScoreServiceDep = Annotated[TaxonScoreService, Depends(get_score_service)]
AnnotationServiceDep = Annotated[AnnotationSubmitService, Depends(get_annotation_service)]

router = APIRouter()


@router.get("/taxa", response_model=list[TaxonSummary])
def list_taxa(service: ServiceDep) -> list[TaxonSummary]:
    return service.list_taxa()


@router.post("/taxa", response_model=AddTaxonResponse, status_code=201)
def add_taxon(request: AddTaxonRequest) -> AddTaxonResponse:
    """Add a species to Review: fetch it from GBIF, enrich, cache, and cluster it.

    The species is fetched and enriched with the same climate and land/sea data as
    the curated set, cached on disk, and recorded in the review registry so it
    survives a restart. The process-wide cluster service is then rebuilt so the new
    species' clusters are available immediately. This needs the WorldClim and Natural
    Earth data on the server, the same as the cache build.
    """
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="A species name is required.")

    try:
        frame = build_taxon_dataset(name)
    except Exception as error:  # noqa: BLE001 - surfaced as a clean API error
        raise HTTPException(
            status_code=502, detail=f"Could not fetch and prepare {name!r}: {error}"
        ) from error
    if frame.empty:
        raise HTTPException(status_code=502, detail=f"GBIF returned no records for {name!r}.")

    path = cache_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    add_review_taxon(name, request.realm)

    # Rebuild the process-wide service so the new species shows up right away.
    get_service.cache_clear()
    service = get_service()
    summary = next((item for item in service.list_taxa() if item.taxon == name), None)
    return AddTaxonResponse(
        taxon=name,
        realm=request.realm,
        cluster_count=summary.cluster_count if summary else 0,
        flagged_records=summary.flagged_records if summary else 0,
    )


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


@router.post("/clean", response_model=CleanReport)
async def clean_upload(
    service: CleanServiceDep,
    file: Annotated[UploadFile, File(description="An occurrence CSV or TSV to check.")],
) -> CleanReport:
    """Run the engine on an uploaded occurrence file and return a before/after report."""
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=400, detail="The file must be UTF-8 encoded text (CSV or TSV)."
        ) from error
    try:
        return service.run(text)
    except UploadError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/clean/{clean_id}/download")
def clean_download(clean_id: str, service: CleanServiceDep) -> Response:
    """Download the annotated, cleaned CSV for a previous clean run."""
    try:
        csv = service.download(clean_id)
    except CleanNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Unknown clean id: {clean_id}") from error
    return Response(
        content=csv,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="taxonguard-cleaned.csv"'},
    )


@router.get("/species/suggest", response_model=list[SpeciesSuggestion])
def species_suggest(service: ScoreServiceDep, q: str = "") -> list[SpeciesSuggestion]:
    """Autocomplete scientific names for the search box (proxies GBIF)."""
    try:
        return service.suggest(q)
    except SpeciesScoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/score", response_model=SpeciesScoreReport)
def score_species(service: ScoreServiceDep, taxon: str) -> SpeciesScoreReport:
    """Fetch and score a species on demand, returning ranked records and a summary."""
    if not taxon.strip():
        raise HTTPException(status_code=400, detail="A taxon name is required.")
    try:
        return service.score(taxon)
    except SpeciesScoreError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/annotate", response_model=AnnotateResponse)
def annotate(request: AnnotateRequest, service: AnnotationServiceDep) -> AnnotateResponse:
    """Draft a rule over the flagged records and write it back to GBIF.

    Used by the Explore screen to publish a rule for any species the user has
    searched and filtered. The rule polygon is built from the supplied points; with
    GBIF credentials configured the rule is posted to the experimental annotation
    API, and without them the response carries manual copy-and-paste instructions.
    """
    if not request.taxon.strip():
        raise HTTPException(status_code=400, detail="A taxon name is required.")
    if not request.points:
        raise HTTPException(
            status_code=400, detail="At least one flagged record is required to propose a rule."
        )
    try:
        return service.submit(taxon=request.taxon, points=request.points, value=request.value)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
