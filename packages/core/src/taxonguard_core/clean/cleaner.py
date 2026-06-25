"""Apply the detection engine to an uploaded occurrence file.

This is the engine half of the "clean my data" feature. It accepts a frame of
occurrence records (parsed from an uploaded CSV), runs the coordinate-quality
deterministic checks on every record, adds the land/sea realm check when the
Natural Earth data is available, and runs the per-taxon climate-outlier model when
WorldClim is available and a taxon has enough records. It fuses the signals into a
suspicion score with a plain-reason breakdown, exactly like the live product, and
reports which checks it was able to run so the result is honest about its own
coverage.

The deterministic checks need no external data, so the feature works on any
deployment with no downloads: a free-tier server, or the judges' laptop. The realm
and climate checks switch on automatically when their data is present. Records are
flagged, never dropped.

Clean a file from the command line:

    uv run python -m taxonguard_core.clean.cleaner occurrences.csv --out cleaned.csv
"""

from __future__ import annotations

import argparse
import io
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..data.schema import TIDY_COLUMNS, validate
from ..engine.deterministic import (
    DETERMINISTIC_FLAG_COLUMNS,
    add_deterministic_flags,
    realm_for,
)
from ..engine.effort import add_sampling_effort
from ..engine.fusion import (
    ENVIRONMENTAL_REASON,
    SUSPICION_CONFIDENCE_COLUMN,
    SUSPICION_REASONS_COLUMN,
    SUSPICION_SCORE_COLUMN,
    FusionWeights,
    fuse_signals,
)
from ..engine.lowdata import assess_low_data

# The operating threshold the product flags at, reused here so the upload view
# matches the live review screen.
DEFAULT_MIN_SCORE = 0.5

# The output columns appended to each record in the cleaned file.
FLAGGED_COLUMN = "flagged"

# Reason codes in reporting order, mapped to plain labels for the summary.
_REASON_LABELS: dict[str, str] = {
    "realm_mismatch": "land/sea realm mismatch",
    "zero_coordinates": "null-island coordinates (0, 0)",
    "equal_coordinates": "latitude equals longitude",
    "gridded_coordinates": "whole-degree (grid or centroid) coordinates",
    "institution_coordinates": "sits on a known institution",
    ENVIRONMENTAL_REASON: "climate outlier for the taxon",
}

# Case-insensitive source column aliases mapped onto the tidy schema, so a raw
# GBIF download (SIMPLE_CSV or Darwin Core) and common hand-made exports all load.
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "gbif_id": ("gbif_id", "gbifid", "key", "occurrenceid", "id"),
    "scientific_name": ("scientific_name", "scientificname", "species", "taxon", "name"),
    "decimal_latitude": ("decimal_latitude", "decimallatitude", "latitude", "lat"),
    "decimal_longitude": ("decimal_longitude", "decimallongitude", "longitude", "lon", "lng"),
    "year": ("year",),
    "basis_of_record": ("basis_of_record", "basisofrecord"),
    "country_code": ("country_code", "countrycode", "country"),
    "coordinate_uncertainty_m": (
        "coordinate_uncertainty_m",
        "coordinateuncertaintyinmeters",
        "coordinateuncertainty",
    ),
}

# A small, curated set of major natural-history institution coordinates (public
# facts). A record sitting on one of these is the holding institution, not the
# collection site. The list is intentionally short and extensible; a fuller
# public-domain institutions database can be loaded here without changing the API.
INSTITUTION_POINTS: tuple[tuple[float, float], ...] = (
    (51.4967, -0.1764),  # Natural History Museum, London
    (51.4787, -0.2956),  # Royal Botanic Gardens, Kew
    (38.8913, -77.0260),  # Smithsonian NMNH, Washington DC
    (40.7813, -73.9740),  # American Museum of Natural History, New York
    (38.6126, -90.2594),  # Missouri Botanical Garden, St Louis
    (41.8663, -87.6170),  # Field Museum, Chicago
    (37.7699, -122.4661),  # California Academy of Sciences, San Francisco
    (48.8424, 2.3560),  # Muséum national d'Histoire naturelle, Paris
    (52.5304, 13.3791),  # Museum für Naturkunde, Berlin
    (52.1641, 4.4775),  # Naturalis Biodiversity Center, Leiden
    (48.2052, 16.3592),  # Naturhistorisches Museum, Vienna
    (-33.8745, 151.2130),  # Australian Museum, Sydney
)


