"""Tests for the actuator endpoints."""

from __future__ import annotations


def test_default_actuators_seeded(operator_client) -> None:
    response = operator_client.get("/api/actuators")
    assert response.status_code == 200
    rows = response.json()
    ids = {row["id"] for row in rows}
    assert ids == {"fan", "pump", "light"}
    assert all(row["state"] == "off" for row in rows)


def test_toggle_actuator_on(operator_client) -> None:
    response = operator_client.post("/api/actuators/fan/state", json={"state": "on"})
    assert response.status_code == 200
    assert response.json()["state"] == "on"

    # Confirm persistence across requests.
    rows = {row["id"]: row for row in operator_client.get("/api/actuators").json()}
    assert rows["fan"]["state"] == "on"
    assert rows["pump"]["state"] == "off"


def test_toggle_actuator_off(operator_client) -> None:
    operator_client.post("/api/actuators/pump/state", json={"state": "on"})
    response = operator_client.post("/api/actuators/pump/state", json={"state": "off"})
    assert response.status_code == 200
    assert response.json()["state"] == "off"


def test_actuator_invalid_state(operator_client) -> None:
    response = operator_client.post("/api/actuators/fan/state", json={"state": "banana"})
    assert response.status_code == 422


def test_actuator_unknown_id(operator_client) -> None:
    # ActuatorId is a Literal, so this is rejected at validation time (422).
    response = operator_client.post("/api/actuators/unknown/state", json={"state": "on"})
    assert response.status_code == 422
