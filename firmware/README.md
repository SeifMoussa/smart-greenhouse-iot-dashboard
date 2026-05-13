# Firmware (optional)

The optional Arduino sketch for the ESP32 microcontroller lives under [`firmware/greenhouse_esp32/`](greenhouse_esp32/).

> **Reviewers / recruiters: use the simulator instead.** The simulator and the firmware send byte-identical payloads to the same backend endpoint. Running `make dev-simulator` or `docker compose up` exercises every code path the firmware would exercise, without any hardware, soldering, or Wi-Fi configuration. The firmware path exists for completeness, not as the recommended demo.

---

## What this firmware does

- Connects an ESP32 to a Wi-Fi network.
- Reads four sensors at a fixed interval:
  - DHT22 → `temperature` (°C) and `humidity` (%)
  - Capacitive soil-moisture sensor on ADC1 → `soil_moisture` (% derived from the raw analog value)
  - LDR on ADC1 (or BH1750 over I²C) → `light` (lux)
- POSTs each reading to the backend's `/api/readings` endpoint with the same JSON shape the simulator uses:

```json
{
  "sensor_id": "esp32-greenhouse-01",
  "type": "temperature",
  "value": 22.4,
  "unit": "C"
}
```

- Sends `X-API-Key` automatically when `API_KEY` is configured.
- Retries with exponential backoff if the backend isn't reachable.
- Logs each POST result to the serial console (115 200 baud).

---

## Required libraries

Install via the Arduino IDE's Library Manager or PlatformIO's `lib_deps`:

- **DHT sensor library** by Adafruit
- **Adafruit Unified Sensor** (dependency of the DHT library)
- **ArduinoJson** (≥ 7.0) for compact JSON construction
- `WiFi.h` and `HTTPClient.h` are bundled with the ESP32 core (Espressif Systems, version 3.0+)
- Optional: **BH1750** library if using the BH1750 light sensor over I²C

---

## Configuration placeholders

Credentials and the backend URL are kept in a separate header so they never end up in a public commit. The sketch directory contains `secrets.h.example` — copy it to `secrets.h` (which is gitignored) and fill in your values:

```cpp
// secrets.h — do not commit
#define WIFI_SSID      "your-network"
#define WIFI_PASSWORD  "your-password"

// Where to POST readings. Reachable from the ESP32's network — not "localhost".
#define BACKEND_URL    "http://192.168.1.50:8000/api/readings"

// Optional API key. Leave empty if your backend has GREENHOUSE_API_KEY unset.
#define API_KEY        ""

// Identifier embedded in every payload.
#define SENSOR_ID      "esp32-greenhouse-01"
```

The example header is documented in [`docs/HARDWARE.md`](../docs/HARDWARE.md#wi-fi-configuration-notes).

---

## How the ESP32 reaches the backend

The backend listens on `0.0.0.0:8000` (or whatever `BACKEND_PORT` is set to). It is reachable from the same LAN at the host's IP address. From the ESP32's perspective:

- `localhost` does **not** work — that points at the ESP32 itself.
- The IP must be reachable from the ESP32's Wi-Fi network. If your dev machine is on a different VLAN, hotspot, or VPN, the ESP32 will not see it.
- CORS does not apply to the ESP32 — it isn't a browser. Don't add the ESP32 IP to `CORS_ALLOWED_ORIGINS`.
- If you set `GREENHOUSE_API_KEY` on the backend, set the same value as `API_KEY` in `secrets.h` on the firmware.

Quick check from a phone on the same Wi-Fi network:

```
http://192.168.1.50:8000/api/health
```

If that returns the JSON health blob, the ESP32 should be able to reach the same URL.

---

## Adapting the backend URL

The sketch posts to `BACKEND_URL` exactly. To point a single ESP32 at multiple backends (e.g. dev vs prod), re-flash with a different `secrets.h`, or extend the sketch to read the URL from a settings portal or NVS storage (out of scope for this demo).

---

## Why the simulator is preferred for demos

The simulator runs in process with the backend test suite. It has:

- the same payload contract,
- the same retry / backoff behaviour conceptually (different implementation),
- 19 dedicated tests that prove the bounded-walk values stay in realistic ranges and that the simulator drives the real backend in two end-to-end tests,
- zero hardware dependencies, zero Wi-Fi setup, zero serial-driver headaches.

If a reviewer wants to see the system "running with real sensors," the firmware path is here. If they want to evaluate the engineering, the simulator is faster, more reproducible, and exercises exactly the same backend code path.

---

## Status of the firmware in this repository

The sketch source itself (`greenhouse_esp32.ino` + `secrets.h.example`) is included as a reference implementation. It has **not** been hardware-tested as part of the automated test suite — the project's testing report is explicit about which checks were run on which artefact. The simulator end-to-end test is what proves the ingest path works.

For wiring, parts list, and safety notes, see [`docs/HARDWARE.md`](../docs/HARDWARE.md).
