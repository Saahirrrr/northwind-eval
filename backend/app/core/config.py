from __future__ import annotations

"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "Gridbricks Wind Intelligence"
    app_version: str = "1.0.0"
    debug: bool = False

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:80"

    # Elexon API
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = 60.0
    elexon_max_retries: int = 3

    # Data parameters
    delivery_start_date: str = "2026-01-01"
    delivery_end_date: str = "2026-01-31"
    forecast_fetch_start: str = "2025-12-29T00:00:00Z"
    forecast_fetch_end: str = "2026-02-01T00:00:00Z"

    # Forecast cutoff policy
    # Default: 09:00 UK time on D-1 (day before delivery)
    # In January, UK time = UTC (no DST)
    cutoff_hour_utc: int = 9
    cutoff_minutes_utc: int = 0
    cutoff_days_before_delivery: int = 1

    # Cache TTL in seconds (0 = no cache)
    cache_ttl_seconds: int = 300

    # Fixture fallback mode
    use_fixtures: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_prefix": "GRIDBRICKS_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
