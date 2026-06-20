# TaxonGuard

Detect, explain, expert-confirm, and write back implausible GBIF occurrence records.

TaxonGuard finds occurrence records in GBIF that are ecologically or
taxonomically implausible, explains why each is suspect in one plain sentence,
lets a domain expert confirm or reject a batch, and publishes the confirmed
judgment to GBIF's occurrence-annotation system. A confirmed rule cleans
existing records and continues to catch matching records in future data drops.

This is an entry for the GBIF Ebbe Nielsen Challenge. It targets the 2027 round.

## What it does

1. Learns where each taxon plausibly occurs from that taxon's own GBIF records.
2. Scans records and flags the implausible ones, for example occurrences of a
   land animal in open ocean.
3. Explains the reason for each flag in one plain sentence.
4. Lets an expert confirm once, which resolves the whole batch and keeps
   catching the same error on future records.
5. Writes the confirmed rule back to GBIF's annotation system so every data
   user benefits.

The component that decides whether a record is suspect is a niche and outlier
model that does measurable, testable math. A language model only writes the
explanation sentence, and there is a deterministic fallback that works with no
language-model key, so the tool runs at no cost.

## Repository layout

| Path | Contents |
|---|---|
| `packages/core` | Python detection engine. Importable and tested on its own. |
| `services/api` | FastAPI service that wraps the core and exposes typed endpoints. |
| `apps/web` | Next.js, TypeScript, and Tailwind frontend that consumes the API. |
| `design/` | `gbif_dark_atlas.md`, the frontend design source of truth. |
| `docs/` | Architecture, compliance, and operating instructions. |
| `infra/` | Dockerfiles and the single Docker Compose file. |

## Requirements

- Python 3.11 or newer, managed with [uv](https://docs.astral.sh/uv/).
- Node.js LTS for the web app.
- Docker Desktop to run the whole stack with one command.

## Quick start (Python engine and API)

```bash
uv sync
uv run pytest
```

Full operating instructions live in `docs/operating-instructions.md`.

## Quick start (web app)

```bash
cd apps/web
npm install
npm run dev
```

Then open http://localhost:3000. Other scripts: `npm run build`,
`npm run lint`, `npm run typecheck`, `npm run test`.

## License

MIT. See `LICENSE`.
