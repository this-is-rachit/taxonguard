from __future__ import annotations

from typing import Any

import httpx
import pytest

from taxonguard_core.data.gbif import GBIFError, iter_occurrences, match_taxon_key
from taxonguard_core.data.ingest import ingest_taxon
from taxonguard_core.data.schema import TIDY_COLUMNS, to_tidy_frame, validate

# Raw records in the GBIF occurrence/search shape. Includes records that must be
# dropped: a missing-coordinate record, an out-of-range record, and a duplicate.
RAW: list[dict[str, Any]] = [
    {
        "key": 1,
        "scientificName": "Panthera leo",
        "decimalLatitude": -1.5,
        "decimalLongitude": 35.0,
        "year": 2010,
        "basisOfRecord": "HUMAN_OBSERVATION",
        "countryCode": "KE",
        "coordinateUncertaintyInMeters": 100.0,
    },
    {
        "key": 2,
        "scientificName": "Panthera leo",
        "decimalLatitude": -2.0,
        "decimalLongitude": 34.0,
        "year": 2012,
        "basisOfRecord": "HUMAN_OBSERVATION",
        "countryCode": "TZ",
    },
    {
        "key": 3,
        "scientificName": "Panthera leo",
        "decimalLatitude": None,
        "decimalLongitude": None,
    },
    {
        "key": 4,
        "scientificName": "Panthera leo",
        "decimalLatitude": 999.0,
        "decimalLongitude": 35.0,
    },
    {
        "key": 1,
        "scientificName": "Panthera leo",
        "decimalLatitude": -1.5,
        "decimalLongitude": 35.0,
    },
]


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/species/match"):
        return httpx.Response(
            200,
            json={"usageKey": 5219404, "matchType": "EXACT", "scientificName": "Panthera leo"},
        )
    if request.url.path.endswith("/occurrence/search"):
        offset = int(request.url.params.get("offset", "0"))
        if offset == 0:
            return httpx.Response(200, json={"results": RAW, "endOfRecords": True})
        return httpx.Response(200, json={"results": [], "endOfRecords": True})
    return httpx.Response(404, json={})


def _client() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(_handler))


def test_to_tidy_frame_maps_fields() -> None:
    frame = to_tidy_frame(RAW[:2])
    assert list(frame.columns) == list(TIDY_COLUMNS)
    assert frame.loc[0, "gbif_id"] == 1
    assert frame.loc[0, "scientific_name"] == "Panthera leo"
    assert frame.loc[0, "decimal_latitude"] == pytest.approx(-1.5)
    assert frame.loc[1, "country_code"] == "TZ"


def test_validate_drops_invalid_and_dedupes() -> None:
    tidy = validate(to_tidy_frame(RAW))
    assert len(tidy) == 2
    assert set(tidy["gbif_id"].tolist()) == {1, 2}


def test_match_taxon_key() -> None:
    with _client() as client:
        assert match_taxon_key("Panthera leo", client=client) == 5219404


def test_match_taxon_key_no_match() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"matchType": "NONE"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(GBIFError),
    ):
        match_taxon_key("Notataxon notaname", client=client)


def test_iter_occurrences_respects_max_records() -> None:
    with _client() as client:
        records = list(iter_occurrences(5219404, max_records=3, client=client))
    assert len(records) == 3


def test_iter_occurrences_paginates() -> None:
    pages = {
        0: {"results": [{"key": 10}, {"key": 11}], "endOfRecords": False},
        300: {"results": [{"key": 12}], "endOfRecords": True},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        return httpx.Response(200, json=pages[offset])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        keys = [r["key"] for r in iter_occurrences(1, client=client)]
    assert keys == [10, 11, 12]


def test_ingest_taxon_end_to_end() -> None:
    with _client() as client:
        frame = ingest_taxon("Panthera leo", client=client)
    assert len(frame) == 2
    assert set(frame["gbif_id"].tolist()) == {1, 2}
    assert frame["decimal_latitude"].between(-90, 90).all()
