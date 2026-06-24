"""Acquire Natural Earth land polygons into the managed data directory.

Natural Earth land polygons (public domain) are used to flag whether an
occurrence falls on land or in the sea. The 50 metre resolution is a good balance
between coastline detail and size. The data is fetched from the natural-earth-
vector repository, kept out of Git, and reacquired by this script.

Run as a script to download:

    uv run python -m taxonguard_core.data.naturalearth --download
"""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx

from .worldclim import get_data_dir

LAND_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_land.geojson"
)
_DOWNLOAD_TIMEOUT = 300.0


def natural_earth_dir(data_dir: Path | None = None) -> Path:
    """Return the directory holding the Natural Earth files."""
    root = data_dir if data_dir is not None else get_data_dir()
    return root / "naturalearth"


def land_geojson_path(data_dir: Path | None = None) -> Path:
    """Return the path to the land polygons GeoJSON."""
    return natural_earth_dir(data_dir) / "ne_50m_land.geojson"


def is_downloaded(data_dir: Path | None = None) -> bool:
    """True if the land GeoJSON is present."""
    return land_geojson_path(data_dir).exists()


def download_natural_earth(*, data_dir: Path | None = None, force: bool = False) -> Path:
    """Download the Natural Earth land GeoJSON. Idempotent."""
    path = land_geojson_path(data_dir)
    if path.exists() and not force:
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream(
        "GET", LAND_GEOJSON_URL, timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True
    ) as response:
        response.raise_for_status()
        with path.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=1 << 20):
                handle.write(chunk)
    return path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Download Natural Earth land data.")
    parser.add_argument("--download", action="store_true", help="Download the data if missing.")
    parser.add_argument("--force", action="store_true", help="Re-download even if present.")
    args = parser.parse_args()

    if args.download:
        path = download_natural_earth(force=args.force)
        print(f"Natural Earth land data ready at {path}")
    else:
        print(f"Downloaded: {is_downloaded()}. Expected at {land_geojson_path()}")


if __name__ == "__main__":
    _main()
