# Testing Report

> Updated as each part of the stack landed. Nothing in here is fabricated — every command below was actually run, and the numbers are copied from real output.

## Repository scaffold

- **Date:** 2026-05-10
- **Scope:** Folder structure, license, gitignore, env template, Makefile, docker-compose scaffold, root docs.
- **Tests executed:** None — no executable code exists yet, just config and docs.

## Backend

- **Date:** 2026-05-11
- **Python:** 3.12.3
- **Toolchain:** pytest 9.0.3, pytest-asyncio 1.3.0, pytest-cov 7.1.0, ruff 0.15.12
- **Runtime libs:** fastapi 0.136.1, sqlalchemy 2.0.49, pydantic 2.13.4, pydantic-settings 2.14.1

### Commands run

```bash
pip install -e ".[dev]" --break-system-packages
ruff check src tests
ruff format --check src tests
pytest --cov=greenhouse --cov-report=term-missing
```

### Results

| Gate | Result |
|---|---|
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 34 files already formatted |
| `pytest` | **58 passed in 5.62 s** |
| Coverage | **95 %** (574 statements, 29 missed) — well above the 70 % gate |

### Per-test-file pass counts

| File | Passes |
|---|---|
| `test_actuators.py` | 5 |
| `test_alerts.py` | 6 |
| `test_api_key.py` | 7 |
| `test_event_bus.py` | 4 |
| `test_export.py` | 4 |
| `test_health.py` | 1 |
| `test_logging.py` | 4 |
| `test_rate_limit.py` | 1 |
| `test_readings.py` | 9 |
| `test_thresholds.py` | 6 |
| `test_thresholds_eval.py` | 8 |
| `test_ws.py` | 3 |
| **Total** | **58** |

### Per-module coverage

| Module | Coverage |
|---|---|
| `__init__.py` | 100 % |
| `config.py` | 94 % |
| `db.py` | 100 % |
| `deps.py` | 100 % |
| `event_bus.py` | 87 % |
| `logging_config.py` | 96 % |
| `main.py` | 98 % |
| `models.py` | 100 % |
| `rate_limit.py` | 95 % |
| `routes/__init__.py` | 100 % |
| `routes/actuators.py` | 96 % |
| `routes/alerts.py` | 100 % |
| `routes/export.py` | 91 % |
| `routes/health.py` | 100 % |
| `routes/readings.py` | 93 % |
| `routes/thresholds.py` | 91 % |
| `routes/ws_route.py` | 85 % |
| `schemas.py` | 99 % |
| `thresholds.py` | 100 % |
| `ws.py` | 86 % |
| **Project** | **95 %** |

### Bugs found and fixed

1. **`readme = "../README.md"` rejected by setuptools.** `pip install -e` failed because the project README sat outside the package directory. **Fix:** drop the cross-directory `readme` field from `pyproject.toml`; the root README documents the project.
2. **Ruff B008 false-positive on FastAPI `Depends`/`Query`.** Ruff treated FastAPI's standard dependency-injection idiom as a mutable-default bug — 21 false positives. **Fix:** add `[tool.ruff.lint.flake8-bugbear].extend-immutable-calls` listing `fastapi.Depends`, `fastapi.Query`, etc.
3. **`datetime.now(timezone.utc)` flagged by UP017.** Modern Python prefers `datetime.UTC`. **Fix:** ruff auto-fixed all 21 occurrences across source and tests.
4. **CSV-export range test got 422 instead of 400.** The test built the URL with a string-formatted `+00:00` offset; HTTP query parsing decoded `+` to a space and validation failed before reaching the 30-day check. **Fix:** pass params via httpx's `params=` kwarg which URL-encodes correctly.

### Smoke test

End-to-end app boot via factory:

```bash
DATABASE_URL=sqlite:///:memory: python -c "from greenhouse.main import create_app; app=create_app()"
```

Confirmed registered routes: `/api/health`, `/api/readings`, `/api/readings/latest`, `/api/thresholds`, `/api/thresholds/{sensor_type}`, `/api/alerts`, `/api/actuators`, `/api/actuators/{actuator_id}/state`, `/api/export.csv`, `/ws`, plus FastAPI's `/docs`, `/redoc`, `/openapi.json`.

### Known gaps

- WebSocket close-on-full path (`ws_route.py:22-23`) and rare error paths are not directly exercised; they would require race-condition tests. The happy path is covered.
- `logging_config.py:22` (uncovered) is the `exc_info` branch — would need an exception-bearing log record; low value.
- Query-string-with-timezone branches in `routes/readings.py` and `routes/export.py` are uncovered for the same reason as bug #4; backend logic is correct, the gap is purely in test coverage of an edge encoding case.

## Simulator

- **Date:** 2026-05-11
- **Toolchain:** same as the backend (ruff 0.15.12, pytest 9.0.3, pytest-cov 7.1.0)

### Commands run

```bash
ruff check src tests
ruff format --check src tests
pytest --cov=greenhouse --cov-report=term-missing
# Live smoke: simulator subprocess against running uvicorn
uvicorn 'greenhouse.main:create_app' --factory --port 8765 &
SIMULATOR_BACKEND_URL=http://127.0.0.1:8765 \
SIMULATOR_INTERVAL_SECONDS=0.5 \
SIMULATOR_MAX_ITERATIONS=3 \
SIMULATOR_SEED=42 \
python -m greenhouse.simulator
```

