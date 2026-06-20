# taxonguard-core

The TaxonGuard detection engine. For a taxon it builds a lightweight
environmental-niche model and scores every record for plausibility, using an
ensemble of cheap signals: an environmental outlier score, a spatial outlier
score with sampling-effort correction, a land or sea and habitat mismatch
check, and metadata checks. The output is a calibrated suspicion score with a
transparent per-signal reason breakdown.

This package is importable and tested on its own, with no dependency on the API
or web layers.

```bash
uv run pytest packages/core
```
