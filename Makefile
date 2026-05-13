# =====================================================================
# Smart Greenhouse IoT Dashboard — Makefile
# =====================================================================
# Convenience targets for local development and CI parity.
# Run `make help` for the full list.

.PHONY: help install install-backend install-frontend \
        dev dev-backend dev-frontend dev-simulator \
        test test-backend test-frontend \
        lint lint-backend lint-frontend \
        format format-backend format-frontend \
        typecheck \
        build build-frontend \
        up down logs \
        clean

help: ## Show this help
	@echo "Smart Greenhouse IoT Dashboard — available targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------

install: install-backend install-frontend ## Install backend + frontend deps

install-backend: ## Install backend Python deps (editable + dev extras)
	cd backend && pip install -e ".[dev]"

install-frontend: ## Install frontend npm deps
	cd frontend && npm ci

# ---------------------------------------------------------------------
# Dev servers
# ---------------------------------------------------------------------

dev-backend: ## Run FastAPI backend (auto-reload)
	cd backend && uvicorn 'greenhouse.main:create_app' --factory --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run Vite dev server
	cd frontend && npm run dev

dev-simulator: ## Run the sensor simulator against the backend
	cd backend && python -m greenhouse.simulator

# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend unit + integration tests with coverage
	cd backend && pytest --cov=greenhouse --cov-report=term-missing --cov-fail-under=70

test-frontend: ## Run frontend Vitest suite (single run)
	cd frontend && npm test -- --run

# ---------------------------------------------------------------------
# Lint / format / typecheck
# ---------------------------------------------------------------------

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Run ruff on backend
	cd backend && ruff check src tests

lint-frontend: ## Run eslint on frontend
	cd frontend && npm run lint

format: format-backend format-frontend ## Auto-format all sources

format-check: format-check-backend format-check-frontend ## Verify formatting without writing

format-backend: ## Run ruff format on backend
	cd backend && ruff format src tests

format-check-backend: ## Verify backend formatting (ruff format --check)
	cd backend && ruff format --check src tests

format-frontend: ## Run prettier on frontend
	cd frontend && npm run format

format-check-frontend: ## Verify frontend formatting (prettier --check)
	cd frontend && npm run format:check

typecheck: ## Run TypeScript typecheck on frontend
	cd frontend && npm run typecheck

# ---------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------

build: build-frontend ## Build all production artifacts

build-frontend: ## Build frontend production bundle
	cd frontend && npm run build

# ---------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------

up: ## Start full stack via Docker Compose (backend + simulator + frontend)
	docker compose up --build

down: ## Stop and remove Docker Compose stack
	docker compose down

logs: ## Tail Docker Compose logs
	docker compose logs -f

# ---------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------

clean: ## Remove caches, build artifacts, and local DB
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	rm -rf backend/.coverage backend/htmlcov backend/coverage.xml
	rm -rf frontend/dist frontend/node_modules/.vite
	rm -rf backend/data/*.db
