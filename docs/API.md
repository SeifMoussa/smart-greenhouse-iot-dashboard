# API Reference

The backend exposes a small REST + WebSocket surface. All responses are JSON unless explicitly noted (CSV export).

- Base URL (local): `http://localhost:8000`
- Interactive Swagger UI: <http://localhost:8000/docs>
- Raw OpenAPI: <http://localhost:8000/openapi.json>

> All examples below assume the backend is running on `localhost:8000`. Replace as needed.

---

## Conventions

- **Content type:** request bodies must be `application/json`. Responses are JSON unless documented otherwise.
- **Timestamps:** ISO 8601, UTC. The backend stores everything as naive UTC internally and serialises without timezone suffix; clients should treat returned timestamps as UTC.
- **Sensor types** (Pydantic `Literal`): `temperature`, `humidity`, `soil_moisture`, `light`. Anything else is rejected with `422`.
- **Actuator IDs** (Pydantic `Literal`): `fan`, `pump`, `light`. Anything else is rejected with `422`.
- **Severity** (Pydantic `Literal`): `warning`, `critical`.
- **Actuator states** (Pydantic `Literal`): `on`, `off`.

## User auth (JWT)

Every endpoint except `GET /api/health` and `POST /api/auth/login` requires a signed-in user. There are two roles:

- **viewer** — can call every `GET` endpoint (readings, thresholds, alerts, actuators, CSV export).
- **operator** — everything a viewer can do, plus `PUT /api/thresholds/{sensor_type}` and `POST /api/actuators/{actuator_id}/state`.

Log in with `POST /api/auth/login` to get a short-lived JWT, then send it as `Authorization: Bearer <token>` on every other request. Tokens expire after `JWT_EXPIRE_MINUTES` (default 60) and there's no refresh-token flow in this lab build — sign in again once it expires.

Two demo accounts are seeded on first start (`SEED_OPERATOR_USERNAME` / `SEED_OPERATOR_PASSWORD`, `SEED_VIEWER_USERNAME` / `SEED_VIEWER_PASSWORD` in `.env.example`) — change these for anything beyond a local demo.

| Endpoint | Minimum role |
|---|---|
| `GET /api/health` | none |
| `POST /api/auth/login` | none |
| `GET /api/readings`, `/api/readings/latest`, `/api/thresholds`, `/api/alerts`, `/api/actuators`, `/api/export.csv` | viewer |
| `PUT /api/thresholds/{sensor_type}` | operator |
| `POST /api/actuators/{actuator_id}/state` | operator |
| `WS /ws` | viewer (token passed as `?token=` query param — see [WebSocket](#websocket)) |

`POST /api/readings` (ingest) is the one exception: it isn't part of the user-auth model at all. It's the endpoint the sensor simulator and ESP32 firmware post to, and neither can do an interactive login — see [API key](#api-key-device-ingest-only) below.

## API key (device ingest only)

If the backend has `GREENHOUSE_API_KEY` set to a non-empty string, `POST /api/readings` requires that value in the `X-API-Key` header. This is separate from the JWT auth above — it's the credential for the sensor simulator and ESP32 firmware, neither of which can do an interactive login.

When the key is empty (default), ingest is open. This is the demo-friendly default; set the env var when running anywhere other than localhost.

---

## Rate limiting

`POST /api/readings` is protected by an in-process token bucket. The default capacity / refill rate is `INGEST_RATE_LIMIT_PER_SECOND=50` requests/second/client IP. Exceeding the budget returns `HTTP 429`.

`POST /api/auth/login` has its own, much tighter bucket — `LOGIN_RATE_LIMIT_PER_SECOND=5` requests/second/client IP — to slow down password guessing.

Other endpoints are not rate-limited at the application layer.

---

## Endpoints

### Health

#### `GET /api/health`

Liveness check used by Docker `HEALTHCHECK` and uptime monitoring.

- **Auth:** none
- **Response:** `200 OK`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_seconds": 42.18
}
```

```bash
curl http://localhost:8000/api/health
```

---

### Auth

#### `POST /api/auth/login` — exchange credentials for a JWT

- **Auth:** none
- **Rate-limited:** yes, tighter bucket than ingest (see [Rate limiting](#rate-limiting))
- **Request body:**

```json
{ "username": "operator", "password": "operator123" }
```

- **Response:** `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "operator",
  "username": "operator"
}
```

- **Errors:**
  - `401` unknown username or wrong password
  - `429` rate limit exceeded

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"operator","password":"operator123"}'
```

Use the returned `access_token` on every other request:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"operator","password":"operator123"}' | jq -r .access_token)

