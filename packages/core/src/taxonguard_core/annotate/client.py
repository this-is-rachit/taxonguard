"""The GBIF annotation adapter: one interface, two implementations.

A confirmed :class:`~taxonguard_core.explain.rule.AnnotationRule` is published to
GBIF's experimental occurrence-annotation system. The rule concept is "records of
a taxon inside a geographic polygon carry a controlled-vocabulary value"; GBIF
stores it as a WKT geometry plus a backbone ``taxonKey`` and an ``annotation``
term. The verified contract (from github.com/gbif/occurrence-annotation):

- Base URL ``https://labs.gbif.org/occurrence/experimental/annotation`` (this is
  the experimental annotation service, which is a different host from the main
  ``api.gbif.org/v1`` API).
- ``POST /rule`` with HTTP Basic Auth (any GBIF account).
- JSON body: ``geometry`` (WKT, required), ``taxonKey`` (a single GBIF backbone
  key), ``annotation`` (a vocabulary term; the server upper-cases it). The
  default ``SUSPICIOUS`` term is always available, so a project is not required.
- The response is the created rule, including a server-assigned integer ``id``.

The experimental API offers no stability guarantee, so the entire surface is kept
inside this file. When credentials are absent the engine degrades to a manual
fallback (:class:`NullAnnotationClient`) that hands the reviewer the exact WKT,
value, and taxon to paste into ``labs.gbif.org/annotations`` by hand, so the
whole tool keeps working at no cost and with no keys.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from ..data.gbif import DEFAULT_TIMEOUT, match_taxon_key
from ..explain.rule import AnnotationRule

# The experimental occurrence-annotation service. Not api.gbif.org/v1.
ANNOTATION_API_BASE = "https://labs.gbif.org/occurrence/experimental/annotation"

# The human-facing annotation UI, where a manual rule is created or a written
# rule can be reviewed.
ANNOTATION_UI_URL = "https://labs.gbif.org/annotations/"


class AnnotationError(RuntimeError):
    """Raised when a write-back to GBIF fails (network, auth, or server error)."""


@dataclass(frozen=True)
class AnnotationResult:
    """The outcome of trying to write a confirmed rule back to GBIF.

    ``submitted`` is True only when the rule was actually posted to GBIF. When it
    is False the rule was not written and ``manual_instructions`` carries a
    copy-and-paste fallback. ``rule_id`` and ``rule_url`` identify a written rule;
    ``ui_url`` always points at the annotation UI.
    """

    submitted: bool
    rule_id: int | None = None
    rule_url: str | None = None
    ui_url: str | None = ANNOTATION_UI_URL
    manual: bool = False
    manual_instructions: str | None = None
    detail: str | None = None


class AnnotationClient(Protocol):
    """Anything that can turn a confirmed rule into a GBIF annotation."""

    def submit(self, rule: AnnotationRule) -> AnnotationResult: ...


def manual_instructions(rule: AnnotationRule) -> str:
    """Build copy-and-paste instructions for creating the rule by hand.

    Used when no GBIF credentials are configured. It names the taxon, the
    controlled value, and the exact WKT polygon, and points at the annotation UI,
    so a reviewer without credentials can still create the rule.
    """
    return (
        f"To create this rule by hand, open {ANNOTATION_UI_URL}, sign in with a "
        f"GBIF account, search for the taxon {rule.taxon!r}, and draw or paste "
        f"this polygon, marking it {rule.value!r}.\n"
        f"Taxon: {rule.taxon}\n"
        f"Annotation: {rule.value.upper()}\n"
        f"Geometry (WKT): {rule.geometry_wkt}"
    )


class NullAnnotationClient:
    """The no-credentials fallback. Never touches the network.

    ``submit`` records that the rule was not written and returns the manual
    instructions, so the review loop still completes and the reviewer is told
    exactly how to publish the rule themselves.
    """

    def submit(self, rule: AnnotationRule) -> AnnotationResult:
        return AnnotationResult(
            submitted=False,
            manual=True,
            manual_instructions=manual_instructions(rule),
            ui_url=ANNOTATION_UI_URL,
            detail="No GBIF credentials configured; rule not written to GBIF.",
        )


@dataclass
class GbifAnnotationClient:
    """Posts a confirmed rule to GBIF's experimental annotation API.

    ``username`` and ``password`` are any GBIF account, used for HTTP Basic Auth.
    The rule carries a taxon name; GBIF wants a backbone ``taxonKey``, so the name
    is resolved with the GBIF species-match API. ``resolve_taxon_key`` and
    ``client`` are injectable so tests can run with no network: pass a resolver
    that returns a fixed key, or a client backed by an httpx ``MockTransport`` that
    serves both the match and the annotation endpoints.
    """

    username: str
    password: str
    client: httpx.Client | None = None
    base_url: str = ANNOTATION_API_BASE
    resolve_taxon_key: Callable[[str], int] | None = None
    timeout: float = DEFAULT_TIMEOUT

    def _taxon_key(self, taxon: str) -> int:
        if self.resolve_taxon_key is not None:
            return self.resolve_taxon_key(taxon)
        return match_taxon_key(taxon, client=self.client)

    def submit(self, rule: AnnotationRule) -> AnnotationResult:
        """Resolve the taxon key and POST the rule. Raises AnnotationError on failure."""
        try:
            taxon_key = self._taxon_key(rule.taxon)
        except httpx.HTTPError as error:
            raise AnnotationError(f"Could not resolve taxon {rule.taxon!r}: {error}") from error

        payload: dict[str, Any] = {
            "geometry": rule.geometry_wkt,
            "taxonKey": taxon_key,
            # The server upper-cases this, but send the canonical term explicitly.
            "annotation": rule.value.upper(),
        }

        own_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout)
        try:
            response = client.post(
                f"{self.base_url}/rule",
                json=payload,
                auth=(self.username, self.password),
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except httpx.HTTPError as error:
            raise AnnotationError(f"GBIF annotation write-back failed: {error}") from error
        finally:
            if own_client:
                client.close()

        rule_id = data.get("id")
        rule_id_int = int(rule_id) if rule_id is not None else None
        rule_url = f"{self.base_url}/rule/{rule_id_int}" if rule_id_int is not None else None

        return AnnotationResult(
            submitted=True,
            rule_id=rule_id_int,
            rule_url=rule_url,
            ui_url=ANNOTATION_UI_URL,
            manual=False,
            detail=f"Rule written to GBIF with id {rule_id_int}."
            if rule_id_int is not None
            else "Rule written to GBIF.",
        )