class UploadError(ValueError):
    """Raised when an uploaded file cannot be parsed into occurrence records."""


@dataclass(frozen=True)
class CleanSummary:
    """A before/after summary of a clean run."""

    total_records: int
    flagged_records: int
    issues: dict[str, int]
    checks_run: list[str]
    taxa: int

    @property
    def clean_records(self) -> int:
        return self.total_records - self.flagged_records


@dataclass(frozen=True)
class CleanResult:
    """The scored frame plus its summary."""

    frame: pd.DataFrame = field(repr=False)
    summary: CleanSummary


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Map a raw upload's columns onto the tidy schema, tolerant of naming."""
    lower_to_actual = {str(column).strip().lower(): column for column in frame.columns}
    data: dict[str, pd.Series] = {}
    for tidy, aliases in _COLUMN_ALIASES.items():
        match = next((lower_to_actual[a] for a in aliases if a in lower_to_actual), None)
        if match is not None:
            data[tidy] = frame[match].reset_index(drop=True)

    if "decimal_latitude" not in data or "decimal_longitude" not in data:
        raise UploadError(
            "could not find latitude and longitude columns in the upload "
            "(expected something like decimalLatitude / decimalLongitude)"
        )

    out = pd.DataFrame(data)
    # Fill any missing tidy columns so the schema is always complete.
    for column in TIDY_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    if "gbif_id" not in data:
        out["gbif_id"] = range(1, len(out) + 1)
    out["scientific_name"] = (
        out["scientific_name"].astype("string")
        if "scientific_name" in data
        else pd.Series(["(unspecified)"] * len(out), dtype="string")
    )

    numeric = (
        "gbif_id",
        "decimal_latitude",
        "decimal_longitude",
        "year",
        "coordinate_uncertainty_m",
    )
    for column in numeric:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.astype(TIDY_COLUMNS)

    # Preserve a provided on_land column if present (so the realm check can run
    # without the Natural Earth data on the server).
    if "on_land" in lower_to_actual:
        out["on_land"] = (
            pd.to_numeric(frame[lower_to_actual["on_land"]], errors="coerce").fillna(0).astype(bool)
        )
    return out


def read_upload_csv(text: str) -> pd.DataFrame:
    """Parse uploaded CSV or TSV text into a tidy, validated occurrence frame.

    Accepts comma- or tab-delimited input and the common column-name variants of
    a GBIF download. Records without usable coordinates are dropped (validation),
    so the returned frame is ready for the engine.
    """
    sample = text[:4096]
    delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
    try:
        raw = pd.read_csv(io.StringIO(text), sep=delimiter, dtype="object", on_bad_lines="skip")
    except (ValueError, pd.errors.ParserError) as error:
        raise UploadError(f"could not parse the uploaded file: {error}") from error
    if raw.empty:
        raise UploadError("the uploaded file has no rows")

    has_on_land = "on_land" in {str(c).strip().lower() for c in raw.columns}
    tidy = _normalize_columns(raw)
    subset = ["on_land"] if has_on_land else None
    validated = validate(tidy.drop(columns=subset) if subset else tidy)
    if subset:
        validated = validated.join(tidy[subset])
    return validated


def _worldclim_available(data_dir: Path | None) -> bool:
    from ..data.worldclim import is_downloaded

    return is_downloaded(data_dir)


def _natural_earth_available(data_dir: Path | None) -> bool:
    from ..data.naturalearth import is_downloaded

    return is_downloaded(data_dir)


def _with_realm(frame: pd.DataFrame, *, data_dir: Path | None) -> tuple[pd.DataFrame, bool]:
    """Add on_land (for the realm check) if it is not already present and the data is.

    Returns the frame and whether the realm check can run.
    """
    if "on_land" in frame.columns:
        return frame, True
    if not _natural_earth_available(data_dir):
        return frame, False
    from ..data.landsea import add_land_sea_flag

    return add_land_sea_flag(frame, data_dir=data_dir, sea_buffer_deg=0.05), True


