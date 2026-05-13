"""Actuator list and state-change endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from greenhouse.deps import get_db, get_event_bus, require_api_key
from greenhouse.event_bus import EventBus
from greenhouse.models import ActuatorState
from greenhouse.schemas import ActuatorId, ActuatorIn, ActuatorOut

router = APIRouter(prefix="/api/actuators", tags=["actuators"])


@router.get("", response_model=list[ActuatorOut])
async def list_actuators(db: Session = Depends(get_db)) -> list[ActuatorOut]:
    """Return every configured actuator and its current state."""
    rows = db.execute(select(ActuatorState).order_by(ActuatorState.id)).scalars().all()
    return [ActuatorOut.model_validate(r) for r in rows]


@router.post(
    "/{actuator_id}/state",
    response_model=ActuatorOut,
    dependencies=[Depends(require_api_key)],
)
async def set_actuator(
    actuator_id: ActuatorId,
    payload: ActuatorIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
) -> ActuatorOut:
    """Set the state of an actuator and broadcast the change."""
    actuator = db.get(ActuatorState, actuator_id)
    if actuator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actuator not found")
    actuator.state = payload.state
    db.commit()
    db.refresh(actuator)

    out = ActuatorOut.model_validate(actuator)
    await bus.publish({"type": "actuator", "data": out.model_dump(mode="json")})
    return out
