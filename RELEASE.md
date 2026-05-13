# Release Preparation (v0.1.0)

> This file contains everything needed to publish the project to GitHub manually.
> Nothing in this repo has been pushed yet. After completing the steps below, this file can be deleted or kept as a release-process record.

---

## 1. Repository metadata

| Field | Value |
|---|---|
| Repository name | `smart-greenhouse-iot-dashboard` |
| Owner | `SeifMoussa` |
| URL | `https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard` |
| Description (≤ 350 chars) | *Full-stack IoT monitoring and control system: FastAPI + WebSocket backend, React + TypeScript dashboard, hardware-free sensor simulator, optional ESP32 firmware, Docker Compose stack, CI + CodeQL workflows. Built end-to-end with tests, docs, and honest engineering practice.* |
| Visibility | **Public** (portfolio project) |
| License | **MIT** (already in `LICENSE`) |
| Default branch | `main` |
| Initialise README in GitHub UI? | **No** — push the existing one |
| Initialise LICENSE in GitHub UI? | **No** — push the existing one |
| Initialise `.gitignore` in GitHub UI? | **No** — push the existing one |

### Topics / tags (paste into GitHub UI or apply via `gh`)

```
iot
fastapi
react
typescript
tailwindcss
sqlalchemy
websocket
docker
docker-compose
sensor-simulator
esp32
python
recharts
tanstack-query
pydantic
pytest
vitest
github-actions
codeql
portfolio
```

---

## 2. Final pre-publish checklist

Run through this checklist once more before `git push`.

### Code complete
- [x] Backend implemented (FastAPI + SQLAlchemy 2 + Pydantic v2, 21 source files, ~1 090 lines)
- [x] Frontend implemented (React 18 + Vite + TS strict, 26 source files, ~1 947 lines)
- [x] Sensor simulator implemented (`backend/src/greenhouse/simulator.py`)
- [x] Optional ESP32 firmware sketch committed (`firmware/greenhouse_esp32/`)
- [x] Three-service Docker Compose stack defined
- [x] Three executable scripts (`verify-docker.sh`, `check-docs.py`)

### Tests passing locally
- [x] Backend: **77 / 77** pytest tests, **95.29 % coverage** (gate 70 %)
- [x] Frontend: **27 / 27** Vitest tests across 6 files
- [x] `make test` runs both green
- [x] Backend ruff lint clean, ruff format clean
- [x] Frontend ESLint clean, Prettier clean, TypeScript strict clean
- [x] Frontend `npm run build` produces `dist/`

### Documentation complete
- [x] `README.md` final with badges, screenshots placeholder, quick-starts, command cheat sheet, doc index, lab-only disclaimer
- [x] `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/HARDWARE.md`, `docs/DEPLOYMENT.md`, `docs/DATA_MODEL.md` all written
- [x] `firmware/README.md` and `examples/README.md`
- [x] `TESTING_REPORT.md` contains real results for Phases 1–8
- [x] `PROJECT_COMPLETION_CHECKLIST.md` accurately reflects status
- [x] `CHANGELOG.md` covers Phases 1–9
- [x] `CONTRIBUTING.md`
- [x] `scripts/check-docs.py` enforces docs-vs-code consistency (4 sub-checks all green)

### CI and workflows
- [x] `.github/workflows/ci.yml` (backend / frontend / docs / docker-smoke)
- [x] `.github/workflows/codeql.yml` (Python + JavaScript/TypeScript)
- [x] `.github/dependabot.yml` (pip / npm / actions / docker)
- [x] Issue templates and PR template under `.github/`
- [x] All `uses:` actions pinned to current majors
- [x] Local validation of every gate the CI workflows will run

### Docker
- [x] `backend/Dockerfile` (multi-stage, non-root, healthcheck)
- [x] `frontend/Dockerfile` (multi-stage Node → nginx alpine)
- [x] `frontend/nginx.conf` (SPA fallback, cache headers, `/healthz`)
- [x] `docker-compose.yml` (three services, named volume, internal network, healthchecks)
- [x] `scripts/verify-docker.sh` smoke script
- [x] `docker compose config --quiet` validates
- [x] Backend `HEALTHCHECK` script tested outside Docker
- [ ] **Pending**: end-to-end `./scripts/verify-docker.sh` on a machine with container-registry access

