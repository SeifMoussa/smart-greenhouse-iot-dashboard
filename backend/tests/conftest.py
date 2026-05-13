"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from greenhouse.config import Settings
from greenhouse.main import create_app


def _build_settings(tmp_path, **overrides) -> Settings:
    base = {
        "database_url": f"sqlite:///{tmp_path}/test.db",
        "greenhouse_api_key": "",
        "cors_allowed_origins": "http://localhost:5173",
        "ingest_rate_limit_per_second": 1000,
        "max_ws_connections": 10,
        "log_level": "WARNING",
        "log_format": "text",
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return _build_settings(tmp_path)


@pytest.fixture
def settings_with_key(tmp_path) -> Settings:
    return _build_settings(tmp_path, greenhouse_api_key="test-secret")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_with_key(settings_with_key: Settings) -> Iterator[TestClient]:
    app = create_app(settings_with_key)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_reading() -> dict[str, object]:
    return {
        "sensor_id": "esp32-01",
        "type": "temperature",
        "value": 22.5,
        "unit": "C",
    }
