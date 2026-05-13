# Contributing

Thanks for your interest in this project! This repository is part of a personal engineering portfolio, but issues and pull requests are welcome.

## Development setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional) Docker + Docker Compose

### First-time setup

```bash
git clone https://github.com/SeifMoussa/smart-greenhouse-iot-dashboard.git
cd smart-greenhouse-iot-dashboard
cp .env.example .env
make install
```

### Running locally

Open three terminals:

```bash
make dev-backend     # FastAPI on :8000
make dev-simulator   # synthetic sensor readings
make dev-frontend    # Vite dev server on :5173
```

Or, with Docker:

```bash
make up
```

## Quality bar

Before opening a pull request, please run:

```bash
make lint
make typecheck
make test
make build
```

CI runs the same checks — PRs cannot merge until all jobs are green.

### Style

- **Python:** ruff is the source of truth for both lint and format. Type hints are required on public functions.
- **TypeScript:** strict mode. ESLint + Prettier configuration is committed; do not override.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) style is preferred (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).
- **Branches:** `main` is protected. Use short-lived feature branches.

## Tests

- New backend code should have at least one unit test and, where it crosses a route boundary, an integration test.
- New frontend components benefit from a small Vitest + React Testing Library test exercising the main interaction.
- Coverage must remain ≥70% on the backend.

## Reporting bugs / requesting features

Use the issue templates under [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE/).

## Scope reminder

This is a lab-only IoT system. Please avoid contributions that:
- Add real-world authentication providers without a clear lab use case
- Add production hardening that doesn't fit the single-tenant SQLite scope
- Add proprietary sensor protocols without a free, open alternative

Bigger changes are very welcome as discussion issues first.
