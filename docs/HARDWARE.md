# Hardware (optional ESP32 path)

The whole stack works with **zero physical hardware** via the simulator (see [`firmware/README.md`](../firmware/README.md) for why this is the recommended path for reviewers). This document describes the optional hardware setup for anyone who wants a real sensor node.

> The optional firmware sketch lives at `firmware/greenhouse_esp32/` and is referenced by [`firmware/README.md`](../firmware/README.md). It is the same payload contract as the simulator — the backend cannot tell the difference between a real ESP32 and the simulator.

---

## Why simulator-first

For reviewers, recruiters, or anyone evaluating the project:

- The simulator and the ESP32 use the **same** `POST /api/readings` endpoint with the **same** payload shape.
- The simulator generates realistic bounded random-walk values for all four sensor types, including occasional threshold breaches that exercise the alert path.
- No soldering, no Wi-Fi setup, no driver installation, no physical assembly. `make dev-simulator` (or `docker compose up`) and the dashboard fills with data within seconds.

The hardware path is documented for completeness and as a recruiter-visible signal of embedded comfort. **Run the simulator first; come back here only if you want to wire up a node.**

---

## Parts list

| Part | Quantity | Notes |
|---|---|---|
| ESP32 development board | 1 | DevKit-C, NodeMCU-ESP32, or any board exposing `3V3`, `GND`, and at least one ADC pin. Wi-Fi capable. |
| DHT22 (AM2302) temperature + humidity sensor | 1 | The cheaper DHT11 also works with a different library call, but DHT22 has better accuracy. |
| Capacitive soil-moisture sensor v1.2/v2.0 | 1 | Resistive sensors corrode quickly in soil; capacitive is strongly preferred for any run longer than a few hours. |
| LDR (photoresistor) or BH1750 module | 1 | LDR + 10 kΩ pull-down for analog reading, or BH1750 over I²C for lux units. |
| 10 kΩ resistor | 1 | DHT22 data-line pull-up. Some breakout modules include this on-board. |
| Jumper wires | ~10 | Female-to-male or male-to-male depending on board. |
| Breadboard | 1 | Half-size is enough. |
| USB cable | 1 | Must be a **data** cable, not charge-only. |

Optional for relay-driven actuators:

| Part | Notes |
|---|---|
| 3 × 5 V relay modules (active-low or active-high) | One each for fan, pump, grow light |
| Small 5 V or 12 V fan | Computer-case fan works well |
| 5 V or 12 V mini water pump | Submersible aquarium-style |
| White or warm-white LED strip | A few cells of WS2812 work too |
| External 5 V / 12 V power supply | Do **not** drive a pump from the ESP32's 3V3 line |

---

## Wiring assumptions

The firmware sketch in `firmware/greenhouse_esp32/` assumes the following default pin mapping. Adjust at the top of the sketch if your board differs.

| Sensor / signal | ESP32 pin | Notes |
|---|---|---|
| DHT22 data | `GPIO 4` | 10 kΩ pull-up to 3V3 |
| DHT22 VCC | `3V3` | DHT22 must run at 3.3 V on ESP32 |
| DHT22 GND | `GND` |  |
| Capacitive soil sensor AOUT | `GPIO 34` (ADC1) | Avoid ADC2 pins — they conflict with Wi-Fi |
| Soil sensor VCC | `3V3` |  |
| Soil sensor GND | `GND` |  |
| LDR + 10 kΩ to GND | `GPIO 35` (ADC1) | Other side of LDR to 3V3 |
| Optional relay fan | `GPIO 25` |  |
| Optional relay pump | `GPIO 26` |  |
| Optional relay light | `GPIO 27` |  |

If you use BH1750 instead of an LDR, wire it to I²C (`GPIO 21` SDA, `GPIO 22` SCL) and switch the sketch's `readLight()` implementation accordingly.

---

## Wi-Fi configuration notes

The sketch reads Wi-Fi credentials from compile-time constants near the top of the file. **Do not commit your real credentials.** A `secrets.h.example` is provided; copy it to `secrets.h` (gitignored) and fill in:

