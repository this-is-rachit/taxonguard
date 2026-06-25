"""Download a citable, DOI-backed occurrence set from the GBIF download API.

The keyless search API (:mod:`taxonguard_core.data.gbif`) is the right tool for
development, but it assigns no DOI. A reproducible, citable benchmark needs the
GBIF download API, which runs an asynchronous query against the full GBIF index
and mints a DOI for the result. This module builds the download predicate, submits
it over HTTP Basic Auth, polls until the download is ready, fetches the SIMPLE_CSV
result, and returns a tidy occurrence frame together with the assigned DOI.

The whole flow is live and asynchronous (a request takes a few minutes to
prepare), and api.gbif.org is not reachable from CI, so the network calls sit
behind an injectable httpx client and an injectable sleep function. Tests drive
the request, status, and result endpoints with an httpx ``MockTransport`` and a
no-op sleep, so the request and response shapes are validated with no network and
no waiting. The user runs the live download on their own machine, exactly as with
the Phase 6 write-back.

Run a live download (needs a free GBIF account; the username is the account name,
not the email):

    uv run python -m taxonguard_core.data.download "Rana temporaria" \
        --country GB --username ACCOUNT --password SECRET

Add ``--build`` to also enrich the result with climate and the land/sea flag and
write a cached parquet plus a JSON sidecar carrying the DOI, ready for the
real-data benchmark in :mod:`taxonguard_core.eval`.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import time
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from .gbif import DEFAULT_TIMEOUT, match_taxon_key
from .schema import TIDY_COLUMNS, validate

# The GBIF occurrence download service, behind the main API gateway. The request,
# status, and result endpoints all hang off this base.
DOWNLOAD_API_BASE = "https://api.gbif.org/v1/occurrence/download"

# SIMPLE_CSV is the smallest download format and is tab-delimited (a long-standing
# GBIF quirk: the name says CSV, the file is TSV). It carries every column the tidy
# schema needs.
SIMPLE_CSV = "SIMPLE_CSV"

# Download lifecycle states. Anything in the failure set ends the poll with an
# error; SUCCEEDED ends it with a result.
_SUCCEEDED = "SUCCEEDED"
_TERMINAL_FAILURES: frozenset[str] = frozenset(
    {"KILLED", "FAILED", "CANCELLED", "SUSPENDED", "FILE_ERASED"}
)

_DEFAULT_POLL_INTERVAL = 20.0
_DEFAULT_MAX_WAIT = 1800.0
_RESULT_TIMEOUT = 600.0

# Tidy column name -> SIMPLE_CSV column name. The download format names a few
# columns differently from the search API (notably gbifID instead of key), so the
# mapping is kept here rather than reusing the search-API mapping in schema.py.
_DOWNLOAD_FIELDS: dict[str, str] = {
    "gbif_id": "gbifID",
    "scientific_name": "scientificName",
    "decimal_latitude": "decimalLatitude",
    "decimal_longitude": "decimalLongitude",
    "year": "year",
    "basis_of_record": "basisOfRecord",
    "country_code": "countryCode",
    "coordinate_uncertainty_m": "coordinateUncertaintyInMeters",
}


class DownloadError(RuntimeError):
    """Raised when a GBIF download cannot be requested, finished, or fetched."""


@dataclass(frozen=True)
class DownloadResult:
    """The outcome of a finished GBIF download.

    ``frame`` is the tidy occurrence frame (the same schema the rest of the
    pipeline uses). ``doi`` is the citable identifier GBIF mints for the download,
    or None if the status payload carried none. ``predicate`` is the exact query
    that produced the set, kept so it can be recorded alongside the DOI.
    """

    frame: pd.DataFrame = field(repr=False)
    doi: str | None
    download_key: str
    total_records: int
    predicate: dict[str, Any]


def build_predicate(
    taxon_key: int,
    *,
    country: str | None = None,
    geometry: str | None = None,
    has_coordinate: bool = True,
) -> dict[str, Any]:
    """Build a GBIF download predicate for one taxon.

    The predicate is an equals on TAXON_KEY, optionally AND-ed with
    HAS_COORDINATE, a COUNTRY filter (an ISO 3166-1 alpha-2 code), and a WKT
    geometry (a within predicate). The country or geometry filter is the practical
    way to cap a wide-ranging taxon to a few thousand records.
    """
    predicates: list[dict[str, Any]] = [
        {"type": "equals", "key": "TAXON_KEY", "value": str(taxon_key)},
    ]
    if has_coordinate:
        predicates.append({"type": "equals", "key": "HAS_COORDINATE", "value": "true"})
    if country is not None:
        predicates.append({"type": "equals", "key": "COUNTRY", "value": country})
    if geometry is not None:
        predicates.append({"type": "within", "geometry": geometry})

    if len(predicates) == 1:
        return predicates[0]
    return {"type": "and", "predicates": predicates}


def build_request_body(
    predicate: dict[str, Any],
    *,
    creator: str,
    notification_addresses: Sequence[str] = (),
    download_format: str = SIMPLE_CSV,
) -> dict[str, Any]:
    """Build the JSON body for the download request endpoint."""
    return {
        "creator": creator,
        "sendNotification": False,
        "notificationAddresses": list(notification_addresses),
        "format": download_format,
        "predicate": predicate,
    }


def request_download(
    predicate: dict[str, Any],
    *,
    username: str,
    password: str,
    creator: str | None = None,
    client: httpx.Client | None = None,
    base_url: str = DOWNLOAD_API_BASE,
    download_format: str = SIMPLE_CSV,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """POST a download request and return the assigned download key.

    The request endpoint replies with the key as a plain-text body. ``creator``
    defaults to the username, which GBIF expects to match the authenticated
    account.
    """
    body = build_request_body(
        predicate,
        creator=creator if creator is not None else username,
        download_format=download_format,
    )
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        response = client.post(
            f"{base_url}/request",
            json=body,
            auth=(username, password),
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise DownloadError(f"GBIF download request failed: {error}") from error
    finally:
        if own_client:
            client.close()

    key = response.text.strip().strip('"')
    if not key:
        raise DownloadError("GBIF download request returned an empty key.")
    return key


def get_download_status(
    download_key: str,
    *,
    client: httpx.Client | None = None,
    base_url: str = DOWNLOAD_API_BASE,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Fetch the status payload for a download. Public, so it needs no auth."""
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        response = client.get(f"{base_url}/{download_key}")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload
    except httpx.HTTPError as error:
        raise DownloadError(f"GBIF download status check failed: {error}") from error
    finally:
        if own_client:
            client.close()


