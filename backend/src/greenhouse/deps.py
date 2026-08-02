"""FastAPI dependencies wired to per-app state."""

from __future__ import annotations

from collections.abc import Generator

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from greenhouse import auth as auth_module
from greenhouse.auth import Role
from greenhouse.config import Settings
from greenhouse.event_bus import EventBus
from greenhouse.rate_limit import TokenBucket


def get_settings(request: Request) -> Settings:
    """Return the running app's settings."""
    return request.app.state.settings


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
    """Enforce the optional API key on the device/simulator ingest endpoint.

    If no key is configured (``GREENHOUSE_API_KEY`` empty), the dependency is
    a no-op so the demo runs out of the box. This is the credential used by
    the sensor simulator and the ESP32 firmware — neither can do an
    interactive login, so they keep using this shared key rather than the
    user-auth path below.
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


def rate_limit_login(request: Request) -> None:
    """Apply the token-bucket rate limit to login attempts, keyed by client IP."""
    bucket: TokenBucket = request.app.state.login_rate_limiter
    client_host = request.client.host if request.client else "unknown"
    if not bucket.check(client_host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return header.removeprefix("Bearer ").strip()


def get_current_user(
    request: Request, settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    """Decode the caller's JWT access token and return ``{"username", "role"}``."""
    token = _extract_bearer_token(request)
    try:
        payload = auth_module.decode_access_token(
            token, secret_key=settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    return {"username": str(payload["sub"]), "role": str(payload["role"])}


def require_role(minimum_role: Role):
    """Build a dependency requiring at least ``minimum_role`` (viewer < operator)."""

    def _dependency(user: dict[str, str] = Depends(get_current_user)) -> dict[str, str]:
        if not auth_module.role_satisfies(user["role"], minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not permit this action",
            )
        return user

    return _dependency
