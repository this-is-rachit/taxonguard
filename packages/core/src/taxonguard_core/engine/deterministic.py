"""Deterministic checks: cheap, rule-based flags for implausible coordinates.

These checks complement the environmental outlier model (step 19) with fast,
explainable rules that need no model. Each check adds one boolean column and
contributes a short reason code, so the calibrated fusion (step 23) gets a clear
per-signal breakdown. Every check flags a record as suspicious; none ever calls
a record wrong, and none deletes anything.

Checks:

- realm mismatch: a terrestrial or freshwater taxon recorded in the open sea, or
  a marine taxon recorded on land. Uses the on_land flag (from the land or sea
  step) and the taxon's expected_realm. This is the canonical "frog in the
  ocean" case.
- zero coordinates: the record sits at exactly (0, 0), the null-island artifact.
- equal coordinates: latitude equals longitude, a common transposition or
  placeholder artifact.
- gridded coordinates: both latitude and longitude fall on whole degrees, which
  is a sign of a country or grid centroid rather than a real observation.
- institution coordinates: the record sits on top of a known biodiversity
  institution (a museum or herbarium), so the coordinate is the holding
  institution, not the collection site. The reference points are supplied by the
  caller; the public-domain institution list can be loaded here later without
  changing the engine.

Flag a cached taxon and print its most clearly implausible records:

    uv run python -m taxonguard_core.engine.deterministic "Rana temporaria" --top 10
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import pandas as pd

from ..data.cache import load_cached
from ..taxa import DEFAULT_TAXA, Realm

# Reason codes, also used as the per-check column suffixes.
REALM_MISMATCH = "realm_mismatch"
ZERO_COORDINATES = "zero_coordinates"
EQUAL_COORDINATES = "equal_coordinates"
GRIDDED_COORDINATES = "gridded_coordinates"
INSTITUTION_COORDINATES = "institution_coordinates"

# Per-check boolean columns, in reason order.
DETERMINISTIC_FLAG_COLUMNS: tuple[str, ...] = (
    f"det_{REALM_MISMATCH}",
    f"det_{ZERO_COORDINATES}",
    f"det_{EQUAL_COORDINATES}",
    f"det_{GRIDDED_COORDINATES}",
    f"det_{INSTITUTION_COORDINATES}",
)

# Aggregate columns.
DET_FLAG_COLUMN = "det_flag"
DET_REASONS_COLUMN = "det_reasons"

# A point this close to a reference coordinate is treated as sitting on it. About
# one kilometre at the equator; small enough to avoid catching nearby real
# records, large enough to absorb rounding.
DEFAULT_INSTITUTION_TOLERANCE_DEG = 0.01

# Realms that are expected to occur on land. Marine is the complement.
_LAND_REALMS: frozenset[Realm] = frozenset({"terrestrial", "freshwater"})


def _coordinate_arrays(
    frame: pd.DataFrame,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    for column in ("decimal_latitude", "decimal_longitude"):
        if column not in frame.columns:
            raise KeyError(f"frame is missing coordinate column: {column!r}")
    latitude = frame["decimal_latitude"].to_numpy(dtype="float64")
    longitude = frame["decimal_longitude"].to_numpy(dtype="float64")
    return latitude, longitude


def _realm_mismatch_mask(
    frame: pd.DataFrame, expected_realm: Realm | None
) -> npt.NDArray[np.bool_]:
    """True where on_land disagrees with the realm. All False if undeterminable."""
    count = len(frame)
    if expected_realm is None or "on_land" not in frame.columns:
        return np.zeros(count, dtype=bool)

    on_land = frame["on_land"]
    known = on_land.notna().to_numpy(dtype=bool)
    on_land_values = on_land.fillna(False).to_numpy(dtype=bool)
    expects_land = expected_realm in _LAND_REALMS
    return np.asarray(known & (on_land_values != expects_land), dtype=bool)


def _institution_mask(
    latitude: npt.NDArray[np.float64],
    longitude: npt.NDArray[np.float64],
    reference_points: Sequence[tuple[float, float]],
    tolerance_deg: float,
) -> npt.NDArray[np.bool_]:
    """True where a point sits within tolerance of any reference coordinate."""
    mask = np.zeros(latitude.shape[0], dtype=bool)
    for ref_lat, ref_lon in reference_points:
        near = (np.abs(latitude - ref_lat) <= tolerance_deg) & (
            np.abs(longitude - ref_lon) <= tolerance_deg
        )
        mask |= near
    return mask


def add_deterministic_flags(
    frame: pd.DataFrame,
    *,
    expected_realm: Realm | None = None,
    institution_points: Sequence[tuple[float, float]] = (),
    institution_tolerance_deg: float = DEFAULT_INSTITUTION_TOLERANCE_DEG,
) -> pd.DataFrame:
    """Return a copy of frame with deterministic flag columns added.

    Adds one boolean column per check (see DETERMINISTIC_FLAG_COLUMNS), an
    aggregate det_flag (True if any check fired), and det_reasons (a comma
    separated list of the reason codes that fired). The realm mismatch check is
    only applied when expected_realm is given and the on_land column is present;
    otherwise it is left False. Coordinate columns must be present.
    """
    out = frame.copy()
    latitude, longitude = _coordinate_arrays(out)
    count = len(out)

    finite = np.isfinite(latitude) & np.isfinite(longitude)

    zero = finite & (latitude == 0.0) & (longitude == 0.0)
    # Exclude the null-island point from the equal and gridded checks so each
    # record carries the single clearest reason.
    equal = finite & ~zero & (latitude == longitude)
    on_grid = (
        finite
        & ~zero
        & np.isclose(latitude, np.round(latitude))
        & np.isclose(longitude, np.round(longitude))
    )
    realm = _realm_mismatch_mask(out, expected_realm) & finite
    institution = (
        _institution_mask(latitude, longitude, institution_points, institution_tolerance_deg)
        & finite
    )

    masks = {
        REALM_MISMATCH: realm,
        ZERO_COORDINATES: zero,
        EQUAL_COORDINATES: equal,
        GRIDDED_COORDINATES: on_grid,
        INSTITUTION_COORDINATES: institution,
    }

    for code, mask in masks.items():
        out[f"det_{code}"] = pd.Series(mask, index=out.index, dtype="boolean")

    any_flag = np.zeros(count, dtype=bool)
    for mask in masks.values():
        any_flag |= mask
    out[DET_FLAG_COLUMN] = pd.Series(any_flag, index=out.index, dtype="boolean")

    reasons = [
        ", ".join(code for code, mask in masks.items() if bool(mask[row])) for row in range(count)
    ]
    out[DET_REASONS_COLUMN] = pd.Series(reasons, index=out.index, dtype="string")
    return out


def realm_for(name: str) -> Realm | None:
    """Return the expected realm for a known taxon name, or None if unknown."""
    for taxon in DEFAULT_TAXA:
        if taxon.name == name:
            return taxon.expected_realm
    return None


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply deterministic coordinate checks to a cached taxon."
    )
    parser.add_argument("taxon", help="Scientific name of a cached taxon.")
    parser.add_argument("--top", type=int, default=10, help="How many flagged records to show.")
    args = parser.parse_args()

    frame = load_cached(args.taxon)
    if frame is None:
        raise SystemExit(
            f"No cached dataset for {args.taxon!r}. Build it first with: "
            f'uv run python -m taxonguard_core.data.cache "{args.taxon}"'
        )

    expected_realm = realm_for(args.taxon)
    flagged = add_deterministic_flags(frame, expected_realm=expected_realm)
    total = int(flagged[DET_FLAG_COLUMN].fillna(False).sum())
    realm_note = expected_realm or "unknown (realm check skipped)"
    print(f"{args.taxon}: {len(flagged)} records, {total} flagged, expected realm {realm_note}")

    if total:
        hits = flagged[flagged[DET_FLAG_COLUMN].fillna(False).to_numpy(dtype=bool)]
        preferred = [
            "gbif_id",
            "decimal_latitude",
            "decimal_longitude",
            "on_land",
            DET_REASONS_COLUMN,
        ]
        present = [column for column in preferred if column in hits.columns]
        print(hits.loc[:, present].head(args.top).to_string(index=False))


if __name__ == "__main__":
    _main()
