# Deployment

This document covers running the project locally for development and bringing the full stack up via Docker Compose.

> **Docker runtime-verification status.** The Docker setup is implemented and config-validated. End-to-end `docker compose up` was **not** run in the authoring sandbox because it blocks container-registry egress (Docker Hub, GHCR, public.ecr.aws all return HTTP 403). Runtime verification must be performed on a machine with normal container-registry access. A self-contained automated verifier is committed at [`scripts/verify-docker.sh`](../scripts/verify-docker.sh).

---

## Prerequisites

For local development (no Docker):

- Python **3.11 or newer**
- Node.js **20 or newer** and npm 10+
- GNU Make (optional but convenient)

For Docker:

- Docker **24 or newer**
- Docker Compose v2 (`docker compose` subcommand, not the legacy `docker-compose` binary)
- The host running Docker must reach `registry-1.docker.io` to pull base images on the first build

---

## 1. Local development setup (no Docker)

### 1.1 Clone and configure

```bash
git clone https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard.git
cd smart-greenhouse-iot-dashboard
cp .env.example .env       # all defaults are safe lab defaults
```

The `.env` file is read by:
- the backend (via `pydantic-settings`)
- the simulator (same loader, different prefix)
- Vite when running `npm run dev` (only `VITE_*` keys cross the boundary into the browser)

### 1.2 Install both stacks

```bash
make install            # → make install-backend && make install-frontend
```

Behind the scenes:

```bash
cd backend  && pip install -e ".[dev]"
cd frontend && npm ci
```

### 1.3 Run the stack

You need three terminals — backend, simulator, and frontend each run their own dev server.

```bash
# Terminal 1 — backend (FastAPI on :8000)
make dev-backend
# = cd backend && uvicorn 'greenhouse.main:create_app' --factory --reload --host 0.0.0.0 --port 8000

# Terminal 2 — simulator (POSTs synthetic readings every 5 s)
make dev-simulator
# = cd backend && python -m greenhouse.simulator

# Terminal 3 — frontend (Vite on :5173)
make dev-frontend
# = cd frontend && npm run dev
```

Open <http://localhost:5173>. Within a few seconds you should see live readings populate as the simulator pushes data.

### 1.4 Backend setup details

The backend is configured entirely through environment variables. The most common defaults:

| Variable | Default | Effect |
|---|---|---|
| `BACKEND_HOST` | `0.0.0.0` | uvicorn bind address |
| `BACKEND_PORT` | `8000` | uvicorn port |
| `DATABASE_URL` | `sqlite:///./data/greenhouse.db` | SQLite path (relative when running locally; absolute in Docker — see below) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins (comma-separated; wildcards intentionally disallowed) |
| `INGEST_RATE_LIMIT_PER_SECOND` | `50` | Token-bucket rate on `POST /api/readings` |
| `MAX_WS_CONNECTIONS` | `100` | WebSocket cap |
| `LOG_LEVEL` | `INFO` |  |
| `LOG_FORMAT` | `json` | `json` for production aggregation, `text` for human reading |
| `GREENHOUSE_API_KEY` | (empty) | If non-empty, write endpoints require `X-API-Key` |

Helpful local backend commands:

```bash
cd backend
ruff check src tests
ruff format --check src tests
pytest --cov=greenhouse --cov-report=term-missing
```

### 1.5 Simulator setup details

The simulator is a CLI utility (`python -m greenhouse.simulator`) that POSTs to the backend. Key env vars:

| Variable | Default | Effect |
|---|---|---|
| `SIMULATOR_BACKEND_URL` | `http://localhost:8000` | Where to POST (`http://backend:8000` inside Docker) |
| `SIMULATOR_INTERVAL_SECONDS` | `5.0` | Seconds between ticks |
| `SIMULATOR_SENSOR_ID` | `esp32-sim-01` | `sensor_id` embedded in payloads |
| `SIMULATOR_API_KEY` | (empty) | Sent as `X-API-Key` when set; must match `GREENHOUSE_API_KEY` |
| `SIMULATOR_MAX_ITERATIONS` | `0` (unlimited) | Stop after N ticks (mainly for tests/demos) |
| `SIMULATOR_MAX_DURATION_SECONDS` | `0.0` (unlimited) | Stop after N seconds |
| `SIMULATOR_INITIAL_BACKOFF_SECONDS` | `1.0` | First sleep after a failed tick |
| `SIMULATOR_MAX_BACKOFF_SECONDS` | `10.0` | Cap on exponential backoff |
| `SIMULATOR_SEED` | (unset) | Optional RNG seed for deterministic walks |

