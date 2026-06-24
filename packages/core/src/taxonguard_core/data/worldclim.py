"""Acquire WorldClim bioclimatic layers into a managed data directory.

WorldClim 2.1 provides 19 bioclimatic variables (BIO1 to BIO19) as GeoTIFF
rasters. This module downloads the 10 arc-minute set, which is small and works
on a CPU, into a data directory that is kept out of Git. The data is free for
academic use; cite Fick and Hijmans (2017). See docs/data-sources.md.

Run as a script to download:

    uv run python -m taxonguard_core.data.worldclim --download

The data directory defaults to ./data (relative to where the command is run) and
can be overridden with the TAXONGUARD_DATA_DIR environment variable.
"""

from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path

import httpx

WORLDCLIM_RESOLUTION = "10m"
WORLDCLIM_ZIP_URL = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_bio.zip"
BIO_VARIABLES: tuple[int, ...] = tuple(range(1, 20))
_DOWNLOAD_TIMEOUT = 600.0


def get_data_dir() -> Path:
    """Return the managed data directory (TAXONGUARD_DATA_DIR or ./data)."""
    return Path(os.environ.get("TAXONGUARD_DATA_DIR", "data"))


def bio_dir(data_dir: Path | None = None) -> Path:
    """Return the directory holding the WorldClim BIO rasters."""
    root = data_dir if data_dir is not None else get_data_dir()
    return root / "worldclim" / f"wc2.1_{WORLDCLIM_RESOLUTION}"


def bio_raster_path(variable: int, data_dir: Path | None = None) -> Path:
    """Return the path to one BIO raster, for example BIO1."""
    return bio_dir(data_dir) / f"wc2.1_{WORLDCLIM_RESOLUTION}_bio_{variable}.tif"


def is_downloaded(data_dir: Path | None = None) -> bool:
    """True if all 19 BIO rasters are present."""
    return all(bio_raster_path(v, data_dir).exists() for v in BIO_VARIABLES)


def download_worldclim(*, data_dir: Path | None = None, force: bool = False) -> Path:
    """Download and extract the WorldClim BIO rasters. Idempotent.

    Returns the directory containing the rasters. Skips the download if the
    rasters are already present, unless force is True.
    """
    target = bio_dir(data_dir)
    if is_downloaded(data_dir) and not force:
        return target

    target.mkdir(parents=True, exist_ok=True)
    zip_path = target / "wc2.1_10m_bio.zip"

    with httpx.stream(
        "GET", WORLDCLIM_ZIP_URL, timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True
    ) as response:
        response.raise_for_status()
        with zip_path.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=1 << 20):
                handle.write(chunk)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target)
    zip_path.unlink(missing_ok=True)

    if not is_downloaded(data_dir):
        raise RuntimeError(f"WorldClim download finished but rasters are missing in {target}.")
    return target


def _main() -> None:
    parser = argparse.ArgumentParser(description="Download WorldClim BIO layers.")
    parser.add_argument("--download", action="store_true", help="Download the rasters if missing.")
    parser.add_argument("--force", action="store_true", help="Re-download even if present.")
    args = parser.parse_args()

    if args.download:
        target = download_worldclim(force=args.force)
        print(f"WorldClim BIO rasters ready in {target}")
    else:
        print(f"Downloaded: {is_downloaded()}. Expected in {bio_dir()}")


if __name__ == "__main__":
    _main()
