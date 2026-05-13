"""Tests for the sensor simulator.

Three layers:

- Pure-unit tests of ``SensorState`` and ``build_payload`` (no HTTP).
- Behavioural tests of ``Simulator`` using ``httpx.MockTransport``.
- One end-to-end test of ``Simulator`` driving the real backend via the
  in-process FastAPI ``TestClient``.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from greenhouse.config import Settings
from greenhouse.main import create_app
from greenhouse.schemas import ReadingIn
from greenhouse.simulator import (
    SENSOR_SPECS,
    SensorSpec,
    SensorState,
    Simulator,
    SimulatorSettings,
    build_payload,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_handler(captured: list[httpx.Request]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(201, json={"id": 1})

    return handler


def _make_settings(**overrides: Any) -> SimulatorSettings:
    defaults: dict[str, Any] = {
        "simulator_backend_url": "http://test",
        "simulator_interval_seconds": 0.0,
        "simulator_sensor_id": "sim-test",
        "simulator_api_key": "",
        "simulator_max_iterations": 1,
        "simulator_max_duration_seconds": 0.0,
        "simulator_initial_backoff_seconds": 0.0,
        "simulator_max_backoff_seconds": 0.0,
        "simulator_seed": 42,
        "log_level": "WARNING",
        "log_format": "text",
    }
    defaults.update(overrides)
    return SimulatorSettings(**defaults)


def _silent_sleep(_: float) -> None:
    return None


# ---------------------------------------------------------------------------
# SensorState — random walk semantics
# ---------------------------------------------------------------------------


def test_sensor_state_starts_at_spec_start() -> None:
    spec = SensorSpec("temperature", "C", 22.0, 0.5, 5.0, 45.0)
    state = SensorState.from_spec(spec)
    assert state.value == 22.0


def test_sensor_state_single_step_bounded_by_walk_step() -> None:
    spec = SensorSpec("temperature", "C", 22.0, 0.5, 5.0, 45.0)
    state = SensorState.from_spec(spec)
    rng = random.Random(123)
    prev = state.value
    new_value = state.step(rng)
    assert abs(new_value - prev) <= spec.walk_step + 1e-6


def test_sensor_state_stays_within_hard_bounds_under_many_steps() -> None:
    rng = random.Random(7)
    for spec in SENSOR_SPECS:
        state = SensorState.from_spec(spec)
        for _ in range(5_000):
            value = state.step(rng)
            assert spec.hard_min <= value <= spec.hard_max


def test_sensor_state_does_not_drift_outside_bounds_even_when_pushed() -> None:
    """Even when every step picks the maximum positive delta, value must clip."""
    spec = SensorSpec("temperature", "C", 44.5, 0.5, 5.0, 45.0)
    state = SensorState.from_spec(spec)

    class PushRng:
        def uniform(self, _a: float, b: float) -> float:
            return b  # always pick the upper end of the delta range

    for _ in range(100):
        state.step(PushRng())  # type: ignore[arg-type]
    assert state.value == 45.0


# ---------------------------------------------------------------------------
# Payload shape
# ---------------------------------------------------------------------------


def test_build_payload_has_expected_keys() -> None:
    spec = SensorSpec("humidity", "%", 55.0, 1.0, 20.0, 95.0)
    state = SensorState.from_spec(spec)
    payload = build_payload("sim-1", state)
    assert set(payload.keys()) == {"sensor_id", "type", "value", "unit"}
    assert payload["sensor_id"] == "sim-1"
    assert payload["type"] == "humidity"
    assert payload["unit"] == "%"


def test_build_payload_passes_backend_validation() -> None:
    """Every spec must produce a payload that the backend's ReadingIn accepts."""
    for spec in SENSOR_SPECS:
        state = SensorState.from_spec(spec)
        payload = build_payload("sim-1", state)
        # Should not raise.
        reading_in = ReadingIn(**payload)
        assert reading_in.type == spec.sensor_type
        assert reading_in.unit == spec.unit


# ---------------------------------------------------------------------------
# Simulator — happy path posting
# ---------------------------------------------------------------------------


def test_tick_posts_one_request_per_sensor() -> None:
    captured: list[httpx.Request] = []
    transport = httpx.MockTransport(_ok_handler(captured))
    client = httpx.Client(transport=transport, base_url="http://test")

    settings = _make_settings()
    sim = Simulator(settings, client=client, sleep=_silent_sleep)
    try:
        successes, failures = sim.tick()
    finally:
        sim.close()
        client.close()

    assert successes == len(SENSOR_SPECS)
    assert failures == 0
    assert len(captured) == len(SENSOR_SPECS)
    sent_types = [r.url.path for r in captured]
    assert all(path == "/api/readings" for path in sent_types)