curl http://localhost:8000/api/readings -H "Authorization: Bearer $TOKEN"
```

---

### Readings

#### `POST /api/readings` — ingest one reading

- **Auth:** API key required when configured (device credential — see [API key](#api-key-device-ingest-only))
- **Rate-limited:** yes (token bucket)
- **Request body:**

```json
{
  "sensor_id": "esp32-01",
  "type": "temperature",
  "value": 22.5,
  "unit": "C",
  "timestamp": "2026-05-11T12:34:56Z"   // optional; defaults to now
}
```

- **Validation:**
  - `sensor_id`: 1–64 chars
  - `type`: one of the four sensor literals
  - `unit`: 1–16 chars
  - `timestamp`: ISO 8601; must not be more than 5 minutes in the future
- **Response:** `201 Created` with the persisted record:

```json
{
  "id": 17,
  "sensor_id": "esp32-01",
  "type": "temperature",
  "value": 22.5,
  "unit": "C",
  "timestamp": "2026-05-11T12:34:56",
  "created_at": "2026-05-11T12:34:56.234"
}
```

If the value breaches the sensor's threshold band, an `alert` is also persisted and broadcast over WebSocket (no separate REST call needed).

- **Errors:**
  - `401` invalid or missing `X-API-Key` (when the key is configured)
  - `422` validation failure (unknown sensor type, missing field, future timestamp, etc.)
  - `429` rate limit exceeded

```bash
curl -X POST http://localhost:8000/api/readings \
  -H "Content-Type: application/json" \
  -d '{"sensor_id":"esp32-01","type":"temperature","value":22.5,"unit":"C"}'
```

#### `GET /api/readings` — list readings

Query params (all optional):

| Param | Type | Description |
|---|---|---|
| `type` | sensor type | Filter to one sensor type |
| `from` | ISO 8601 | Inclusive lower bound on `timestamp` |
| `to` | ISO 8601 | Inclusive upper bound on `timestamp` |
| `limit` | integer | 1–10 000; default `100` |

- **Auth:** viewer role required (Bearer token)
- **Response:** `200 OK`, array of `ReadingOut`, **newest first**:

```json
[
  {
    "id": 18,
    "sensor_id": "esp32-01",
    "type": "humidity",
    "value": 55.2,
    "unit": "%",
    "timestamp": "2026-05-11T12:35:01",
    "created_at": "2026-05-11T12:35:01.012"
  }
]
```

```bash
# Last 50 humidity readings
curl 'http://localhost:8000/api/readings?type=humidity&limit=50'

# All readings in a time window
curl 'http://localhost:8000/api/readings' \
  --data-urlencode 'from=2026-05-11T00:00:00Z' \
  --data-urlencode 'to=2026-05-11T23:59:59Z' -G