def _score_taxon(
    group: pd.DataFrame,
    *,
    name: str,
    realm_available: bool,
    run_environmental: bool,
    data_dir: Path | None,
    weights: FusionWeights | None,
) -> tuple[pd.DataFrame, bool]:
    """Score one taxon's records. Returns the scored frame and whether climate ran."""
    expected_realm = realm_for(name) if realm_available else None

    climate_ran = False
    confidence = 1.0
    working = group
    if run_environmental and _worldclim_available(data_dir):
        from ..data.enrich import enrich_with_climate
        from ..engine.environment import score_environmental_outliers

        try:
            enriched = enrich_with_climate(group, data_dir=data_dir)
            working = score_environmental_outliers(enriched)
            confidence = assess_low_data(working).confidence
            climate_ran = True
        except (FileNotFoundError, KeyError, ValueError):
            working = group

    flagged = add_deterministic_flags(
        working, expected_realm=expected_realm, institution_points=INSTITUTION_POINTS
    )
    with_effort = add_sampling_effort(flagged)
    fused = fuse_signals(with_effort, weights=weights, confidence=confidence)
    return fused, climate_ran


def clean_occurrences(
    frame: pd.DataFrame,
    *,
    data_dir: Path | None = None,
    run_environmental: bool = True,
    weights: FusionWeights | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
) -> CleanResult:
    """Run the engine on an uploaded frame and return scored records plus a summary.

    Always runs the coordinate-quality checks. Adds the land/sea realm check when
    an on_land column is present or the Natural Earth data is available, and the
    per-taxon climate-outlier model when ``run_environmental`` is set and WorldClim
    is available. Records scoring at or above ``min_score`` are marked flagged. The
    summary lists which checks ran and counts the records each issue affected.
    """
    if frame.empty:
        empty = frame.copy()
        empty[SUSPICION_SCORE_COLUMN] = pd.Series(dtype="float64")
        empty[FLAGGED_COLUMN] = pd.Series(dtype="boolean")
        return CleanResult(
            frame=empty,
            summary=CleanSummary(0, 0, {}, ["coordinate quality"], 0),
        )

    with_realm, realm_available = _with_realm(frame, data_dir=data_dir)

    scored_parts: list[pd.DataFrame] = []
    any_climate = False
    names = [str(n) for n in with_realm["scientific_name"].fillna("(unspecified)").unique()]
    for name in names:
        group = with_realm[with_realm["scientific_name"].fillna("(unspecified)") == name]
        scored, climate_ran = _score_taxon(
            group,
            name=name,
            realm_available=realm_available,
            run_environmental=run_environmental,
            data_dir=data_dir,
            weights=weights,
        )
        any_climate = any_climate or climate_ran
        scored_parts.append(scored)

    result = pd.concat(scored_parts, ignore_index=True)

    checks_run = ["coordinate quality"]
    if realm_available:
        checks_run.append("land/sea realm")
    if any_climate:
        checks_run.append("climate niche")

    return build_report_from_scored(result, checks_run=checks_run, min_score=min_score)