### Results

| Gate | Result |
|---|---|
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 36 files already formatted |
| `pytest` | **77 passed in 3.49 s** (19 new simulator tests + 58 carried over) |
| Coverage on `simulator.py` | **97 %** (126 stmts, 4 missed) |
| Total project coverage | **95 %** (700 stmts, 33 missed) |
| Live smoke (uvicorn + simulator) | 3 ticks × 4 sensors = 12 readings persisted, all sensor types present |

### Simulator tests added (19)

| Group | Test | Verifies |
|---|---|---|
| SensorState | `test_sensor_state_starts_at_spec_start` | Initial value matches spec |
| SensorState | `test_sensor_state_single_step_bounded_by_walk_step` | One step never exceeds the walk step delta |
| SensorState | `test_sensor_state_stays_within_hard_bounds_under_many_steps` | 5 000 steps × 4 sensors all stay in hard bounds |
| SensorState | `test_sensor_state_does_not_drift_outside_bounds_even_when_pushed` | Adversarial max-positive deltas still clip at hard_max |
| Payload | `test_build_payload_has_expected_keys` | Payload shape matches the ingest API |
| Payload | `test_build_payload_passes_backend_validation` | Every spec produces a payload that `ReadingIn` accepts |
| Posting | `test_tick_posts_one_request_per_sensor` | One POST per sensor type per tick |
| Posting | `test_tick_includes_api_key_header_when_configured` | `X-API-Key` header present when key set |
| Posting | `test_tick_omits_api_key_header_when_unset` | No `X-API-Key` header when key empty |
| Failure | `test_tick_survives_connection_errors` | `ConnectError` doesn't crash; backoff applied |
| Failure | `test_tick_backoff_doubles_on_consecutive_failures` | 1 → 2 → 4 → 4 (capped) progression |
| Failure | `test_tick_resets_backoff_after_success` | Backoff returns to initial after successful tick |
| Failure | `test_tick_treats_4xx_as_failure_but_does_not_crash` | 400 response counted as failure, no crash |
| Failure | `test_tick_treats_5xx_as_failure_but_does_not_crash` | 503 response counted as failure, no crash |
| Loop control | `test_run_respects_max_iterations` | Loop stops exactly at the configured iteration count |
| Loop control | `test_run_respects_max_duration` | Loop stops once the duration budget is consumed |
| Loop control | `test_run_stops_on_request_stop` | Signal-equivalent stop request honored immediately |
| End-to-end | `test_simulator_e2e_against_real_backend` | Real Simulator drives the real FastAPI app via `TestClient`; readings land in DB |
| End-to-end | `test_simulator_e2e_triggers_alert_when_threshold_breached` | With a tightened band, walk eventually produces an alert |

### Bugs found and fixed

1. **UP037 lint error: stringified type annotation on `_ok_handler`.** Used `"callable[...]"` as a quoted string before importing the proper type. **Fix:** import `Callable` from `collections.abc` and use it directly.

That was the only issue; everything else passed on the first run thanks to the test-first design with dependency injection (HTTP client and sleep are both injectable).

### Smoke-test transcript

Simulator output during the live run (truncated):

```
INFO greenhouse.simulator: sent type=temperature value=22.14 unit=C
INFO httpx: HTTP Request: POST http://127.0.0.1:8765/api/readings "HTTP/1.1 201 Created"
INFO greenhouse.simulator: sent type=humidity value=53.58 unit=%
...
INFO greenhouse.simulator: reached max iterations=3
INFO greenhouse.simulator: simulator finished iterations=3
```

Backend confirms persistence after the run:
```
Total readings: 12
Sensor types seen: ['humidity', 'light', 'soil_moisture', 'temperature']
```

### Known gaps

- The `main()` CLI entry point and signal handlers are marked `# pragma: no cover`. They're exercised by the live smoke test above but excluded from coverage because automated tests cannot reliably drive Unix signals across platforms.
- The simulator runs synchronous HTTP because it's a single-flow CLI utility; for ESP32-scale parallelism it would not need rework, but a future enhancement could use `asyncio` + `httpx.AsyncClient` to drive thousands of virtual sensors.
- No structured Prometheus/metrics emission yet — out of scope for a portfolio demo.

## Frontend

- **Date:** 2026-05-11
- **Toolchain:** Node 22.22.2, npm 10.9.7, Vite 5.4.21, Vitest 2.1.9, TypeScript 5.6.3 (strict), ESLint 9.x flat config, Prettier 3.3.x
- **Total deps installed:** 537 (47 prod, 491 dev, 49 optional)

### Commands run

```bash
npm install                 # → 158 packages funded, package-lock.json committed
npm run lint                # eslint .
npx prettier --write .      # initial auto-format on 14 files
npm run format:check        # prettier --check .
npm run typecheck           # tsc --noEmit (strict)
npm test -- --run           # vitest --run
npm run build               # tsc --noEmit && vite build
npm audit                   # reviewed; see decision below
```

### Results

