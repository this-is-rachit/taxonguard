# Architecture

TaxonGuard is a monorepo with clear boundaries between the detection engine,
the API service, and the web app.

## Functional parts

1. Detection engine (`packages/core`, Python, the core). For a taxon it builds
   a lightweight environmental-niche model and scores every record for
   plausibility, using an ensemble of cheap signals: an environmental outlier
   score from an isolation forest on climate, a spatial outlier score with
   sampling-effort correction, a land or sea and habitat mismatch check, and
   metadata checks such as museum coordinates and country or grid centroids.
   Output is a calibrated suspicion score with a transparent reason breakdown.

2. Explanation layer (language model, thin). Turns the numbers into one
   sentence and a draft rule. It only narrates the computed evidence. It never
   invents biology. A deterministic fallback runs with no language-model key.

3. Review screen (`apps/web`, the product). Flagged clusters on a map, ranked
   by confidence and by records affected, with confirm, reject, and refine
   controls.

4. Write-back (the network benefit). Confirmed rules go to the GBIF annotation
   API with the model evidence as provenance. Behind a single adapter
   interface, so an API change is a one-file fix.

5. Optional data-gap by-product. The same niche model can reveal where records
   are implausibly absent, which produces hunger maps.

## Repository layout

- `packages/core` is the Python detection engine, importable and tested alone.
- `services/api` is a FastAPI service that wraps the core.
- `apps/web` is the Next.js, TypeScript, and Tailwind frontend.
- `design/` holds `gbif_dark_atlas.md`, the design source of truth.
- `infra/` holds the Dockerfiles and the single Compose file.
- `docs/` holds architecture, data sources, evaluation, and operating instructions.

## Python workspace

uv manages a workspace with two members: `taxonguard-core` and
`taxonguard-api`. A single `.venv` at the repo root installs both in editable
mode. `uv.lock` is committed for reproducibility.

## Tooling

uv for Python with a committed lockfile, Ruff and mypy for Python, ESLint and
Prettier for the web, pre-commit hooks, conventional commit messages, pytest
for Python, Vitest and Playwright for the web, GitHub Actions for continuous
integration, MapLibre GL for the map with no API key, and TanStack Query for
data fetching. Docker Compose runs the whole stack with one command.
