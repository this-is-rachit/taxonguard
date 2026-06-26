"""Tests for the /annotate endpoint (Explore write-back, Phase 8C).

The annotation client is injected, so the whole flow runs with no network: a fake
"written" client, the real no-credentials manual fallback, and a raising client to
prove a write-back failure degrades to the manual fallback rather than erroring.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from taxonguard_api.annotate_service import AnnotationSubmitService
from taxonguard_api.main import app
from taxonguard_api.routes import get_annotation_service
from taxonguard_core.annotate.client import (
    AnnotationError,
    AnnotationResult,
    NullAnnotationClient,
)
from taxonguard_core.explain.rule import AnnotationRule

_POINTS = [
    {"latitude": 51.5, "longitude": -0.12},
    {"latitude": 52.2, "longitude": -1.1},
    {"latitude": 50.1, "longitude": -2.3},
]


class _WrittenClient:
    """A fake client that reports a successful GBIF write-back."""

    def submit(self, rule: AnnotationRule) -> AnnotationResult:
        return AnnotationResult(
            submitted=True,
            rule_id=4242,
            rule_url="https://api.gbif.org/v1/occurrence/experimental/annotation/rule/4242",
            manual=False,
            detail="Rule written to GBIF with id 4242.",
        )


class _RaisingClient:
    """A fake client whose write-back always fails."""

    def submit(self, rule: AnnotationRule) -> AnnotationResult:
        raise AnnotationError("boom")


def _client_with(service: AnnotationSubmitService) -> Iterator[TestClient]:
    app.dependency_overrides[get_annotation_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def written_client() -> Iterator[TestClient]:
    yield from _client_with(AnnotationSubmitService(client=_WrittenClient()))


@pytest.fixture
def manual_client() -> Iterator[TestClient]:
    yield from _client_with(AnnotationSubmitService(client=NullAnnotationClient()))


@pytest.fixture
def raising_client() -> Iterator[TestClient]:
    yield from _client_with(AnnotationSubmitService(client=_RaisingClient()))


def test_annotate_written(written_client: TestClient) -> None:
    response = written_client.post(
        "/annotate", json={"taxon": "Rana temporaria", "points": _POINTS}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["submitted"] is True
    assert body["written_to_gbif"] is True
    assert body["annotation_id"] == 4242
    assert "rule/4242" in body["annotation_url"]
    # The rule polygon is built from the points, in one tested place.
    assert body["rule"]["geometry"].startswith("POLYGON")
    assert body["rule"]["value"] == "suspicious"
    assert body["rule"]["taxon"] == "Rana temporaria"
    assert body["rule"]["record_count"] == 3


def test_annotate_manual_fallback(manual_client: TestClient) -> None:
    response = manual_client.post("/annotate", json={"taxon": "Rana temporaria", "points": _POINTS})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["submitted"] is False
    assert body["written_to_gbif"] is False
    assert body["annotation_url"] is None
    assert body["manual_instructions"]
    assert "Rana temporaria" in body["manual_instructions"]
    assert "POLYGON" in body["manual_instructions"]


def test_annotate_write_failure_degrades_to_manual(raising_client: TestClient) -> None:
    response = raising_client.post(
        "/annotate", json={"taxon": "Rana temporaria", "points": _POINTS}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["submitted"] is False
    assert body["manual_instructions"]
    assert "failed" in (body["detail"] or "").lower()


def test_annotate_requires_points(written_client: TestClient) -> None:
    response = written_client.post("/annotate", json={"taxon": "Rana temporaria", "points": []})
    assert response.status_code == 400


def test_annotate_requires_taxon(written_client: TestClient) -> None:
    response = written_client.post("/annotate", json={"taxon": "  ", "points": _POINTS})
    assert response.status_code == 400


def test_annotate_rejects_unknown_value(written_client: TestClient) -> None:
    response = written_client.post(
        "/annotate",
        json={"taxon": "Rana temporaria", "points": _POINTS, "value": "definitely_wrong"},
    )
    assert response.status_code == 400


def test_annotate_single_point_is_buffered(written_client: TestClient) -> None:
    response = written_client.post(
        "/annotate",
        json={"taxon": "Rana temporaria", "points": [{"latitude": 51.5, "longitude": -0.1}]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rule"]["geometry"].startswith("POLYGON")
    assert body["rule"]["record_count"] == 1