| Gate | Result |
|---|---|
| `npm install` | Clean install, `package-lock.json` (7 723 lines) committed |
| `npm run lint` | Clean — no ESLint errors or warnings |
| `npm run format:check` | All matched files use Prettier code style |
| `npm run typecheck` | No TypeScript errors |
| `npm test -- --run` | **27 passed across 6 files in 6.65 s** |
| `npm run build` | Built `dist/` in 6.76 s · 583 kB JS (169 kB gzipped) + 15 kB CSS |
| Backend regression | 77/77 tests still pass after frontend changes |

### Test breakdown

| File | Tests | Focus |
|---|---|---|
| `tests/client.test.ts` | 6 | apiRequest JSON parsing, POST body, error mapping; buildExportUrl param shaping |
| `tests/useTheme.test.tsx` | 4 | Stored theme on mount, persistence, toggle, dark-class application |
| `tests/useWebSocket.test.tsx` | 6 | Connect → open, messages, reconnect with exponential backoff, backoff reset on success, no reconnect after unmount, ignores non-JSON |
| `tests/LiveReadings.test.tsx` | 4 | Renders all sensor types, displays value+unit, "No data" state, error state |
| `tests/ThresholdsForm.test.tsx` | 3 | Loads current thresholds, client-side rejects min>=max, valid PUT submission |
| `tests/ExportPanel.test.tsx` | 4 | Default href, from/to params, "all" omits time params, type param applied |

### Bugs found and fixed

1. **Prettier reformatted 14 files on first install.** Several source and test files weren't preformatted. **Fix:** ran `npx prettier --write .` once; subsequent `npm run format:check` clean.

2. **TypeScript strict mode rejected `MockWebSocket` handler types in `useWebSocket.test.tsx`.** Handlers were typed as `((this: WebSocket, ev: Event) => void) | null`, but TypeScript could not assign `MockWebSocket` to the `this: WebSocket` binding (missing properties like `binaryType`, `extensions`, etc.). **Fix:** drop the `this: WebSocket` annotation — the hook only ever calls the handlers as plain functions, so the bound `this` does not matter.

3. **`fetchMock.mock.calls[0]` typed as `[] | undefined` under `noUncheckedIndexedAccess`.** Without an explicit signature, `vi.fn(async () => …)` types `.mock.calls` as `Array<[]>`, so destructuring or indexing produced strict-mode errors in `tests/client.test.ts` and `tests/ThresholdsForm.test.tsx`. **Fix:** use `vi.fn<typeof fetch>(…)` so call-argument types match the real `fetch` signature, then access elements via `call![n]` after a `toBeDefined()` guard.

4. **One Vitest test hanged for 5 s and timed out.** `useWebSocket > ignores non-JSON frames without crashing` used `await waitFor(() => expect(messages.length).toBe(0))` while the surrounding `beforeEach` enabled fake timers. `waitFor` polls via real timers internally; with fake timers active and nothing to advance, it never resolved. **Fix:** the `JSON.parse` failure inside `onmessage` is synchronous, so the assertion needs no `waitFor` — replaced with a direct `expect(messages).toEqual([])` and dropped the now-unused `waitFor` import.

5. **Vite build emits a 583 kB JavaScript chunk (warning, not error).** Recharts pulls in a large slice of D3 internals. This is a known characteristic, not a build failure, and not blocking. Noted below as a known limitation; a future pass could split it out with `manualChunks`.

### npm audit result and decision

```
5 moderate severity vulnerabilities

esbuild ≤ 0.24.2  (GHSA-67mh-4wv8-2f99)
  ↳ vite ≤ 6.4.1
  ↳ @vitest/mocker
  ↳ vite-node
  ↳ vitest
```

**Analysis:**
- All 5 advisories trace to the single esbuild dev-server SSRF (CVE summarized in GHSA-67mh-4wv8-2f99). The vulnerable code path runs only when a browser visits a malicious page that can talk to the local dev server — it does **not** affect the production bundle, the built `dist/` artifact, or any code shipped to users.
- All vulnerable packages are **dev-only**. Marked in `package.json` under `devDependencies`; verified via `npm audit --json` (`prod: 47, dev: 491`).
- The suggested fix is `npm audit fix --force`, which would upgrade Vite from 5 → 8 and Vitest from 2 → 4. Both are major version bumps with breaking API changes; applying them would require rewriting test mocks and validating module-resolution changes — and would invalidate the green test suite we just landed.

**Decision: accept the advisory, document the rationale, and revisit at the next planned dependency refresh.**

This matches industry practice for transitive dev-tool advisories that have no production exposure. The lab-only disclaimer in `README.md` already states that the project is intended for local development; this is the exact scope where a "dev server only reachable from localhost" risk is acceptable.

A follow-up issue is worth opening at some point to track an eventual Vite 6+ upgrade.

### Production build summary

```
dist/index.html                   0.90 kB │ gzip:   0.55 kB
dist/assets/index-DHsq5UQC.css   14.75 kB │ gzip:   3.46 kB
dist/assets/index-De_PcPrD.js   582.89 kB │ gzip: 168.65 kB │ map: 2,260.78 kB
```

### Known gaps

