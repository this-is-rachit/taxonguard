"""Tests for the on-demand species scoring and suggest endpoints.

The dataset builder is injected with a synthetic frame and the GBIF suggest call
is served by an httpx MockTransport, so nothing here touches the network or the
WorldClim and Natural Earth data files.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from taxonguard_api.main import app
from taxonguard_api.routes import get_score_service
from taxonguard_api.score_service import SpeciesScoreError, TaxonScoreService

TAXON = "Rana temporaria"


def _synthetic_frame(name: str, max_records: int) -> pd.DataFrame:
    """A small enriched frame: plausible inland records plus planted errors."""
    rng = np.random.default_rng(0)
    n = 15
    lat = [*rng.uniform(48.0, 56.0, n), 0.0, 45.5, 40.0, 12.34]
    lon = [*rng.uniform(-6.0, 2.0, n), 0.0, 45.5, -3.0, -40.0]
    # null island is in the ocean; equal and gridded are on land; the last is ocean.
    on_land = [True] * n + [False, True, True, False]
    total = n + 4
    data: dict[str, object] = {
        "gbif_id": list(range(1, total + 1)),
        "scientific_name": [name] * total,
        "decimal_latitude": lat,
        "decimal_longitude": lon,
        "on_land": pd.array(on_land, dtype="boolean"),
    }
    for variable in range(1, 20):
        data[f"bio_{variable}"] = list(rng.normal(100.0, 10.0, total))
    return pd.DataFrame(data)


def _suggest_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/species/suggest")
        return httpx.Response(
            200,
            json=[
                {
                    "key": 2430781,
                    "scientificName": "Rana temporaria Linnaeus, 1758",
                    "canonicalName": "Rana temporaria",
                    "rank": "SPECIES",
                    "kingdom": "Animalia",
                },
                {
                    "key": 2430782,
                    "scientificName": "Rana arvalis",
                    "rank": "SPECIES",
                    "kingdom": "Animalia",
                },
            ],
        )

    return httpx.MockTransport(handler)


@pytest.fixture
def client() -> Iterator[TestClient]:
    service = TaxonScoreService(
        builder=_synthetic_frame,
        suggest_client=httpx.Client(transport=_suggest_transport()),
    )
    app.dependency_overrides[get_score_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_suggest_returns_names(client: TestClient) -> None:
    response = client.get("/species/suggest", params={"q": "rana"})
    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"].startswith("Rana temporaria")
    assert body[0]["key"] == 2430781


def test_suggest_empty_query_is_empty(client: TestClient) -> None:
    response = client.get("/species/suggest", params={"q": ""})
    assert response.status_code == 200
    assert response.json() == []


def test_score_species_report(client: TestClient) -> None:
    response = client.get("/score", params={"taxon": TAXON})
    assert response.status_code == 200, response.text
    report = response.json()

    assert report["taxon"] == TAXON
    summary = report["summary"]
    assert summary["total_records"] == 19
    # null island (ocean), the ocean record, equal, and gridded are all flagged.
    assert summary["flagged_records"] == 4
    assert "climate niche" in summary["checks_run"]

    issue_text = " ".join(issue["label"] for issue in summary["issues"])
    assert "realm mismatch" in issue_text
    assert "null-island" in issue_text

    scores = [record["suspicion_score"] for record in report["records"]]
    assert scores == sorted(scores, reverse=True)


def test_score_caches_by_name() -> None:
    calls = {"n": 0}

    def counting_builder(name: str, max_records: int) -> pd.DataFrame:
        calls["n"] += 1
        return _synthetic_frame(name, max_records)

    service = TaxonScoreService(builder=counting_builder)
    service.score(TAXON)
    service.score(TAXON)
    assert calls["n"] == 1


def test_empty_taxon_is_400(client: TestClient) -> None:
    response = client.get("/score", params={"taxon": "   "})
    assert response.status_code == 400


def test_builder_failure_is_502(client: TestClient) -> None:
    def failing_builder(name: str, max_records: int) -> pd.DataFrame:
        raise RuntimeError("gbif down")

    service = TaxonScoreService(builder=failing_builder)
    app.dependency_overrides[get_score_service] = lambda: service
    response = client.get("/score", params={"taxon": TAXON})
    app.dependency_overrides.clear()
    assert response.status_code == 502


def test_suggest_helper_handles_http_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    service = TaxonScoreService(suggest_client=httpx.Client(transport=httpx.MockTransport(boom)))
    with pytest.raises(SpeciesScoreError):
        service.suggest("rana")