### Security and hygiene
- [x] No `.env` committed
- [x] No SQLite database committed
- [x] No `node_modules/` committed
- [x] No `dist/` committed
- [x] `firmware/**/secrets.h` gitignored
- [x] No hardcoded API keys, passwords, AWS keys, Stripe keys, GitHub PATs anywhere
- [x] CORS default is narrow (`localhost:5173` only — no wildcard)
- [x] Backend Docker container runs as non-root `USER app`
- [x] Lab-only disclaimer present in README
- [x] No fabricated screenshots committed

### Honesty
- [x] README screenshots section explicitly marked "pending real captures"
- [x] Docker runtime wording consistent across all docs ("implementation-complete and config-validated; runtime verification pending")
- [x] CI badges point at the future repo URL and will read "no workflow runs found" until the first push (documented)

### Pending the first push to GitHub
- [ ] CI workflow runs green on a real GitHub runner
- [ ] CodeQL initial scan completes
- [ ] README badges resolve to green / yellow
- [ ] Topics applied to the repo settings
- [ ] `v0.1.0` tag created and GitHub Release published
- [ ] Real dashboard screenshots captured and added to README

---

## 3. Git commands (manual publish path)

```bash
cd smart-greenhouse-iot-dashboard

# Confirm we are at the project root.
ls -la README.md LICENSE Makefile docker-compose.yml

# Sanity sweep before committing.
make lint
make format-check
make typecheck
make test
python3 scripts/check-docs.py

# Initialise the local git repo (if not already initialised).
git init

# Confirm the gitignore is doing its job — no node_modules, dist, .env, *.db, etc.
git status

# Stage everything that is not gitignored.
git add .

# Verify the staging list looks right.
git diff --cached --stat | tail -20

# First commit (full message in section 5 below).
git commit -F .git-first-commit-message.txt
# OR inline:
git commit -m "Initial commit: Smart Greenhouse IoT Dashboard v0.1.0"

# Rename default branch to main.
git branch -M main

# Add the GitHub remote.
git remote add origin https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard.git

# Push. The first push must use --set-upstream so subsequent pushes are simple.
git push --set-upstream origin main
```

> Tip: if you usually pull / push using SSH, replace the remote URL with
> `git@github.com:SeifMoussa/smart-greenhouse-iot-dashboard.git`.

---

## 4. GitHub CLI commands (optional one-liner publish)

If you have the `gh` CLI installed and authenticated, the create + push + topics + description can be a single shell session:

```bash
cd smart-greenhouse-iot-dashboard

# Create the repo on GitHub (public, owned by SeifMoussa), set the description.
gh repo create SeifMoussa/smart-greenhouse-iot-dashboard \
  --public \
  --description "Full-stack IoT monitoring and control system: FastAPI + WebSocket backend, React + TypeScript dashboard, hardware-free sensor simulator, optional ESP32 firmware, Docker Compose stack, CI + CodeQL workflows." \
  --homepage "https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard" \
  --source . \
  --remote origin \
  --push

# Apply all the topics in one go.
gh repo edit SeifMoussa/smart-greenhouse-iot-dashboard \
  --add-topic iot \
  --add-topic fastapi \
  --add-topic react \
  --add-topic typescript \
  --add-topic tailwindcss \
  --add-topic sqlalchemy \
  --add-topic websocket \
  --add-topic docker \
  --add-topic docker-compose \
  --add-topic sensor-simulator \
  --add-topic esp32 \
  --add-topic python \
  --add-topic recharts \
  --add-topic tanstack-query \
  --add-topic pydantic \
  --add-topic pytest \
  --add-topic vitest \
  --add-topic github-actions \
  --add-topic codeql \
  --add-topic portfolio

# Issues and discussions are on by default; confirm.
gh repo view SeifMoussa/smart-greenhouse-iot-dashboard --json hasIssuesEnabled
```

---

## 5. First commit message

