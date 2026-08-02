"""Database engine, session factory, and bootstrap helpers."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

if TYPE_CHECKING:
    from greenhouse.config import Settings

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# Default values seeded on first start so the system works out of the box.
DEFAULT_THRESHOLDS: dict[str, tuple[float, float]] = {
    "temperature": (15.0, 32.0),  # °C
    "humidity": (40.0, 80.0),  # %
    "soil_moisture": (30.0, 80.0),  # %
    "light": (200.0, 1500.0),  # lux
}

DEFAULT_ACTUATORS: list[tuple[str, str]] = [
    ("fan", "Ventilation Fan"),
    ("pump", "Water Pump"),
    ("light", "Grow Light"),
]


def create_engine_for(database_url: str) -> Engine:
    """Create a SQLAlchemy engine appropriate for the given URL.

    For SQLite we relax the same-thread guard so FastAPI's thread-pool
    can use the session without complaint.
    """
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args, future=True)


def make_session_factory(engine: Engine) -> sessionmaker:
    """Build a session factory bound to the given engine."""
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
        expire_on_commit=False,
    )


def init_db(engine: Engine) -> None:
    """Create tables and seed defaults. Idempotent."""
    # Ensure SQLite parent directory exists when using a file-based URL.
    if engine.url.drivername.startswith("sqlite"):
        db_path = engine.url.database
        if db_path and db_path not in (":memory:", ""):
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

    # Import models so they are registered on Base before create_all.
    from greenhouse import models  # noqa: F401

    Base.metadata.create_all(engine)
    _seed_defaults(engine)


def _seed_defaults(engine: Engine) -> None:
    """Insert default thresholds and actuators if they do not already exist."""
    from greenhouse.models import ActuatorState, Threshold

    factory = make_session_factory(engine)
    with factory() as session:
        for sensor_type, (mn, mx) in DEFAULT_THRESHOLDS.items():
            if not session.get(Threshold, sensor_type):
                session.add(Threshold(type=sensor_type, min_value=mn, max_value=mx))
        for actuator_id, name in DEFAULT_ACTUATORS:
            if not session.get(ActuatorState, actuator_id):
                session.add(ActuatorState(id=actuator_id, name=name, state="off"))
        session.commit()
    log.info("database initialized", extra={"ctx_url": str(engine.url)})


def seed_default_users(engine: Engine, settings: Settings) -> None:
    """Insert the demo operator and viewer accounts if they don't already exist.

    Idempotent, same as the threshold/actuator seeding above, so it's safe
    to call on every start.
    """
    from greenhouse import auth
    from greenhouse.models import User

    factory = make_session_factory(engine)
    with factory() as session:
        seeds = [
            (settings.seed_operator_username, settings.seed_operator_password, "operator"),
            (settings.seed_viewer_username, settings.seed_viewer_password, "viewer"),
        ]
        for username, password, role in seeds:
            if not session.query(User).filter_by(username=username).first():
                session.add(
                    User(
                        username=username,
                        password_hash=auth.hash_password(password),
                        role=role,
                    )
                )
        session.commit()
