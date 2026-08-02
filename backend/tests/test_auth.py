"""Tests for POST /api/auth/login and JWT-based authentication."""

from __future__ import annotations


def test_login_with_correct_credentials_succeeds(client, operator_credentials) -> None:
    username, password = operator_credentials
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "operator"
    assert body["username"] == username
    assert body["access_token"]


def test_login_with_wrong_password_rejected(client, operator_credentials) -> None:
    username, _ = operator_credentials
    response = client.post("/api/auth/login", json={"username": username, "password": "nope"})
    assert response.status_code == 401


def test_login_with_unknown_username_rejected(client) -> None:
    response = client.post(
        "/api/auth/login", json={"username": "no-such-user", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_response_does_not_leak_password_hash(client, viewer_credentials) -> None:
    username, password = viewer_credentials
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert "password" not in response.text
    assert "password_hash" not in response.text


def test_protected_endpoint_without_token_rejected(client) -> None:
    response = client.get("/api/readings")
    assert response.status_code == 401


def test_protected_endpoint_with_malformed_header_rejected(client) -> None:
    response = client.get("/api/readings", headers={"Authorization": "not-bearer-format"})
    assert response.status_code == 401


def test_protected_endpoint_with_garbage_token_rejected(client) -> None:
    response = client.get("/api/readings", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token_accepted(client, viewer_headers) -> None:
    response = client.get("/api/readings", headers=viewer_headers)
    assert response.status_code == 200


def test_login_is_rate_limited(tmp_path) -> None:
    """A burst of login attempts at a low rate cap must produce at least one 429."""
    from fastapi.testclient import TestClient

    from greenhouse.config import Settings
    from greenhouse.main import create_app

    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/rl_login.db",
        login_rate_limit_per_second=2,
        cors_allowed_origins="http://localhost",
        log_level="WARNING",
        log_format="text",
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        statuses = [
            test_client.post(
                "/api/auth/login", json={"username": "nope", "password": "nope"}
            ).status_code
            for _ in range(20)
        ]

    assert 429 in statuses, f"expected at least one 429, got {set(statuses)}"
