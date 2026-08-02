# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI (`ci.yml`) with backend, frontend, docs, and Docker-smoke jobs, plus a weekly CodeQL scan
- `scripts/check-docs.py`, a consistency check that diffs documented routes, `make` targets, and `npm run` scripts against the real repo so the docs can't silently drift
- Real ESP32 reference firmware (`firmware/greenhouse_esp32/greenhouse_esp32.ino`) and `secrets.h.example`
- `make format-check` and per-stack variants so the CI formatting gate can be reproduced locally
- Docker Compose stack (`backend`, `simulator`, `frontend`), multi-stage Dockerfiles, nginx config for the frontend, and `scripts/verify-docker.sh` for an end-to-end smoke test
- Full documentation set: `README.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/HARDWARE.md`, `docs/DEPLOYMENT.md`, `docs/DATA_MODEL.md`
- React + Vite + TypeScript frontend: live readings, history chart, alerts panel, thresholds form, actuator toggles, CSV export panel, WebSocket hook with exponential-backoff reconnect, light/dark theme
- FastAPI backend: CORS, optional API-key middleware, ingest rate limiting, SQLite persistence via SQLAlchemy, threshold evaluation with alerting, WebSocket broadcast of live events
- Sensor simulator (`python -m greenhouse.simulator`) for running the whole stack with zero hardware
- Initial repository scaffold: license, gitignore, env template, Makefile, Docker Compose scaffold, contributing guide

### Known limitations
- Docker Compose hasn't been run end-to-end on a machine with normal container-registry access yet — see `TESTING_REPORT.md` for what has and hasn't been verified locally.
- Frontend bundle is a single ~583 kB JS chunk (Recharts pulls in a chunk of D3); splitting it out with `manualChunks` is a reasonable follow-up.
- 5 dev-only `npm audit` advisories (esbuild dev-server SSRF, GHSA-67mh-4wv8-2f99) are accepted with documented rationale in `TESTING_REPORT.md`.

## [0.1.0] — TBD

First public release.
