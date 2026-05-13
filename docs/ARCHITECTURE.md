# Architecture

This document describes how the Smart Greenhouse IoT Dashboard is structured and how its components interact at runtime.

---

## 1. Component overview

```
   ┌──────────────────┐        REST + WebSocket        ┌──────────────────┐
   │  Browser (host)  │ ─────────────────────────────▶ │     Backend       │
   │  React + Vite    │   localhost:8000  /  /ws       │ FastAPI / uvicorn │
   │  Tailwind, charts│ ◀───────────────────────────── │  (factory mode)   │
   └────────┬─────────┘                                └───────┬───────────┘
            │                                                  │
            │    static bundle served by nginx                 │  SQLAlchemy
            │    (Docker) or Vite dev (local)                  ▼
            │                                          ┌──────────────────┐
            │                                          │   SQLite file    │
            │                                          │ /app/data/...    │
            │                                          └──────────────────┘
            │
            │
            │                ┌────────────────────────┐
            │                │       Simulator        │
            └────────────────│   python -m greenhouse │
                             │       .simulator       │
                             └───────────┬────────────┘
                                         │  POST /api/readings
                                         ▼
                                 (backend route ingest)


             ─── optional path ───────────────────────────────────────
                                       ┌────────────────────────┐
                                       │   ESP32 firmware       │
                                       │  DHT22 + soil sensor   │
                                       └───────────┬────────────┘
                                                   │  POST /api/readings
                                                   ▼
                                         (backend route ingest)
```

### Roles

| Component | Role | Lives in |
|---|---|---|
| **Backend** | Single source of truth. Persists readings, evaluates thresholds, generates alerts, manages actuator state, broadcasts events via WebSocket. | `backend/src/greenhouse/` |
| **Frontend** | Read-and-control UI. Renders live tiles, history chart, alert log, threshold form, actuator toggles, CSV export panel. | `frontend/src/` |
| **Simulator** | CLI utility that pushes synthetic readings to the backend via HTTP POST. Lets the entire stack run with zero hardware. | `backend/src/greenhouse/simulator.py` |
| **Firmware (optional)** | ESP32 Arduino sketch that reads DHT22 + soil-moisture sensors and POSTs to the same `/api/readings` endpoint. Hardware-only path; the simulator is fully equivalent for review. | `firmware/greenhouse_esp32/` |
| **Database** | SQLite. Four tables: `readings`, `thresholds`, `alerts`, `actuator_state`. Tables auto-created and defaults seeded on first start. | Volume `greenhouse-data` in Docker; `./data/greenhouse.db` locally |

---

## 2. REST flow

A typical "ingest one reading" call:

```
 simulator                  backend                       SQLite                event_bus
    │                          │                            │                       │
    │ POST /api/readings ─────▶│                            │                       │
    │  {sensor_id, type,       │                            │                       │
    │   value, unit, ts?}      │ Pydantic validation        │                       │
    │                          │ rate-limit check           │                       │
    │                          │ optional API-key check     │                       │
    │                          │                            │                       │
    │                          │  INSERT readings ─────────▶│                       │
    │                          │                            │                       │
    │                          │ Threshold lookup           │                       │
    │                          │ thresholds.evaluate()      │                       │
    │                          │                            │                       │
    │                          │  if breach: INSERT alerts ▶│                       │
    │                          │                            │                       │
    │                          │ publish("reading", ...) ───────────────────────────▶│
    │                          │ publish("alert", ...)   ───────────────────────────▶│
    │                          │                            │                       │
    │ 201 Created ◀────────────│ commit + serialize         │                       │
    │ ReadingOut JSON          │                            │                       │
```

The same endpoint handles ingest whether the caller is the simulator, a real ESP32, or curl. Everything writeable is validated by Pydantic literals, so unknown sensor types are rejected at the schema layer before any persistence runs.

---

## 3. WebSocket flow