Example short demo run:

```bash
SIMULATOR_INTERVAL_SECONDS=1 SIMULATOR_MAX_ITERATIONS=10 \
  python -m greenhouse.simulator
```

### 1.6 Frontend setup details

Vite reads `VITE_*` variables from `../.env` (the repository-root file). The defaults match the local backend.

| Variable | Default | Effect |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | REST base URL inlined into the bundle |
| `VITE_WS_URL` | `ws://localhost:8000/ws` | WebSocket URL inlined into the bundle |

Helpful local frontend commands:

```bash
cd frontend
npm run lint
npm run format:check
npm run typecheck
npm test -- --run
npm run build
```

---

## 2. Docker Compose setup

> **Status reminder.** Docker support is implemented and config-validated. Runtime verification is pending on a machine with container-registry access.

### 2.1 One-command bring-up

```bash
docker compose up --build
```

This builds three images (backend, simulator reuses the backend image, frontend) and starts the stack. The frontend is served by nginx on host port `5173`. The backend listens on host port `8000`. The simulator runs in the background and pushes to the backend via the internal `greenhouse-net` bridge network.

To run detached:

```bash
docker compose up -d --build
```

To follow logs:

```bash
docker compose logs -f                  # all services
docker compose logs -f backend          # just the backend
docker compose logs -f simulator        # just the simulator
```

To stop:

```bash
docker compose down                     # keeps the SQLite volume
docker compose down -v                  # also removes the volume
```

### 2.2 Verification script

A self-contained script at [`scripts/verify-docker.sh`](../scripts/verify-docker.sh) runs the full smoke test:

```bash
./scripts/verify-docker.sh
```

It does the following and fails loudly on any unexpected result, then tears down:

1. `docker compose build`
2. `docker compose up -d`
3. Waits up to 60 s for `GET /api/health` to return 200
4. `GET /api/health` and assert `"status":"ok"`
5. `sleep 10` so the simulator can push at least one batch
6. `GET /api/readings/latest` and assert all four sensor types are present
7. `GET http://localhost:5173/` and assert HTTP 200
8. `GET http://localhost:5173/healthz` and assert body is `ok`
9. `docker compose logs --tail 10 simulator`
10. `docker compose ps`

Tear-down runs from a `trap EXIT` so Ctrl-C also cleans up.

### 2.3 Compose layout summary

| Service | Image | Host port → container | Healthcheck |
|---|---|---|---|
| `backend` | `greenhouse-backend:0.1.0` | `8000 → 8000` | Python `urllib.request` against `/api/health` |
| `simulator` | reuses `greenhouse-backend:0.1.0` with overridden `command:` | (internal only) | none (depends on backend health) |
| `frontend` | `greenhouse-frontend:0.1.0` | `5173 → 80` | `wget -qO- /healthz` |

Volumes:

| Volume | Mount | Purpose |
|---|---|---|
| `greenhouse-data` | `/app/data` on `backend` | Persists `greenhouse.db` across container restarts |

Networks:

| Network | Driver | Members |
|---|---|---|
| `greenhouse-net` | bridge | All three services |

---

## 3. Environment variables (Docker)

The variables exposed to each container are declared inline in [`docker-compose.yml`](../docker-compose.yml). Key differences from the local-dev defaults:

- `DATABASE_URL=sqlite:////app/data/greenhouse.db` — absolute path, four slashes, matching the volume mount.
- `SIMULATOR_BACKEND_URL=http://backend:8000` — internal Docker DNS hostname, not `localhost`.
- `LOG_FORMAT=json` on the backend, `text` on the simulator (so `docker compose logs simulator` reads naturally).
- `VITE_API_BASE_URL` and `VITE_WS_URL` are passed as **build args**, not runtime env, because Vite inlines them at compile time. They are set to `http://localhost:8000` / `ws://localhost:8000/ws` because the browser runs on the host.