```
Initial commit: Smart Greenhouse IoT Dashboard v0.1.0

Full-stack IoT monitoring and control system built end-to-end with
phase-gated quality checks and an honest engineering trail.

Backend (FastAPI + SQLAlchemy 2 + Pydantic v2 + SQLite):
- REST + WebSocket API with health, readings, thresholds, alerts,
  actuators, CSV export, /ws live event broadcast
- Threshold evaluation with warning / critical severity tiers
- In-process async event bus, token-bucket rate limiter, optional
  X-API-Key gating on writes, CORS hardened to known origins
- 77 pytest tests, 95.29 % coverage

Frontend (React 18 + Vite + TypeScript strict + Tailwind):
- Live readings, history chart (Recharts, 1h/24h/7d), alerts panel,
  thresholds form with client-side validation, actuator toggles with
  optimistic UI, CSV export panel
- WebSocket hook with exponential-backoff auto-reconnect
- Light/dark theme persisted to localStorage
- 27 Vitest tests across 6 files

Sensor simulator (hardware-free demo):
- Bounded random-walk generator for all four sensor types
- Configurable via env (interval, seed, max iterations)
- 19 simulator tests including 2 end-to-end against the real backend

Optional ESP32 firmware: reference Arduino sketch with DHT22 + soil
moisture + LDR, posting to the same /api/readings endpoint.

DevSecOps:
- Three-service Docker Compose stack with healthchecks and a named
  SQLite volume
- GitHub Actions CI: backend lint/test/coverage, frontend lint/format
  /typecheck/test/build, docs consistency check, Docker Compose smoke
- CodeQL security scanning for Python and JavaScript/TypeScript
- Dependabot for pip, npm, actions, docker
- Multi-stage non-root containers

Documentation:
- README with architecture diagram, quick-starts, doc index, lab-only
  disclaimer, recruiter-focused value statement
- docs/ARCHITECTURE.md, API.md, HARDWARE.md, DEPLOYMENT.md, DATA_MODEL.md
- TESTING_REPORT.md with per-phase real results
- PROJECT_COMPLETION_CHECKLIST.md per-phase tracking
- scripts/check-docs.py enforces docs <-> code consistency

Pending after this push:
- CI workflow execution on a real GitHub runner
- Docker Compose end-to-end runtime verification on a machine with
  container-registry access (./scripts/verify-docker.sh)
- Real dashboard screenshots for the README
```

For convenience, the message is also available as a here-doc you can pipe to `git commit -F -`:

```bash
git commit -F - <<'EOF'
Initial commit: Smart Greenhouse IoT Dashboard v0.1.0

(... same body as above ...)
EOF
```

---

## 6. Release plan (v0.1.0)

### Tag command

```bash
git tag -a v0.1.0 -m "v0.1.0 — initial public release"
git push origin v0.1.0
```

### Release title

```
v0.1.0 — Smart Greenhouse IoT Dashboard
```

### Release notes (paste into the GitHub Releases UI)

```markdown
First public release of the Smart Greenhouse IoT Dashboard — a full-stack IoT
monitoring and control system runnable end-to-end without any physical hardware.

## What works

- **Backend (FastAPI + SQLAlchemy 2 + SQLite)** — REST + WebSocket API, threshold
  evaluation, alert generation, CSV export. **77 / 77 tests passing, 95.29 % coverage.**
- **Frontend (React + Vite + TypeScript strict + Tailwind)** — live readings,
  history chart, alerts, threshold form, actuator toggles, CSV export, light/dark
  mode, WebSocket auto-reconnect. **27 / 27 tests passing.**
- **Sensor simulator** — bounded random-walk generator that pushes synthetic
  readings to the backend, with 19 dedicated tests including 2 end-to-end against
  the real backend.
- **Optional ESP32 firmware** — reference Arduino sketch.
- **Docker Compose** — three-service stack (backend, simulator, frontend), named
  volume for SQLite persistence, healthchecks, internal bridge network.
  Implementation-complete and config-validated.
- **CI** — GitHub Actions workflow with backend / frontend / docs / docker-smoke
  jobs, plus CodeQL security scanning.

## Verified
- All tests pass locally on Python 3.12 and Node 22
- Backend coverage 95.29 % (gate 70 %)
- All linters and formatters clean
- Documentation consistency (`scripts/check-docs.py`) clean
- No secrets committed, narrow CORS default, non-root Docker containers

## Pending
- End-to-end `docker compose up` runtime verification — automated by
  `./scripts/verify-docker.sh` (must run on a machine with container-registry
  access; the dev sandbox blocks Docker Hub)
- Real dashboard screenshots — captured after the Docker runtime verification

## Lab-only scope
This is a portfolio / lab demonstration. No HTTPS, no production-grade auth,
SQLite single-tenant. Do not deploy as-is to public networks.

## Documentation
- [README.md](https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard#readme)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API.md](docs/API.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md)
- [docs/HARDWARE.md](docs/HARDWARE.md)
- [TESTING_REPORT.md](TESTING_REPORT.md) — per-phase real results

## License
MIT
```

