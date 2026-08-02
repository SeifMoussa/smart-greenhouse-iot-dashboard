"""Tests for the thresholds endpoints."""

from __future__ import annotations


def test_default_thresholds_seeded(operator_client) -> None:
    response = operator_client.get("/api/thresholds")
    assert response.status_code == 200
    rows = response.json()
    types = {row["type"] for row in rows}
    assert types == {"temperature", "humidity", "soil_moisture", "light"}


def test_update_threshold_succeeds(operator_client) -> None:
    response = operator_client.put(
        "/api/thresholds/temperature",
        json={"min_value": 10.0, "max_value": 30.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["min_value"] == 10.0
    assert body["max_value"] == 30.0
    assert body["type"] == "temperature"


def test_update_threshold_persists(operator_client) -> None:
    operator_client.put("/api/thresholds/humidity", json={"min_value": 35.0, "max_value": 85.0})
    response = operator_client.get("/api/thresholds")
    rows = {row["type"]: row for row in response.json()}
    assert rows["humidity"]["min_value"] == 35.0
    assert rows["humidity"]["max_value"] == 85.0


def test_update_threshold_invalid_bounds(operator_client) -> None:
    response = operator_client.put(
        "/api/thresholds/temperature",
        json={"min_value": 30.0, "max_value": 10.0},
    )
    assert response.status_code == 422


def test_update_threshold_equal_bounds_rejected(operator_client) -> None:
    response = operator_client.put(
        "/api/thresholds/temperature",
        json={"min_value": 20.0, "max_value": 20.0},
    )
    assert response.status_code == 422


def test_update_threshold_unknown_type(operator_client) -> None:
    response = operator_client.put(
        "/api/thresholds/ozone",
        json={"min_value": 0.0, "max_value": 100.0},
    )
    assert response.status_code == 422