```cpp
// secrets.h
#define WIFI_SSID      "your-network"
#define WIFI_PASSWORD  "your-password"
#define BACKEND_URL    "http://192.168.1.50:8000/api/readings"
#define API_KEY        ""   // leave empty if your backend has no key
```

The backend URL must be **reachable from the ESP32** — that means the host running the FastAPI backend must be on the same network as the ESP32, and the host's firewall must allow inbound on the chosen port. `localhost` does not work from the ESP32's perspective.

If your backend has `GREENHOUSE_API_KEY` set, the firmware sends it as the `X-API-Key` header — see the sketch's `httpPost()` helper.

---

## Firmware flashing notes

The sketch is plain Arduino C++. Tested toolchain:

- Arduino IDE 2.x **or** PlatformIO
- ESP32 board package by Espressif Systems (3.0+)
- DHT sensor library by Adafruit
- Adafruit Unified Sensor library
- `WiFi.h` and `HTTPClient.h` (bundled with the ESP32 core)

High-level flashing recipe (Arduino IDE):

1. Open `firmware/greenhouse_esp32/greenhouse_esp32.ino`.
2. Copy `secrets.h.example` to `secrets.h` next to the sketch and fill it in.
3. Select your board (e.g. "ESP32 Dev Module") and the correct serial port.
4. Click **Verify** to compile, then **Upload**.
5. Open the Serial Monitor at 115 200 baud. You should see lines like:

   ```
   [wifi] connecting...
   [wifi] connected: 192.168.1.42
   [post] temperature 22.4 C -> 201
   [post] humidity 54.1 % -> 201
   [post] soil_moisture 60.3 % -> 201
   [post] light 812 lux -> 201
   ```

   `201` means the backend accepted the reading. Anything else — log it and check the backend logs.

---

## Safety notes

Hardware introduces real-world risk that the simulator never does. Read this before plugging anything in:

- **Mains voltage:** if you control an AC pump or AC light through a relay, that is **not a beginner project**. Use a properly enclosed relay module rated for the load, and do not work on live mains. If you are not comfortable doing this safely, run pumps and lights on a low-voltage DC supply instead.
- **Polarity:** double-check VCC / GND before powering on. Reversing a sensor will at best destroy the sensor and at worst back-feed the ESP32.
- **Water + electronics:** the pump and the soil-moisture sensor live in damp environments. Keep all connectors out of the soil, seal anything that might be splashed, and use a low-voltage supply.
- **Long deployments:** capacitive soil sensors last; resistive sensors corrode within days. Use capacitive.
- **Power budget:** the ESP32's 3V3 line cannot drive a pump or a heating element. Use a separate supply and have its ground share with the ESP32 ground.
- **ADC2 vs ADC1:** ESP32 ADC2 pins are usable only when Wi-Fi is **not** active. Use ADC1 (GPIO 32–39) for any analog read while Wi-Fi is connected.
- **Don't share a USB hub** between flashing the ESP32 and any high-current peripheral; brownouts during boot cause flashing failures.

---

## Where to go from the simulator to real hardware

If the simulator works end-to-end on your machine and you decide to add hardware:

1. Confirm your backend is reachable from the ESP32's network (try `curl http://<backend-host>:8000/api/health` from a phone on the same Wi-Fi).
2. Wire one sensor first — usually DHT22 is the easiest. Get it posting cleanly before adding the others.
3. Watch the Serial Monitor and the backend logs side by side. The backend's structured JSON logs will tell you exactly why a reading was rejected (e.g. unknown sensor type, missing field, future timestamp).
4. Only add relays after the read path is rock-solid. A misbehaving relay can lock your firmware in a reboot loop.

---

## Why this document exists if you might never use it

This is a software-engineering portfolio repository. Documenting the optional hardware path shows comfort with the full IoT stack — embedded reads → network → ingest → persistence → UI → control — without forcing a reviewer to actually build the thing. The simulator delivers identical behaviour from the backend's perspective, so the rest of the project does not depend on this page at all.
