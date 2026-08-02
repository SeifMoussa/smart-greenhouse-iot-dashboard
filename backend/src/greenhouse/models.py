"""SQLAlchemy ORM models. All timestamps are naive UTC by convention."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from greenhouse.db import Base


def utc_now() -> datetime:
    """Return current UTC time as a naive datetime (convention: all UTC)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Reading(Base):
    """One sensor reading from any sensor."""

    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    __table_args__ = (Index("ix_readings_type_timestamp", "type", "timestamp"),)


class Threshold(Base):
    """Per-sensor min/max alerting band."""

    __tablename__ = "thresholds"

    type: Mapped[str] = mapped_column(String(32), primary_key=True)
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class Alert(Base):
    """A persisted threshold-breach event."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[float] = mapped_column(Float)
    threshold_min: Mapped[float] = mapped_column(Float)
    threshold_max: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16))  # "warning" | "critical"
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class ActuatorState(Base):
    """Current state of a controllable device (fan, pump, light)."""

    __tablename__ = "actuator_state"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(8))  # "on" | "off"
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class User(Base):
    """A dashboard account. Role determines read/write access."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))  # "viewer" | "operator"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
