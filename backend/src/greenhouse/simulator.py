"""Synthetic sensor data generator.

Run with::

    python -m greenhouse.simulator

The simulator generates bounded random-walk values for the four supported
sensor types and POSTs them to the running backend's ``/api/readings``
endpoint at a configurable interval. It is intended for local demos and
end-to-end testing without requiring real ESP32 hardware.
"""

from __future__ import annotations

import logging
import random
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from types import FrameType

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from greenhouse.logging_config import configure_logging

log = logging.getLogger("greenhouse.simulator")


@dataclass(frozen=True)
class SensorSpec:
    """Static description of one simulated sensor."""

    sensor_type: str
    unit: str
    start: float
    walk_step: float
    hard_min: float
    hard_max: float


# Realistic-but-conservative envelopes. These are wider than the default
# alert bands on purpose, so the simulator can occasionally trigger alerts.
SENSOR_SPECS: tuple[SensorSpec, ...] = (
    SensorSpec("temperature", "C", start=22.0, walk_step=0.5, hard_min=5.0, hard_max=45.0),
    SensorSpec("humidity", "%", start=55.0, walk_step=1.5, hard_min=20.0, hard_max=95.0),
    SensorSpec("soil_moisture", "%", start=50.0, walk_step=1.0, hard_min=10.0, hard_max=90.0),
    SensorSpec("light", "lux", start=800.0, walk_step=100.0, hard_min=0.0, hard_max=3000.0),
)


@dataclass
class SensorState:
    """Mutable per-sensor random-walk state."""

    spec: SensorSpec
    value: float

    @classmethod
    def from_spec(cls, spec: SensorSpec) -> SensorState:
        return cls(spec=spec, value=spec.start)

    def step(self, rng: random.Random) -> float:
        """Advance the value by a bounded random delta and clip to hard bounds."""
        delta = rng.uniform(-self.spec.walk_step, self.spec.walk_step)
        new_value = self.value + delta
        new_value = max(self.spec.hard_min, min(self.spec.hard_max, new_value))
        self.value = round(new_value, 2)
        return self.value


def build_payload(sensor_id: str, state: SensorState) -> dict[str, object]:
    """Return a payload matching the backend's ``ReadingIn`` schema."""
    return {
        "sensor_id": sensor_id,
        "type": state.spec.sensor_type,
        "value": state.value,
        "unit": state.spec.unit,
    }


class SimulatorSettings(BaseSettings):
    """Simulator-specific settings; loaded from environment with safe defaults.

    ``simulator_max_iterations`` and ``simulator_max_duration_seconds`` both
    default to 0, meaning "run forever". They are primarily useful for tests
    and short demos.
    """

    simulator_backend_url: str = "http://localhost:8000"
    simulator_interval_seconds: float = 5.0
    simulator_sensor_id: str = "esp32-sim-01"
    simulator_api_key: str = ""
    simulator_max_iterations: int = 0
    simulator_max_duration_seconds: float = 0.0
    simulator_request_timeout_seconds: float = 5.0
    simulator_initial_backoff_seconds: float = 1.0
    simulator_max_backoff_seconds: float = 10.0
    simulator_seed: int | None = None

    log_level: str = "INFO"
    log_format: str = "text"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class Simulator:
    """Drive a fleet of synthetic sensors against the backend."""

    def __init__(
        self,
        settings: SimulatorSettings,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self.settings = settings
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=settings.simulator_request_timeout_seconds)
        self._sleep = sleep
        if rng is not None:
            self._rng = rng
        elif settings.simulator_seed is not None:
            self._rng = random.Random(settings.simulator_seed)
        else:
            self._rng = random.Random()
        self._states: list[SensorState] = [SensorState.from_spec(spec) for spec in SENSOR_SPECS]
        self._stop = False
        self._backoff = settings.simulator_initial_backoff_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_stop(self) -> None:
        """Ask the running loop to exit at its next check."""
        self._stop = True

    def close(self) -> None:
        """Release the HTTP client if owned by this simulator."""
        if self._owns_client:
            self._client.close()

    def states(self) -> list[SensorState]:
        """Return the live sensor-state list (for inspection in tests)."""
        return self._states

    def tick(self) -> tuple[int, int]:
        """Send one reading per sensor.

        Returns ``(successes, failures)``. If any failures occurred, sleeps
        the current backoff before returning so the outer loop does not
        immediately hammer the backend; the backoff is doubled up to the
        configured maximum.
        """
        successes = 0
        failures = 0
        for state in self._states:
            state.step(self._rng)
            payload = build_payload(self.settings.simulator_sensor_id, state)
            if self._post(payload):
                successes += 1
                log.info(
                    "sent type=%s value=%s unit=%s",
                    payload["type"],
                    payload["value"],
                    payload["unit"],
                )
            else:
                failures += 1

        if failures:
            log.warning("tick had %d failures; sleeping backoff=%.1fs", failures, self._backoff)
            self._sleep(self._backoff)
            self._backoff = min(self._backoff * 2, self.settings.simulator_max_backoff_seconds)
        else:
            self._backoff = self.settings.simulator_initial_backoff_seconds

        return successes, failures

    def run(self) -> int:
        """Run the main loop. Returns the number of ticks completed."""
        url = self.settings.simulator_backend_url
        log.info(
            "simulator starting url=%s interval=%.1fs sensor_id=%s",
            url,
            self.settings.simulator_interval_seconds,
            self.settings.simulator_sensor_id,
        )
        iterations = 0
        start = time.monotonic()
        try:
            while not self._stop:
                self.tick()
                iterations += 1

                max_iter = self.settings.simulator_max_iterations
                if max_iter and iterations >= max_iter:
                    log.info("reached max iterations=%d", iterations)
                    break

                max_dur = self.settings.simulator_max_duration_seconds
                if max_dur and (time.monotonic() - start) >= max_dur:
                    log.info("reached max duration after %d iterations", iterations)
                    break

                if not self._stop:
                    self._sleep(self.settings.simulator_interval_seconds)
        finally:
            self.close()
        return iterations

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if self.settings.simulator_api_key:
            return {"X-API-Key": self.settings.simulator_api_key}
        return {}

    def _post(self, payload: dict[str, object]) -> bool:
        """POST one payload. Returns True on 201, False otherwise."""
        url = f"{self.settings.simulator_backend_url.rstrip('/')}/api/readings"
        try:
            response = self._client.post(url, json=payload, headers=self._headers())
        except httpx.HTTPError as exc:
            log.warning("post failed type=%s err=%s", payload["type"], exc)
            return False

        if response.status_code == 201:
            return True
        body_preview = response.text[:200] if response.text else ""
        if 400 <= response.status_code < 500:
            log.error(
                "backend rejected reading type=%s status=%d body=%s",
                payload["type"],
                response.status_code,
                body_preview,
            )
        else:
            log.warning(
                "unexpected status type=%s status=%d body=%s",
                payload["type"],
                response.status_code,
                body_preview,
            )
        return False


def main() -> int:  # pragma: no cover
    """CLI entry point: build settings from env, install signal handlers, run."""
    settings = SimulatorSettings()
    configure_logging(settings.log_level, settings.log_format)
    simulator = Simulator(settings)

    def _signal_handler(signum: int, _frame: FrameType | None) -> None:
        log.info("received signal=%d; requesting stop", signum)
        simulator.request_stop()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    iterations = simulator.run()
    log.info("simulator finished iterations=%d", iterations)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