```
 browser              backend              event_bus              other browser
   │                    │                      │                       │
   │ wss /ws ──────────▶│ try_reserve()        │                       │
   │                    │   hub slot OK        │                       │
   │ <─── 101 Switch ───│                      │                       │
   │                    │ subscribe() ───────▶ queue                   │
   │                    │                      │                       │
   │                    │                      │                       │ (other browser
   │                    │                      │ ◀─── subscribe()      │   subscribes)
   │                    │                      │                       │
   │ (ingest happens elsewhere — see REST flow above)                  │
   │                    │ publish(reading) ──▶ fan-out                 │
   │ ◀── {type:reading, │                  ────────────────────────────│ ◀── (same)
   │      data:{...}}   │                      │                       │
   │                    │                      │                       │
   │ (publish alert)    │ publish(alert) ────▶ fan-out                 │
   │ ◀── {type:alert,   │                  ────────────────────────────│ ◀── (same)
   │      data:{...}}   │                      │                       │
```

If a subscriber queue fills (slow consumer), the bus drops its oldest message before pushing the new one — this prevents a stuck client from blocking the publisher. The hub enforces a `MAX_WS_CONNECTIONS` cap (default 100) and rejects new sockets with code 1013 when full.

On the client, [`useWebSocket`](../frontend/src/hooks/useWebSocket.ts) reconnects with exponential backoff (1 s → 2 → 4 → 8 → 16 → 30 s cap) and resets to the initial delay after a successful open. [`useGreenhouseSocket`](../frontend/src/hooks/useGreenhouseSocket.ts) merges incoming events into the TanStack Query cache (`["readings","latest"]`, `["alerts"]`, `["actuators"]`) so every panel updates live without a poll.

---

## 4. Database flow

- Engine is created via SQLAlchemy 2 in `db.py:create_engine_for(url)`. For SQLite the `check_same_thread` guard is relaxed so FastAPI's thread pool can use the session.
- Sessions are issued per-request through a FastAPI dependency (`deps.get_db`). The dependency yields the session and closes it on response — no global session state.
- `expire_on_commit=False` is set on the session factory so ORM objects remain usable after `session.commit()`, which matters for serializing the just-persisted reading into a Pydantic response without a re-fetch.
- Timestamps are stored as **naive UTC** by convention. Incoming tz-aware timestamps are normalised in `schemas.py:_normalize_to_naive_utc` before they touch the DB. Outgoing timestamps are returned as ISO 8601 strings.
- Indexes: `readings.sensor_id`, `readings.type`, `readings.timestamp`, and a composite `(type, timestamp)` index to make "last-N readings of type X" queries cheap.
- Defaults: on first start, `init_db` seeds four thresholds (`temperature 15–32 °C`, `humidity 40–80 %`, `soil_moisture 30–80 %`, `light 200–1500 lux`) and three actuators (`fan`, `pump`, `light`) all set to `off`. The seeding is idempotent — restarting an already-initialised DB is a no-op.

See [`DATA_MODEL.md`](DATA_MODEL.md) for the full schema.

---

## 5. Docker architecture

The Compose stack ([`docker-compose.yml`](../docker-compose.yml)) brings up three containers on a private bridge network:

```
                                          host:8000
                                          │
            ┌────────────────────────── greenhouse-net (bridge) ────────────┐
            │                             │                                 │
            │   ┌────────────────────────┴───┐    ┌──────────────────────┐  │
            │   │       greenhouse-backend   │    │  greenhouse-frontend │  │
            │   │   FastAPI / uvicorn 8000   │    │     nginx :80        │  │
            │   │   /app/data ◀── volume     │    │  /usr/share/nginx/   │  │
            │   └─────────────┬──────────────┘    │      html (dist)     │  │
            │                 │ healthcheck       │  /healthz            │  │
            │                 │                   └──────────┬───────────┘  │
            │                 │                              │              │
            │                 │                              │ depends_on:  │
            │                 │                              │ service_healthy
            │   ┌─────────────┴──────────────┐               │              │
            │   │     greenhouse-simulator   │               │              │
            │   │  python -m simulator       │               │              │
            │   │  http://backend:8000       │ depends_on:   │              │
            │   └────────────────────────────┘  service_healthy             │
            │                                                               │
            └───────────────────────────────────────────────────────────────┘
                                          │
                                          host:5173 ──▶ frontend container
```

