"""CSV export endpoint."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from greenhouse.deps import get_db
from greenhouse.models import Reading
from greenhouse.schemas import SensorType

router = APIRouter(prefix="/api", tags=["export"])

MAX_RANGE_DAYS = 30
CSV_HEADER = ["id", "sensor_id", "type", "value", "unit", "timestamp"]


def _rows_to_csv(rows: Iterable[Reading]) -> Iterable[str]:
    """Yield CSV lines: header first, then one line per row."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_HEADER)
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate()
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.sensor_id,
                row.type,
                row.value,
                row.unit,
                row.timestamp.isoformat(),
            ]
        )
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()


@router.get("/export.csv")
async def export_csv(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    sensor_type: SensorType | None = Query(default=None, alias="type"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream a CSV of readings within an optional range and type filter."""
    if from_ is not None and to is not None and (to - from_).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Time range exceeds {MAX_RANGE_DAYS} days",
        )

    query = select(Reading).order_by(Reading.timestamp)
    if from_ is not None:
        from_naive = from_.replace(tzinfo=None) if from_.tzinfo else from_
        query = query.where(Reading.timestamp >= from_naive)
    if to is not None:
        to_naive = to.replace(tzinfo=None) if to.tzinfo else to
        query = query.where(Reading.timestamp <= to_naive)
    if sensor_type is not None:
        query = query.where(Reading.type == sensor_type)

    # Materialize before streaming so we do not depend on the session,
    # which is closed when the dependency cleanup runs.
    rows = db.execute(query).scalars().all()

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    # Sanitize filename: only safe ASCII characters.
    filename = f"greenhouse-readings-{stamp}.csv"

    return StreamingResponse(
        _rows_to_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
