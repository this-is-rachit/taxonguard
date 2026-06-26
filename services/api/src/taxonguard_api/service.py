"""The cluster service: the API's view of the detection engine.

The service holds already-scored frames per taxon, builds clusters from them, and
keeps an in-memory record of expert decisions. It is deliberately decoupled from
how the frames are produced: the production builder loads cached taxon datasets
and scores them, while tests inject seeded synthetic frames. Confirming a cluster
validates and records the decision and writes the confirmed rule back to GBIF
through the annotation adapter, degrading to a manual fallback with no credentials.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from taxonguard_core.annotate.client import (
    AnnotationClient,
    AnnotationError,
    AnnotationResult,
    NullAnnotationClient,
    manual_instructions,
)
from taxonguard_core.explain.cluster import Cluster, cluster_records
from taxonguard_core.explain.explainer import Explainer, TemplateExplainer
from taxonguard_core.explain.rule import ALLOWED_VALUES, SUSPICIOUS

from .models import (
    ClusterDetail,
    ClusterSummary,
    DecisionRequest,
    DecisionResponse,
    DecisionState,
    RecordOut,
    RuleOut,
    TaxonSummary,
)


class ClusterNotFoundError(KeyError):
    """Raised when a cluster id is not known to the service."""


class InvalidDecisionError(ValueError):
    """Raised when a decision request is not valid."""


class ClusterService:
    """Build clusters from scored frames and track expert decisions."""

    def __init__(
        self,
        frames: Mapping[str, pd.DataFrame],
        *,
        realms: Mapping[str, str] | None = None,
        explainer: Explainer | None = None,
        annotation_client: AnnotationClient | None = None,
        min_score: float = 0.5,
    ) -> None:
        self._explainer = explainer or TemplateExplainer()
        self._annotation_client: AnnotationClient = annotation_client or NullAnnotationClient()
        self._clusters: dict[str, Cluster] = {}
        self._order: list[str] = []
        self._decisions: dict[str, DecisionState] = {}
        realms = realms or {}

        for taxon, frame in frames.items():
            for cluster in cluster_records(
                frame,
                taxon=taxon,
                expected_realm=realms.get(taxon),
                min_score=min_score,
            ):
                self._clusters[cluster.cluster_id] = cluster
                self._order.append(cluster.cluster_id)

    def _summary(self, cluster: Cluster) -> ClusterSummary:
        return ClusterSummary(
            cluster_id=cluster.cluster_id,
            taxon=cluster.taxon,
            count=cluster.count,
            max_score=round(cluster.max_score, 4),
            mean_score=round(cluster.mean_score, 4),
            latitude=round(cluster.representative.latitude, 6),
            longitude=round(cluster.representative.longitude, 6),
            reason_counts=cluster.reason_counts,
            explanation=self._explainer.explain(cluster.representative),
            decision=self._decisions.get(cluster.cluster_id),
        )

    def list_taxa(self) -> list[TaxonSummary]:
        counts: dict[str, list[int]] = {}
        for cluster in self._clusters.values():
            entry = counts.setdefault(cluster.taxon, [0, 0])
            entry[0] += 1
            entry[1] += cluster.count
        return [
            TaxonSummary(taxon=taxon, cluster_count=clusters, flagged_records=records)
            for taxon, (clusters, records) in sorted(counts.items())
        ]

    def list_clusters(self, taxon: str | None = None) -> list[ClusterSummary]:
        summaries = [
            self._summary(self._clusters[cluster_id])
            for cluster_id in self._order
            if taxon is None or self._clusters[cluster_id].taxon == taxon
        ]
        return sorted(summaries, key=lambda summary: summary.max_score, reverse=True)

    def get_cluster(self, cluster_id: str) -> ClusterDetail:
        cluster = self._clusters.get(cluster_id)
        if cluster is None:
            raise ClusterNotFoundError(cluster_id)

        summary = self._summary(cluster)
        records = [
            RecordOut(
                gbif_id=evidence.gbif_id,
                latitude=evidence.latitude,
                longitude=evidence.longitude,
                suspicion_score=round(evidence.suspicion_score, 4),
                confidence=round(evidence.confidence, 4),
                reasons=list(evidence.reasons),
            )
            for evidence in cluster.records[:200]
        ]
        rule = RuleOut(
            taxon=cluster.rule.taxon,
            geometry=cluster.rule.geometry_wkt,
            value=cluster.rule.value,
            record_count=cluster.rule.record_count,
        )
        return ClusterDetail(**summary.model_dump(), records=records, rule=rule)

    def _write_back(self, cluster: Cluster) -> AnnotationResult:
        """Submit a confirmed cluster's rule to GBIF, degrading to a manual result.

        A configured GBIF client posts the rule; the no-credentials default returns
        a manual fallback. If a write-back attempt errors, the failure is turned
        into a manual fallback as well, so a decision is always recorded.
        """
        try:
            return self._annotation_client.submit(cluster.rule)
        except AnnotationError as error:
            return AnnotationResult(
                submitted=False,
                manual=True,
                manual_instructions=manual_instructions(cluster.rule),
                detail=f"Write-back to GBIF failed: {error}",
            )

    def decide(self, cluster_id: str, request: DecisionRequest) -> DecisionResponse:
        cluster = self._clusters.get(cluster_id)
        if cluster is None:
            raise ClusterNotFoundError(cluster_id)

        value = request.value or SUSPICIOUS
        if request.action == "refine" and value not in ALLOWED_VALUES:
            raise InvalidDecisionError(
                f"value must be one of {sorted(ALLOWED_VALUES)} for a refined rule"
            )

        written_to_gbif = False
        annotation_id: int | None = None
        annotation_url: str | None = None
        manual: str | None = None
        if request.action == "confirm":
            result = self._write_back(cluster)
            written_to_gbif = result.submitted
            annotation_id = result.rule_id
            if result.submitted:
                annotation_url = result.rule_url or result.ui_url
            manual = result.manual_instructions

        state = DecisionState(
            action=request.action,
            value=value if request.action != "reject" else None,
            note=request.note,
            written_to_gbif=written_to_gbif,
            annotation_id=annotation_id,
            annotation_url=annotation_url,
            manual_instructions=manual,
        )
        self._decisions[cluster_id] = state
        return DecisionResponse(cluster_id=cluster_id, decision=state)


def build_default_service() -> ClusterService:
    """Build a service from whatever taxon datasets are cached locally.

    Loads each default taxon's cached dataset, scores it, and clusters the
    result. Taxa without a cache, or that fail to load or score, are skipped, so
    the API always starts even with no data on disk. The annotation client is
    chosen from settings: a real GBIF client when credentials are present, and the
    manual-fallback client otherwise, so the API runs at no cost with no keys.
    """
    from taxonguard_core.annotate.client import GbifAnnotationClient
    from taxonguard_core.data.cache import load_cached
    from taxonguard_core.engine.fusion import score_occurrences
    from taxonguard_core.explain.cluster import DEFAULT_MIN_SCORE
    from taxonguard_core.taxa import DEFAULT_TAXA

    from .config import settings
    from .review_taxa import load_added_taxa

    frames: dict[str, pd.DataFrame] = {}
    realms: dict[str, str] = {}
    for taxon in (*DEFAULT_TAXA, *load_added_taxa()):
        try:
            cached = load_cached(taxon.name)
            if cached is None or cached.empty:
                continue
            frames[taxon.name] = score_occurrences(cached, expected_realm=taxon.expected_realm)
            realms[taxon.name] = taxon.expected_realm
        except Exception:
            continue

    annotation_client: AnnotationClient
    username = settings.gbif_username
    password = settings.gbif_password
    if username and password:
        annotation_client = GbifAnnotationClient(username=username, password=password)
    else:
        annotation_client = NullAnnotationClient()

    return ClusterService(
        frames,
        realms=realms,
        annotation_client=annotation_client,
        min_score=DEFAULT_MIN_SCORE,
    )
