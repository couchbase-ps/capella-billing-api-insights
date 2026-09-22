"""Runtime configuration, read from environment variables (see design spec §3.1)."""

from __future__ import annotations

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings. Field names map to upper-case env vars."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    capella_api_key: SecretStr | None = None
    capella_base_url: str = "https://cloudapi.cloud.couchbase.com"
    capella_org_id: str | None = None
    capella_mock: bool = False
    sync_backfill_days: int = 90
    sync_refresh_days: int = 7
    sync_on_start: bool = True
    sync_interval_minutes: int = 360
    rate_limit_per_minute: int = 80
    db_path: str = "/data/insights.db"
    log_level: str = "info"

    @field_validator("capella_api_key", "capella_org_id", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        """docker-compose passes empty strings for unset variables; treat them as unset."""
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @property
    def configured(self) -> bool:
        """True when a sync can run: either mock mode or an API key is present."""
        return self.capella_mock or self.capella_api_key is not None

    @property
    def api_key_value(self) -> str | None:
        """Plain secret for the HTTP client; never log this."""
        return self.capella_api_key.get_secret_value() if self.capella_api_key else None


def load_settings() -> Settings:
    """Build settings from the process environment."""
    return Settings()