To override, edit `docker-compose.yml` or create a Compose override file (`docker-compose.override.yml`).

---

## 4. SQLite persistence

The backend stores data in `/app/data/greenhouse.db` inside its container, which is the mount point of the named volume `greenhouse-data`. Data survives:

- `docker compose down` (volume retained)
- `docker compose restart`
- `docker compose up` after a previous `down`

Data is wiped by:

- `docker compose down -v`
- `docker volume rm smart-greenhouse-iot-dashboard_greenhouse-data`

Inspect the volume's contents directly:

```bash
docker run --rm -it -v smart-greenhouse-iot-dashboard_greenhouse-data:/data alpine ls -la /data
```

Backup the SQLite file from a running stack:

```bash
docker compose cp backend:/app/data/greenhouse.db ./greenhouse.db.backup
```

---

## 5. Troubleshooting

### "Connection refused" on http://localhost:8000

- Confirm the backend container is up and healthy: `docker compose ps`. The status column should read `Up (healthy)` after ~10 s.
- Local dev: confirm `make dev-backend` is running in another terminal.

### Dashboard loads but shows "Could not load latest readings"

- The backend may be reachable, but `CORS_ALLOWED_ORIGINS` may not include your origin. The defaults cover `http://localhost:5173` and `http://127.0.0.1:5173`. If you serve the dashboard elsewhere, add that origin.
- Open browser DevTools → Network and watch the failing request. A CORS error appears as a blocked preflight or a red request without a status code.

### No alerts after waiting

- Default thresholds are wide enough that normal simulator values rarely breach them. To force a breach for testing, tighten a band:
  ```bash
  curl -X PUT http://localhost:8000/api/thresholds/temperature \
    -H "Content-Type: application/json" \
    -d '{"min_value":21,"max_value":23}'
  ```
- Check `docker compose logs backend` for `ingest` log entries; the alert path is exercised whenever a reading arrives outside the band.

### Frontend renders an empty dashboard with no errors

- Open DevTools → Network and check whether requests go to the expected backend host. If they go to `http://localhost:8000` but you're proxying through some other URL, the `VITE_API_BASE_URL` baked into the build is stale. Rebuild the frontend container (`docker compose build --no-cache frontend`) or restart `npm run dev`.

### WebSocket badge shows "Connection error" or stays "Connecting"

- The frontend connects to `VITE_WS_URL` which defaults to `ws://localhost:8000/ws`. Confirm the backend is reachable at that URL using `wscat -c ws://localhost:8000/ws` (or `websocat`).
- The slot limit (`MAX_WS_CONNECTIONS`) defaults to 100; you can hit it if many tabs are open. Increase the env var and restart the backend.

### `docker compose build` fails at the first BuildKit step with HTTP 403

- The machine you're on cannot reach `registry-1.docker.io`. The authoring sandbox hit exactly this — confirm with `curl -I https://registry-1.docker.io/v2/`. Move to a machine with normal registry access.

### `pytest` fails with `ModuleNotFoundError: No module named 'greenhouse'`

- The package wasn't installed in editable mode. From `backend/`:
  ```bash
  pip install -e ".[dev]"
  ```

### `npm test` hangs forever

- Check that no test is using `waitFor` while `vi.useFakeTimers()` is active. The known case is fixed; if you see a regression, prefer direct synchronous assertions in fake-timer tests.

---

## 6. Status summary

| Item | Status |
|---|---|
| Local dev (backend + simulator + frontend) | ✅ verified, 77 backend tests + 27 frontend tests + production build all green |
| Docker artifacts (Dockerfiles, nginx.conf, compose) | ✅ implemented and config-validated |
| Docker end-to-end runtime | ⏳ pending on a machine with container-registry access — run `./scripts/verify-docker.sh` |

Once the Docker runtime verification passes on your machine, mark the corresponding items in [`PROJECT_COMPLETION_CHECKLIST.md`](../PROJECT_COMPLETION_CHECKLIST.md) and capture screenshots for the README.
