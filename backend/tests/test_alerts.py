"""Tests for alert generation via the ingest pathway and listing endpoint."""

from __future__ import annotations


def test_no_alert_inside_band(client) -> None:
    # Default temperature band is 15.0 to 32.0.
    client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "temperature", "value": 22.0, "unit": "C"},
    )
    response = client.get("/api/alerts")
    assert response.status_code == 200
    assert response.json() == []


def test_critical_alert_far_above_band(client) -> None:
    client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "temperature", "value": 60.0, "unit": "C"},
    )
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["type"] == "temperature"
    assert alert["severity"] == "critical"
    assert alert["value"] == 60.0
    assert "above" in alert["message"].lower()


def test_warning_alert_just_outside_band(client) -> None:
    # Band 15.0 - 32.0, width 17.0. 33.0 is 1.0/17.0 = ~5.9% past — warning.
    client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "temperature", "value": 33.0, "unit": "C"},
    )
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "warning"


def test_alert_below_band(client) -> None:
    client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "temperature", "value": -5.0, "unit": "C"},
    )
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"
    assert "below" in alerts[0]["message"].lower()


def test_alerts_returned_newest_first(client) -> None:
    for value in (50.0, 51.0, 52.0):
        client.post(
            "/api/readings",
            json={
                "sensor_id": "e1",
                "type": "temperature",
                "value": value,
                "unit": "C",
            },
        )
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 3
    assert alerts[0]["value"] == 52.0


def test_alerts_limit_parameter(client) -> None:
    for value in (50.0, 51.0, 52.0):
        client.post(
            "/api/readings",
            json={
                "sensor_id": "e1",
                "type": "temperature",
                "value": value,
                "unit": "C",
            },
        )
    alerts = client.get("/api/alerts?limit=2").json()
    assert len(alerts) == 2