def wait_for_download(
    download_key: str,
    *,
    client: httpx.Client | None = None,
    base_url: str = DOWNLOAD_API_BASE,
    sleep: Callable[[float], None] = time.sleep,
    poll_interval: float = _DEFAULT_POLL_INTERVAL,
    max_wait: float = _DEFAULT_MAX_WAIT,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Poll the status endpoint until the download succeeds, fails, or times out.

    Returns the final status payload (which carries the DOI and the result link).
    Raises DownloadError on a terminal failure state or if max_wait is exceeded.
    The sleep function is injectable so tests poll instantly.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    waited = 0.0
    try:
        while True:
            payload = get_download_status(download_key, client=client, base_url=base_url)
            status = str(payload.get("status", "")).upper()
            if status == _SUCCEEDED:
                return payload
            if status in _TERMINAL_FAILURES:
                raise DownloadError(f"GBIF download {download_key} ended in state {status!r}.")
            if waited >= max_wait:
                raise DownloadError(
                    f"GBIF download {download_key} not ready after {max_wait:g}s "
                    f"(last state {status!r})."
                )
            sleep(poll_interval)
            waited += poll_interval
    finally:
        if own_client:
            client.close()


def tidy_from_download_csv(raw: pd.DataFrame) -> pd.DataFrame:
    """Map a SIMPLE_CSV frame onto the tidy schema and validate it.

    Only the tidy columns are kept; missing source columns are filled with NA so
    the schema is always complete. SIMPLE_CSV represents missing values as empty
    strings, so numeric columns are coerced (empty or non-numeric becomes NA)
    before the schema dtypes are applied. Validation then drops records without
    usable coordinates and duplicate ids, exactly as for the search-API path.
    """
    numeric = {
        "gbif_id",
        "decimal_latitude",
        "decimal_longitude",
        "year",
        "coordinate_uncertainty_m",
    }
    columns: dict[str, pd.Series] = {}
    for tidy, source in _DOWNLOAD_FIELDS.items():
        series = raw[source] if source in raw.columns else pd.Series([pd.NA] * len(raw))
        if tidy in numeric:
            series = pd.to_numeric(series, errors="coerce")
        columns[tidy] = series

    frame = pd.DataFrame(columns, columns=list(TIDY_COLUMNS))
    frame = frame.astype(TIDY_COLUMNS)
    return validate(frame)


def read_simple_csv_zip(content: bytes) -> pd.DataFrame:
    """Extract the single CSV from a SIMPLE_CSV download zip into a tidy frame.

    SIMPLE_CSV is tab-delimited. The archive holds one ``.csv`` member; its rows
    are mapped onto the tidy schema.
    """
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise DownloadError("GBIF download archive contained no CSV file.")
        with archive.open(csv_names[0]) as handle:
            raw = pd.read_csv(handle, sep="\t", dtype="object", on_bad_lines="skip")
    return tidy_from_download_csv(raw)


def fetch_download_frame(
    download_link: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = _RESULT_TIMEOUT,
) -> pd.DataFrame:
    """Download and parse the SIMPLE_CSV result archive into a tidy frame."""
    own_client = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = client.get(download_link)
        response.raise_for_status()
        content = response.content
    except httpx.HTTPError as error:
        raise DownloadError(f"GBIF download result fetch failed: {error}") from error
    finally:
        if own_client:
            client.close()
    return read_simple_csv_zip(content)


def download_taxon(
    name_or_key: str | int,
    *,
    username: str,
    password: str,
    country: str | None = None,
    geometry: str | None = None,
    client: httpx.Client | None = None,
    base_url: str = DOWNLOAD_API_BASE,
    sleep: Callable[[float], None] = time.sleep,
    poll_interval: float = _DEFAULT_POLL_INTERVAL,
    max_wait: float = _DEFAULT_MAX_WAIT,
    timeout: float = DEFAULT_TIMEOUT,
) -> DownloadResult:
    """Run a full GBIF download for a taxon and return the tidy frame plus the DOI.

    Resolves the taxon name to a backbone key (unless a key is given), builds the
    predicate, requests the download, waits for it, and fetches the result. The
    httpx client and the sleep function are injectable so the whole flow runs in
    tests with no network and no waiting.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        taxon_key = (
            name_or_key
            if isinstance(name_or_key, int)
            else match_taxon_key(name_or_key, client=client)
        )
        predicate = build_predicate(taxon_key, country=country, geometry=geometry)
        download_key = request_download(
            predicate,
            username=username,
            password=password,
            client=client,
            base_url=base_url,
            timeout=timeout,
        )
        status = wait_for_download(
            download_key,
            client=client,
            base_url=base_url,
            sleep=sleep,
            poll_interval=poll_interval,
            max_wait=max_wait,
            timeout=timeout,
        )
        link = status.get("downloadLink") or f"{base_url}/request/{download_key}.zip"
        frame = fetch_download_frame(link, client=client)
    finally:
        if own_client:
            client.close()

    doi = status.get("doi")
    total = status.get("totalRecords")
    return DownloadResult(
        frame=frame,
        doi=str(doi) if doi is not None else None,
        download_key=download_key,
        total_records=int(total) if total is not None else len(frame),
        predicate=predicate,
    )


def build_real_dataset(
    name: str,
    *,
    username: str,
    password: str,
    country: str | None = None,
    geometry: str | None = None,
    data_dir: Path | None = None,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[pd.DataFrame, DownloadResult]:
    """Download a taxon, enrich it with climate and the land/sea flag, and return it.

    The returned frame matches the cached dataset shape (tidy occurrences plus
    bio_1..19 and on_land), so it drops straight into the real-data benchmark. The
    climate and land/sea steps are imported lazily so importing this module does
    not pull in the raster stack. Requires WorldClim and Natural Earth to be
    downloaded already (see worldclim.py and naturalearth.py).
    """
    from .enrich import enrich_with_climate
    from .landsea import add_land_sea_flag

    result = download_taxon(
        name,
        username=username,
        password=password,
        country=country,
        geometry=geometry,
        client=client,
        sleep=sleep,
    )
    enriched = enrich_with_climate(result.frame, data_dir=data_dir)
    enriched = add_land_sea_flag(enriched, data_dir=data_dir)
    return enriched, result


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a citable, DOI-backed occurrence set from GBIF."
    )
    parser.add_argument("taxon", help="Scientific name, for example 'Rana temporaria'.")
    parser.add_argument(
        "--country", help="ISO 3166-1 alpha-2 country code to cap the set, e.g. GB."
    )
    parser.add_argument("--geometry", help="Optional WKT polygon to restrict the area.")
    parser.add_argument(
        "--username",
        default=os.environ.get("GBIF_USERNAME") or os.environ.get("TAXONGUARD_GBIF_USERNAME"),
        help="GBIF account name (defaults to the GBIF_USERNAME environment variable).",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("GBIF_PASSWORD") or os.environ.get("TAXONGUARD_GBIF_PASSWORD"),
        help="GBIF password (defaults to the GBIF_PASSWORD environment variable).",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Also enrich with climate and the land/sea flag and cache a parquet plus DOI sidecar.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/real"),
        help="Directory for the cached parquet and the DOI sidecar (with --build).",
    )
    args = parser.parse_args()

    if not args.username or not args.password:
        raise SystemExit(
            "GBIF credentials are required. Pass --username/--password or set "
            "GBIF_USERNAME and GBIF_PASSWORD."
        )

    slug = args.taxon.strip().lower().replace(" ", "_")
    if args.build:
        frame, result = build_real_dataset(
            args.taxon,
            username=args.username,
            password=args.password,
            country=args.country,
            geometry=args.geometry,
        )
        args.out.mkdir(parents=True, exist_ok=True)
        parquet_path = args.out / f"{slug}.parquet"
        frame.to_parquet(parquet_path, index=False)
        sidecar = {
            "taxon": args.taxon,
            "doi": result.doi,
            "download_key": result.download_key,
            "total_records": result.total_records,
            "record_count": int(len(frame)),
            "predicate": result.predicate,
        }
        (args.out / f"{slug}.json").write_text(json.dumps(sidecar, indent=2))
        print(
            f"{args.taxon}: {len(frame)} enriched records cached at {parquet_path} "
            f"(DOI {result.doi})"
        )
    else:
        result = download_taxon(
            args.taxon,
            username=args.username,
            password=args.password,
            country=args.country,
            geometry=args.geometry,
        )
        print(
            f"{args.taxon}: {len(result.frame)} records, download key "
            f"{result.download_key}, DOI {result.doi}"
        )


if __name__ == "__main__":
    _main()
