"""Tests for /api/health."""

from __future__ import annotations


def test_health_returns_ok(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str)
    assert body["version"]
    assert body["uptime_seconds"] >= 0
