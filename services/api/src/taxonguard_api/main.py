"""TaxonGuard API application.

Exposes health and version plus the cluster and decision endpoints that wrap the
detection engine: list taxa and flagged clusters, fetch one cluster with its
evidence, explanation, and draft rule, and record an expert decision. The whole
stack starts with one command from the Docker Compose file.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import taxonguard_core

from . import __version__
from .config import settings
from .routes import router

logging.basicConfig(level=settings.log_level)

app = FastAPI(title=settings.app_name, version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


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
