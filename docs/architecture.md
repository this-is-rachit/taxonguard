# Architecture

TaxonGuard is a monorepo with clear boundaries between the detection engine,
the API service, and the web app.

## Functional parts

1. Detection engine (`packages/core`, Python, the core). For a taxon it builds
   a lightweight environmental-niche model and scores every record for
   plausibility, combining several signals with a noisy-OR. The continuous signal
   is a graded environmental outlier score from an isolation forest on the taxon's
   own climate, scaled down by a local sampling-effort weight and a taxon-level
   low-data confidence so sparse or poorly recorded settings are not over-flagged.
   The remaining signals are deterministic coordinate checks at full strength: a
   land or sea realm mismatch (the canonical frog in the ocean), null-island
   coordinates at exactly (0, 0), latitude equal to longitude, whole-degree
   centroids, and known institution coordinates. Output is a calibrated suspicion
   score with a transparent per-signal reason breakdown.

2. Explanation layer (language model, thin). Turns the numbers into one
   sentence and a draft rule. It only narrates the computed evidence. It never
   invents biology. A deterministic fallback runs with no language-model key.

3. Web app (`apps/web`, the product). Three screens over the same engine:
   Explore (search and score any species on demand), Review (work through grouped
   clusters of flagged records on a map and confirm, reject, or refine them), and
   Clean my data (check an uploaded occurrence file). The flagged records share
   faceted map, table, and summary views.

4. Write-back (the network benefit). Confirmed rules go to the GBIF annotation
   API with the model evidence as provenance. Behind a single adapter
   interface, so an API change is a one-file fix.

5. Data-gap by-product (a planned extension, not yet built). The same niche
   model could reveal where records are implausibly absent, producing hunger maps
   of under-recorded areas. This is a future direction; it is not part of the
   current build.

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
