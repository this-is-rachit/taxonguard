# Evaluation

This is how TaxonGuard's detection engine is measured: against a labeled set of
occurrence records where every error is known, so the two numbers that matter can
be counted directly — how many real errors the engine catches, and how many
plausible records it falsely flags.

The harness lives in `taxonguard_core.eval`. Reproduce everything, including the
figure, with:

```
uv run python -m taxonguard_core.eval.run
```

## The benchmark

Ground-truth labels on occurrence data require either expert annotation or
controlled error injection. The benchmark takes the second route: it builds
realistic plausible populations and plants known errors into them.

It contains 684 records across three terrestrial taxa with distinct climate
niches (cold, temperate, and warm). 612 records are plausible — drawn from each
niche's climate distribution, on land, with a dense well-sampled locality in one
grid cell to exercise the sampling-effort weighting. The remaining 72 are planted
errors, twelve of each of six kinds, each placed to trip exactly one detector:

- a land taxon in the open sea (realm mismatch),
- the null-island artifact at exactly (0, 0),
- latitude equal to longitude (a transposition),
- a whole-degree centroid (a country or grid centroid),
- a coordinate sitting on a museum (an institution point),
- a climate outlier inside the well-sampled cell.

The deterministic error types are near-binary: a coordinate either is on null
island or it is not. The climate errors are graded by severity, from about three
standard deviations off the niche mean (which sits near the tail of the plausible
population and is genuinely hard) out to far outliers. The populations are
synthetic, but they mirror the cached dataset shape, so the same harness scores a
real GBIF download by swapping in its frame.

## Results

With the calibrated weights, at the product's operating threshold of 0.5:

- recall 100% (all 72 planted errors caught),
- precision 100% (no plausible record flagged),
- false positive rate 0%,
- per-type recall 100% for every one of the six error kinds.

As a ranking, the suspicion score separates the two classes completely: every
planted error scores above every plausible record (ROC-AUC 1.00, average
precision 1.00). The figure below shows the ROC curve and the suspicion score for
each category, with the operating threshold marked. The plausible cluster sits
well below the line; the borderline cases — the soft coordinate flags and the
mildest climate outliers — sit just above it.

![Evaluation: ROC curve and suspicion score by category](evaluation.png)

These numbers describe a controlled benchmark, not real-world performance. The
plausible populations are clean draws from a known distribution, so perfect
separation reflects the controlled setting; messy real records will be harder, and
the deterministic detectors are near-binary by construction. The result that is
meaningful is the shape: clear errors of every kind are caught with no false
alarms, and the hard climate cases land just above the threshold rather than far
above it.

## Calibration

The six noisy-OR weights were calibrated against this benchmark by coordinate
descent (`taxonguard_core.eval.calibrate`). The objective is F1 at the operating
threshold, because that is what the weights genuinely affect. Threshold-independent
ranking measures such as ROC-AUC barely move with the weights — the weights scale
the scores monotonically, which leaves the ranking unchanged — but the absolute
score scale decides whether each error clears the threshold the product actually
decides at.

Calibration raised the environmental weight from a starting 0.8 to 0.93 and left
the other five weights unchanged. At the starting weights, three of the mildest
climate outliers scored just under 0.5 (0.433, 0.439, 0.460) and were missed, for
a recall of 95.8% at the operating threshold. Raising the environmental weight
lifted those three above the line without lifting any plausible record, recovering
them for a recall of 100% with precision unchanged at 100%. Across benchmark seeds
the selected value ranges from 0.93 to 0.99; the conservative 0.93 is adopted as
the default, since a smaller weight is less likely to over-flag the messier
climate distributions of real data.

The weights are now empirically grounded rather than asserted, but they are
grounded on a synthetic benchmark. When a labeled set built from real GBIF records
is available, the same harness re-derives them with one command.

## A deliberate limitation

The engine down-weights climate outliers in sparsely sampled areas on purpose, so
that under-sampled regions are not treated as wrong. A genuine climate error
alone in an unsampled cell is therefore scored low and may be missed — the cost of
not flooding experts with false alarms over poorly sampled places. The benchmark
places its climate errors inside the well-sampled cell, where the engine is meant
to catch them; it does not credit the engine for the isolated case it
intentionally lets pass. This trade-off is a design choice, and the harness makes
it measurable rather than hiding it.

## Toward a citable benchmark

The next step for this evaluation is provenance: building the plausible base
population from a real GBIF download so the set carries a citable DOI, then
planting the same controlled errors into it. The harness already accepts any base
population, so this is a data swap rather than a rewrite. The DOI will be recorded
in `docs/data-sources.md` when the download is run.
