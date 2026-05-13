"""Readings ingest, history, and latest-per-type endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import get_args

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from greenhouse import thresholds as threshold_eval
from greenhouse.deps import get_db, get_event_bus, rate_limit_ingest, require_api_key
from greenhouse.event_bus import EventBus
from greenhouse.models import Alert, Reading, Threshold, utc_now
from greenhouse.schemas import AlertOut, ReadingIn, ReadingOut, SensorType

router = APIRouter(prefix="/api/readings", tags=["readings"])


@router.post(
    "",
    response_model=ReadingOut,
    status_code=201,
    dependencies=[Depends(rate_limit_ingest), Depends(require_api_key)],
)
async def ingest(
    payload: ReadingIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
) -> ReadingOut:
    """Ingest one sensor reading, evaluate thresholds, broadcast events."""
    reading = Reading(
        sensor_id=payload.sensor_id,
        type=payload.type,
        value=payload.value,
        unit=payload.unit,
        timestamp=payload.timestamp or utc_now(),
    )
    db.add(reading)
    db.flush()

    threshold = db.get(Threshold, payload.type)
    alert: Alert | None = None
    if threshold is not None:
        result = threshold_eval.evaluate(payload.value, threshold.min_value, threshold.max_value)
        if result is not None:
            alert = Alert(
                type=payload.type,
                value=payload.value,
                threshold_min=threshold.min_value,
                threshold_max=threshold.max_value,
                severity=result["severity"],
                message=result["message"],
            )
            db.add(alert)
            db.flush()

    db.commit()
    db.refresh(reading)
    if alert is not None:
        db.refresh(alert)

    # Broadcast to WebSocket subscribers.
    reading_out = ReadingOut.model_validate(reading)
    await bus.publish({"type": "reading", "data": reading_out.model_dump(mode="json")})
    if alert is not None:
        alert_out = AlertOut.model_validate(alert)
        await bus.publish({"type": "alert", "data": alert_out.model_dump(mode="json")})

    return reading_out


@router.get("", response_model=list[ReadingOut])
async def list_readings(
    sensor_type: SensorType | None = Query(default=None, alias="type"),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> list[ReadingOut]:
    """List readings with optional type and time-range filters."""
    query = select(Reading)
    if sensor_type is not None:
        query = query.where(Reading.type == sensor_type)
    if from_ is not None:
        from_naive = from_.replace(tzinfo=None) if from_.tzinfo else from_
        query = query.where(Reading.timestamp >= from_naive)
    if to is not None:
        to_naive = to.replace(tzinfo=None) if to.tzinfo else to
        query = query.where(Reading.timestamp <= to_naive)
    query = query.order_by(desc(Reading.timestamp)).limit(limit)
    rows = db.execute(query).scalars().all()
    return [ReadingOut.model_validate(r) for r in rows]


@router.get("/latest", response_model=list[ReadingOut])
async def latest_readings(db: Session = Depends(get_db)) -> list[ReadingOut]:
    """Return the most recent reading for each known sensor type."""
    results: list[ReadingOut] = []
    for sensor_type in get_args(SensorType):
        latest = db.execute(
            select(Reading)
            .where(Reading.type == sensor_type)
            .order_by(desc(Reading.timestamp))
            .limit(1)
        ).scalar_one_or_none()
        if latest is not None:
            results.append(ReadingOut.model_validate(latest))
    return results
