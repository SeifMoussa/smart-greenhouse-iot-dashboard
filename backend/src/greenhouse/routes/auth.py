"""Login endpoint issuing JWT access tokens."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from greenhouse import auth as auth_module
from greenhouse.config import Settings
from greenhouse.deps import get_db, get_settings, rate_limit_login
from greenhouse.models import User
from greenhouse.schemas import LoginIn, TokenOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit_login)])
async def login(
    payload: LoginIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenOut:
    """Exchange a username/password for a short-lived JWT access token."""
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if user is None or not auth_module.verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = auth_module.create_access_token(
        username=user.username,
        role=user.role,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
    return TokenOut(access_token=token, role=user.role, username=user.username)
