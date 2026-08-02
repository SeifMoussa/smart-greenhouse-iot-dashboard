"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from greenhouse.config import Settings
from greenhouse.main import create_app

TEST_OPERATOR = ("test-operator", "operator-pass-123")
TEST_VIEWER = ("test-viewer", "viewer-pass-123")


def _build_settings(tmp_path, **overrides) -> Settings:
    base = {
        "database_url": f"sqlite:///{tmp_path}/test.db",
        "greenhouse_api_key": "",
        "cors_allowed_origins": "http://localhost:5173",
        "ingest_rate_limit_per_second": 1000,
        "login_rate_limit_per_second": 1000,
        "max_ws_connections": 10,
        "log_level": "WARNING",
        "log_format": "text",
        "jwt_secret_key": "test-secret-key-for-unit-tests-only-not-for-real-use",
        "seed_operator_username": TEST_OPERATOR[0],
        "seed_operator_password": TEST_OPERATOR[1],
        "seed_viewer_username": TEST_VIEWER[0],
        "seed_viewer_password": TEST_VIEWER[1],
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


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def operator_credentials() -> tuple[str, str]:
    return TEST_OPERATOR


@pytest.fixture
def viewer_credentials() -> tuple[str, str]:
    return TEST_VIEWER


@pytest.fixture
def operator_token(client: TestClient) -> str:
    return _login(client, *TEST_OPERATOR)


@pytest.fixture
def viewer_token(client: TestClient) -> str:
    return _login(client, *TEST_VIEWER)


@pytest.fixture
def operator_headers(operator_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture
def viewer_headers(viewer_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def operator_client(client: TestClient, operator_headers: dict[str, str]) -> TestClient:
    """The shared client, pre-authenticated as the operator role."""
    client.headers.update(operator_headers)
    return client


@pytest.fixture
def sample_reading() -> dict[str, object]:
    return {
        "sensor_id": "esp32-01",
        "type": "temperature",
        "value": 22.5,
        "unit": "C",
    }
