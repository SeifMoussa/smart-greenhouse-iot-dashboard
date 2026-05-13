"""FastAPI dependencies wired to per-app state."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from greenhouse.event_bus import EventBus
from greenhouse.rate_limit import TokenBucket


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session bound to the running app's engine."""
    factory = request.app.state.session_factory
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


def get_event_bus(request: Request) -> EventBus:
    """Return the running app's shared event bus."""
    return request.app.state.event_bus


def require_api_key(request: Request) -> None:
    """Enforce the optional API key on write endpoints.

    If no key is configured (``GREENHOUSE_API_KEY`` empty), the dependency is
    a no-op so the demo runs out of the box.
    """
    settings = request.app.state.settings
    expected: str = settings.greenhouse_api_key
    if not expected:
        return
    provided = request.headers.get("X-API-Key", "")
    if provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def rate_limit_ingest(request: Request) -> None:
    """Apply the token-bucket rate limit to ingest requests."""
    bucket: TokenBucket = request.app.state.rate_limiter
    client_host = request.client.host if request.client else "unknown"
    if not bucket.check(client_host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
