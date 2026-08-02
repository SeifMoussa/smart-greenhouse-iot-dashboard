"""Cross-endpoint tests proving viewer/operator role enforcement.

Viewers can read everything but must be blocked from every write endpoint;
operators can do both. This is the actual security boundary PR2 introduces,
so it gets its own dedicated coverage on top of the per-route tests.
"""

from __future__ import annotations

import pytest

READ_ENDPOINTS = [
    "/api/readings",
    "/api/readings/latest",
    "/api/thresholds",
    "/api/alerts",
    "/api/actuators",
    "/api/export.csv",
]


@pytest.mark.parametrize("path", READ_ENDPOINTS)
def test_read_endpoints_reject_unauthenticated(client, path) -> None:
    response = client.get(path)
    assert response.status_code == 401


@pytest.mark.parametrize("path", READ_ENDPOINTS)
def test_read_endpoints_allow_viewer(client, viewer_headers, path) -> None:
    response = client.get(path, headers=viewer_headers)
    assert response.status_code == 200


@pytest.mark.parametrize("path", READ_ENDPOINTS)
def test_read_endpoints_allow_operator(client, operator_headers, path) -> None:
    response = client.get(path, headers=operator_headers)
    assert response.status_code == 200


def test_viewer_blocked_from_updating_thresholds(client, viewer_headers) -> None:
    response = client.put(
        "/api/thresholds/temperature",
        json={"min_value": 10.0, "max_value": 30.0},
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_operator_allowed_to_update_thresholds(client, operator_headers) -> None:
    response = client.put(
        "/api/thresholds/temperature",
        json={"min_value": 10.0, "max_value": 30.0},
        headers=operator_headers,
    )
    assert response.status_code == 200


def test_viewer_blocked_from_setting_actuator(client, viewer_headers) -> None:
    response = client.post(
        "/api/actuators/fan/state",
        json={"state": "on"},
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_operator_allowed_to_set_actuator(client, operator_headers) -> None:
    response = client.post(
        "/api/actuators/fan/state",
        json={"state": "on"},
        headers=operator_headers,
    )
    assert response.status_code == 200


def test_unauthenticated_blocked_from_writes(client) -> None:
    assert (
        client.put(
            "/api/thresholds/temperature", json={"min_value": 10.0, "max_value": 30.0}
        ).status_code
        == 401
    )
    assert client.post("/api/actuators/fan/state", json={"state": "on"}).status_code == 401
