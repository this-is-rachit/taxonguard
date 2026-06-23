"""Explanation and rule generation (Phase 3).

A thin layer over the detection engine. It turns the numeric evidence behind a
flag into one plain sentence and builds a draft GBIF annotation rule (taxon, a
WKT polygon, and a controlled-vocabulary value). The sentence has a deterministic
template path that needs no language model and no key, so the whole tool runs and
is reviewable at no cost. An optional language model can narrate the same
evidence, but only ever narrates the provided numbers and falls back to the
template if its output is not faithful.

Import from the modules:

    from taxonguard_core.explain.sentence import explain_sentence
    from taxonguard_core.explain.rule import build_rule
    from taxonguard_core.explain.explainer import TemplateExplainer, LLMExplainer
"""
