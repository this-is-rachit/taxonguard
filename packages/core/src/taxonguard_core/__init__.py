"""TaxonGuard detection engine.

The core package learns where a taxon plausibly occurs from its own GBIF
records and scores every record for plausibility. It is importable and tested
on its own, with no dependency on the API or web layers.
"""

__version__ = "0.1.0"


def health() -> dict[str, str]:
    """Return a small status payload used by smoke tests and the API."""
    return {"package": "taxonguard-core", "version": __version__, "status": "ok"}
