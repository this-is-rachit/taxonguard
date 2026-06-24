"""Data pipeline: ingest GBIF occurrence records into tidy, validated frames.

Import the ingestion entry point from its module to keep the command-line
interface clean:

    from taxonguard_core.data.ingest import ingest_taxon
"""

from .schema import TIDY_COLUMNS, to_tidy_frame, validate

__all__ = ["TIDY_COLUMNS", "to_tidy_frame", "validate"]
