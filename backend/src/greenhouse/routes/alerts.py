"""Alerts listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from greenhouse.deps import get_db
from greenhouse.models import Alert
from greenhouse.schemas import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[AlertOut]:
    """Return the most recent ``limit`` alerts, newest first."""
    rows = db.execute(select(Alert).order_by(desc(Alert.created_at)).limit(limit)).scalars().all()
    return [AlertOut.model_validate(r) for r in rows]
