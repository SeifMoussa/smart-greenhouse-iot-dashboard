"""Password hashing and JWT helpers for user authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt

Role = Literal["viewer", "operator"]

# Higher rank can do everything a lower rank can.
_ROLE_RANK: dict[str, int] = {"viewer": 1, "operator": 2}


def hash_password(password: str) -> str:
    """Hash a plaintext password with a fresh per-password bcrypt salt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(
    *,
    username: str,
    role: str,
    secret_key: str,
    algorithm: str,
    expire_minutes: int,
) -> str:
    """Issue a signed, short-lived JWT access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, *, secret_key: str, algorithm: str) -> dict[str, object]:
    """Decode and verify a JWT access token. Raises ``jwt.PyJWTError`` on failure."""
    return jwt.decode(token, secret_key, algorithms=[algorithm])


def role_satisfies(actual_role: str, minimum_role: Role) -> bool:
    """Return True if ``actual_role`` is at least as privileged as ``minimum_role``."""
    return _ROLE_RANK.get(actual_role, 0) >= _ROLE_RANK[minimum_role]
