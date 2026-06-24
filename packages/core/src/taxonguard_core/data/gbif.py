"""Client for the GBIF occurrence search and species match APIs.

Uses the public, keyless GBIF REST API (https://api.gbif.org/v1). It is free to
run with no credentials, which keeps the tool reviewable at no cost. For the
final reproducible, citable dataset the GBIF download API (which yields a DOI)
will be used; this search-based client is the practical path for development and
iteration. The HTTP client is injectable so tests run with no network.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

GBIF_API = "https://api.gbif.org/v1"
DEFAULT_TIMEOUT = 30.0

# GBIF caps a single search page at 300 records and offset + limit at 100000.
_PAGE_LIMIT = 300
_MAX_OFFSET = 100_000


class GBIFError(RuntimeError):
    """Raised when GBIF returns no usable result for a request."""


def match_taxon_key(name: str, *, client: httpx.Client | None = None) -> int:
    """Resolve a scientific name to a GBIF taxon (usage) key.

    Raises GBIFError if GBIF cannot match the name.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    try:
        response = client.get(f"{GBIF_API}/species/match", params={"name": name})
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        key = data.get("usageKey")
        if key is None or data.get("matchType") == "NONE":
            raise GBIFError(f"No GBIF taxon match for {name!r}")
        return int(key)
    finally:
        if own_client:
            client.close()


def iter_occurrences(
    taxon_key: int,
    *,
    max_records: int = 2000,
    client: httpx.Client | None = None,
    extra_params: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield raw GBIF occurrence records for a taxon, paginating as needed.

    Only records with coordinates are requested (hasCoordinate=true). Stops at
    max_records, at the end of the result set, or at the GBIF offset ceiling.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    params: dict[str, Any] = {
        "taxonKey": taxon_key,
        "hasCoordinate": "true",
        "limit": _PAGE_LIMIT,
        "offset": 0,
    }
    if extra_params:
        params.update(extra_params)

    fetched = 0
    try:
        while True:
            response = client.get(f"{GBIF_API}/occurrence/search", params=params)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            for record in payload.get("results", []):
                yield record
                fetched += 1
                if fetched >= max_records:
                    return
            if payload.get("endOfRecords", True):
                return
            params["offset"] += _PAGE_LIMIT
            if params["offset"] >= _MAX_OFFSET:
                return
    finally:
        if own_client:
            client.close()
