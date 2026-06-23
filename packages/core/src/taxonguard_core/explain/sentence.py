"""Deterministic explanation sentence from numeric evidence.

Turns a RecordEvidence into one plain, factual sentence in GBIF tone, with no
language model and no key. Each reason code maps to a fixed clause that states
only what the engine computed. This is both the default explanation and the
fallback when an optional language model is unavailable or unfaithful.
"""

from __future__ import annotations

from .evidence import RecordEvidence

# Reason codes, kept local to avoid importing the whole engine for strings.
_REALM_MISMATCH = "realm_mismatch"
_ZERO_COORDINATES = "zero_coordinates"
_EQUAL_COORDINATES = "equal_coordinates"
_GRIDDED_COORDINATES = "gridded_coordinates"
_INSTITUTION_COORDINATES = "institution_coordinates"
_ENVIRONMENTAL_OUTLIER = "environmental_outlier"


def _realm_clause(evidence: RecordEvidence) -> str:
    realm = evidence.expected_realm
    if realm == "marine":
        return f"it falls on land although {evidence.taxon} is a marine species"
    if realm in ("terrestrial", "freshwater"):
        return f"it falls in the sea although {evidence.taxon} is a {realm} species"
    return "it falls outside the expected land or sea area for the species"


def _clause(code: str, evidence: RecordEvidence) -> str | None:
    if code == _REALM_MISMATCH:
        return _realm_clause(evidence)
    if code == _ZERO_COORDINATES:
        return "its coordinates are exactly zero, the null-island error"
    if code == _EQUAL_COORDINATES:
        return "its latitude and longitude are identical, a common data-entry error"
    if code == _GRIDDED_COORDINATES:
        return (
            "its coordinates fall on whole degrees, which suggests a country or "
            "grid centroid rather than an observed location"
        )
    if code == _INSTITUTION_COORDINATES:
        return "its coordinates match a known institution rather than a collection site"
    if code == _ENVIRONMENTAL_OUTLIER:
        return (
            f"its local climate is far outside the range where {evidence.taxon} is "
            "normally recorded"
        )
    return None


def _join_clauses(clauses: list[str]) -> str:
    if len(clauses) == 1:
        return clauses[0]
    return ", ".join(clauses[:-1]) + ", and " + clauses[-1]


def explain_sentence(evidence: RecordEvidence) -> str:
    """Return one plain sentence explaining why the record is suspicious.

    Uses only the values in the evidence. If there are no reasons, says so.
    """
    clauses = [clause for code in evidence.reasons if (clause := _clause(code, evidence))]
    if not clauses:
        return f"This {evidence.taxon} record was not flagged as suspicious."

    score = f"{evidence.suspicion_score:.2f}"
    body = _join_clauses(clauses)
    return f"This {evidence.taxon} record is flagged as suspicious (score {score}) because {body}."
