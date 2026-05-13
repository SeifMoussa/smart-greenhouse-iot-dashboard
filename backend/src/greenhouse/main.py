"""FastAPI app factory.

Run via uvicorn's factory mode::

    uvicorn 'greenhouse.main:create_app' --factory --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from greenhouse import __version__
from greenhouse.config import Settings, get_settings
from greenhouse.db import create_engine_for, init_db, make_session_factory
from greenhouse.event_bus import EventBus
from greenhouse.logging_config import configure_logging
from greenhouse.rate_limit import TokenBucket
from greenhouse.routes import (
    actuators,
    alerts,
    export,
    health,
    readings,
    thresholds,
    ws_route,
)
from greenhouse.ws import WebSocketHub

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fully wired FastAPI application instance."""
    if settings is None:
        settings = get_settings()

    configure_logging(settings.log_level, settings.log_format)

    engine = create_engine_for(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)

    event_bus = EventBus()
    ws_hub = WebSocketHub(max_connections=settings.max_ws_connections)
    rate_limiter = TokenBucket(settings.ingest_rate_limit_per_second)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        log.info("backend starting", extra={"ctx_version": __version__})
        try:
            yield
        finally:
            log.info("backend stopping")
            engine.dispose()

    app = FastAPI(
        title="Smart Greenhouse IoT Dashboard",
        version=__version__,
        lifespan=lifespan,
    )

    # Shared per-app state, accessible via request.app.state.* in routes.
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.event_bus = event_bus
    app.state.ws_hub = ws_hub
    app.state.rate_limiter = rate_limiter
    app.state.start_time = time.time()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(readings.router)
    app.include_router(thresholds.router)
    app.include_router(alerts.router)
    app.include_router(actuators.router)
    app.include_router(export.router)
    app.include_router(ws_route.router)

    return app
