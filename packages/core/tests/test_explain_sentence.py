from __future__ import annotations

from taxonguard_core.explain.evidence import RecordEvidence
from taxonguard_core.explain.sentence import explain_sentence


def _evidence(reasons: tuple[str, ...], **kwargs: object) -> RecordEvidence:
    defaults: dict[str, object] = {
        "taxon": "Rana temporaria",
        "gbif_id": 42,
        "latitude": 10.0,
        "longitude": 20.0,
        "suspicion_score": 0.9,
        "confidence": 1.0,
        "reasons": reasons,
        "expected_realm": "freshwater",
        "on_land": False,
        "environmental_normalized": 0.95,
    }
    defaults.update(kwargs)
    return RecordEvidence(**defaults)  # type: ignore[arg-type]


def test_realm_mismatch_sentence_mentions_sea_and_realm() -> None:
    sentence = explain_sentence(_evidence(("realm_mismatch",)))
    assert "sea" in sentence
    assert "freshwater" in sentence
    assert sentence.endswith(".")


def test_marine_realm_mismatch_mentions_land() -> None:
    sentence = explain_sentence(
        _evidence(("realm_mismatch",), taxon="Test whale", expected_realm="marine", on_land=True)
    )
    assert "on land" in sentence
    assert "marine" in sentence


def test_environmental_outlier_sentence() -> None:
    sentence = explain_sentence(_evidence(("environmental_outlier",)))
    assert "climate" in sentence


def test_multiple_reasons_combined_in_one_sentence() -> None:
    sentence = explain_sentence(_evidence(("realm_mismatch", "gridded_coordinates")))
    assert sentence.count(". ") == 0  # no internal sentence break
    assert sentence.endswith(".")
    assert "and" in sentence
    assert "whole degrees" in sentence


def test_score_is_included() -> None:
    sentence = explain_sentence(_evidence(("zero_coordinates",), suspicion_score=0.99))
    assert "0.99" in sentence


def test_no_em_dashes_used() -> None:
    sentence = explain_sentence(_evidence(("realm_mismatch", "environmental_outlier")))
    assert "\u2014" not in sentence


def test_no_reasons_returns_neutral_sentence() -> None:
    sentence = explain_sentence(_evidence(()))
    assert "not flagged" in sentence
