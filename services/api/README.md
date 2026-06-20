# taxonguard-api

A FastAPI service that wraps `taxonguard-core` and exposes typed endpoints for
listing flagged clusters, fetching one cluster with its evidence and reason,
and confirming, rejecting, or refining a rule. GBIF credentials for write-back
are handled on the server only.

```bash
uv run uvicorn taxonguard_api.main:app --reload
```