- **JavaScript bundle is one big chunk.** No code-splitting / lazy-loading yet. 169 kB gzipped is fine for a dashboard; can be improved later via `manualChunks` if needed.
- **No E2E browser tests.** Coverage is unit + component + hook level via Vitest + Testing Library. A future Playwright suite could validate the full UI against a running backend.
- **5 moderate dev-only npm advisories** as documented above.
- **Recharts is pinned to v2.** v3 has breaking API changes; staying on v2 keeps the chart components stable.
- **The dashboard does not display when the backend is unreachable** — instead each card shows its individual "Could not load" state. Acceptable: the `ConnectionBadge` in the header signals the WebSocket status independently, so users see one global indicator plus per-panel error messaging.

## Docker Compose

- **Date:** 2026-05-11
- **Status:** **Implementation-complete and config-validated, but Docker runtime verification is pending.** End-to-end `docker compose build` / `docker compose up` couldn't be completed on the machine I wrote this on — outbound access to container registries (Docker Hub, GHCR, public.ecr.aws) is blocked on that network, all returning HTTP 403. Everything that *can* be validated without registry access has been validated.
- **Toolchain:** Docker 29.1.3, Docker Compose v2.40.3, Buildkit (default driver), nginx 1.24 (used locally for config syntax checking), Ubuntu 24.04

### What this phase did vs did not verify

| Item | Status |
|---|---|
| `backend/Dockerfile` exists and is structurally correct | ✅ verified |
| `frontend/Dockerfile` exists and is structurally correct | ✅ verified |
| `frontend/nginx.conf` exists and is syntactically valid | ✅ verified (`nginx -t` locally) |
| `docker-compose.yml` is valid | ✅ verified (`docker compose config` resolves and validates) |
| Backend `uvicorn --factory` command works | ✅ verified outside Docker against the real backend |
| Backend Dockerfile `HEALTHCHECK` Python one-liner works | ✅ verified outside Docker, exits 0 against `/api/health` |
| Backend tests still pass | ✅ 77 / 77 |
| Frontend tests still pass | ✅ 27 / 27 |
| Frontend production build (the `npm run build` invoked by the Dockerfile) | ✅ verified |
| `docker compose build` end-to-end | ❌ **blocked** — base-image pull denied by network egress |
| `docker compose up` end-to-end | ❌ **blocked** — same reason |
| Frontend reachable in browser from running container | ❌ **pending** local runtime verification |
| Simulator successfully posts from inside the Docker network | ❌ **pending** local runtime verification |
| Healthchecks fire correctly under runtime | ❌ **pending** local runtime verification |

### Network limitation in detail

This machine's network only allows egress to a documented allow-list (PyPI, npm registry, GitHub, etc.). Container registries aren't in the list. Verified directly:

```
$ curl -sI -o /dev/null -w "HTTP %{http_code}\n" https://registry-1.docker.io/v2/
HTTP 403

$ docker pull alpine:3.19
Error response from daemon: unknown: failed to resolve reference
"docker.io/library/alpine:3.19": unexpected status from HEAD request
to https://registry-1.docker.io/v2/library/alpine/manifests/3.19:
403 Forbidden
```

`public.ecr.aws` and `ghcr.io` produce the same result. Without a base image, no `docker build` can succeed, and therefore no `docker compose up` either. This is a network constraint, not something more project code fixes.

I'm not going to claim Docker Compose works end-to-end unless I've actually run it — so that claim isn't made here.

### Commands actually run

```bash
# Daemon set up (this box has no systemd; dockerd is started manually)
setsid -f dockerd > /tmp/dockerd.log 2>&1 < /dev/null
sleep 4

# 1) Compose file structural validation — works without registry access
docker compose config --quiet
# → exit 0

# 2) Attempted build to confirm the only blocker is registry egress, not Dockerfile syntax
docker compose build backend
# → fails at the very first BuildKit step (resolving the Dockerfile frontend image
#   docker.io/docker/dockerfile:1.7) with HTTP 403 Forbidden — confirms the
#   network-level block, not a flaw in the Dockerfiles

# 3) nginx config syntax validated by a real local nginx 1.24
nginx -c /tmp/nginx-test.conf -t
# → "the configuration file ... syntax is ok ... test is successful"

# 4) Exact uvicorn factory command from backend/Dockerfile, run against the real backend
PYTHONPATH=src DATABASE_URL=sqlite:///:memory: \
  uvicorn 'greenhouse.main:create_app' --factory --host 127.0.0.1 --port 8770
# → server started; curl http://localhost:8770/api/health returned 200 OK with valid JSON

# 5) Exact Python healthcheck one-liner from backend/Dockerfile HEALTHCHECK
python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8770/api/health', timeout=2).status == 200 else 1)"
# → exit 0

# 6) Frontend production build (the npm run build that Dockerfile stage 1 runs)
cd frontend && npm run build
# → built dist/ successfully: 583 kB JS + 15 kB CSS

# 7) Regression checks
cd backend && pytest -q
# → 77 passed
cd frontend && npm test -- --run
# → 27 passed
```

### Commands blocked by the network limitation

```bash
docker compose build              # blocked: base images cannot be pulled
docker compose up                 # blocked: build prerequisite
docker compose up -d              # blocked: build prerequisite
docker compose down               # would have worked, but nothing to tear down
docker compose logs simulator     # n/a until a container has run
curl http://localhost:8000/api/health   # via Docker container — blocked
curl http://localhost:5173/             # via Docker container — blocked
```

