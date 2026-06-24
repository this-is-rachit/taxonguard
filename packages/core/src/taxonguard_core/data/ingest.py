"""Ingest occurrence records for a taxon into a tidy, validated DataFrame.

Run as a script to fetch real data from GBIF, for example:

    uv run python -m taxonguard_core.data.ingest "Rana temporaria" --max-records 500

Add --out path.csv to save the tidy table.
"""

from __future__ import annotations

import argparse

import httpx
import pandas as pd

from .gbif import DEFAULT_TIMEOUT, iter_occurrences, match_taxon_key
from .schema import to_tidy_frame, validate


def ingest_taxon(
    name_or_key: str | int,
    *,
    max_records: int = 2000,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """Fetch, tidy, and validate occurrence records for a taxon.

    Accepts a scientific name (resolved via the GBIF match API) or a GBIF taxon
    key. Returns a tidy frame containing only records with valid coordinates.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    try:
        key = (
            name_or_key
            if isinstance(name_or_key, int)
            else match_taxon_key(name_or_key, client=client)
        )
        records = iter_occurrences(key, max_records=max_records, client=client)
        return validate(to_tidy_frame(records))
    finally:
        if own_client:
            client.close()


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and tidy GBIF occurrence records for a taxon."
    )
    parser.add_argument("taxon", help="Scientific name, for example 'Rana temporaria'.")
    parser.add_argument(
        "--max-records",
        type=int,
        default=2000,
        help="Maximum number of records to fetch (default 2000).",
    )
    parser.add_argument("--out", help="Optional CSV path to write the tidy table.")
    args = parser.parse_args()

    frame = ingest_taxon(args.taxon, max_records=args.max_records)
    print(f"{args.taxon}: {len(frame)} valid records with coordinates")
    if not frame.empty:
        print(frame.head(10).to_string(index=False))
    if args.out:
        frame.to_csv(args.out, index=False)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    _main()
