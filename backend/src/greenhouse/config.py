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

    # Optional API key for the device/simulator ingest endpoint
    greenhouse_api_key: str = ""

    # CORS — comma-separated origin list (wildcards intentionally not allowed)
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limiting on ingest endpoint
    ingest_rate_limit_per_second: int = 50

    # User auth (JWT). The default secret is fine for local dev only —
    # any real deployment must override it via the environment.
    jwt_secret_key: str = "insecure-dev-secret-change-me-before-deploying"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    login_rate_limit_per_second: int = 5

    # Demo accounts seeded on first start (change these for anything but a lab demo)
    seed_operator_username: str = "operator"
    seed_operator_password: str = "operator123"
    seed_viewer_username: str = "viewer"
    seed_viewer_password: str = "viewer123"

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
