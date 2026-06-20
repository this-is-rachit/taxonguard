"""Typed application settings.

Values are read from environment variables (and an optional .env file) with the
prefix TAXONGUARD_. See .env.example for the documented variables. Secrets such
as GBIF credentials are optional here and only required for write-back.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TAXONGUARD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TaxonGuard API"
    log_level: str = "INFO"

    # Comma-separated list of allowed CORS origins for the web app.
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # GBIF credentials for annotation write-back. Optional until Phase 6.
    gbif_username: str | None = None
    gbif_password: str | None = None


settings = Settings()
