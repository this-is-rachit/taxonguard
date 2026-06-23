from __future__ import annotations

from taxonguard_core.explain.evidence import RecordEvidence
from taxonguard_core.explain.explainer import (
    LLMExplainer,
    TemplateExplainer,
    build_prompt,
    narration_is_faithful,
)


def _evidence(**kwargs: object) -> RecordEvidence:
    defaults: dict[str, object] = {
        "taxon": "Vulpes lagopus",
        "gbif_id": 7,
        "latitude": 5.0,
        "longitude": 30.0,
        "suspicion_score": 0.88,
        "confidence": 1.0,
        "reasons": ("environmental_outlier",),
        "expected_realm": "terrestrial",
        "on_land": True,
        "environmental_normalized": 0.97,
    }
    defaults.update(kwargs)
    return RecordEvidence(**defaults)  # type: ignore[arg-type]


def test_prompt_includes_evidence_and_constraints() -> None:
    prompt = build_prompt(_evidence())
    assert "Vulpes lagopus" in prompt
    assert "0.88" in prompt
    assert "only the evidence" in prompt
    assert "one sentence" in prompt
    assert "climate" in prompt  # the environmental reason phrase


def test_template_explainer_needs_no_key() -> None:
    sentence = TemplateExplainer().explain(_evidence())
    assert "Vulpes lagopus" in sentence
    assert sentence.endswith(".")


def test_faithful_output_is_returned() -> None:
    evidence = _evidence()

    def complete(_: str) -> str:
        return "This record is suspicious because its climate is unusual (score 0.88)."

    result = LLMExplainer(complete=complete).explain(evidence)
    assert "0.88" in result
    assert "climate" in result


def test_hallucinated_number_triggers_fallback() -> None:
    evidence = _evidence()

    def complete(_: str) -> str:
        # 1850 is not in the evidence, so this must be rejected.
        return "This fox was first described in 1850 and is clearly misplaced."

    result = LLMExplainer(complete=complete).explain(evidence)
    # Falls back to the deterministic template sentence.
    assert result == TemplateExplainer().explain(evidence)


def test_model_error_triggers_fallback() -> None:
    evidence = _evidence()

    def complete(_: str) -> str:
        raise RuntimeError("model unavailable")

    result = LLMExplainer(complete=complete).explain(evidence)
    assert result == TemplateExplainer().explain(evidence)


def test_empty_output_triggers_fallback() -> None:
    evidence = _evidence()
    result = LLMExplainer(complete=lambda _: "   ").explain(evidence)
    assert result == TemplateExplainer().explain(evidence)


def test_faithfulness_guard_directly() -> None:
    evidence = _evidence()
    assert narration_is_faithful("Suspicious with score 0.88.", evidence)
    assert not narration_is_faithful("Recorded 200 km from its range.", evidence)
