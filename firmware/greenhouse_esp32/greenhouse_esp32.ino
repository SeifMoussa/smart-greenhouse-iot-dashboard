/*
 * Smart Greenhouse — ESP32 reference firmware
 * ----------------------------------------------------------------------------
 * Reads four sensors (DHT22 + capacitive soil moisture + LDR/BH1750) at a
 * configurable interval and POSTs each reading to the backend's
 *     POST /api/readings
 * endpoint with the same JSON shape the Python simulator uses.
 *
 * Wiring assumptions are documented in docs/HARDWARE.md. Adjust the pin
 * constants at the top of this file if your board differs.
 *
 * Required Arduino libraries:
 *   - DHT sensor library by Adafruit
 *   - Adafruit Unified Sensor (dependency of DHT)
 *   - ArduinoJson (>= 7.0)
 *   - WiFi.h and HTTPClient.h are bundled with the ESP32 Arduino core
 *
 * Configuration:
 *   1. Copy `secrets.h.example` to `secrets.h` next to this sketch.
 *   2. Fill in WIFI_SSID, WIFI_PASSWORD, BACKEND_URL, optionally API_KEY,
 *      and SENSOR_ID.
 *   3. Verify and upload through the Arduino IDE or PlatformIO.
 *
 * Lab-only disclaimer:
 *   This sketch is for educational and portfolio use. It does not implement
 *   OTA updates, TLS certificate pinning, watchdog hardening, or any of the
 *   other features required for a production deployment.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

#include "secrets.h"

// ============================================================================
// Pin mapping  —  see docs/HARDWARE.md
// ============================================================================
constexpr int PIN_DHT          = 4;    // DHT22 data line (10 kΩ pull-up to 3V3)
constexpr int PIN_SOIL         = 34;   // Capacitive soil moisture (ADC1)
constexpr int PIN_LIGHT        = 35;   // LDR (ADC1)
constexpr int DHT_TYPE         = DHT22;

// ============================================================================
// Timing
// ============================================================================
constexpr unsigned long SAMPLE_INTERVAL_MS    = 5000UL;
constexpr unsigned long WIFI_RETRY_INTERVAL_MS = 5000UL;
constexpr unsigned long HTTP_TIMEOUT_MS       = 5000UL;

// ============================================================================
// Calibration constants for the analog sensors
// ============================================================================
// Capacitive soil sensors typically return ~ADC 2700 in dry air and ~ADC 1100
// when fully wet. Adjust these two endpoints for your particular sensor by
// reading raw values in air and submerged in water, then update.
constexpr int SOIL_RAW_DRY = 2700;
constexpr int SOIL_RAW_WET = 1100;

// LDR with a 10 kΩ pull-down: brighter -> higher voltage -> higher ADC.
// The mapping below is a coarse linearisation; a real BH1750 would be better.
constexpr int LIGHT_RAW_DARK  = 200;
constexpr int LIGHT_RAW_BRIGHT = 3800;
constexpr int LIGHT_LUX_DARK   = 0;
constexpr int LIGHT_LUX_BRIGHT = 3000;

// ============================================================================
// Globals
// ============================================================================
DHT dht(PIN_DHT, DHT_TYPE);
unsigned long lastSampleAtMs = 0;

// ----------------------------------------------------------------------------
// Wi-Fi
// ----------------------------------------------------------------------------
static void connectWifi() {
    Serial.printf("[wifi] connecting to %s ...\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n[wifi] connected: %s\n", WiFi.localIP().toString().c_str());
}

// ----------------------------------------------------------------------------
// Sensors
// ----------------------------------------------------------------------------
static int clampInt(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static float readSoilMoisturePercent() {
    int raw = analogRead(PIN_SOIL);
    raw = clampInt(raw, SOIL_RAW_WET, SOIL_RAW_DRY);
    // Higher raw value = drier soil. Invert so 100% = fully wet.
    return 100.0f * (SOIL_RAW_DRY - raw) / float(SOIL_RAW_DRY - SOIL_RAW_WET);
}

static float readLightLux() {
    int raw = analogRead(PIN_LIGHT);
    raw = clampInt(raw, LIGHT_RAW_DARK, LIGHT_RAW_BRIGHT);
    return LIGHT_LUX_DARK +
        (raw - LIGHT_RAW_DARK) * float(LIGHT_LUX_BRIGHT - LIGHT_LUX_DARK) /
        float(LIGHT_RAW_BRIGHT - LIGHT_RAW_DARK);
}

// ----------------------------------------------------------------------------
// HTTP POST one reading
// ----------------------------------------------------------------------------
static int httpPost(const char* sensorType, float value, const char* unit) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[post] skipped: wifi down");
        return -1;
    }

    StaticJsonDocument<192> doc;
    doc["sensor_id"] = SENSOR_ID;
    doc["type"] = sensorType;
    doc["value"] = value;
    doc["unit"] = unit;

    char body[192];
    size_t len = serializeJson(doc, body, sizeof(body));
    if (len == 0) {
        Serial.println("[post] json serialise failed");
        return -1;
    }

    HTTPClient http;
    http.setTimeout(HTTP_TIMEOUT_MS);
    if (!http.begin(BACKEND_URL)) {
        Serial.println("[post] http.begin failed");
        return -1;
    }
    http.addHeader("Content-Type", "application/json");
    if (strlen(API_KEY) > 0) {
        http.addHeader("X-API-Key", API_KEY);
    }

    int status = http.POST((uint8_t*)body, len);
    Serial.printf("[post] %s %.2f %s -> %d\n", sensorType, value, unit, status);
    if (status < 0) {
        Serial.printf("[post] error: %s\n", http.errorToString(status).c_str());
    }
    http.end();
    return status;
}

// ----------------------------------------------------------------------------
// One tick
// ----------------------------------------------------------------------------
static void sampleAndSend() {
    float temperature = dht.readTemperature();  // °C
    float humidity    = dht.readHumidity();      // %
    float soil        = readSoilMoisturePercent();
    float light       = readLightLux();

    if (!isnan(temperature)) {
        httpPost("temperature", temperature, "C");
    } else {
        Serial.println("[dht] temperature read failed");
    }
    if (!isnan(humidity)) {
        httpPost("humidity", humidity, "%");
    } else {
        Serial.println("[dht] humidity read failed");
    }
    httpPost("soil_moisture", soil, "%");
    httpPost("light", light, "lux");
}

// ============================================================================
// Arduino entry points
// ============================================================================
void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println();
    Serial.println("[boot] smart-greenhouse esp32 firmware starting");

    pinMode(PIN_SOIL, INPUT);
    pinMode(PIN_LIGHT, INPUT);
    dht.begin();

    connectWifi();
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[wifi] reconnecting...");
        WiFi.disconnect();
        delay(WIFI_RETRY_INTERVAL_MS);
        connectWifi();
        return;
    }

    unsigned long now = millis();
    if (now - lastSampleAtMs >= SAMPLE_INTERVAL_MS) {
        lastSampleAtMs = now;
        sampleAndSend();
    }
}
