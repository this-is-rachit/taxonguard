"""Build and cache tidy, enriched, versioned per-taxon datasets.

A taxon dataset is the tidy occurrence frame plus climate columns (bio_1 to
bio_19) and the on_land flag. It is written to a versioned parquet file under the
data directory, with a JSON metadata sidecar, so the engine does not refetch from
GBIF on every run. The schema is documented in docs/data-schema.md.

Build and cache one taxon:

    uv run python -m taxonguard_core.data.cache "Rana temporaria" --max-records 1000

Build and cache the default starter set:

    uv run python -m taxonguard_core.data.cache --all
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

from ..taxa import DEFAULT_TAXA
from .enrich import enrich_with_climate
from .ingest import ingest_taxon
from .landsea import add_land_sea_flag
from .worldclim import BIO_VARIABLES, get_data_dir

# Bump when the dataset schema changes. The cache path includes this version so
# old and new datasets never collide.
SCHEMA_VERSION = 1


def _slug(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def cache_dir(data_dir: Path | None = None) -> Path:
    root = data_dir if data_dir is not None else get_data_dir()
    return root / "cache" / f"v{SCHEMA_VERSION}"


def cache_path(name: str, data_dir: Path | None = None) -> Path:
    return cache_dir(data_dir) / f"{_slug(name)}.parquet"


def metadata_path(name: str, data_dir: Path | None = None) -> Path:
    return cache_dir(data_dir) / f"{_slug(name)}.json"


def build_taxon_dataset(
    name: str,
    *,
    max_records: int = 2000,
    data_dir: Path | None = None,
    variables: tuple[int, ...] = BIO_VARIABLES,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """Fetch, tidy, enrich with climate, and add the land/sea flag for a taxon."""
    frame = ingest_taxon(name, max_records=max_records, client=client)
    frame = enrich_with_climate(frame, data_dir=data_dir, variables=variables)
    return add_land_sea_flag(frame, data_dir=data_dir)


def cache_taxon(
    name: str,
    *,
    max_records: int = 2000,
    data_dir: Path | None = None,
    variables: tuple[int, ...] = BIO_VARIABLES,
    client: httpx.Client | None = None,
    force: bool = False,
) -> Path:
    """Build the dataset for a taxon and write it to the versioned cache.

    Returns the parquet path. Skips the build if the cache exists, unless force.
    """
    path = cache_path(name, data_dir)
    if path.exists() and not force:
        return path

    frame = build_taxon_dataset(
        name,
        max_records=max_records,
        data_dir=data_dir,
        variables=variables,
        client=client,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)

    metadata = {
        "name": name,
        "schema_version": SCHEMA_VERSION,
        "record_count": int(len(frame)),
        "on_land_count": int(frame["on_land"].sum()) if not frame.empty else 0,
        "climate_variables": list(variables),
        "gbif_source": "occurrence search API",
        "worldclim_resolution": "10m",
        "created_utc": datetime.now(UTC).isoformat(),
    }
    metadata_path(name, data_dir).write_text(json.dumps(metadata, indent=2))
    return path


def load_cached(name: str, data_dir: Path | None = None) -> pd.DataFrame | None:
    """Load a cached taxon dataset, or None if it has not been built."""
    path = cache_path(name, data_dir)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Build and cache taxon datasets.")
    parser.add_argument("taxon", nargs="?", help="Scientific name to build.")
    parser.add_argument("--all", action="store_true", help="Build the default set.")
    parser.add_argument("--max-records", type=int, default=2000)
    parser.add_argument("--force", action="store_true", help="Rebuild if cached.")
    args = parser.parse_args()

    if args.all:
        names = [taxon.name for taxon in DEFAULT_TAXA]
    elif args.taxon:
        names = [args.taxon]
    else:
        parser.error("provide a taxon name or --all")

    for name in names:
        path = cache_taxon(name, max_records=args.max_records, force=args.force)
        frame = load_cached(name)
        count = 0 if frame is None else len(frame)
        print(f"{name}: {count} records cached at {path}")


if __name__ == "__main__":
    _main()
