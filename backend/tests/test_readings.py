"""Tests for the readings endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_ingest_creates_record(client, sample_reading) -> None:
    response = client.post("/api/readings", json=sample_reading)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "temperature"
    assert body["value"] == 22.5
    assert body["unit"] == "C"
    assert body["sensor_id"] == "esp32-01"
    assert "id" in body
    assert "timestamp" in body
    assert "created_at" in body


def test_ingest_rejects_unknown_type(client, sample_reading) -> None:
    sample_reading["type"] = "ozone"
    response = client.post("/api/readings", json=sample_reading)
    assert response.status_code == 422


def test_ingest_rejects_missing_fields(client) -> None:
    response = client.post("/api/readings", json={"type": "temperature"})
    assert response.status_code == 422


def test_ingest_rejects_future_timestamp(client, sample_reading) -> None:
    future = datetime.now(UTC) + timedelta(hours=1)
    sample_reading["timestamp"] = future.isoformat()
    response = client.post("/api/readings", json=sample_reading)
    assert response.status_code == 422


def test_ingest_accepts_recent_timestamp(client, sample_reading) -> None:
    recent = datetime.now(UTC) - timedelta(minutes=1)
    sample_reading["timestamp"] = recent.isoformat()
    response = client.post("/api/readings", json=sample_reading)
    assert response.status_code == 201


def test_list_readings_requires_auth(client) -> None:
    response = client.get("/api/readings")
    assert response.status_code == 401


def test_list_readings_returns_newest_first(operator_client, sample_reading) -> None:
    for value in (20.0, 21.0, 22.0):
        sample_reading["value"] = value
        assert operator_client.post("/api/readings", json=sample_reading).status_code == 201

    response = operator_client.get("/api/readings?limit=10")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 3
    assert rows[0]["value"] == 22.0
    assert rows[-1]["value"] == 20.0


def test_list_readings_type_filter(operator_client) -> None:
    operator_client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "temperature", "value": 22.0, "unit": "C"},
    )
    operator_client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "humidity", "value": 50.0, "unit": "%"},
    )
    response = operator_client.get("/api/readings?type=humidity")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["type"] == "humidity"


def test_latest_returns_one_per_type(operator_client) -> None:
    fixtures = [
        ("temperature", 22.0, "C"),
        ("humidity", 50.0, "%"),
        ("soil_moisture", 60.0, "%"),
        ("light", 800.0, "lux"),
    ]
    for sensor_type, value, unit in fixtures:
        operator_client.post(
            "/api/readings",
            json={"sensor_id": "e1", "type": sensor_type, "value": value, "unit": unit},
        )

    response = operator_client.get("/api/readings/latest")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 4
    assert {r["type"] for r in rows} == {
        "temperature",
        "humidity",
        "soil_moisture",
        "light",
    }


def test_latest_empty_when_no_data(operator_client) -> None:
    response = operator_client.get("/api/readings/latest")
    assert response.status_code == 200
    assert response.json() == []