```

#### `GET /api/readings/latest` — latest reading per sensor type

Returns up to one reading per sensor type — the most recent one. Used by the dashboard's Live Readings panel.

- **Auth:** viewer role required (Bearer token)
- **Response:** `200 OK`, array of `ReadingOut` (possibly empty)

```bash
curl http://localhost:8000/api/readings/latest
```

---

### Thresholds

#### `GET /api/thresholds` — list configured threshold bands

- **Auth:** viewer role required (Bearer token)
- **Response:** `200 OK`

```json
[
  {"type": "humidity",      "min_value": 40.0,  "max_value": 80.0,   "updated_at": "2026-05-11T12:00:00"},
  {"type": "light",         "min_value": 200.0, "max_value": 1500.0, "updated_at": "2026-05-11T12:00:00"},
  {"type": "soil_moisture", "min_value": 30.0,  "max_value": 80.0,   "updated_at": "2026-05-11T12:00:00"},
  {"type": "temperature",   "min_value": 15.0,  "max_value": 32.0,   "updated_at": "2026-05-11T12:00:00"}
]
```

Defaults are seeded on first start; you'll always see all four entries.

```bash
curl http://localhost:8000/api/thresholds
```

#### `PUT /api/thresholds/{sensor_type}` — update one threshold band

- **Auth:** operator role required (Bearer token)
- **Path:** `sensor_type` must be one of the four sensor literals
- **Request body:**

```json
{
  "min_value": 18.0,
  "max_value": 30.0
}
```

- **Validation:** `min_value` must be strictly less than `max_value`.
- **Response:** `200 OK` with the updated `ThresholdOut`.
- **Errors:**
  - `401` missing, invalid, or expired token
  - `403` token is valid but the role is `viewer`, not `operator`
  - `422` unknown sensor type or `min ≥ max`

```bash
curl -X PUT http://localhost:8000/api/thresholds/temperature \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"min_value":18,"max_value":30}'
```

---

### Alerts

#### `GET /api/alerts` — list recent alerts

Returned newest first. Alerts are produced automatically by the backend when an ingested reading falls outside the sensor's threshold band.

Query params:

| Param | Type | Description |
|---|---|---|
| `limit` | integer | 1–1 000; default `50` |

- **Auth:** viewer role required (Bearer token)
- **Response:** `200 OK`

```json
[
  {
    "id": 9,
    "type": "temperature",
    "value": 35.0,
    "threshold_min": 15.0,
    "threshold_max": 32.0,
    "severity": "warning",
    "message": "Value 35.0 is above maximum 32.0",
    "created_at": "2026-05-11T12:36:00"
  }
]
```

Severity rules: if the distance past the band is greater than 25 % of the band width, the alert is `critical`; otherwise `warning`.

```bash
curl 'http://localhost:8000/api/alerts?limit=20'
```

---

### Actuators

#### `GET /api/actuators` — list actuators and current state

- **Auth:** viewer role required (Bearer token)
- **Response:** `200 OK`

```json
[
  {"id": "fan",   "name": "Ventilation Fan", "state": "off", "updated_at": "2026-05-11T12:00:00"},
  {"id": "light", "name": "Grow Light",      "state": "off", "updated_at": "2026-05-11T12:00:00"},
  {"id": "pump",  "name": "Water Pump",      "state": "off", "updated_at": "2026-05-11T12:00:00"}
]
```

```bash
curl http://localhost:8000/api/actuators -H "Authorization: Bearer $TOKEN"
```

#### `POST /api/actuators/{actuator_id}/state` — set actuator state

- **Auth:** operator role required (Bearer token)
- **Path:** `actuator_id` is one of `fan`, `pump`, `light`
- **Request body:**

```json
{ "state": "on" }    // or "off"
```

- **Response:** `200 OK` with the updated `ActuatorOut`. The change is also broadcast over WebSocket as an `actuator` event.
- **Errors:**
  - `401` missing, invalid, or expired token
  - `403` token is valid but the role is `viewer`, not `operator`
  - `404` actuator not found in DB (should not happen with default seeding)
  - `422` unknown `actuator_id` or invalid `state`

```bash
curl -X POST http://localhost:8000/api/actuators/fan/state \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state":"on"}'
```

---

### CSV export

#### `GET /api/export.csv` — stream readings as CSV

Query params:

| Param | Type | Description |
|---|---|---|
| `from` | ISO 8601 | Inclusive lower bound |
| `to` | ISO 8601 | Inclusive upper bound |
| `type` | sensor type | Filter to a single sensor type |

- **Auth:** viewer role required (Bearer token). The dashboard fetches this with the Authorization header attached and saves the response as a blob — it can't use a plain download link, since browsers don't attach custom headers to a normal navigation.
- **Constraints:** if both `from` and `to` are provided, their range must not exceed **30 days**.
- **Response:** `200 OK`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="greenhouse-readings-<UTC-stamp>.csv"`
- **CSV header:** `id,sensor_id,type,value,unit,timestamp`
- **Errors:**
  - `400` time range exceeds 30 days
  - `401` missing, invalid, or expired token

