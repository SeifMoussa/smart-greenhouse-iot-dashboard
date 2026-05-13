"""Liveness/health endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from greenhouse import __version__
from greenhouse.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    """Return service status, version, and uptime in seconds."""
    start_time: float = request.app.state.start_time
    return HealthOut(
        status="ok",
        version=__version__,
        uptime_seconds=max(0.0, time.time() - start_time),
    )
