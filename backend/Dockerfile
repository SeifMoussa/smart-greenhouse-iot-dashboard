# syntax=docker/dockerfile:1.7

# ---------- Stage 1: build wheels for runtime deps ----------
FROM python:3.12-slim AS deps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src

# Install runtime deps + the package itself in a virtualenv so we can copy
# the whole thing to the final stage and run as a non-root user.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create a non-root user.
RUN groupadd --system app && useradd --system --gid app --home /app --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=deps /opt/venv /opt/venv
COPY src ./src

# /data is the SQLite volume mount target.
RUN mkdir -p /app/data && chown -R app:app /app

USER app

EXPOSE 8000

# Healthcheck without bash/curl: pure stdlib.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=2).status == 200 else 1)" || exit 1

# Default DATABASE_URL points at /app/data which is the documented volume.
ENV DATABASE_URL=sqlite:////app/data/greenhouse.db \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    PYTHONPATH=/app/src

CMD ["sh", "-c", "uvicorn 'greenhouse.main:create_app' --factory --host ${BACKEND_HOST} --port ${BACKEND_PORT}"]
