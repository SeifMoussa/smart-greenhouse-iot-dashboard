"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; populated from environment with safe lab defaults."""

    # Network
    backend_host: str = "0.0.0.0"  # noqa: S104  (lab default)
    backend_port: int = 8000

    # Persistence
    database_url: str = "sqlite:///./data/greenhouse.db"

    # Optional API key for write endpoints
    greenhouse_api_key: str = ""

    # CORS — comma-separated origin list (wildcards intentionally not allowed)
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limiting on ingest endpoint
    ingest_rate_limit_per_second: int = 50

    # WebSocket
    max_ws_connections: int = 100

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a clean list."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    """Build a Settings instance from the current environment."""
    return Settings()
