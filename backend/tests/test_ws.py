"""WebSocket integration tests."""

from __future__ import annotations


def test_websocket_receives_reading_event(client) -> None:
    with client.websocket_connect("/ws") as ws:
        client.post(
            "/api/readings",
            json={
                "sensor_id": "e1",
                "type": "humidity",
                "value": 50.0,
                "unit": "%",
            },
        )
        message = ws.receive_json()
        assert message["type"] == "reading"
        assert message["data"]["type"] == "humidity"
        assert message["data"]["value"] == 50.0


def test_websocket_receives_alert_on_threshold_breach(client) -> None:
    with client.websocket_connect("/ws") as ws:
        client.post(
            "/api/readings",
            json={
                "sensor_id": "e1",
                "type": "temperature",
                "value": 60.0,
                "unit": "C",
            },
        )
        # Expect one reading event and one alert event in some order.
        first = ws.receive_json()
        second = ws.receive_json()
        types = {first["type"], second["type"]}
        assert types == {"reading", "alert"}


def test_websocket_receives_actuator_event(client) -> None:
    with client.websocket_connect("/ws") as ws:
        client.post("/api/actuators/fan/state", json={"state": "on"})
        message = ws.receive_json()
        assert message["type"] == "actuator"
        assert message["data"]["id"] == "fan"
        assert message["data"]["state"] == "on"
