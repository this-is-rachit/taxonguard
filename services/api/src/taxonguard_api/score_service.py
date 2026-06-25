"""On-demand species scoring: fetch, enrich, and score any taxon by name.

The review screen used to show only species that had been cached ahead of time.
This service makes the engine work on *any* species the user names: it resolves
the name, fetches that species' records from GBIF, enriches them, runs the full
detection engine, and returns the scored records with a per-issue summary. Results
are cached in memory so a repeat request is instant. It also proxies GBIF's
keyless species autocomplete so the search box can suggest scientific names as the
user types.

The fetch-and-score work reuses the existing pipeline
(:func:`~taxonguard_core.data.cache.build_taxon_dataset` and
:func:`~taxonguard_core.engine.fusion.score_occurrences`). Both the dataset
builder and the HTTP client are injectable so tests run with no network and no
data files; in production they default to the real pipeline, which needs the
WorldClim and Natural Earth data on the server (the same data the cache build
uses).
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from typing import Any

import httpx
import pandas as pd

from taxonguard_core.clean.cleaner import INSTITUTION_POINTS, build_report_from_scored
from taxonguard_core.data.gbif import GBIF_API
from taxonguard_core.engine.deterministic import realm_for
from taxonguard_core.engine.fusion import score_occurrences

from .models import (
    CleanIssue,
    CleanRecord,
    CleanSummaryOut,
    SpeciesScoreReport,
    SpeciesSuggestion,
)

# The largest number of records returned inline in a score report.
MAX_RECORDS_IN_REPORT = 1000

# How many records to fetch per species when scoring on demand. Capped so a live
# request stays responsive; the engine still learns the niche from this sample.
DEFAULT_FETCH_LIMIT = 1500

DatasetBuilder = Callable[[str, int], pd.DataFrame]


class SpeciesScoreError(RuntimeError):
    """Raised when a species cannot be fetched or scored."""


def _default_builder(name: str, max_records: int) -> pd.DataFrame:
    # Imported lazily so importing this module needs no data files.
    from taxonguard_core.data.cache import build_taxon_dataset

    return build_taxon_dataset(name, max_records=max_records)


def suggest_species(
    query: str,
    *,
    client: httpx.Client | None = None,
    limit: int = 8,
) -> list[SpeciesSuggestion]:
    """Return GBIF scientific-name suggestions for an autocomplete query."""
    query = query.strip()
    if not query:
        return []

    own_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        response = client.get(f"{GBIF_API}/species/suggest", params={"q": query, "limit": limit})
        response.raise_for_status()
        payload: list[dict[str, Any]] = response.json()
    except httpx.HTTPError as error:
        raise SpeciesScoreError(f"Could not reach the species suggest API: {error}") from error
    finally:
        if own_client:
            client.close()

    suggestions: list[SpeciesSuggestion] = []
    for item in payload:
        key = item.get("key")
        name = item.get("scientificName") or item.get("canonicalName")
        if key is None or not name:
            continue
        suggestions.append(
            SpeciesSuggestion(
                key=int(key),
                name=str(name),
                rank=item.get("rank"),
                kingdom=item.get("kingdom"),
            )
        )
    return suggestions


@dataclass
class TaxonScoreService:
    """Fetch, score, and cache any species named at request time."""

    builder: DatasetBuilder = _default_builder
    suggest_client: httpx.Client | None = None
    fetch_limit: int = DEFAULT_FETCH_LIMIT
    _cache: dict[str, pd.DataFrame] = field(default_factory=dict)

    def suggest(self, query: str, *, limit: int = 8) -> list[SpeciesSuggestion]:
        return suggest_species(query, client=self.suggest_client, limit=limit)

    def scored_frame(self, name: str) -> pd.DataFrame:
        """Return the scored frame for a species, building and caching if needed."""
        key = name.strip()
        if key in self._cache:
            return self._cache[key]
        try:
            frame = self.builder(key, self.fetch_limit)
        except Exception as error:  # noqa: BLE001 - surfaced as a clean API error
            raise SpeciesScoreError(f"Could not fetch records for {name!r}: {error}") from error
        if frame.empty:
            raise SpeciesScoreError(f"GBIF returned no usable records for {name!r}.")

        scored = score_occurrences(
            frame,
            expected_realm=realm_for(key),
            institution_points=INSTITUTION_POINTS,
        )
        self._cache[key] = scored
        return scored

    def score(self, name: str) -> SpeciesScoreReport:
        """Score a species and build a report (summary plus ranked records)."""
        scored = self.scored_frame(name)
        result = build_report_from_scored(
            scored, checks_run=["coordinate quality", "land/sea realm", "climate niche"]
        )

        ranked = scored.sort_values("suspicion_score", ascending=False)
        records: list[CleanRecord] = []
        for mapping in ranked.head(MAX_RECORDS_IN_REPORT).to_dict(orient="records"):
            records.append(_record_from_row(mapping))

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
        return SpeciesScoreReport(
            taxon=name,
            summary=summary_out,
            records=records,
            records_truncated=summary.total_records > len(records),
        )


def _is_na(value: object) -> bool:
    return value != value  # noqa: PLR0124 - NaN is the only value not equal to itself


def _opt_str(value: object) -> str | None:
    if value is None or _is_na(value):
        return None
    return str(value)


def _split_reasons(value: object) -> list[str]:
    text = "" if value is None or _is_na(value) else str(value)
    return [part.strip() for part in text.split(",") if part.strip()]


def _record_from_row(mapping: dict[Hashable, Any]) -> CleanRecord:
    gbif_id = mapping.get("gbif_id")
    score = mapping.get("suspicion_score", 0.0)
    return CleanRecord(
        gbif_id=int(gbif_id) if gbif_id is not None and not _is_na(gbif_id) else None,
        scientific_name=_opt_str(mapping.get("scientific_name")),
        latitude=float(mapping["decimal_latitude"]),
        longitude=float(mapping["decimal_longitude"]),
        flagged=bool(float(score) >= 0.5),
        suspicion_score=round(float(score), 4),
        confidence=round(float(mapping.get("suspicion_confidence", 0.0)), 4),
        reasons=_split_reasons(mapping.get("suspicion_reasons")),
    )


__all__ = [
    "TaxonScoreService",
    "SpeciesScoreError",
    "suggest_species",
    "MAX_RECORDS_IN_REPORT",
    "DEFAULT_FETCH_LIMIT",
]
