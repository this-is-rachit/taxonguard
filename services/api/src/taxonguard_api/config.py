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

    # GBIF credentials for annotation write-back. Optional.
    gbif_username: str | None = None
    gbif_password: str | None = None

    @property
    def annotation_enabled(self) -> bool:
        """True only when both GBIF credentials are set, so write-back is possible.

        When this is False the API still runs in full; confirmed rules are recorded
        and a manual copy-and-paste fallback is offered instead of being written.
        """
        return bool(self.gbif_username and self.gbif_password)


settings = Settings()
