"""A small persisted registry of species added to Review from the UI.

The Review screen is seeded from the curated ``DEFAULT_TAXA`` set in the core
package. This registry lets a user add more species at request time: the chosen
scientific name and habitat realm are written to a small JSON file in the data
directory, so they survive a restart, and the cluster service reads them alongside
the defaults. The realm has to be supplied because the land or sea check needs to
know whether a species belongs on land, in fresh water, or at sea, and that cannot
be inferred from the name alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from taxonguard_core.data.worldclim import get_data_dir
from taxonguard_core.taxa import DEFAULT_TAXA, Realm, Taxon

REVIEW_TAXA_FILENAME = "review_taxa.json"

VALID_REALMS: frozenset[str] = frozenset({"terrestrial", "freshwater", "marine"})
_DEFAULT_NAMES: frozenset[str] = frozenset(taxon.name for taxon in DEFAULT_TAXA)
_ADDED_NOTE = "Added from the Review page."


def registry_path(data_dir: Path | None = None) -> Path:
    """Return the path to the user-added review taxa registry file."""
    root = data_dir if data_dir is not None else get_data_dir()
    return root / REVIEW_TAXA_FILENAME


def load_added_taxa(data_dir: Path | None = None) -> list[Taxon]:
    """Return the user-added review taxa, skipping defaults and malformed entries."""
    path = registry_path(data_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []

    taxa: list[Taxon] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        realm = str(item.get("realm", "")).strip()
        if not name or realm not in VALID_REALMS:
            continue
        if name in _DEFAULT_NAMES or name in seen:
            continue
        seen.add(name)
        taxa.append(Taxon(name, cast(Realm, realm), _ADDED_NOTE))
    return taxa


def add_review_taxon(name: str, realm: Realm, data_dir: Path | None = None) -> bool:
    """Add a species to the registry. Return False if it was a duplicate or default.

    Defaults (already in the curated set) and species already added are ignored, so
    calling this more than once for the same name is safe.
    """
    name = name.strip()
    if not name or realm not in VALID_REALMS or name in _DEFAULT_NAMES:
        return False
    existing = load_added_taxa(data_dir)
    if any(taxon.name == name for taxon in existing):
        return False

    path = registry_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"name": taxon.name, "realm": taxon.expected_realm} for taxon in existing]
    payload.append({"name": name, "realm": realm})
    path.write_text(json.dumps(payload, indent=2))
    return True


__all__ = [
    "REVIEW_TAXA_FILENAME",
    "VALID_REALMS",
    "registry_path",
    "load_added_taxa",
    "add_review_taxon",
]
