# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 9 — Release preparation:
  - `RELEASE.md` — single source of truth for the manual publish path, containing repository metadata, final pre-publish checklist, `git` and `gh` publish commands, first commit message, v0.1.0 release plan with release notes, 16-item post-push verification checklist, Docker verification recipe, screenshots plan, LinkedIn post + Projects-section entry, 5 CV bullet points, and recruiter summary paragraph
  - Repository description and ~20 topic tags drafted
  - Pre-publish materials updated in `TESTING_REPORT.md`, `PROJECT_COMPLETION_CHECKLIST.md`, `CHANGELOG.md`
  - Honest framing maintained throughout: implementation items ticked, runtime items (CI execution, Docker e2e, screenshots) explicitly marked as pending the user's manual publish action

### Pending the user's manual publish action
- Apply repository description and topics on GitHub settings
- `git push origin main` to publish; CI and CodeQL workflows execute then
- Run `./scripts/verify-docker.sh` on a Docker-capable machine
- Capture real dashboard screenshots and update README
- Push `v0.1.0` tag and create the GitHub Release

- Phase 8 — Final QA:
  - Re-ran every gate from scratch (16 security checks, 4 docs consistency checks, 8 backend behaviour verifications, 8 frontend gates, 12 CI validations, Makefile targets) — all green
  - Added the real ESP32 reference firmware: `firmware/greenhouse_esp32/greenhouse_esp32.ino` (180 lines, posts to `/api/readings` with ArduinoJson, supports API key, retries on Wi-Fi loss) and `firmware/greenhouse_esp32/secrets.h.example`. Resolves the inconsistency where the docs referenced these files as committed
  - Added `make format-check`, `make format-check-backend`, `make format-check-frontend` Makefile targets so the CI-parity command exists locally; README cheat sheet updated
  - Added `firmware/**/secrets.h` to `.gitignore` so the optional credentials file cannot accidentally be committed
  - `TESTING_REPORT.md` Phase 8 section: full QA matrix with real commands and results, both bugs found and fixed, remaining limitations, final pending items
  - Final state: backend 77/77 tests, 95.29 % coverage; frontend 27/27 tests, production build green; both runtime items honestly marked pending (Docker e2e and GitHub Actions execution)

- Phase 7 — GitHub Actions CI:
  - `.github/workflows/ci.yml` with four jobs: `backend` (ruff + pytest with 70 % coverage gate), `frontend` (eslint + prettier + tsc + vitest + vite build), `docs` (runs `scripts/check-docs.py`), and `docker-smoke` (runs `scripts/verify-docker.sh` on push to `main` and on `workflow_dispatch`)
  - `.github/workflows/codeql.yml` with a matrix over `python` and `javascript-typescript`, triggered on push, PR, weekly schedule (Monday 03:17 UTC), and `workflow_dispatch`
  - `scripts/check-docs.py` — reusable consistency check for relative Markdown links, `make` targets, `npm run` scripts, and the API.md ↔ backend route diff
  - Concurrency control: cancel-in-progress on the same branch
  - All actions pinned to current major versions (`@v4`, `@v5`, `@v3`)
  - Coverage XML uploaded as a CI artifact; built `dist/` uploaded for the frontend job; `docker compose logs` uploaded on Docker smoke failure
  - README badges added for CI and CodeQL alongside the existing license / version / test badges
  - One doc fix caught by the new `check-docs.py`: aligned `docs/API.md` route parameter names (`{type}` → `{sensor_type}`, `{id}` → `{actuator_id}`) with the actual FastAPI routes

### Pending (only confirmable after `git push`)
- The CI badges resolve and turn green once `ci.yml` runs on a GitHub-hosted runner.
- The Docker smoke job is gated on GitHub Hub registry access, which the CI runners have but the local dev sandbox does not.

- Phase 6 — Documentation:
  - Final `README.md` with project value statement, full feature list, tech stack, architecture diagram, local + Docker quick-starts, command cheat sheet, project structure, documentation index, known limitations, and an explicit "Why this project (for recruiters)" section
  - `docs/ARCHITECTURE.md` — component overview, REST flow, WebSocket flow, database flow, Docker architecture, design decisions and tradeoffs
  - `docs/API.md` — every endpoint documented with method, path, auth, validation, response shape, curl example, and status codes; WebSocket event reference; API-key behaviour matrix
  - `docs/HARDWARE.md` — optional ESP32 path: parts list, pin mapping, Wi-Fi config notes, safety notes, simulator-first recommendation
  - `docs/DEPLOYMENT.md` — local dev setup, Docker setup, env var reference, SQLite persistence guide, troubleshooting; explicit Docker runtime-verification status
  - `docs/DATA_MODEL.md` — schema for all four tables, conventions, indexes, severity rule, timestamp handling, future-improvements section
  - `firmware/README.md` — firmware purpose, required libs, configuration placeholders, why-simulator-first
  - `examples/README.md` — top-of-file pointers back to README / DEPLOYMENT / API
  - Screenshots intentionally not committed; placeholder section explains real captures will be added after Docker runtime verification
  - All command examples cross-checked against the actual Makefile targets, npm scripts, and backend module names