### What to **say is verified** in the release notes

- Backend / frontend / simulator code is implemented and tested
- Backend 77/77 + 95.29% coverage, frontend 27/27, all linters clean
- Docs consistency enforced by automated check
- Security hygiene checks all pass

### What to **say is pending** in the release notes

- End-to-end Docker runtime verification (one command: `./scripts/verify-docker.sh`)
- CI workflow execution on a real GitHub runner (happens automatically after push)
- Real screenshots (capture after Docker verification)

---

## 7. Post-push verification checklist

Walk through this **after** `git push`. Most items are visual / one-click.

| # | Check | Where |
|---|---|---|
| 1 | First push appears on GitHub with the commit message intact | <https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard> |
| 2 | `Actions` tab shows the **CI** workflow running on the first push | Actions tab → CI |
| 3 | All four CI jobs complete (`backend`, `frontend`, `docs`, `docker-smoke`) | Click into the CI run |
| 4 | If `docker-smoke` fails, download the `docker-compose-logs` artifact | Failed job → Summary → Artifacts |
| 5 | `Actions` tab shows the **CodeQL** workflow completed without critical findings | Actions tab → CodeQL |
| 6 | README CI badge turns green (or yellow during run) | Top of README on GitHub |
| 7 | README CodeQL badge resolves | Same row of badges |
| 8 | License badge clickable to `LICENSE` | Same row |
| 9 | About sidebar shows the description text | Right side of repo page |
| 10 | Topics row shows ~20 topics from the list above | Right side of repo page, under description |
| 11 | "Issues" tab is enabled (default for new public repos) | Issues tab visible |
| 12 | "Security" tab shows CodeQL alerts (probably 0) | Security tab |
| 13 | No secrets / `.env` / `.db` / `node_modules` appear in the file tree | Browse root of repo |
| 14 | README renders correctly (code blocks, headings, badges) | Repo homepage |
| 15 | `docs/`, `examples/`, `firmware/`, `scripts/` all visible | Top-level tree |
| 16 | `Dependabot alerts` shows expected dev-only npm advisories from Phase 4 | Security → Dependabot alerts |

If everything above is good, create the v0.1.0 release per section 6.

---

## 8. Docker verification instructions

These commands are also automated by `./scripts/verify-docker.sh`, which is the recommended way to run them. The script tears down on success **and** on failure via `trap EXIT`.

```bash
# Build everything
docker compose build

# Start the stack in the background
docker compose up -d

# Wait a moment for healthchecks to settle
sleep 10

# Smoke the backend
curl http://localhost:8000/api/health
# expect: {"status":"ok","version":"0.1.0","uptime_seconds":<n>}

# Confirm readings are landing (simulator has had ~10 s to push)
curl http://localhost:8000/api/readings/latest
# expect 4 entries: temperature, humidity, soil_moisture, light

# Confirm dashboard is reachable
curl http://localhost:5173
# expect HTML
curl http://localhost:5173/healthz
# expect: ok

# Inspect simulator log
docker compose logs simulator
# expect lines like: sent type=temperature value=22.14 unit=C

# Tear down
docker compose down
# Or full reset including SQLite volume:
docker compose down -v
```

