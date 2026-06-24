"""Build a labeled occurrence benchmark by planting known errors.

A benchmark is a list of :class:`BenchmarkCase`, one per taxon. Each case has a
realistic plausible population for a distinct climate niche (a dense, well-sampled
locality included), into which a controlled number of errors of each kind are
planted with a known ``label`` and ``error_type``. The planted errors are placed
to trip exactly one detector each, so the benchmark exercises every signal:

- ``ocean``        -> realm mismatch (a land taxon in the open sea)
- ``null_island``  -> the (0, 0) artifact
- ``equal``        -> latitude equals longitude (a transposition artifact)
- ``gridded``      -> whole-degree centroid (a country or grid centroid)
- ``institution``  -> a coordinate sitting on a museum
- ``climate``      -> a strong climate outlier inside a well-sampled cell

The builder is deterministic and needs no network. The plausible populations are
synthetic but mirror the cached dataset shape (tidy occurrences plus the climate
columns and ``on_land``), so the same harness scores a real GBIF download by
swapping in its frame. Climate niches are terrestrial because the environmental
model is climate-based; the realm check still covers the land/sea axis through
the planted ocean errors.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..taxa import Realm

# Climate variables used throughout the benchmark (bio_1, bio_2). The synthetic
# populations provide these two columns, matching the engine's expectations.
BENCHMARK_VARIABLES: tuple[int, ...] = (1, 2)

# Museum reference points, one per taxon, kept well away from each plausible
# population so only the planted institution error sits on them.
_INSTITUTIONS: dict[str, tuple[float, float]] = {
    "cold": (52.5200, 13.4050),  # Berlin
    "temperate": (48.8566, 2.3522),  # Paris
    "warm": (-1.2921, 36.8219),  # Nairobi
}


@dataclass(frozen=True)
class _Niche:
    """A terrestrial climate niche for a synthetic plausible population."""

    name: str
    lat_range: tuple[float, float]
    lon_range: tuple[float, float]
    # Mean and spread of the two climate variables for the plausible population.
    bio_1: tuple[float, float]
    bio_2: tuple[float, float]
    # A dense, well-sampled locality inside the population (a single grid cell).
    sampled_cell: tuple[float, float]
    # A climate value that is a strong outlier for this niche (planted error).
    outlier_bio: tuple[float, float]


_NICHES: tuple[_Niche, ...] = (
    _Niche(
        name="cold",
        lat_range=(60.0, 72.0),
        lon_range=(10.0, 30.0),
        bio_1=(-40.0, 8.0),
        bio_2=(30.0, 4.0),
        sampled_cell=(64.0, 18.0),
        outlier_bio=(285.0, 140.0),  # tropical heat in a cold-specialist
    ),
    _Niche(
        name="temperate",
        lat_range=(40.0, 52.0),
        lon_range=(-5.0, 15.0),
        bio_1=(110.0, 10.0),
        bio_2=(70.0, 6.0),
        sampled_cell=(45.0, 5.0),
        outlier_bio=(-60.0, 200.0),  # arctic cold in a temperate species
    ),
    _Niche(
        name="warm",
        lat_range=(-25.0, -5.0),
        lon_range=(15.0, 40.0),
        bio_1=(250.0, 12.0),
        bio_2=(110.0, 8.0),
        sampled_cell=(-15.0, 28.0),
        outlier_bio=(-40.0, 250.0),  # polar cold in a tropical species
    ),
)


@dataclass(frozen=True)
class BenchmarkCase:
    """One taxon's labeled population plus the parameters to score it."""

    name: str
    expected_realm: Realm
    institution_points: tuple[tuple[float, float], ...]
    frame: pd.DataFrame = field(repr=False)


# How many errors of each type to plant per taxon. Kept small relative to the
# plausible population so the benchmark reflects realistic error rates.
DEFAULT_ERRORS_PER_TYPE = 4
DEFAULT_PLAUSIBLE = 180
DEFAULT_SAMPLED = 24


