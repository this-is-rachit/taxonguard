# syntax=docker/dockerfile:1
# Build context is the repository root.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONPATH=/app/services/api/src:/app/packages/core/src

WORKDIR /app

# System libraries that rasterio/GDAL's bundled wheels load at runtime but that
# the slim base image omits. libexpat1 provides libexpat.so.1, which GDAL links.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the workspace and install runtime dependencies from the frozen lockfile.
COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY services ./services

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "taxonguard_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
