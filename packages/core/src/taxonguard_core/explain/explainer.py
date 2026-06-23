"""Explainers: a no-key template and an optional, guarded language model.

The default explainer is deterministic and needs no key. An optional explainer
narrates the same evidence with a language model, but is held to a strict
contract: the prompt forbids any fact or number that is not in the evidence, and
the output is checked so that every number it contains traces back to the
evidence. If the model is unavailable, errors, or strays from the evidence, the
explainer falls back to the deterministic sentence. The language model is
injected as a simple complete(prompt) -> str callable, so there is no SDK
dependency and tests need no network.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from .evidence import RecordEvidence
from .sentence import explain_sentence

_REASON_PHRASES = {
    "realm_mismatch": "the point is on the wrong side of the land or sea boundary for the species",
    "zero_coordinates": "the coordinates are exactly zero",
    "equal_coordinates": "the latitude and longitude are identical",
    "gridded_coordinates": "the coordinates fall on whole degrees",
    "institution_coordinates": "the coordinates match a known institution",
    "environmental_outlier": "the local climate is far outside the usual range",
}

_SYSTEM = (
    "You write one short, factual sentence explaining why a species occurrence "
    "record was flagged as suspicious. Use only the evidence given below. Do not "
    "add biological facts, numbers, places, or claims that are not in the "
    "evidence. Do not speculate. Write plain English, one sentence, and do not "
    "use em dashes."
)

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
_FAITHFULNESS_TOLERANCE = 0.01


class Explainer(Protocol):
    """Anything that turns evidence into a sentence."""

    def explain(self, evidence: RecordEvidence) -> str: ...


def build_prompt(evidence: RecordEvidence) -> str:
    """Build the strict prompt for a language model from the evidence."""
    lines = [
        f"- taxon: {evidence.taxon}",
        f"- suspicion score from 0 to 1: {evidence.suspicion_score:.2f}",
    ]
    if evidence.expected_realm is not None:
        lines.append(f"- expected realm: {evidence.expected_realm}")
    if evidence.on_land is not None:
        lines.append(f"- on land: {str(evidence.on_land).lower()}")
    if evidence.environmental_normalized is not None:
        lines.append(
            f"- environmental outlier score from 0 to 1: {evidence.environmental_normalized:.2f}"
        )
    reasons = [_REASON_PHRASES.get(code, code) for code in evidence.reasons]
    if reasons:
        lines.append("- reasons: " + "; ".join(reasons))

    return _SYSTEM + "\n\nEvidence:\n" + "\n".join(lines) + "\n\nWrite one sentence."


def _evidence_numbers(evidence: RecordEvidence) -> set[float]:
    numbers = {
        round(evidence.suspicion_score, 2),
        round(evidence.confidence, 2),
        round(evidence.latitude, 2),
        round(evidence.longitude, 2),
    }
    if evidence.environmental_normalized is not None:
        numbers.add(round(evidence.environmental_normalized, 2))
    if evidence.gbif_id is not None:
        numbers.add(float(evidence.gbif_id))
    return numbers


def narration_is_faithful(text: str, evidence: RecordEvidence) -> bool:
    """True if every number in text traces back to a number in the evidence.

    This is the automated half of the contract: a language model may rephrase the
    evidence but may not introduce numbers of its own, which is the clearest sign
    of an invented fact.
    """
    allowed = _evidence_numbers(evidence)
    for token in _NUMBER_RE.findall(text):
        value = float(token)
        if not any(abs(value - candidate) <= _FAITHFULNESS_TOLERANCE for candidate in allowed):
            return False
    return True


class TemplateExplainer:
    """The deterministic, no-key explainer."""

    def explain(self, evidence: RecordEvidence) -> str:
        return explain_sentence(evidence)


@dataclass
class LLMExplainer:
    """An optional language-model explainer, guarded and with a fallback.

    complete is any callable that takes the prompt and returns the model's text.
    Provide your own to wire in a model; nothing here imports an SDK.
    """

    complete: Callable[[str], str]
    fallback: Explainer = field(default_factory=TemplateExplainer)

    def explain(self, evidence: RecordEvidence) -> str:
        try:
            text = self.complete(build_prompt(evidence)).strip()
        except Exception:
            return self.fallback.explain(evidence)
        if text and narration_is_faithful(text, evidence):
            return text
        return self.fallback.explain(evidence)