Notes:
- The **backend** and **simulator** share the same image (`greenhouse-backend:0.1.0`). The simulator service just overrides `command:` to `python -m greenhouse.simulator`. One image, two roles, one build pipeline.
- The **frontend Dockerfile** is two stages: a Node 22 build that runs `npm ci && npm run build`, followed by an `nginx:1.27-alpine` runtime that copies `dist/` into `/usr/share/nginx/html`.
- `VITE_API_BASE_URL` and `VITE_WS_URL` are **compile-time build args**, not runtime env vars, because Vite inlines them into the produced JavaScript bundle. They default to `http://localhost:8000` / `ws://localhost:8000/ws` because the browser runs on the host, not inside the Docker network — using the internal `backend` hostname here would break the dashboard.
- The named **volume** `greenhouse-data` mounts at `/app/data` inside the backend container. SQLite lives at `/app/data/greenhouse.db` and survives `docker compose down`. Use `docker compose down -v` to also wipe the volume.

> Docker support is implemented and config-validated. Runtime verification is pending on a machine with container-registry access. See [`DEPLOYMENT.md`](DEPLOYMENT.md) and [`scripts/verify-docker.sh`](../scripts/verify-docker.sh).

---

## 6. Design decisions and tradeoffs

| Decision | Why | Tradeoff |
|---|---|---|
| **SQLite over Postgres** | Single-tenant lab demo; no extra process to run; data is portable | Not suitable for high concurrency or multi-instance deployment |
| **In-process event bus, not Redis** | Zero extra dependencies; trivial to reason about; testable | Doesn't scale beyond one backend process |
| **Custom `TokenBucket`, not `slowapi`** | One file, ~30 lines, fully unit-tested; zero extra runtime dep | Less feature-rich than the alternative (no per-route rules, no header reporting) |
| **App factory pattern** (`create_app(settings)`) | Lets tests inject per-test `Settings` and a fresh SQLite file; lets uvicorn use `--factory` | One indirection more than `app = FastAPI()` |
| **`expire_on_commit=False`** on the session | Lets the CSV streaming response materialize rows before the session is closed by the dependency teardown | Slight risk of using stale ORM state across requests; mitigated by short-lived sessions |
| **Naive UTC for stored timestamps** | Avoids dialect-specific timezone handling in SQLite | Requires explicit normalisation at the schema boundary |
| **Pydantic `Literal` enums for sensor / actuator types** | Unknown values rejected at validation time with HTTP 422 — no special-case code in routes | Adding a new sensor type means editing both the literal and the seed map |
| **Frontend `noUncheckedIndexedAccess`** | Catches "array might be empty" bugs at compile time | Tests need `obj!` or `toBeDefined()` guards after `.find()` / `[index]` |
| **Recharts v2** | Stable API for the project's lifetime | v3 has new features but breaks the chart components; staying on v2 |
| **Vite 5 + Vitest 2 (not v6 / v3)** | Stable API; aligns with current ecosystem docs | 5 dev-only npm audit advisories (dev-server-only); accepted with documented rationale |
| **Same image for backend + simulator** | One Docker build, one set of layers cached, one place to install Python deps | Slightly larger simulator image (it carries FastAPI/uvicorn it doesn't need) |
| **No reverse proxy in front of backend** | Simpler dev experience; browser talks straight to `:8000` | CORS must be open for the dashboard origin; production would prefer single-origin |
| **No screenshots committed in Phase 6** | I do not commit fabricated UI captures | Real screenshots wait for Docker runtime verification |

---

## 7. Future improvements (out of Phase 6 scope)

- Replace SQLite with Postgres + Alembic migrations
- Replace in-process bus with Redis pub/sub so multiple backend instances can broadcast
- Add a reverse-proxy + TLS layer (Caddy or Traefik) for non-localhost deployments
- Code-split the frontend bundle (`manualChunks` for Recharts)
- Add Playwright E2E tests against the running Docker stack
- Move from optional API-key gating to a proper OAuth/JWT system if multi-user becomes a goal
- Expose Prometheus-style `/metrics` endpoint for backend + simulator
