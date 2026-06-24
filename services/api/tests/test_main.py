from fastapi.testclient import TestClient

from taxonguard_api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "0.1.0"
    assert body["core"] == "0.1.0"


def test_annotation_enabled_requires_both_credentials() -> None:
    from taxonguard_api.config import Settings

    assert Settings(gbif_username="u", gbif_password="p").annotation_enabled is True
    assert Settings(gbif_username="u", gbif_password=None).annotation_enabled is False
    assert Settings(gbif_username=None, gbif_password="p").annotation_enabled is False
    assert Settings(gbif_username=None, gbif_password=None).annotation_enabled is False
