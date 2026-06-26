"""Tests for adding a species to Review (POST /taxa) and the review registry.

The dataset builder is patched so the whole flow runs with no network and no data
files: a synthetic enriched frame stands in for the GBIF fetch and climate/land-sea
enrichment, and the data directory is redirected to a temp path so the cache and
the registry are written there. The process-wide service cache is cleared around
each test that rebuilds it so tests do not leak state into one another.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from taxonguard_api import routes
from taxonguard_api.main import app
from taxonguard_api.review_taxa import add_review_taxon, load_added_taxa, registry_path
from taxonguard_api.routes import get_service


def _enriched_frame(name: str) -> pd.DataFrame:
    """A synthetic enriched (unscored) frame with the full climate schema.

    Most rows are ordinary land records; two are clearly wrong (in the sea), so
    scoring flags them and the cluster service forms at least one cluster.
    """
    rng = np.random.default_rng(0)
    n = 60
    bio = {
        f"bio_{i}": np.r_[rng.normal(10.0 * i, 2.0, n), [50.0 * i, 51.0 * i]] for i in range(1, 20)
    }
    return pd.DataFrame(
        {
            "gbif_id": list(range(1, n + 3)),
            "scientific_name": [name] * (n + 2),
            "decimal_latitude": np.r_[rng.uniform(40, 50, n), [0.0, 3.0]],
            "decimal_longitude": np.r_[rng.uniform(-5, 5, n), [0.0, -35.0]],
            "on_land": pd.array([True] * n + [False, False], dtype="boolean"),
            **bio,
        }
    )


@pytest.fixture
def service_cache() -> Iterator[None]:
    """Clear the process-wide cluster service cache before and after a test."""
    get_service.cache_clear()
    yield
    get_service.cache_clear()


def test_add_taxon_caches_persists_and_appears(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, service_cache: None
) -> None:
    monkeypatch.setenv("TAXONGUARD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(routes, "build_taxon_dataset", lambda name: _enriched_frame(name))

    with TestClient(app) as client:
        response = client.post("/taxa", json={"name": "Bufo bufo", "realm": "terrestrial"})
        assert response.status_code == 201
        body = response.json()
        assert body["taxon"] == "Bufo bufo"
        assert body["realm"] == "terrestrial"
        assert body["cluster_count"] >= 1

        # The registry was persisted and the species now shows up in the review set.
        assert registry_path().exists()
        taxa = client.get("/taxa").json()
        assert any(item["taxon"] == "Bufo bufo" for item in taxa)


def test_add_taxon_with_no_records_is_502_and_not_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, service_cache: None
) -> None:
    monkeypatch.setenv("TAXONGUARD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(routes, "build_taxon_dataset", lambda name: pd.DataFrame())

    with TestClient(app) as client:
        response = client.post("/taxa", json={"name": "Nope nope", "realm": "marine"})
        assert response.status_code == 502
    assert not registry_path().exists()


def test_add_taxon_rejects_unknown_realm() -> None:
    with TestClient(app) as client:
        response = client.post("/taxa", json={"name": "Bufo bufo", "realm": "sky"})
        assert response.status_code == 422


def test_add_taxon_rejects_blank_name() -> None:
    with TestClient(app) as client:
        response = client.post("/taxa", json={"name": "   ", "realm": "terrestrial"})
        assert response.status_code == 400


def test_registry_skips_defaults_and_duplicates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TAXONGUARD_DATA_DIR", str(tmp_path))
    assert add_review_taxon("Bufo bufo", "terrestrial") is True
    assert add_review_taxon("Bufo bufo", "terrestrial") is False  # duplicate
    assert add_review_taxon("Panthera leo", "terrestrial") is False  # already a default
    names = [taxon.name for taxon in load_added_taxa()]
    assert names == ["Bufo bufo"]
