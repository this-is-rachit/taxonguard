"""Tests for the clean-my-data endpoints.

Uses the FastAPI TestClient with the clean service overridden to skip the climate
model (no WorldClim in the test environment); the uploaded CSV carries an on_land
column so the realm check runs without the Natural Earth data. No network.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from taxonguard_api.clean_service import CleanService
from taxonguard_api.main import app
from taxonguard_api.routes import get_clean_service

_CSV = (
    "gbifID,scientificName,decimalLatitude,decimalLongitude,on_land\n"
    "1,Rana temporaria,51.50,-0.12,1\n"
    "2,Rana temporaria,52.20,-1.10,1\n"
    "3,Rana temporaria,0.0,0.0,0\n"
    "4,Rana temporaria,45.5,45.5,1\n"
    "5,Rana temporaria,12.34,-40.0,0\n"
    "6,Rana temporaria,50.10,-2.30,1\n"
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    # One shared service so the upload and the later download see the same store.
    service = CleanService(run_environmental=False)
    app.dependency_overrides[get_clean_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _upload(client: TestClient, text: str = _CSV) -> dict:
    response = client.post(
        "/clean", files={"file": ("occurrences.csv", text.encode("utf-8"), "text/csv")}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_clean_report_shape(client: TestClient) -> None:
    report = _upload(client)
    summary = report["summary"]

    assert summary["total_records"] == 6
    assert summary["flagged_records"] == 3  # null island, equal, ocean
    assert summary["clean_records"] == 3
    assert "land/sea realm" in summary["checks_run"]
    assert any(issue["label"] and issue["count"] for issue in summary["issues"])

    assert report["clean_id"]
    assert report["download_url"] == f"/clean/{report['clean_id']}/download"
    assert not report["flagged_truncated"]

    # Flagged records are sorted most suspicious first and carry reasons.
    scores = [record["suspicion_score"] for record in report["flagged"]]
    assert scores == sorted(scores, reverse=True)
    assert report["flagged"][0]["reasons"]


def test_clean_download_returns_csv(client: TestClient) -> None:
    report = _upload(client)
    response = client.get(report["download_url"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    header = body.splitlines()[0]
    assert "flagged" in header
    assert "suspicion_score" in header
    # Never drops rows: header plus all six input records.
    assert len(body.splitlines()) == 7


def test_unknown_clean_id_is_404(client: TestClient) -> None:
    response = client.get("/clean/does-not-exist/download")
    assert response.status_code == 404


def test_bad_upload_is_400(client: TestClient) -> None:
    response = client.post(
        "/clean", files={"file": ("bad.csv", b"name,note\nfoo,bar\n", "text/csv")}
    )
    assert response.status_code == 400
