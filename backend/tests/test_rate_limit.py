"""Tests for the ingest rate limiter."""

from __future__ import annotations

from fastapi.testclient import TestClient

from greenhouse.config import Settings
from greenhouse.main import create_app


def test_rate_limit_triggers_on_burst(tmp_path) -> None:
    """A burst of requests at a low rate cap must produce at least one 429."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/rl.db",
        ingest_rate_limit_per_second=2,
        cors_allowed_origins="http://localhost",
        log_level="WARNING",
        log_format="text",
    )
    app = create_app(settings)
    payload = {
        "sensor_id": "e1",
        "type": "temperature",
        "value": 22.0,
        "unit": "C",
    }
    with TestClient(app) as client:
        statuses = []
        for _ in range(20):
            statuses.append(client.post("/api/readings", json=payload).status_code)

    assert 429 in statuses, f"expected at least one 429, got {set(statuses)}"
    # The bucket starts full (capacity = rate), so the first few should succeed.
    assert 201 in statuses
