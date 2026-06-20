# Operating instructions

TaxonGuard runs at no cost on readily available hardware. There are two ways to
run it: the one-command Docker path (recommended for review) and the local
development path.

## Requirements

- Docker Desktop, for the one-command path.
- For local development: Python 3.11 or newer with [uv](https://docs.astral.sh/uv/),
  and Node.js LTS.

No secret keys are required to run or review. GBIF credentials are only needed
for annotation write-back, which is added in Phase 6.

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
