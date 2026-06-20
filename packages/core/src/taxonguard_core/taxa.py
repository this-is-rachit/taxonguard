"""The starter set of taxa for the first version.

Chosen for obvious, visually clear errors (the "frog in the ocean" type) and for
well-surveyed, well-known groups that exercise different detection signals:
land or sea mismatch, climate-niche outliers, and geographic range. The pipeline
is taxon-agnostic, so edit this list freely. `expected_realm` is consumed later
by the land or sea deterministic check (Phase 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Realm = Literal["terrestrial", "freshwater", "marine"]


@dataclass(frozen=True)
class Taxon:
    name: str
    expected_realm: Realm
    note: str


DEFAULT_TAXA: tuple[Taxon, ...] = (
    Taxon(
        "Panthera leo",
        "terrestrial",
        "Lion. Iconic and well surveyed; ocean points are obviously wrong.",
    ),
    Taxon(
        "Struthio camelus",
        "terrestrial",
        "Ostrich. Flightless African bird; ocean points are obviously wrong.",
    ),
    Taxon(
        "Rana temporaria",
        "freshwater",
        "European common frog. The canonical frog-in-the-ocean case.",
    ),
    Taxon(
        "Salamandra salamandra",
        "terrestrial",
        "Fire salamander. Forest amphibian; sea and desert points stand out.",
    ),
    Taxon(
        "Vulpes lagopus",
        "terrestrial",
        "Arctic fox. Cold specialist; warm-climate points test the niche model.",
    ),
    Taxon(
        "Bradypus variegatus",
        "terrestrial",
        "Brown-throated sloth. Neotropical; points outside the Americas stand out.",
    ),
)
