# Example commands

Copy-pasteable command recipes covering the most useful workflows. For the
full reference see:

- [README](../README.md) — quick-start and project overview
- [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) — full deployment instructions and troubleshooting
- [docs/API.md](../docs/API.md) — every backend endpoint with curl examples

## Automated Docker verification

A self-contained script runs the full Docker smoke test end-to-end on a
machine with container-registry access. It builds, starts the stack,
waits for health, exercises every endpoint the dashboard relies on, and
tears down again — failing loudly if anything is wrong.

```bash
./scripts/verify-docker.sh
```

What it runs (also documented step by step below):

```bash
docker compose build
docker compose up -d
curl http://localhost:8000/api/health
sleep 10
curl http://localhost:8000/api/readings/latest
curl http://localhost:5173                  # frontend HTML
curl http://localhost:5173/healthz          # nginx healthcheck
docker compose logs simulator
docker compose down
```

---

## One-command Docker demo

```bash
# From the repository root
docker compose up --build
```

Then open <http://localhost:5173> in your browser. The simulator
automatically starts feeding the backend, and the dashboard updates live.

To stop and remove the stack (keeps the SQLite volume):

```bash
docker compose down
```

To also remove the persisted SQLite database:

```bash
docker compose down -v
```

## Tail Docker logs

```bash
docker compose logs -f                  # all services
docker compose logs -f backend          # just the backend
docker compose logs -f simulator        # just the simulator
```

## Quick health & smoke checks once Compose is up

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/readings/latest
curl http://localhost:5173/healthz
```

---

## Run the simulator against a local backend

```bash
# Defaults: 4 sensors, 5-second interval, runs forever until Ctrl-C.
cd backend
python -m greenhouse.simulator
```

## Short demo run (10 ticks then stop)

```bash
SIMULATOR_MAX_ITERATIONS=10 \
SIMULATOR_INTERVAL_SECONDS=1 \
python -m greenhouse.simulator
```

## Deterministic walk for screencasts / docs

```bash
SIMULATOR_SEED=42 \
SIMULATOR_MAX_ITERATIONS=30 \
python -m greenhouse.simulator
```

## Against a backend protected by an API key

```bash
SIMULATOR_API_KEY=$(grep ^GREENHOUSE_API_KEY .env | cut -d= -f2) \
python -m greenhouse.simulator
```

## Driving a remote backend

```bash
SIMULATOR_BACKEND_URL=http://192.168.1.50:8000 \
SIMULATOR_SENSOR_ID=raspi-greenhouse-A \
python -m greenhouse.simulator
```

## Manual ingest with curl (for parity testing)

```bash
curl -X POST http://localhost:8000/api/readings \
  -H "Content-Type: application/json" \
  -d '{"sensor_id":"manual-1","type":"temperature","value":22.5,"unit":"C"}'
```

## Tail alerts

```bash
watch -n 2 'curl -s http://localhost:8000/api/alerts | jq ".[0:3]"'
```