Expected end state:
- All three containers report `Up (healthy)` in `docker compose ps`
- `docker volume ls` shows `smart-greenhouse-iot-dashboard_greenhouse-data`
- Browser at <http://localhost:5173> shows the live dashboard
- Restart (`docker compose down && docker compose up -d`) preserves SQLite data

---

## 9. Screenshots plan

Screenshots are deliberately not committed yet because none have been captured against a verified runtime. Capture them after the Docker verification.

### How to run the app for screenshots

```bash
docker compose up -d
# wait ~30 seconds for the simulator to populate live data and the chart
open http://localhost:5173    # macOS
# or: xdg-open http://localhost:5173   # Linux
# or: start http://localhost:5173       # Windows
```

### What to capture

| Filename | Description | Why this captures the project |
|---|---|---|
| `screenshots/dashboard-light.png` | Full dashboard with simulator data, **light theme**, mid-day on the history chart | Hero shot |
| `screenshots/dashboard-dark.png` | Same dashboard in **dark theme** | Shows the theme system |
| `screenshots/alerts.png` | Tighten a threshold via the form, wait for a breach, capture the Alerts panel showing both warning and critical entries | Shows the alert pipeline working live |
| `screenshots/actuators.png` | Two actuators on, one off, with one toggle in the loading state | Shows optimistic UI |
| `screenshots/history-7d.png` | History chart with the 7-day range selected (after enough simulator data has accumulated, or after letting the stack run for a while) | Shows the chart and range selector |
| `screenshots/demo.gif` (optional) | 10-15 s screen recording: open dashboard → values updating → toggle an actuator → see the badge flip | Most engaging for LinkedIn / recruiter views |

### Where to save them

Create the directory at repo root:

```bash
mkdir -p screenshots
```

PNGs should be 1600 px wide or smaller; aim for < 1 MB each. The optional GIF should be < 5 MB (use `ffmpeg` or `gifski` to compress).

### Update the README after adding them

Replace the placeholder block in `README.md` with the real images:

```markdown
## Screenshots

![Dashboard (light mode)](screenshots/dashboard-light.png)
*Live readings, history chart, alerts panel, actuator toggles, all updating in real time.*

![Dashboard (dark mode)](screenshots/dashboard-dark.png)

![Alerts after tightening the temperature threshold](screenshots/alerts.png)
```

Commit message for the screenshot update:

```
docs(screenshots): add real dashboard captures

Captures taken against docker compose up output:
- dashboard-light.png, dashboard-dark.png
- alerts.png after a threshold breach
- actuators.png with mixed actuator states
- history-7d.png after a longer run
```

---

## 10. LinkedIn project update (post)

Use this as a LinkedIn feed post when you're ready to announce.

> 🌱 New project: **Smart Greenhouse IoT Dashboard**
>
> Full-stack IoT monitoring and control system, built end-to-end as a portfolio project.
>
> 🧱 **Stack:** FastAPI · React + TypeScript (strict) · Tailwind · WebSocket · SQLAlchemy 2 · SQLite · Docker Compose · Recharts · TanStack Query
>
> ✅ **What's in it**
> • Live readings for temperature, humidity, soil moisture, and light
> • History chart with 1h / 24h / 7d range selector and CSV export
> • Threshold form with client-side validation and live alert generation
> • Actuator toggles (fan, pump, grow light) with optimistic UI
> • WebSocket live event stream with exponential-backoff auto-reconnect
> • Hardware-free demo via a built-in sensor simulator
> • Optional ESP32 reference firmware for real hardware
>
> 🧪 **Engineering practice**
> • **77 / 77** backend pytest tests, **95.29%** coverage
> • **27 / 27** frontend Vitest tests
> • TypeScript strict mode, ESLint, Prettier, Ruff (lint + format)
> • GitHub Actions CI (backend / frontend / docs / Docker smoke) + CodeQL
> • Three-service Docker Compose stack with non-root containers and healthchecks
> • Documented design decisions, REST + WebSocket reference, deployment guide
>
> 🔒 **Security awareness baked in**
> CORS hardened, ingest rate-limited, optional API key on writes, parameterised
> queries, sanitised filenames, secret-free defaults. Lab-only scope is clearly
> documented; the project is honest about what is and isn't production-ready.
>
> 🤖 What it shows about how I work: I write requirements before code, write tests
> alongside features, and refuse to call something "done" without running the
> tests. The repository has a phase-by-phase testing report that anyone can audit.
>
> 🔗 **GitHub:** `https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard`
> *(replace with real link when published)*
>
> Open to feedback. Open to opportunities in software engineering, cybersecurity,
> SOC/Blue Team, and secure software development.
>
> #SoftwareEngineering #IoT #FastAPI #React #TypeScript #Cybersecurity #Docker
> #GitHubActions #Python #FullStack

