"""Tests for /api/export.csv."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_export_csv_header_only_when_empty(client) -> None:
    response = client.get("/api/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="greenhouse-readings-' in response.headers.get(
        "content-disposition", ""
    )
    lines = [line for line in response.text.splitlines() if line]
    assert len(lines) == 1
    assert lines[0] == "id,sensor_id,type,value,unit,timestamp"


def test_export_csv_includes_rows(client) -> None:
    client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "temperature", "value": 22.5, "unit": "C"},
    )
    response = client.get("/api/export.csv")
    assert response.status_code == 200
    lines = [line for line in response.text.splitlines() if line]
    assert len(lines) == 2
    header, row = lines
    assert header == "id,sensor_id,type,value,unit,timestamp"
    parts = row.split(",")
    assert parts[1] == "e1"
    assert parts[2] == "temperature"
    assert parts[3] == "22.5"
    assert parts[4] == "C"


def test_export_csv_type_filter(client) -> None:
    client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "temperature", "value": 22.0, "unit": "C"},
    )
    client.post(
        "/api/readings",
        json={"sensor_id": "e1", "type": "humidity", "value": 55.0, "unit": "%"},
    )
    response = client.get("/api/export.csv?type=humidity")
    body = response.text
    assert "humidity" in body
    assert "temperature" not in body


def test_export_csv_range_too_large(client) -> None:
    fr = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    to = datetime.now(UTC).isoformat()
    response = client.get("/api/export.csv", params={"from": fr, "to": to})
    assert response.status_code == 400
