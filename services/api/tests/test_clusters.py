from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from taxonguard_api.main import app
from taxonguard_api.routes import get_service
from taxonguard_api.service import ClusterService
from taxonguard_core.annotate.client import AnnotationError, AnnotationResult
from taxonguard_core.engine.fusion import score_occurrences

TAXON = "Test fox"


def _seeded_frames() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(0)
    n = 70
    frame = pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 3)),
            "scientific_name": [TAXON] * (n + 2),
            "decimal_latitude": np.r_[rng.uniform(60, 68, n), [3.0, 4.0]],
            "decimal_longitude": np.r_[rng.uniform(10, 20, n), [-35.0, -36.0]],
            "bio_1": np.r_[rng.normal(-40, 6, n), [285.0, 286.0]],
            "bio_2": np.r_[rng.normal(30, 3, n), [140.0, 141.0]],
            "on_land": pd.array([True] * n + [False, False], dtype="boolean"),
        }
    )
    scored = score_occurrences(frame, expected_realm="terrestrial", variables=(1, 2))
    return {TAXON: scored}


def _seeded_service(annotation_client: object | None = None) -> ClusterService:
    return ClusterService(
        _seeded_frames(),
        realms={TAXON: "terrestrial"},
        annotation_client=annotation_client,  # type: ignore[arg-type]
    )


@pytest.fixture
def client() -> TestClient:
    service = _seeded_service()
    app.dependency_overrides[get_service] = lambda: service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_list_taxa(client: TestClient) -> None:
    response = client.get("/taxa")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["taxon"] == TAXON
    assert body[0]["cluster_count"] >= 1


def test_list_clusters(client: TestClient) -> None:
    response = client.get("/clusters")
    assert response.status_code == 200
    clusters = response.json()
    assert len(clusters) >= 1
    top = clusters[0]
    assert top["taxon"] == TAXON
    assert top["explanation"].endswith(".")
    assert "realm_mismatch" in top["reason_counts"]


def test_filter_clusters_by_taxon(client: TestClient) -> None:
    assert client.get("/clusters", params={"taxon": TAXON}).json()
    assert client.get("/clusters", params={"taxon": "Nonexistent"}).json() == []


def test_get_cluster_detail(client: TestClient) -> None:
    cluster_id = client.get("/clusters").json()[0]["cluster_id"]
    response = client.get(f"/clusters/{cluster_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["cluster_id"] == cluster_id
    assert detail["rule"]["value"] == "suspicious"
    assert detail["rule"]["geometry"].startswith("POLYGON")
    assert len(detail["records"]) >= 1


def test_unknown_cluster_returns_404(client: TestClient) -> None:
    response = client.get("/clusters/does_not_exist")
    assert response.status_code == 404


def test_confirm_decision_is_recorded(client: TestClient) -> None:
    cluster_id = client.get("/clusters").json()[0]["cluster_id"]
    response = client.post(
        f"/clusters/{cluster_id}/decision",
        json={"action": "confirm", "note": "checked on the map"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["action"] == "confirm"
    assert body["decision"]["value"] == "suspicious"
    assert body["decision"]["written_to_gbif"] is False

    # The decision shows up on the cluster afterwards.
    detail = client.get(f"/clusters/{cluster_id}").json()
    assert detail["decision"]["action"] == "confirm"


def test_reject_clears_value(client: TestClient) -> None:
    cluster_id = client.get("/clusters").json()[0]["cluster_id"]
    body = client.post(f"/clusters/{cluster_id}/decision", json={"action": "reject"}).json()
    assert body["decision"]["action"] == "reject"
    assert body["decision"]["value"] is None


def test_invalid_action_rejected_by_validation(client: TestClient) -> None:
    cluster_id = client.get("/clusters").json()[0]["cluster_id"]
    response = client.post(f"/clusters/{cluster_id}/decision", json={"action": "delete"})
    assert response.status_code == 422  # not in the allowed Literal


def test_decision_on_unknown_cluster_returns_404(client: TestClient) -> None:
    response = client.post("/clusters/nope/decision", json={"action": "confirm"})
    assert response.status_code == 404


def _client_for(service: ClusterService) -> TestClient:
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)


class _FakeAnnotationClient:
    """An annotation client that records the rule and returns a written result."""

    def __init__(self) -> None:
        self.submitted: list[object] = []

    def submit(self, rule: object) -> AnnotationResult:
        self.submitted.append(rule)
        return AnnotationResult(
            submitted=True,
            rule_id=99,
            rule_url="https://api.gbif.org/v1/occurrence/experimental/annotation/rule/99",
            ui_url="https://labs.gbif.org/annotations/",
            manual=False,
        )


class _FailingAnnotationClient:
    """An annotation client that always fails, to exercise the manual fallback."""

    def submit(self, rule: object) -> AnnotationResult:
        raise AnnotationError("network down")


def test_confirm_writes_back_when_annotation_client_succeeds() -> None:
    fake = _FakeAnnotationClient()
    test_client = _client_for(_seeded_service(annotation_client=fake))
    try:
        cluster_id = test_client.get("/clusters").json()[0]["cluster_id"]
        body = test_client.post(
            f"/clusters/{cluster_id}/decision", json={"action": "confirm"}
        ).json()
        assert body["decision"]["written_to_gbif"] is True
        assert body["decision"]["annotation_id"] == 99
        assert body["decision"]["annotation_url"].endswith("/rule/99")
        assert len(fake.submitted) == 1
    finally:
        app.dependency_overrides.clear()


def test_confirm_offers_manual_fallback_without_credentials() -> None:
    # The default service uses the no-credentials NullAnnotationClient.
    test_client = _client_for(_seeded_service())
    try:
        cluster_id = test_client.get("/clusters").json()[0]["cluster_id"]
        body = test_client.post(
            f"/clusters/{cluster_id}/decision", json={"action": "confirm"}
        ).json()
        assert body["decision"]["written_to_gbif"] is False
        instructions = body["decision"]["manual_instructions"]
        assert instructions is not None
        assert "labs.gbif.org" in instructions
        assert TAXON in instructions
    finally:
        app.dependency_overrides.clear()


def test_confirm_degrades_to_manual_when_write_back_errors() -> None:
    test_client = _client_for(_seeded_service(annotation_client=_FailingAnnotationClient()))
    try:
        cluster_id = test_client.get("/clusters").json()[0]["cluster_id"]
        body = test_client.post(
            f"/clusters/{cluster_id}/decision", json={"action": "confirm"}
        ).json()
        assert body["decision"]["written_to_gbif"] is False
        assert body["decision"]["manual_instructions"] is not None
    finally:
        app.dependency_overrides.clear()


def test_reject_does_not_write_back() -> None:
    fake = _FakeAnnotationClient()
    test_client = _client_for(_seeded_service(annotation_client=fake))
    try:
        cluster_id = test_client.get("/clusters").json()[0]["cluster_id"]
        body = test_client.post(
            f"/clusters/{cluster_id}/decision", json={"action": "reject"}
        ).json()
        assert body["decision"]["written_to_gbif"] is False
        assert fake.submitted == []  # reject never calls the annotation client
    finally:
        app.dependency_overrides.clear()