- Phase 5 — Docker Compose support **(implementation-complete and config-validated, runtime verification pending)**:
  - `backend/Dockerfile`: multi-stage build with venv stage and a slim runtime; non-root `app` user; pure-stdlib healthcheck; absolute SQLite path (`/app/data/greenhouse.db`) under a Docker volume; uvicorn factory mode
  - `frontend/Dockerfile`: multi-stage Node 22 → nginx alpine; build args `VITE_API_BASE_URL` and `VITE_WS_URL` (defaulting to `localhost` because the browser runs on the host); `/healthz` for Docker healthcheck
  - `frontend/nginx.conf`: SPA fallback to `index.html`, immutable cache headers on hashed assets, `no-store` on index, gzip, basic security headers
  - `backend/.dockerignore`, `frontend/.dockerignore` to keep build contexts small
  - `docker-compose.yml`: three services (`backend`, `simulator`, `frontend`), shared `greenhouse-backend:0.1.0` image for backend and simulator, dependency on `service_healthy`, persistent named volume, internal bridge network, healthchecks on backend and frontend
  - `scripts/verify-docker.sh`: self-contained end-to-end verification script
  - `examples/README.md` updated with Docker recipes pointing to `scripts/verify-docker.sh`

### Pending (environmental limitation)
- End-to-end `docker compose build` / `docker compose up` was **not** verified in the sandbox that produced this phase because the sandbox network blocks container-registry egress (Docker Hub, GHCR, public.ecr.aws all return HTTP 403). All Docker artifacts are syntactically valid (`docker compose config` and `nginx -t` both pass) and the contained commands have been independently verified outside Docker. Full runtime verification is pending on a machine with normal container-registry access; the verification commands are committed at `scripts/verify-docker.sh` and documented step by step in `TESTING_REPORT.md`.

- Phase 4 — Frontend (React + Vite + TypeScript):
  - Strict-mode TypeScript with React 18, Vite 5, Tailwind CSS 3, TanStack Query 5, Recharts 2
  - Typed REST API client and resource modules mirroring backend Pydantic schemas exactly
  - WebSocket hook (`useWebSocket`) with exponential-backoff reconnect (1 s → 30 s cap), reset on success, no reconnect after unmount, dependency-injectable socket factory
  - Greenhouse-specific WS hook (`useGreenhouseSocket`) that merges live events into the React Query cache
  - Light/dark theme hook (`useTheme`) with `localStorage` persistence and OS-preference fallback
  - Dashboard panels: `LiveReadings`, `HistoryChart` (1 h / 24 h / 7 d), `AlertsPanel`, `ThresholdsForm` (client-side validation), `Actuators` (optimistic toggles), `ExportPanel` (CSV download URL builder), `ConnectionBadge`, `ThemeToggle`
  - Responsive layout, keyboard-accessible controls, ARIA labels and live regions where relevant
  - 27 frontend tests passing across 6 files (API client, theme persistence, WS reconnect, LiveReadings rendering, ThresholdsForm validation/submission, ExportPanel URL building)
  - All gates green: lint, format:check, typecheck (strict), tests, build
  - `package-lock.json` committed for reproducible installs
  - 5 dev-only `npm audit` advisories (esbuild dev server, GHSA-67mh-4wv8-2f99) documented and accepted; revisit at next dependency refresh

- Phase 3 — Sensor simulator:
  - `python -m greenhouse.simulator` CLI entry point with signal-handled clean shutdown
  - Bounded random-walk generators for `temperature`, `humidity`, `soil_moisture`, `light`
  - Configurable via env: backend URL, interval, sensor ID, API key, max iterations, max duration, request timeout, exponential backoff bounds, seed
  - Graceful failure handling: connection errors / 4xx / 5xx are logged and the next tick is attempted with exponential backoff (resets on success)
  - Dependency-injectable HTTP client and sleep function for deterministic tests
  - 19 simulator tests including two end-to-end tests driving the real FastAPI app via `httpx.MockTransport` and `TestClient`
  - 97 % simulator-module coverage, total project coverage unchanged at 95 %
  - `examples/README.md` with five runnable command recipes

- Phase 2 — Backend (FastAPI):
  - App factory in `greenhouse.main` with CORS, optional API-key middleware, and ingest rate limiting
  - SQLite persistence with SQLAlchemy 2 ORM models (`readings`, `thresholds`, `alerts`, `actuator_state`)
  - Pydantic v2 request/response schemas with strict literal enums and timestamp normalization
  - Endpoints: `GET /api/health`, `POST/GET /api/readings`, `GET /api/readings/latest`, `GET/PUT /api/thresholds`, `GET /api/alerts`, `GET/POST /api/actuators`, `GET /api/export.csv`
  - `WebSocket /ws` broadcasting `reading`, `alert`, and `actuator` events via in-process event bus
  - Threshold evaluation with warning/critical severity tiers and automatic alert persistence
  - Default thresholds and actuators seeded on first start
  - Structured JSON logging (or text mode) via env var
  - Token-bucket rate limiter
  - 58 backend tests passing, 95 % coverage

- Phase 1 — Repository scaffold:
  - Folder structure for `backend/`, `frontend/`, `firmware/`, `docs/`, `examples/`, `scripts/`, `.github/`
  - MIT `LICENSE`
  - Root `.gitignore` covering Python, Node, OS, IDE, SQLite, and Arduino artifacts
  - `.env.example` documenting every configurable environment variable
  - `Makefile` with install / dev / test / lint / format / build / Compose / clean targets
  - `docker-compose.yml` scaffold for backend, simulator, and frontend services
  - Root `README.md` draft describing the project, stack, and target quick-start
  - `CONTRIBUTING.md`, `CHANGELOG.md`, `PROJECT_COMPLETION_CHECKLIST.md`, `TESTING_REPORT.md`
  - GitHub issue and PR templates, Dependabot config

## [0.1.0] — TBD

First public release. Will be tagged after Phases 2–9 complete.