---

## 11. LinkedIn Projects section entry

Use this as the entry in the **Projects** section of your LinkedIn profile (shorter, no emojis).

> **Smart Greenhouse IoT Dashboard** — *Portfolio project, 2026*
>
> Full-stack IoT monitoring and control system. FastAPI backend with REST + WebSocket
> API, threshold-based alerting, and SQLite persistence. React + TypeScript dashboard
> with live readings, history chart, alert log, threshold form, actuator controls,
> CSV export, and auto-reconnecting WebSocket. Hardware-free demo via a built-in
> sensor simulator; optional ESP32 firmware for real sensors. Three-service Docker
> Compose stack with non-root containers and healthchecks. GitHub Actions CI
> (backend / frontend / docs / Docker smoke) plus CodeQL security scanning.
>
> 77 backend tests (95% coverage), 27 frontend tests, all linters and formatters
> clean. Documented design decisions, deployment guide, and per-phase testing
> report.
>
> Tech: Python · FastAPI · SQLAlchemy 2 · Pydantic v2 · React 18 · Vite ·
> TypeScript · Tailwind · WebSocket · Recharts · Docker · GitHub Actions · CodeQL
>
> github.com/SeifMoussa/smart-greenhouse-iot-dashboard

---

## 12. CV bullet points

Use any 3–5 of these on the project section of your CV. Pick those that align with the specific role you're applying for.

- **Smart Greenhouse IoT Dashboard** — Built and tested a full-stack IoT system end-to-end: FastAPI backend with REST + WebSocket API, threshold-based alerting, and SQLite persistence; React + TypeScript dashboard with live readings, history chart, and CSV export; hardware-free Python simulator and optional ESP32 firmware path.
- Wrote **77 backend pytest tests achieving 95% coverage** and **27 frontend Vitest tests**, with strict TypeScript and zero linter warnings; every test runs in the committed GitHub Actions CI workflow.
- Designed a three-service Docker Compose stack (backend, simulator, frontend) with **non-root containers**, named-volume SQLite persistence, healthchecks, and an automated smoke-test script (`scripts/verify-docker.sh`).
- Implemented **security-aware defaults**: narrow CORS, ingest rate-limiting, optional API-key gating on writes, parameterised queries, sanitised export filenames, and explicit lab-only scope; documented all 5 transitive npm-audit advisories with rationale rather than silencing them.
- Established a phase-gated engineering process: written requirements → implementation → real test runs → docs consistency check → CI workflows. The repository's `TESTING_REPORT.md` and `PROJECT_COMPLETION_CHECKLIST.md` provide a complete audit trail.

---

## 13. Recruiter summary

> The Smart Greenhouse IoT Dashboard is a complete, runnable engineering artifact rather than a tutorial walk-through. It exercises a recruiter-relevant slice of full-stack and cybersecurity-adjacent skills — REST + WebSocket APIs, async pub/sub, SQL persistence, typed React UI, real-time visualization, optional embedded firmware, Docker Compose stack, GitHub Actions CI, CodeQL — and ships with a per-phase testing report whose results can be verified in minutes. Every claim in the README is backed by a command in the testing report; nothing is fabricated. Security awareness is treated as on-the-level with feature work (CORS, rate limiting, API-key gating, secret-free defaults). The Docker runtime verification and final screenshots are explicitly marked pending rather than faked, which is itself a useful signal about how the candidate works.

---

## 14. Final status report

This is captured in the Phase 9 report I'll deliver after committing this file.
