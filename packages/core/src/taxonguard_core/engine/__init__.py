"""Detection engine: score occurrence records for plausibility.

Phase 2 of TaxonGuard. The first signal is the environmental outlier model, an
isolation forest fitted on each taxon's own WorldClim climate values. Later
signals (the deterministic land or sea and metadata checks, sampling-effort
correction) and the calibrated fusion are added alongside it.

Import the model from its module, which mirrors the data package layout:

    from taxonguard_core.engine.environment import score_environmental_outliers
"""