def build_report_from_scored(
    frame: pd.DataFrame,
    *,
    checks_run: list[str],
    min_score: float = DEFAULT_MIN_SCORE,
) -> CleanResult:
    """Shape an already-scored frame into a flagged frame plus a summary.

    The frame must carry the fused suspicion columns. Records scoring at or above
    ``min_score`` are marked flagged, issue counts are tallied per reason, and
    ``checks_run`` records which checks produced the scores. Shared by the upload
    cleaner and the on-demand species scorer so both report identically.
    """
    result = frame.copy()
    if result.empty:
        result[FLAGGED_COLUMN] = pd.Series(dtype="boolean")
        return CleanResult(frame=result, summary=CleanSummary(0, 0, {}, checks_run, 0))

    flagged_mask = result[SUSPICION_SCORE_COLUMN].fillna(0.0) >= min_score
    result[FLAGGED_COLUMN] = pd.Series(
        flagged_mask.to_numpy(dtype=bool), index=result.index, dtype="boolean"
    )

    issues: dict[str, int] = {}
    for column in DETERMINISTIC_FLAG_COLUMNS:
        code = column.removeprefix("det_")
        count = int(result[column].fillna(False).sum()) if column in result.columns else 0
        if count:
            issues[_REASON_LABELS.get(code, code)] = count
    env_reason = (
        int(result[SUSPICION_REASONS_COLUMN].fillna("").str.contains(ENVIRONMENTAL_REASON).sum())
        if SUSPICION_REASONS_COLUMN in result.columns
        else 0
    )
    if env_reason:
        issues[_REASON_LABELS[ENVIRONMENTAL_REASON]] = env_reason

    taxa = int(result["scientific_name"].nunique()) if "scientific_name" in result.columns else 1
    summary = CleanSummary(
        total_records=int(len(result)),
        flagged_records=int(flagged_mask.sum()),
        issues=issues,
        checks_run=checks_run,
        taxa=taxa,
    )
    return CleanResult(frame=result, summary=summary)


# The columns of the cleaned download, in order: the tidy occurrence fields plus
# the engine's verdict.
_OUTPUT_COLUMNS: tuple[str, ...] = (
    "gbif_id",
    "scientific_name",
    "decimal_latitude",
    "decimal_longitude",
    "year",
    "basis_of_record",
    "country_code",
    "coordinate_uncertainty_m",
    FLAGGED_COLUMN,
    SUSPICION_SCORE_COLUMN,
    SUSPICION_REASONS_COLUMN,
    SUSPICION_CONFIDENCE_COLUMN,
)


def cleaned_frame(result: CleanResult) -> pd.DataFrame:
    """Return the annotated frame for download: tidy fields plus the verdict."""
    present = [column for column in _OUTPUT_COLUMNS if column in result.frame.columns]
    out = result.frame.loc[:, present].copy()
    for column in (SUSPICION_SCORE_COLUMN, SUSPICION_CONFIDENCE_COLUMN):
        if column in out.columns:
            out[column] = out[column].round(4)
    return out


def cleaned_csv(result: CleanResult) -> str:
    """Serialize the annotated frame to CSV text for download."""
    return cleaned_frame(result).to_csv(index=False)


def flagged_records(result: CleanResult, *, limit: int | None = None) -> pd.DataFrame:
    """Return only the flagged records, most suspicious first."""
    flagged = result.frame[result.frame[FLAGGED_COLUMN].fillna(False).to_numpy(dtype=bool)]
    ranked = flagged.sort_values(SUSPICION_SCORE_COLUMN, ascending=False)
    return ranked.head(limit) if limit is not None else ranked


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Check an uploaded occurrence file with the TaxonGuard engine."
    )
    parser.add_argument("path", type=Path, help="CSV or TSV of occurrence records.")
    parser.add_argument("--out", type=Path, help="Write the annotated, cleaned CSV here.")
    parser.add_argument(
        "--no-environmental",
        action="store_true",
        help="Skip the climate model even if WorldClim is available.",
    )
    parser.add_argument("--top", type=int, default=10, help="How many flagged records to print.")
    args = parser.parse_args()

    frame = read_upload_csv(args.path.read_text(encoding="utf-8"))
    result = clean_occurrences(frame, run_environmental=not args.no_environmental)
    summary = result.summary
    print(
        f"{summary.total_records} records, {summary.flagged_records} flagged, "
        f"{summary.clean_records} clean across {summary.taxa} taxa"
    )
    print(f"checks run: {', '.join(summary.checks_run)}")
    for issue, count in summary.issues.items():
        print(f"  {issue}: {count}")

    top = flagged_records(result, limit=args.top)
    if not top.empty:
        preferred = [
            "gbif_id",
            "scientific_name",
            "decimal_latitude",
            "decimal_longitude",
            SUSPICION_SCORE_COLUMN,
            SUSPICION_REASONS_COLUMN,
        ]
        present = [column for column in preferred if column in top.columns]
        print(top.loc[:, present].to_string(index=False))

    if args.out:
        args.out.write_text(cleaned_csv(result), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    _main()