```bash
# Download last 24 hours as CSV
curl -OJ 'http://localhost:8000/api/export.csv' \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "from=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --data-urlencode "to=$(date -u +%Y-%m-%dT%H:%M:%SZ)" -G
```

---

## WebSocket

### `WS /ws`

Connect to receive a live stream of events. There are no client commands — the server only pushes.

- **URL:** `ws://localhost:8000/ws?token=<access_token>` (or `wss://` when behind TLS)
- **Auth:** viewer role required. Browsers can't attach custom headers to a WebSocket handshake, so the JWT travels as a `token` query parameter instead of a `Bearer` header — it's verified the same way. A missing or invalid token closes the connection with code `1008` (policy violation) before it's accepted.
- **Slot limit:** `MAX_WS_CONNECTIONS` (default `100`). When the limit is reached, new connections are rejected before the upgrade with code `1013`.
- **Format:** one JSON object per server-sent frame, with `{"type": <event>, "data": <object>}` shape.

### Event types

| `type` | `data` | When the server emits it |
|---|---|---|
| `reading` | `ReadingOut` (same shape as `GET /api/readings/latest` element) | After a successful `POST /api/readings` |
| `alert` | `AlertOut` (same shape as `GET /api/alerts` element) | After ingest, when the new reading breaches the threshold band |
| `actuator` | `ActuatorOut` (same shape as `GET /api/actuators` element) | After a successful `POST /api/actuators/{actuator_id}/state` |

Example sequence the dashboard might observe:

```json
{"type":"reading","data":{"id":17,"sensor_id":"esp32-01","type":"temperature","value":35.0,"unit":"C","timestamp":"2026-05-11T12:36:00","created_at":"2026-05-11T12:36:00.012"}}
{"type":"alert","data":{"id":4,"type":"temperature","value":35.0,"threshold_min":15.0,"threshold_max":32.0,"severity":"warning","message":"Value 35.0 is above maximum 32.0","created_at":"2026-05-11T12:36:00.029"}}
{"type":"actuator","data":{"id":"fan","name":"Ventilation Fan","state":"on","updated_at":"2026-05-11T12:36:05"}}
```

The frontend uses [`useWebSocket`](../frontend/src/hooks/useWebSocket.ts) for the connection and [`useGreenhouseSocket`](../frontend/src/hooks/useGreenhouseSocket.ts) to merge events into the TanStack Query cache.

### Client behaviour notes

- Non-JSON frames are silently ignored on the client.
- On close or error the client reconnects with exponential backoff (1 s → 2 → 4 → 8 → 16 → 30 s cap). Backoff resets to the initial delay after a successful open.
- There is no ping/pong protocol implemented on the application layer; rely on the underlying WebSocket implementation's keep-alive.

---

## Quick smoke recipe

After `make dev-backend` (or once Docker is up):

```bash
# Health (no auth needed)
curl -s http://localhost:8000/api/health | jq

# Sign in as the seeded operator account and grab the token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"operator","password":"operator123"}' | jq -r .access_token)

# Defaults seeded?
curl -s http://localhost:8000/api/thresholds -H "Authorization: Bearer $TOKEN" | jq
curl -s http://localhost:8000/api/actuators -H "Authorization: Bearer $TOKEN" | jq

# Ingest one reading (device credential, not the JWT above)
curl -s -X POST http://localhost:8000/api/readings \
  -H "Content-Type: application/json" \
  -d '{"sensor_id":"manual-1","type":"temperature","value":22.0,"unit":"C"}' | jq

# Latest per sensor type
curl -s http://localhost:8000/api/readings/latest -H "Authorization: Bearer $TOKEN" | jq

# Live stream (requires websocat or wscat)
websocat "ws://localhost:8000/ws?token=$TOKEN"
```
