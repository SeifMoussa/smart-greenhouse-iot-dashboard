"""Pydantic v2 request/response schemas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SensorType = Literal["temperature", "humidity", "soil_moisture", "light"]
ActuatorId = Literal["fan", "pump", "light"]
Severity = Literal["warning", "critical"]
ActuatorStateLiteral = Literal["on", "off"]


def _normalize_to_naive_utc(value: datetime) -> datetime:
    """Convert any datetime to naive UTC (the project's storage convention)."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


# ---------------------------------------------------------------------------
# Readings
# ---------------------------------------------------------------------------


class ReadingIn(BaseModel):
    """Payload accepted by POST /api/readings."""

    sensor_id: str = Field(min_length=1, max_length=64)
    type: SensorType
    value: float
    unit: str = Field(min_length=1, max_length=16)
    timestamp: datetime | None = None

    @field_validator("timestamp")
    @classmethod
    def _normalize_and_validate_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        value = _normalize_to_naive_utc(value)
        now_utc_naive = datetime.now(UTC).replace(tzinfo=None)
        if value > now_utc_naive + timedelta(minutes=5):
            raise ValueError("timestamp must not be more than 5 minutes in the future")
        return value


class ReadingOut(BaseModel):
    """Reading returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: str
    type: SensorType
    value: float
    unit: str
    timestamp: datetime
    created_at: datetime


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------


class ThresholdIn(BaseModel):
    """Payload accepted by PUT /api/thresholds/{type}."""

    min_value: float
    max_value: float

    @model_validator(mode="after")
    def _check_bounds(self) -> ThresholdIn:
        if self.min_value >= self.max_value:
            raise ValueError("min_value must be strictly less than max_value")
        return self


class ThresholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: SensorType
    min_value: float
    max_value: float
    updated_at: datetime


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: SensorType
    value: float
    threshold_min: float
    threshold_max: float
    severity: Severity
    message: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Actuators
# ---------------------------------------------------------------------------


class ActuatorIn(BaseModel):
    state: ActuatorStateLiteral


class ActuatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: ActuatorId
    name: str
    state: ActuatorStateLiteral
    updated_at: datetime


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginIn(BaseModel):
    """Payload accepted by POST /api/auth/login."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)


class TokenOut(BaseModel):
    """Access token returned on successful login."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: Literal["viewer", "operator"]
    username: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str
    uptime_seconds: float
