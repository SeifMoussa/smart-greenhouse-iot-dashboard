"""Tests for the optional X-API-Key write gate."""

from __future__ import annotations


def test_post_reading_without_key_rejected(client_with_key, sample_reading) -> None:
    response = client_with_key.post("/api/readings", json=sample_reading)
    assert response.status_code == 401


def test_post_reading_with_wrong_key_rejected(client_with_key, sample_reading) -> None:
    response = client_with_key.post(
        "/api/readings", json=sample_reading, headers={"X-API-Key": "nope"}
    )
    assert response.status_code == 401


def test_post_reading_with_correct_key_accepted(client_with_key, sample_reading) -> None:
    response = client_with_key.post(
        "/api/readings",
        json=sample_reading,
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 201


def test_put_threshold_without_key_rejected(client_with_key) -> None:
    response = client_with_key.put(
        "/api/thresholds/temperature",
        json={"min_value": 10.0, "max_value": 30.0},
    )
    assert response.status_code == 401


def test_put_threshold_with_key_accepted(client_with_key) -> None:
    response = client_with_key.put(
        "/api/thresholds/temperature",
        json={"min_value": 10.0, "max_value": 30.0},
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 200


def test_actuator_post_requires_key(client_with_key) -> None:
    response = client_with_key.post("/api/actuators/fan/state", json={"state": "on"})
    assert response.status_code == 401


def test_read_endpoints_open_without_key(client_with_key) -> None:
    assert client_with_key.get("/api/health").status_code == 200
    assert client_with_key.get("/api/readings").status_code == 200
    assert client_with_key.get("/api/thresholds").status_code == 200
    assert client_with_key.get("/api/alerts").status_code == 200
    assert client_with_key.get("/api/actuators").status_code == 200
