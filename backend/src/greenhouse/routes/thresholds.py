"""Per-sensor-type threshold list and update endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from greenhouse.deps import get_db, require_role
from greenhouse.models import Threshold
from greenhouse.schemas import SensorType, ThresholdIn, ThresholdOut

router = APIRouter(prefix="/api/thresholds", tags=["thresholds"])


@router.get("", response_model=list[ThresholdOut], dependencies=[Depends(require_role("viewer"))])
async def list_thresholds(db: Session = Depends(get_db)) -> list[ThresholdOut]:
    """List the configured threshold band for every sensor type."""
    rows = db.execute(select(Threshold).order_by(Threshold.type)).scalars().all()
    return [ThresholdOut.model_validate(r) for r in rows]


@router.put(
    "/{sensor_type}",
    response_model=ThresholdOut,
    dependencies=[Depends(require_role("operator"))],
)
async def update_threshold(
    sensor_type: SensorType,
    payload: ThresholdIn,
    db: Session = Depends(get_db),
) -> ThresholdOut:
    """Create or update the threshold band for a single sensor type."""
    threshold = db.get(Threshold, sensor_type)
    if threshold is None:
        threshold = Threshold(
            type=sensor_type,
            min_value=payload.min_value,
            max_value=payload.max_value,
        )
        db.add(threshold)
    else:
        threshold.min_value = payload.min_value
        threshold.max_value = payload.max_value
    db.commit()
    db.refresh(threshold)
    return ThresholdOut.model_validate(threshold)