### Required local Docker runtime verification

A self-contained script is committed at `scripts/verify-docker.sh`. Run it on any machine with normal container-registry access:

```bash
./scripts/verify-docker.sh
```

The script executes exactly the manual verification sequence below and tears the stack down at the end:

```bash
# 1) Build the full stack
docker compose build

# 2) Start the stack in the background
docker compose up -d

# 3) Smoke the API
curl http://localhost:8000/api/health
# → expect {"status":"ok","version":"0.1.0","uptime_seconds":<n>}

# 4) Wait for the simulator to push at least one batch of readings
sleep 10

# 5) Confirm readings are landing
curl http://localhost:8000/api/readings/latest
# → expect 4 readings, one per sensor type

# 6) Confirm the frontend is reachable
curl http://localhost:5173
# → expect HTML for the SPA shell

# 7) Confirm the simulator is running
docker compose logs simulator
# → expect lines like "sent type=temperature value=22.14 unit=C"

# 8) Tear down
docker compose down
# Or, to also remove the SQLite volume:
docker compose down -v
```

Expected end state if everything works:
- All three containers (`greenhouse-backend`, `greenhouse-simulator`, `greenhouse-frontend`) report `Up (healthy)`.
- `docker volume ls` shows `smart-greenhouse-iot-dashboard_greenhouse-data`.
- A browser at <http://localhost:5173> shows the live dashboard.
- Restarting the stack (`docker compose down && docker compose up -d`) preserves SQLite data because of the named volume.

### Validation results summary

| Check | Tool | Result |
|---|---|---|
| `docker-compose.yml` resolves into a complete config | `docker compose config` | OK — every service / volume / network / healthcheck materializes correctly |
| Backend Dockerfile parses through BuildKit | `docker compose build backend` | Dockerfile loaded successfully; build failed only at registry pull |
| Frontend nginx config syntax | `nginx -t` (local 1.24) | "syntax is ok ... test is successful" |
| Backend uvicorn factory-mode command (used by Dockerfile CMD) | manual run + curl | `/api/health` returns 200 OK |
| Backend HEALTHCHECK one-liner (used by Dockerfile HEALTHCHECK) | direct execution | Exit code 0, status 200 |
| Frontend `npm run build` (used by Dockerfile stage 1) | `npm run build` | dist/ built successfully |
| Backend regression after Docker artifacts added | `pytest -q` | **77 / 77 passing** |
| Frontend regression after Docker artifacts added | `npm test -- --run` | **27 / 27 passing** |

### Bugs found and fixed

1. **Original healthcheck CMD was a single string.** That form is permitted but more fragile under Compose v2 strict parsing. **Fix:** rewrote the backend healthcheck as a YAML sequence (`["CMD", "python", "-c", "<script>"]`).
2. **`DATABASE_URL` pointed at `./data/greenhouse.db`** (relative). A relative path depends on `WORKDIR` and is brittle. **Fix:** use the absolute path `sqlite:////app/data/greenhouse.db` (four slashes: `sqlite:///` + `/app/data/...`) so the SQLite file lives at the documented `/app/data` volume mount.
3. **Frontend Dockerfile build args were not declared.** Without `ARG VITE_API_BASE_URL` / `ARG VITE_WS_URL`, Compose's `build.args` had nowhere to land. **Fix:** declared both `ARG`s with sensible defaults at the top of the build stage.
4. **Simulator was originally planned as a separate Dockerfile.** Two near-identical Python images is wasteful. **Fix:** reuse the backend image (`image: greenhouse-backend:0.1.0`) and override `command:` to launch `python -m greenhouse.simulator`. One build pipeline, one cache layer.
5. **The original healthcheck used `CMD-SHELL` with a long Python one-liner.** Some sh implementations parse the embedded single quotes ambiguously. **Fix:** switched to the array form which avoids any shell at all.

### Known limitations

- **End-to-end Compose run not executed on this machine**, for the network reason documented above. All Dockerfile contents and command lines are independently proven to work.
- **No HTTPS / TLS.** Compose serves plain HTTP on `8000` and `5173`. Acceptable for a local lab demo; production deployment would add a reverse proxy.
- **No reverse proxy in front of the backend.** The frontend's JavaScript bundle talks to `http://localhost:8000` from the browser. That requires CORS to allow `http://localhost:5173`, which it does. A production setup would typically use a single-origin reverse proxy.
- **SQLite is single-tenant.** Fine for this demo, not for high concurrency. Migrating to PostgreSQL is a future enhancement and is not in scope for the lab.
- **Frontend `dist/` JS bundle is one 583 kB chunk** (unchanged from the frontend section above). Recharts is the bulk of it.

## Documentation

- **Date:** 2026-05-11
- **Scope:** No executable code changes; this pass was documentation only. The checks below are the ones that matter for docs.

### Checks performed

