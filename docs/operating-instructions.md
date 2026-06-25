# Operating instructions

TaxonGuard runs at no cost on readily available hardware. There are two ways to
run it: the one-command Docker path (recommended for review) and the local
development path.

## Requirements

- Docker Desktop, for the one-command path.
- For local development: Python 3.11 or newer with [uv](https://docs.astral.sh/uv/),
  and Node.js LTS.

No secret keys are required to run or review. GBIF credentials are only needed
for annotation write-back.

## One command (Docker)

From the repository root:

```bash
docker compose -f infra/docker-compose.yml up --build
```

This builds and starts both services:

- Web app: http://localhost:3000
- API: http://localhost:8000 (interactive docs at http://localhost:8000/docs)

Stop with `Ctrl + C`. To remove the containers:

```bash
docker compose -f infra/docker-compose.yml down
```

## Local development

### Python engine and API

```bash
uv sync
uv run pytest
uv run uvicorn taxonguard_api.main:app --reload --app-dir services/api/src
```

The API serves http://localhost:8000/health and http://localhost:8000/docs.

### Web app

```bash
cd apps/web
npm install
npm run dev
```

The web app serves http://localhost:3000.

### Checks

Python: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
`uv run pytest`.

Web (from `apps/web`): `npm run lint`, `npm run format:check`,
`npm run typecheck`, `npm run test`, and `npm run e2e` (requires
`npx playwright install chromium` once).

## Configuration

Settings are read from environment variables with the prefix `TAXONGUARD_`.
Copy `.env.example` to `.env` to override defaults. All variables are optional
for local development.

## Writing confirmed rules back to GBIF (optional)

Confirming a cluster on the review screen publishes its rule to GBIF's
experimental occurrence-annotation system at
`https://api.gbif.org/v1/occurrence/experimental/annotation`. This is the only
feature that needs an account, and it is entirely optional.

To enable it, create a free account at https://www.gbif.org/ and put the
credentials in `.env` (which is git-ignored and must never be committed):

```bash
TAXONGUARD_GBIF_USERNAME=your_gbif_username
TAXONGUARD_GBIF_PASSWORD=your_gbif_password
```

With both set, confirming a cluster posts the rule (the taxon, the WKT polygon,
and the value `suspicious`) over HTTP Basic Auth and the review screen links to
the written annotation. With either missing, the tool still runs in full: the
decision is recorded and the screen shows the exact WKT, value, and taxon to
create the rule by hand at https://labs.gbif.org/annotations/. No keys are ever
required to run or review the rest of the tool.

## Explore (search and score any species on demand)

The `/explore` screen is the search-first entry point. Type a scientific name and
the search box suggests matches (via GBIF's keyless suggest API); pick one and the
engine fetches that species' records, learns where it plausibly occurs, scores
every record, and returns the suspicious ones with a plain reason and a score for
each. Results are cached in memory, so a repeat search for the same species is
instant. The screen has a faceted left rail (a minimum-suspicion slider and reason
filters with live counts) and three views of the same result set: a map, a sortable
table, and a summary of issue counts. Clicking a record opens a detail panel with
its coordinates, reasons, and a link to the record on GBIF. On the map you can
draw a polygon ("Draw area") to restrict the results to a region and frame the
view to the records ("Fit to data"); the score slider, reason filters, and drawn
area apply across all three views. The "Clean my data" screen uses these same
faceted views over its flagged records.

On-demand scoring runs the full pipeline, so the climate-niche check needs the
WorldClim rasters and the land/sea check needs the Natural Earth data on the
server (the same data the cache build uses); without them the coordinate-quality
checks still run. For a deployment, pre-cache the demo species so the first search
is instant. The same path is available from the API:

```bash
# Autocomplete scientific names.
curl.exe "http://localhost:8000/species/suggest?q=rana"

# Fetch and score a species on demand.
curl.exe "http://localhost:8000/score?taxon=Rana%20temporaria"
```

## Clean my data (run the engine on an uploaded file)

The `/clean` screen runs the detection engine on a file of occurrence records
that a user uploads (a GBIF download or their own export), then returns a
before/after summary and an annotated, cleaned CSV. The coordinate-quality
checks (null island, equal coordinates, whole-degree centroids, and known
institution coordinates) always run and need no external data, so the feature
works on any deployment with no downloads. The land/sea realm check runs when
the Natural Earth data is present or the upload already carries an `on_land`
column, and the per-taxon climate-outlier model runs when the WorldClim rasters
are present and a taxon has enough records. The response states which checks ran.
Records are flagged, never deleted: the cleaned file keeps every original row and
adds a `flagged` column, the `suspicion_score`, and the `suspicion_reasons`.

The same path is available from the command line and from the API:

```bash
# Command line: check a CSV or TSV and write the annotated, cleaned file.
uv run python -m taxonguard_core.clean.cleaner occurrences.csv --out cleaned.csv

# API: upload to POST /clean, then download the cleaned CSV.
curl.exe -F "file=@occurrences.csv" http://localhost:8000/clean
curl.exe -OJ http://localhost:8000/clean/<clean_id>/download
```

The accepted columns follow the common GBIF and Darwin Core names (for example
`decimalLatitude`/`decimalLongitude`, `scientificName`, `gbifID`); plain
`latitude`/`longitude`/`species` also work. Records without usable coordinates
are dropped before scoring.
