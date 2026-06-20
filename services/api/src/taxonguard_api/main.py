"""TaxonGuard API application.

This is the minimal service shell: health and version endpoints plus CORS for
the web app. The flagged-cluster, evidence, and rule endpoints are added in
Phase 4. Keeping a runnable app here lets the whole stack start with one
command from the Docker Compose file.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import taxonguard_core

from . import __version__
from .config import settings

app = FastAPI(title=settings.app_name, version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    api: str
    core: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(api=__version__, core=taxonguard_core.__version__)