def _build_case(
    niche: _Niche,
    *,
    rng: np.random.Generator,
    n_plausible: int,
    n_sampled: int,
    errors_per_type: int,
) -> BenchmarkCase:
    institution = _INSTITUTIONS[niche.name]
    lat: list[float] = []
    lon: list[float] = []
    bio_1: list[float] = []
    bio_2: list[float] = []
    on_land: list[bool] = []
    label: list[str] = []
    error_type: list[str] = []

    def add(latitude: float, longitude: float, b1: float, b2: float, land: bool, kind: str) -> None:
        lat.append(latitude)
        lon.append(longitude)
        bio_1.append(b1)
        bio_2.append(b2)
        on_land.append(land)
        label.append("suspicious" if kind else "plausible")
        error_type.append(kind)

    # Plausible population spread across the niche's range, all on land.
    for _ in range(n_plausible):
        add(
            float(rng.uniform(*niche.lat_range)),
            float(rng.uniform(*niche.lon_range)),
            float(rng.normal(*niche.bio_1)),
            float(rng.normal(*niche.bio_2)),
            True,
            "",
        )

    # A dense, well-sampled locality in one grid cell of the niche.
    cell_lat, cell_lon = niche.sampled_cell
    for _ in range(n_sampled):
        add(
            float(rng.uniform(cell_lat + 0.05, cell_lat + 0.95)),
            float(rng.uniform(cell_lon + 0.05, cell_lon + 0.95)),
            float(rng.normal(niche.bio_1[0], niche.bio_1[1] * 0.75)),
            float(rng.normal(niche.bio_2[0], niche.bio_2[1] * 0.75)),
            True,
            "",
        )

    # Planted errors. The deterministic error types are near-binary and are
    # planted at a fixed count; the climate error is graded by severity (below)
    # because real climate outliers range from mild to extreme.
    for _ in range(errors_per_type):
        # Ocean: a land taxon in the open sea (realm mismatch).
        add(
            float(rng.uniform(*niche.lat_range)),
            float(rng.uniform(*niche.lon_range)),
            float(rng.normal(*niche.bio_1)),
            float(rng.normal(*niche.bio_2)),
            False,
            "ocean",
        )
        # Null island: exactly (0, 0).
        add(
            0.0,
            0.0,
            float(rng.normal(*niche.bio_1)),
            float(rng.normal(*niche.bio_2)),
            False,
            "null_island",
        )
        # Equal coordinates: latitude equals longitude, non-integer to avoid the
        # gridded check also firing.
        v = float(rng.uniform(20.3, 79.7))
        add(v, v, float(rng.normal(*niche.bio_1)), float(rng.normal(*niche.bio_2)), True, "equal")
        # Gridded: both coordinates on whole degrees, and unequal.
        glat = float(rng.integers(int(niche.lat_range[0]), int(niche.lat_range[1])))
        glon = float(rng.integers(int(niche.lon_range[0]) + 1, int(niche.lon_range[1])))
        glon = glon if glon != glat else glon + 1.0
        add(
            glat,
            glon,
            float(rng.normal(*niche.bio_1)),
            float(rng.normal(*niche.bio_2)),
            True,
            "gridded",
        )
        # Institution: sitting on the museum coordinate.
        add(
            institution[0],
            institution[1],
            float(rng.normal(*niche.bio_1)),
            float(rng.normal(*niche.bio_2)),
            True,
            "institution",
        )

    # Climate errors, graded by severity in standard deviations from the niche
    # mean toward the outlier direction. The mildest (about 3 sigma) sit near the
    # tail of the plausible population and are genuinely hard; the strongest are
    # far outliers. All are placed inside the well-sampled cell so sampling effort
    # does not down-weight them.
    dir_1 = 1.0 if niche.outlier_bio[0] > niche.bio_1[0] else -1.0
    dir_2 = 1.0 if niche.outlier_bio[1] > niche.bio_2[0] else -1.0
    for severity in np.linspace(3.0, 11.0, errors_per_type):
        add(
            float(rng.uniform(cell_lat + 0.05, cell_lat + 0.95)),
            float(rng.uniform(cell_lon + 0.05, cell_lon + 0.95)),
            niche.bio_1[0] + float(severity) * niche.bio_1[1] * dir_1,
            niche.bio_2[0] + float(severity) * niche.bio_2[1] * dir_2,
            True,
            "climate",
        )

    frame = pd.DataFrame(
        {
            "gbif_id": list(range(1, len(lat) + 1)),
            "scientific_name": f"Benchmark {niche.name} taxon",
            "decimal_latitude": lat,
            "decimal_longitude": lon,
            "bio_1": bio_1,
            "bio_2": bio_2,
            "on_land": pd.array(on_land, dtype="boolean"),
            "label": label,
            "error_type": error_type,
            "taxon": niche.name,
        }
    )
    return BenchmarkCase(
        name=niche.name,
        expected_realm="terrestrial",
        institution_points=(institution,),
        frame=frame,
    )


def build_benchmark(
    seed: int = 0,
    *,
    n_plausible: int = DEFAULT_PLAUSIBLE,
    n_sampled: int = DEFAULT_SAMPLED,
    errors_per_type: int = DEFAULT_ERRORS_PER_TYPE,
) -> list[BenchmarkCase]:
    """Build the labeled benchmark: one case per climate niche.

    Deterministic for a given seed. Each case carries a ``label`` column
    ('plausible' or 'suspicious'), an ``error_type`` column, and a ``taxon``
    column, plus the climate columns and ``on_land`` the engine expects.
    """
    rng = np.random.default_rng(seed)
    return [
        _build_case(
            niche,
            rng=rng,
            n_plausible=n_plausible,
            n_sampled=n_sampled,
            errors_per_type=errors_per_type,
        )
        for niche in _NICHES
    ]


def benchmark_label_counts(cases: Sequence[BenchmarkCase]) -> dict[str, int]:
    """Total plausible and suspicious record counts across all cases."""
    plausible = 0
    suspicious = 0
    for case in cases:
        labels = case.frame["label"]
        plausible += int((labels == "plausible").sum())
        suspicious += int((labels == "suspicious").sum())
    return {"plausible": plausible, "suspicious": suspicious, "total": plausible + suspicious}