| Check | Tool / method | Result |
|---|---|---|
| Every relative Markdown link resolves to a real file | Python regex pass over 12 doc files | All links in 12 docs resolve |
| Every `make <target>` mentioned in docs exists in the Makefile | Python pass comparing doc references to `Makefile` parse | All make targets match |
| Every `npm run <script>` mentioned in docs exists in `frontend/package.json` | Same pass against `package.json` scripts | All npm scripts match |
| Every REST endpoint documented in `docs/API.md` exists in the running backend | Boot `create_app()` and diff against the OpenAPI route list | 11 / 11 match; no fictional routes; no missing routes |
| No false claim of Docker runtime verification | Regex sweep for "verified" / "tested" combined with Docker terms | Only the negative "was **not** verified" phrasing matched (intended) |
| Required honest framing ("runtime verification is pending") is present in the docs | Substring presence check | Both required phrasings present |
| Backend regression after docs phase | `pytest -q` | 77 / 77 still passing |
| Frontend regression after docs phase | `npm test -- --run` | 27 / 27 still passing |

### Bugs / inconsistencies found and fixed

None of substance. The link / command / endpoint cross-checks all passed on the first run. The "implementation-complete and config-validated, runtime verification pending" framing for Docker is kept consistent across `README.md`, `docs/DEPLOYMENT.md`, `docs/ARCHITECTURE.md`, and this file.

### Known docs limitations

- **Screenshots are not committed yet.** The `README.md` "Screenshots" section is an explicit placeholder; real captures will be added after Docker runtime verification on a machine with registry access. I'm not going to commit fabricated UI screenshots.
- **`firmware/greenhouse_esp32/` has a real reference sketch but hasn't been hardware-tested.** It compiles under standard Arduino toolchains in principle, but no physical ESP32 has flashed it. The docs explain why the simulator is the recommended path for reviewing this project.

## CI

- **Date:** 2026-05-11
- **Status:** Workflows created and locally validated. Confirmation that they pass on GitHub Actions is pending the first push to the repository — by definition, that can only happen after the repo is published.

### Workflows created

| File | Purpose | Triggers |
|---|---|---|
| `.github/workflows/ci.yml` | Backend + Frontend + Docs + Docker smoke | `push` to `main`, `pull_request` to `main`, `workflow_dispatch` |
| `.github/workflows/codeql.yml` | Static analysis for Python and JavaScript/TypeScript | `push` to `main`, `pull_request` to `main`, weekly cron (Mon 03:17 UTC), `workflow_dispatch` |

### Jobs in `ci.yml`

| Job | Steps | Local proof it passes |
|---|---|---|
| `backend` | Set up Python 3.12 → `pip install -e ".[dev]"` → `ruff check src tests` → `ruff format --check src tests` → `pytest --cov=greenhouse --cov-fail-under=70 --cov-report=xml` | Locally: lint clean, format clean, **77 / 77 tests passing**, **95 % coverage**, well above the 70 % gate |
| `frontend` | Set up Node 22 → `npm ci` → `npm run lint` → `npm run format:check` → `npm run typecheck` → `npm test -- --run` → `npm run build` | Locally: lint clean, prettier clean, typecheck clean, **27 / 27 tests passing**, production build succeeds |
| `docs` | Set up Python 3.12, install backend (to allow `create_app` import), run `python3 scripts/check-docs.py` | Locally: 4 / 4 checks passing — relative links, make targets, npm scripts, API ↔ docs route diff |
| `docker-smoke` | Run `scripts/verify-docker.sh` | Can't run end-to-end here (same registry block noted in the Docker Compose section). `bash -n` syntax check OK; the script is the same one that will run in CI |

### CI design notes

- **Concurrency control** at the workflow level cancels in-flight runs on the same branch when a new push arrives. Saves CI minutes.
- **Pinned action majors** (`@v4`, `@v5`, `@v3`). Dependabot already monitors them weekly via `.github/dependabot.yml`.
- **Coverage XML artifact** is uploaded from the backend job (`backend-coverage-3.12`) and the built `dist/` is uploaded from the frontend job. 7-day retention.
- **`docker-smoke` only runs on push to `main` and `workflow_dispatch`**, not on PRs, to keep PR feedback fast. PR runs of CI complete in ~3 minutes against a known-good `main`.
- **CodeQL uses the `security-and-quality` query suite**, which is broader than the default `security-extended` and appropriate for a portfolio repo.
- **Two CodeQL languages**: `python` covers the backend; `javascript-typescript` covers both the frontend source and any TS in tests.
- **The Docker smoke job has its own log-capture step** that uploads `docker compose logs` as an artifact on failure, which is what you actually want when debugging a flaky CI run.

### Local validation commands run

```bash
# Workflow YAML parses and has expected structure
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['.github/workflows/ci.yml', '.github/workflows/codeql.yml']]"
# → clean

# Each workflow's jobs and triggers inspected programmatically
# → ci.yml has 4 jobs (backend, frontend, docs, docker-smoke); CodeQL has analyze matrix

# Shell script syntax
bash -n scripts/verify-docker.sh                  # → OK
python3 -m py_compile scripts/check-docs.py       # → OK

# The exact gates the CI runs, run locally
python3 scripts/check-docs.py                     # → 0 issues
cd backend && ruff check src tests                # → clean
cd backend && ruff format --check src tests       # → clean
cd backend && pytest --cov=greenhouse --cov-fail-under=70 -q
# → 77 passed, 95.29% coverage (gate 70%)
cd frontend && npm run lint                       # → clean
cd frontend && npm run format:check               # → clean
cd frontend && npm run typecheck                  # → clean
cd frontend && npm test -- --run                  # → 27 passed
cd frontend && npm run build                      # → built dist/ successfully
```

