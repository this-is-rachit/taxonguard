"""Tests for the GBIF download client (data/download.py).

The download flow is live and asynchronous in production, so these tests drive the
species-match, request, status, and result endpoints with an httpx MockTransport
and a no-op sleep. No network is touched and no time is spent waiting; the tests
assert the request shape (auth, predicate, format) and the parsing of the
SIMPLE_CSV result and the DOI.
"""

from __future__ import annotations

import io
import zipfile

import httpx
import pandas as pd
import pytest

from taxonguard_core.data.download import (
    DownloadError,
    build_predicate,
    build_request_body,
    download_taxon,
    read_simple_csv_zip,
    tidy_from_download_csv,
    wait_for_download,
)

DOWNLOAD_KEY = "0001234-230101000000000"
DOI = "10.15468/dl.testdoi"


def _simple_csv_zip() -> bytes:
    """A minimal SIMPLE_CSV (tab-delimited) archive with three records."""
    header = (
        "gbifID\tscientificName\tdecimalLatitude\tdecimalLongitude\t"
        "year\tbasisOfRecord\tcountryCode\tcoordinateUncertaintyInMeters"
    )
    rows = [
        "1\tRana temporaria\t51.5\t-0.1\t2020\tHUMAN_OBSERVATION\tGB\t10",
        "2\tRana temporaria\t52.0\t-1.0\t2019\tHUMAN_OBSERVATION\tGB\t",
        # No coordinates: dropped by validation.
        "3\tRana temporaria\t\t\t2018\tHUMAN_OBSERVATION\tGB\t",
    ]
    csv = "\n".join([header, *rows]) + "\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{DOWNLOAD_KEY}.csv", csv)
    return buffer.getvalue()


def _mock_client(zip_bytes: bytes, *, status_sequence: list[str]) -> httpx.Client:
    state = {"status_calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/species/match"):
            return httpx.Response(200, json={"usageKey": 2431885, "matchType": "EXACT"})
        if path.endswith("/download/request"):
            assert request.headers.get("authorization", "").startswith("Basic ")
            body = request.read().decode()
            assert "TAXON_KEY" in body and "2431885" in body
            assert "HAS_COORDINATE" in body
            assert "SIMPLE_CSV" in body
            return httpx.Response(201, text=DOWNLOAD_KEY)
        if path.endswith(f"/download/{DOWNLOAD_KEY}"):
            index = min(state["status_calls"], len(status_sequence) - 1)
            status = status_sequence[index]
            state["status_calls"] += 1
            payload = {"status": status}
            if status == "SUCCEEDED":
                payload.update(
                    {
                        "doi": DOI,
                        "totalRecords": 2,
                        "downloadLink": (
                            "https://api.gbif.org/v1/occurrence/download/request/"
                            f"{DOWNLOAD_KEY}.zip"
                        ),
                    }
                )
            return httpx.Response(200, json=payload)
        if path.endswith(f"{DOWNLOAD_KEY}.zip"):
            return httpx.Response(200, content=zip_bytes)
        return httpx.Response(404, text=f"unexpected {path}")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_build_predicate_combines_filters() -> None:
    predicate = build_predicate(2431885, country="GB")
    assert predicate["type"] == "and"
    keys = {p.get("key") for p in predicate["predicates"]}
    assert keys == {"TAXON_KEY", "HAS_COORDINATE", "COUNTRY"}
    values = {p["key"]: p["value"] for p in predicate["predicates"]}
    assert values["TAXON_KEY"] == "2431885"
    assert values["COUNTRY"] == "GB"


def test_build_predicate_single_when_unfiltered() -> None:
    predicate = build_predicate(1, has_coordinate=False)
    assert predicate == {"type": "equals", "key": "TAXON_KEY", "value": "1"}


def test_build_request_body_defaults_creator_and_format() -> None:
    body = build_request_body({"type": "equals"}, creator="acct")
    assert body["creator"] == "acct"
    assert body["format"] == "SIMPLE_CSV"
    assert body["sendNotification"] is False


def test_tidy_from_download_csv_maps_and_validates() -> None:
    raw = pd.DataFrame(
        {
            "gbifID": ["10", "11"],
            "scientificName": ["Rana temporaria", "Rana temporaria"],
            "decimalLatitude": ["51.0", "52.0"],
            "decimalLongitude": ["-1.0", "-2.0"],
            "year": ["2020", "2021"],
            "basisOfRecord": ["HUMAN_OBSERVATION", "HUMAN_OBSERVATION"],
            "countryCode": ["GB", "GB"],
            "coordinateUncertaintyInMeters": ["10", ""],
        }
    )
    tidy = tidy_from_download_csv(raw)
    assert list(tidy.columns)[:4] == [
        "gbif_id",
        "scientific_name",
        "decimal_latitude",
        "decimal_longitude",
    ]
    assert tidy["gbif_id"].dtype == "Int64"
    assert len(tidy) == 2


def test_read_simple_csv_zip_drops_records_without_coordinates() -> None:
    frame = read_simple_csv_zip(_simple_csv_zip())
    # Three rows in, one without coordinates, so two valid records out.
    assert len(frame) == 2
    assert set(frame["gbif_id"].tolist()) == {1, 2}


def test_download_taxon_returns_frame_and_doi_without_network() -> None:
    slept: list[float] = []
    client = _mock_client(_simple_csv_zip(), status_sequence=["RUNNING", "SUCCEEDED"])
    result = download_taxon(
        "Rana temporaria",
        username="acct",
        password="secret",
        country="GB",
        client=client,
        sleep=slept.append,
        poll_interval=5.0,
    )
    assert result.doi == DOI
    assert result.download_key == DOWNLOAD_KEY
    assert len(result.frame) == 2
    # One RUNNING poll before SUCCEEDED means exactly one sleep.
    assert slept == [5.0]


def test_wait_for_download_raises_on_failure_state() -> None:
    client = _mock_client(_simple_csv_zip(), status_sequence=["FAILED"])
    with pytest.raises(DownloadError):
        wait_for_download(DOWNLOAD_KEY, client=client, sleep=lambda _: None)


def test_wait_for_download_times_out() -> None:
    client = _mock_client(_simple_csv_zip(), status_sequence=["RUNNING"])
    with pytest.raises(DownloadError):
        wait_for_download(
            DOWNLOAD_KEY, client=client, sleep=lambda _: None, poll_interval=10.0, max_wait=10.0
        )
