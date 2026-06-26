"""Draft a rule from flagged records and write it back to GBIF (Phase 8C).

The review screen writes back per cluster through :class:`ClusterService`. This
service exposes the same write-back for the Explore screen, where a user has
searched and scored any species and wants to publish a rule over the records they
have filtered to. It builds the rule from the points with the core rule builder
(so geometry construction stays in one tested place), then submits it through the
Phase 6 annotation adapter: a real GBIF client when credentials are configured,
and the manual copy-and-paste fallback otherwise. Any write-back error is turned
into the manual fallback as well, so a proposal never hard-fails and the screen
never looks broken.

The annotation client is injectable so tests run with no network.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from taxonguard_core.annotate.client import (
    AnnotationClient,
    AnnotationError,
    AnnotationResult,
    GbifAnnotationClient,
    NullAnnotationClient,
    manual_instructions,
)
from taxonguard_core.explain.rule import build_rule

from .config import settings
from .models import AnnotatePoint, AnnotateResponse, RuleOut


@dataclass
class AnnotationSubmitService:
    """Build a rule over flagged points and submit it to GBIF's annotation API.

    When ``client`` is not set, the client is chosen from settings at call time: a
    real GBIF client when both credentials are present, otherwise the manual
    fallback. Passing ``client`` (for example an httpx ``MockTransport``-backed
    client, or a fake) makes the whole flow run with no network in tests.
    """

    client: AnnotationClient | None = None

    def _resolve_client(self) -> AnnotationClient:
        if self.client is not None:
            return self.client
        username = settings.gbif_username
        password = settings.gbif_password
        if username and password:
            return GbifAnnotationClient(username=username, password=password)
        return NullAnnotationClient()

    def submit(
        self,
        *,
        taxon: str,
        points: Sequence[AnnotatePoint],
        value: str = "suspicious",
    ) -> AnnotateResponse:
        """Draft and submit a rule. Raises ValueError on empty points or a bad value.

        Builds the rule polygon from the points (the core builder validates the
        controlled value and the non-empty point set), submits it through the
        configured client, and degrades a write-back failure to the manual fallback.
        """
        rule = build_rule(
            taxon,
            [(point.latitude, point.longitude) for point in points],
            value=value,
        )

        try:
            result = self._resolve_client().submit(rule)
        except AnnotationError as error:
            result = AnnotationResult(
                submitted=False,
                manual=True,
                manual_instructions=manual_instructions(rule),
                detail=f"Write-back to GBIF failed: {error}",
            )

        rule_out = RuleOut(
            taxon=rule.taxon,
            geometry=rule.geometry_wkt,
            value=rule.value,
            record_count=rule.record_count,
        )
        return AnnotateResponse(
            submitted=result.submitted,
            rule=rule_out,
            written_to_gbif=result.submitted,
            annotation_id=result.rule_id,
            annotation_url=(result.rule_url or result.ui_url) if result.submitted else None,
            manual_instructions=result.manual_instructions,
            detail=result.detail,
        )