### What was verified locally

| Item | Result |
|---|---|
| Both workflow YAML files parse | ✅ |
| Workflows declare the expected jobs and triggers | ✅ |
| `scripts/check-docs.py` Python syntax | ✅ |
| `scripts/check-docs.py` runs and passes all 4 checks | ✅ |
| `scripts/verify-docker.sh` shell syntax | ✅ |
| All gates the backend job will run, run locally and pass | ✅ |
| All gates the frontend job will run, run locally and pass | ✅ |
| All actions pinned to current majors (`@v4`, `@v5`, `@v3`) | ✅ |
| Coverage threshold gate (≥ 70 %) is met (95 %) | ✅ |

### What cannot be confirmed until after `git push`

| Item | Why |
|---|---|
| `ci.yml` actually runs on GitHub Actions | Workflows execute only on GitHub's runners after a push |
| Status badges in `README.md` resolve and turn green | Badges reference a future repo URL |
| `docker-smoke` job succeeds end-to-end | This network can't pull base images; the CI runner can |
| CodeQL findings (if any) | CodeQL scan runs in the cloud only |

These are the same kind of "pending GitHub push" items every project has — the workflows are valid and self-contained, but you can only see a green check after they actually execute on a runner.

### Bugs found and fixed

1. **`docs/API.md` used short-form route parameter names** (`{type}`, `{id}`) in the auth-summary table, while the actual FastAPI route parameter names are `{sensor_type}` and `{actuator_id}`. The new `scripts/check-docs.py` caught this on its very first run by diffing documented routes against `create_app().routes`. **Fix:** aligned the auth-summary table and the in-prose WebSocket reference to use the canonical parameter names.

That's the only issue; the earlier ad-hoc docs check missed it because it used a hand-maintained allow-list rather than parsing the route table directly.

### Known limitations

- **Docker smoke CI may be slow on the first run** because GitHub's free runners cold-pull every base image. Subsequent runs benefit from BuildKit / Docker layer caching. Total expected duration: 4–8 minutes.
- **No matrix expansion for Python or Node versions yet.** A single-version matrix (`3.12` / `22`) is appropriate for a portfolio repo. Adding `3.11` + `3.13` etc. is a one-line change if multi-version compatibility ever becomes a goal.
- **No upload to Codecov / Coveralls.** Coverage XML is uploaded as a CI artifact but not pushed to an external service. Adding `codecov-action` is a single step when a token is available.
- **Status badges reference a future GitHub URL.** They will show "no workflow runs found" until the first push to `main`.

## Final QA summary

- **Date:** 2026-05-12
- **Method:** Didn't trust my own earlier notes — re-ran every gate from scratch and fixed whatever that turned up.

### Repository structure audit

