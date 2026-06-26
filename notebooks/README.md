# Notebooks

## `taxonguard_demo.ipynb` — the full loop, end to end

A single, reproducible notebook that runs TaxonGuard's whole pipeline and shows
the result at every step: detect implausible occurrence records, explain each one
in a plain sentence, group them into a reviewable cluster, draft a GBIF annotation
rule, and write that rule back to GBIF (or print the exact manual steps when no
credentials are set). It runs the same loop across three taxa, so the result is a
generalization claim rather than a single-species result:

- *Rana temporaria* (freshwater) — the land/sea check, the "frog in the ocean".
- *Vulpes lagopus* (terrestrial) — the climate-niche outlier model.
- *Delphinus delphis* (marine) — the land/sea check inverted, a marine species
  recorded inland.

### Run it (free, no key, no downloaded data)

From the repository root:

```bash
uv run jupyter notebook notebooks/taxonguard_demo.ipynb
```

Or execute it headlessly (the same command CI runs):

```bash
uv run jupyter nbconvert --to notebook --execute notebooks/taxonguard_demo.ipynb \
    --output-dir /tmp
```

Every cell runs with no account and no data files. The notebook automatically
falls back to a labeled synthetic dataset (built with the same error-planting
machinery as the real-data benchmark), so it is reproducible offline and reports
its own catch rate.

### Run it on real GBIF data

The notebook prefers real data when it is present. Build a cache once, then re-run:

```bash
uv run python -m taxonguard_core.data.worldclim --download
uv run python -m taxonguard_core.data.naturalearth --download
uv run python -m taxonguard_core.data.cache "Rana temporaria" --max-records 1500
```

On the next run the data source for that taxon shows as `cache` instead of
`synthetic`. To also enable the live, keyless GBIF fetch for taxa without a cache,
set `TAXONGUARD_NOTEBOOK_LIVE=1` (this needs the network and the layers above).

### Post a real annotation rule

Set a free GBIF account in the environment before running the write-back section:

```bash
export TAXONGUARD_GBIF_USERNAME=your_account_name   # the account name, not the email
export TAXONGUARD_GBIF_PASSWORD=your_password
```

Without these, the write-back section prints the exact WKT, value, and taxon to
create the rule by hand, so the notebook still completes at no cost.

### The citable accuracy benchmark

The notebook's accuracy figures are measured on the labeled synthetic fallback.
The honest, citable benchmark plants the same error types into a real GBIF
download and reports on a held-out split (GBIF download DOI
`10.15468/dl.bpfzpj`, *Rana temporaria*, Great Britain). See `docs/evaluation.md`
and `docs/data-sources.md`; the controlled benchmark is reproduced with
`uv run python -m taxonguard_core.eval.run`, and the two commands for the real,
held-out benchmark are in `docs/evaluation.md`.
