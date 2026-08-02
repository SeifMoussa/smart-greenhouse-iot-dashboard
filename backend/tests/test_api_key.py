"""Tests for the optional X-API-Key gate on the device/simulator ingest endpoint."""

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