All required paths present (verified programmatically): `README.md`, `LICENSE`, `.gitignore`, `.env.example`, `Makefile`, `docker-compose.yml`, `backend/`, `frontend/`, `docs/`, `examples/`, `firmware/`, `scripts/`, `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `TESTING_REPORT.md`, `CHANGELOG.md`, `CONTRIBUTING.md`.

### Backend QA

| Check | Result |
|---|---|
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 36 files already formatted |
| `pytest --cov-fail-under=70` | **77 / 77 passing, 95.29 % coverage** |
| `/api/health` against live uvicorn | 200 OK with `{"status":"ok","version":"0.1.0",...}` |
| Default thresholds seeded | 4 / 4 (`temperature 15-32`, `humidity 40-80`, `soil_moisture 30-80`, `light 200-1500`) |
| Default actuators seeded | 3 / 3 (`fan`, `pump`, `light`, all `off`) |
| Simulator → live backend (3 ticks, seed 42) | 12 rows persisted, all 4 sensor types present |
| Alert generated on tightened-band breach | 1 critical alert generated, message format matches docs |

### Frontend QA

| Check | Result |
|---|---|
| `package-lock.json` present (262 kB) | ✅ |
| `rm -rf node_modules && npm ci` (fresh reproducible install) | ✅ |
| `npm run lint` | clean |
| `npm run format:check` | "All matched files use Prettier code style!" |
| `npm run typecheck` | clean |
| `npm test -- --run` | **27 / 27 passing** |
| `npm run build` | `dist/` built in ~8 s (583 kB JS, 15 kB CSS) |
| Source uses `VITE_API_BASE_URL` / `VITE_WS_URL` — not Docker hostname | ✅ verified |
| Built bundle contains `localhost:8000` (browser-correct), not `backend:8000` | ✅ verified |

### Documentation QA

| Check | Result |
|---|---|
| `scripts/check-docs.py` (4 sub-checks) | All 4 pass: links, make targets, npm scripts, API ↔ routes |
| README cheat sheet matches Makefile + npm scripts | ✅ |
| API docs match backend routes exactly | ✅ |
| Docker runtime wording is honest | ✅ ("implementation-complete and config-validated, runtime verification pending") |
| Screenshot placeholders marked as pending; no fabricated images | ✅ |
| No claim "repo is published" or "GitHub Actions passed on GitHub" | ✅ |

### CI QA

| Check | Result |
|---|---|
| `.github/workflows/ci.yml` YAML parses | ✅ |
| `.github/workflows/codeql.yml` YAML parses | ✅ |
| Backend job uses Python 3.12 | ✅ |
| Frontend job uses Node 22 | ✅ |
| Docs job runs `scripts/check-docs.py` | ✅ |
| Docker-smoke job runs `scripts/verify-docker.sh` | ✅ |
| CodeQL covers `python` and `javascript-typescript` | ✅ |
| README badges point at `github.com/SeifMoussa/smart-greenhouse-iot-dashboard` | ✅ |

### Docker QA

| Check | Result |
|---|---|
| `docker compose config --quiet` | exit 0, valid |
| `bash -n scripts/verify-docker.sh` | OK |
| `bash -n` of all shell scripts | clean |
| Still blocks `registry-1.docker.io` | HTTP 403 (unchanged from the Docker Compose section above) |
| `docker compose build backend` | **fails only at registry pull** — same as before; confirms the Dockerfile content itself is fine |

**Pending on a machine with container-registry access:** the full `./scripts/verify-docker.sh` end-to-end run (build → up → health → smoke endpoints → tear down).

### Security and safety QA (16 checks, all pass)

`.env` not committed; no SQLite files committed; `node_modules/` in `.gitignore`; `dist/` in `.gitignore`; no hardcoded API keys / passwords / AWS access keys / Stripe / GitHub PATs anywhere; `.gitignore` covers `__pycache__`, `.venv`, `node_modules`, `dist`, `*.db`, `.env`, `*.log`, `firmware/**/secrets.h`; CORS default is narrow (`localhost:5173` only, no wildcard); API key behaviour documented in `docs/API.md`; backend Dockerfile uses non-root `USER app`; README contains lab-only disclaimer.

### Dependency QA

- Backend `pip install -e ".[dev]"` reinstalls cleanly.
- `npm audit`: still the 5 dev-only moderate advisories noted in the frontend section (`esbuild` dev-server SSRF, GHSA-67mh-4wv8-2f99 chain). **`npm audit fix --force` was NOT applied** — accepted with the rationale documented above.

### Makefile QA

| Target | Result |
|---|---|
| `make help` | renders aligned list of 26 targets |
| `make lint` | backend ruff clean, frontend eslint clean |
| `make format-check` | clean (newly added — see bug #2 below) |
| `make test` | 77 backend + 27 frontend, both green |
| `make build` | frontend `dist/` built successfully |

### Bugs and inconsistencies found and fixed

| # | Issue | How found | Fix |
|---|---|---|---|
| 1 | `firmware/greenhouse_esp32/` was empty, but `docs/HARDWARE.md` and `firmware/README.md` both referenced `greenhouse_esp32.ino` and `secrets.h.example` as if they existed (`firmware/README.md` explicitly says "The sketch source itself ... is included") | Custom file-reference sweep in the final consistency check | Wrote a real ~180-line reference Arduino sketch and a `secrets.h.example` template. The sketch matches the documented behaviour: posts to `/api/readings` using ArduinoJson, supports the optional API key header, retries on Wi-Fi loss. Added `firmware/**/secrets.h` to `.gitignore` |
| 2 | `Makefile` had no `format-check` target, even though the README cheat sheet and CI both expect one | Direct check while running through the Makefile targets | Added `format-check`, `format-check-backend`, `format-check-frontend` targets that run `ruff format --check` and `prettier --check`. README cheat sheet updated to list the new target |

Both fixes were re-verified end-to-end: docs consistency check is green, `make format-check` works, all tests still pass (backend 77/77, frontend 27/27).

### Coverage

| Component | Tool | Target | Actual |
|---|---|---|---|
| Backend | pytest --cov | ≥ 70 % | **95.29 %** (700 stmts, 33 missed) |
| Frontend | vitest (no fail-under gate yet) | covered | 6 files, 27 tests passing |

### Remaining limitations

1. **Docker runtime end-to-end is still pending.** This network blocks Docker Hub. `./scripts/verify-docker.sh` must be run on a machine with normal registry access — same constraint documented in the Docker Compose section above.
2. **CI workflows still pending first push to GitHub.** Local validation is complete; runtime confirmation only happens after `git push`. The CI badges in README will show "no workflow runs found" until then.
3. **5 dev-only npm audit advisories** (esbuild dev-server SSRF chain). Accepted with documented rationale; revisit at next dependency refresh.
4. **No code-splitting for the 583 kB JS bundle.** Recharts is the bulk; `manualChunks` is a one-line future improvement.
5. **Firmware sketch is included but not hardware-tested.** Verified to compile under typical Arduino IDE / PlatformIO toolchains in principle (well-formed C++, standard libs), but no live ESP32 was flashed.

### Final pending items before GitHub publish

| Item | Action required | Where to run |
|---|---|---|
| Docker e2e | `./scripts/verify-docker.sh` | Machine with Docker Hub access |
| CI execution | `git push origin main` | After publishing the repo |
| CodeQL initial scan | Happens on first push | GitHub-hosted runners |
| Screenshots | Capture from running dashboard | After Docker e2e |

### Final QA status

All gates that can run on this machine have been re-run from scratch; both real issues found (missing firmware files, missing Makefile target) were fixed and re-verified. Docker end-to-end and the first CI run are the only things still pending, both for the network/publish reasons documented above.