def test_tick_includes_api_key_header_when_configured() -> None:
    captured: list[httpx.Request] = []
    transport = httpx.MockTransport(_ok_handler(captured))
    client = httpx.Client(transport=transport, base_url="http://test")

    settings = _make_settings(simulator_api_key="abc-123")
    sim = Simulator(settings, client=client, sleep=_silent_sleep)
    try:
        sim.tick()
    finally:
        sim.close()
        client.close()

    assert all(r.headers.get("X-API-Key") == "abc-123" for r in captured)


def test_tick_omits_api_key_header_when_unset() -> None:
    captured: list[httpx.Request] = []
    transport = httpx.MockTransport(_ok_handler(captured))
    client = httpx.Client(transport=transport, base_url="http://test")

    settings = _make_settings(simulator_api_key="")
    sim = Simulator(settings, client=client, sleep=_silent_sleep)
    try:
        sim.tick()
    finally:
        sim.close()
        client.close()

    assert all("X-API-Key" not in r.headers for r in captured)


# ---------------------------------------------------------------------------
# Simulator — failure handling
# ---------------------------------------------------------------------------


def test_tick_survives_connection_errors() -> None:
    def boom(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network outage")

    transport = httpx.MockTransport(boom)
    client = httpx.Client(transport=transport, base_url="http://test")

    sleep_calls: list[float] = []
    settings = _make_settings(simulator_initial_backoff_seconds=0.25)
    sim = Simulator(settings, client=client, sleep=sleep_calls.append)
    try:
        successes, failures = sim.tick()
    finally:
        sim.close()
        client.close()

    assert successes == 0
    assert failures == len(SENSOR_SPECS)
    # Backoff was applied once after the failing tick.
    assert sleep_calls == [0.25]


def test_tick_backoff_doubles_on_consecutive_failures() -> None:
    def boom(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    transport = httpx.MockTransport(boom)
    client = httpx.Client(transport=transport, base_url="http://test")

    sleep_calls: list[float] = []
    settings = _make_settings(
        simulator_initial_backoff_seconds=1.0,
        simulator_max_backoff_seconds=4.0,
    )
    sim = Simulator(settings, client=client, sleep=sleep_calls.append)
    try:
        for _ in range(4):
            sim.tick()
    finally:
        sim.close()
        client.close()

    # 1 → 2 → 4 → 4 (capped).
    assert sleep_calls == [1.0, 2.0, 4.0, 4.0]


def test_tick_resets_backoff_after_success() -> None:
    """After a successful tick the backoff returns to its initial value."""
    call_state = {"count": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        call_state["count"] += 1
        # First tick (4 calls) fails; subsequent calls succeed.
        if call_state["count"] <= len(SENSOR_SPECS):
            raise httpx.ConnectError("first tick fails")
        return httpx.Response(201, json={"id": call_state["count"]})

    transport = httpx.MockTransport(flaky)
    client = httpx.Client(transport=transport, base_url="http://test")

    sleep_calls: list[float] = []
    settings = _make_settings(
        simulator_initial_backoff_seconds=1.0,
        simulator_max_backoff_seconds=8.0,
    )
    sim = Simulator(settings, client=client, sleep=sleep_calls.append)
    try:
        sim.tick()  # failures → sleep 1.0, backoff becomes 2.0
        sim.tick()  # successes → backoff resets to 1.0, no sleep
        sim.tick()  # successes → still 1.0, no sleep
    finally:
        sim.close()
        client.close()

    assert sleep_calls == [1.0]


def test_tick_treats_4xx_as_failure_but_does_not_crash() -> None:
    def four_hundred(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "nope"})

    transport = httpx.MockTransport(four_hundred)
    client = httpx.Client(transport=transport, base_url="http://test")

    settings = _make_settings()
    sim = Simulator(settings, client=client, sleep=_silent_sleep)
    try:
        successes, failures = sim.tick()
    finally:
        sim.close()
        client.close()

    assert successes == 0
    assert failures == len(SENSOR_SPECS)


def test_tick_treats_5xx_as_failure_but_does_not_crash() -> None:
    def five_hundred(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="boom")

    transport = httpx.MockTransport(five_hundred)
    client = httpx.Client(transport=transport, base_url="http://test")

    settings = _make_settings()
    sim = Simulator(settings, client=client, sleep=_silent_sleep)
    try:
        successes, failures = sim.tick()
    finally:
        sim.close()
        client.close()

    assert successes == 0
    assert failures == len(SENSOR_SPECS)


# ---------------------------------------------------------------------------
# Simulator.run — iteration and duration limits
# ---------------------------------------------------------------------------


def test_run_respects_max_iterations() -> None:
    captured: list[httpx.Request] = []
    transport = httpx.MockTransport(_ok_handler(captured))
    client = httpx.Client(transport=transport, base_url="http://test")

    sleep_calls: list[float] = []
    settings = _make_settings(simulator_max_iterations=3, simulator_interval_seconds=0.1)
    sim = Simulator(settings, client=client, sleep=sleep_calls.append)
    try:
        iterations = sim.run()
    finally:
        client.close()

    assert iterations == 3
    assert len(captured) == 3 * len(SENSOR_SPECS)
    # Two interval sleeps between three ticks; the third tick does not
    # sleep because the limit is reached before the next interval.
    interval_sleeps = [s for s in sleep_calls if s == 0.1]
    assert len(interval_sleeps) == 2


def test_run_respects_max_duration() -> None:
    captured: list[httpx.Request] = []
    transport = httpx.MockTransport(_ok_handler(captured))
    client = httpx.Client(transport=transport, base_url="http://test")

    # An advancing fake clock keeps time.monotonic() moving without real sleep.
    now = {"t": 0.0}

    def fake_sleep(dt: float) -> None:
        now["t"] += dt

    settings = _make_settings(
        simulator_max_iterations=0,
        simulator_max_duration_seconds=0.5,
        simulator_interval_seconds=0.2,
    )
    sim = Simulator(settings, client=client, sleep=fake_sleep)
    # Patch the simulator's clock source via the module-level monotonic.
    import greenhouse.simulator as sim_mod

    original = sim_mod.time.monotonic
    sim_mod.time.monotonic = lambda: now["t"]  # type: ignore[assignment]
    try:
        iterations = sim.run()
    finally:
        sim_mod.time.monotonic = original  # type: ignore[assignment]
        client.close()

    # At interval 0.2s with max duration 0.5s the loop runs 3 ticks before
    # the third interval sleep pushes time past 0.5s.
    assert iterations >= 2
    assert len(captured) == iterations * len(SENSOR_SPECS)


def test_run_stops_on_request_stop() -> None:
    captured: list[httpx.Request] = []

    def stop_after_first(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if len(captured) == len(SENSOR_SPECS):
            simulator.request_stop()
        return httpx.Response(201, json={"id": 1})

    transport = httpx.MockTransport(stop_after_first)
    client = httpx.Client(transport=transport, base_url="http://test")

    settings = _make_settings(simulator_max_iterations=0)
    simulator = Simulator(settings, client=client, sleep=_silent_sleep)
    try:
        iterations = simulator.run()
    finally:
        client.close()

    assert iterations == 1


# ---------------------------------------------------------------------------
# End-to-end against the real backend
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("tmp_path")
def test_simulator_e2e_against_real_backend(tmp_path) -> None:
    """Drive the real FastAPI app via TestClient and verify readings persist."""
    backend_settings = Settings(
        database_url=f"sqlite:///{tmp_path}/e2e.db",
        cors_allowed_origins="http://test",
        ingest_rate_limit_per_second=10_000,
        log_level="WARNING",
        log_format="text",
    )
    app = create_app(backend_settings)

    with TestClient(app, base_url="http://testserver") as backend_client:
        sim_settings = _make_settings(
            simulator_backend_url="http://testserver",
            simulator_max_iterations=2,
        )
        # Pass the TestClient (which is itself an httpx.Client) as the
        # simulator's HTTP client; Simulator will not close it.
        simulator = Simulator(sim_settings, client=backend_client, sleep=_silent_sleep)
        iterations = simulator.run()
        assert iterations == 2

        readings = backend_client.get("/api/readings?limit=100").json()
        assert len(readings) == 2 * len(SENSOR_SPECS)
        types = {row["type"] for row in readings}
        assert types == {spec.sensor_type for spec in SENSOR_SPECS}


def test_simulator_e2e_triggers_alert_when_threshold_breached(tmp_path) -> None:
    """Force a temperature reading outside the band and assert an alert lands."""
    backend_settings = Settings(
        database_url=f"sqlite:///{tmp_path}/alerts.db",
        cors_allowed_origins="http://test",
        ingest_rate_limit_per_second=10_000,
        log_level="WARNING",
        log_format="text",
    )
    app = create_app(backend_settings)

    with TestClient(app, base_url="http://testserver") as backend_client:
        # Tighten the temperature band so a normal-walk value will breach it.
        response = backend_client.put(
            "/api/thresholds/temperature",
            json={"min_value": 21.0, "max_value": 23.0},
        )
        assert response.status_code == 200

        sim_settings = _make_settings(
            simulator_backend_url="http://testserver",
            simulator_max_iterations=20,
            simulator_seed=1,
        )
        simulator = Simulator(sim_settings, client=backend_client, sleep=_silent_sleep)
        simulator.run()

        alerts = backend_client.get("/api/alerts").json()
        # Walk drifts from 22.0 over 20 ticks with step 0.5 → high probability
        # of breach; seed makes the result deterministic.
        assert any(alert["type"] == "temperature" for alert in alerts), (
            f"expected at least one temperature alert, got: {alerts}"
        )
