"""The clean-my-data service: run the engine on an uploaded file.

Parses an uploaded occurrence CSV, runs the detection engine through the core
:func:`~taxonguard_core.clean.cleaner.clean_occurrences` (coordinate-quality
checks always, plus the land/sea realm and climate checks when their data is
available), and returns a before/after report. The annotated, cleaned CSV is held
in a small in-memory store keyed by a generated id, mirroring how the cluster
service keeps decisions in memory, so a follow-up request can download it.
"""

from __future__ import annotations

import uuid

from taxonguard_core.clean.cleaner import (
    FLAGGED_COLUMN,
    UploadError,
    clean_occurrences,
    cleaned_csv,
    flagged_records,
    read_upload_csv,
)
from taxonguard_core.engine.fusion import (
    SUSPICION_CONFIDENCE_COLUMN,
    SUSPICION_REASONS_COLUMN,
    SUSPICION_SCORE_COLUMN,
)

from .models import (
    CleanIssue,
    CleanRecord,
    CleanReport,
    CleanSummaryOut,
)

# The largest number of flagged records returned inline in a report. The full set
# is always available in the downloadable CSV; this only caps the JSON payload.
MAX_FLAGGED_IN_REPORT = 500


class CleanNotFoundError(KeyError):
    """Raised when a clean id is not known to the service."""


def _split_reasons(value: object) -> list[str]:
    text = "" if value is None else str(value)
    return [part.strip() for part in text.split(",") if part.strip()]


class CleanService:
    """Run uploads through the engine and hold cleaned files for download."""

    def __init__(self, *, run_environmental: bool = True) -> None:
        # Climate runs only when WorldClim is present; the flag lets a deployment
        # without the rasters skip the attempt entirely.
        self._run_environmental = run_environmental
        self._files: dict[str, str] = {}

    def run(self, text: str) -> CleanReport:
        """Parse, score, store the cleaned CSV, and build the report.

        Raises :class:`~taxonguard_core.clean.cleaner.UploadError` if the file
        cannot be parsed into occurrence records.
        """
        frame = read_upload_csv(text)
        result = clean_occurrences(frame, run_environmental=self._run_environmental)

        clean_id = uuid.uuid4().hex
        self._files[clean_id] = cleaned_csv(result)

        summary = result.summary
        summary_out = CleanSummaryOut(
            total_records=summary.total_records,
            flagged_records=summary.flagged_records,
            clean_records=summary.clean_records,
            taxa=summary.taxa,
            checks_run=summary.checks_run,
            issues=[
                CleanIssue(label=label, count=count) for label, count in summary.issues.items()
            ],
        )

        ranked = flagged_records(result, limit=MAX_FLAGGED_IN_REPORT)
        flagged: list[CleanRecord] = []
        for mapping in ranked.to_dict(orient="records"):
            gbif_id = mapping.get("gbif_id")
            flagged.append(
                CleanRecord(
                    gbif_id=int(gbif_id) if gbif_id is not None and not _is_na(gbif_id) else None,
                    scientific_name=_opt_str(mapping.get("scientific_name")),
                    latitude=float(mapping["decimal_latitude"]),
                    longitude=float(mapping["decimal_longitude"]),
                    flagged=bool(mapping.get(FLAGGED_COLUMN, True)),
                    suspicion_score=float(mapping.get(SUSPICION_SCORE_COLUMN, 0.0)),
                    confidence=float(mapping.get(SUSPICION_CONFIDENCE_COLUMN, 0.0)),
                    reasons=_split_reasons(mapping.get(SUSPICION_REASONS_COLUMN)),
                )
            )

        return CleanReport(
            clean_id=clean_id,
            summary=summary_out,
            flagged=flagged,
            flagged_truncated=summary.flagged_records > len(flagged),
            download_url=f"/clean/{clean_id}/download",
        )

    def download(self, clean_id: str) -> str:
        """Return the stored cleaned CSV text for a clean id, or raise."""
        try:
            return self._files[clean_id]
        except KeyError as error:
            raise CleanNotFoundError(clean_id) from error


def _is_na(value: object) -> bool:
    return value != value  # noqa: PLR0124 - NaN is the only value not equal to itself


def _opt_str(value: object) -> str | None:
    if value is None or _is_na(value):
        return None
    return str(value)


__all__ = ["CleanService", "CleanNotFoundError", "UploadError", "MAX_FLAGGED_IN_REPORT"]
