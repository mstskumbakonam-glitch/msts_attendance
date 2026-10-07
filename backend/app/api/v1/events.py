"""Detection Events API."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.deps import get_db, require_role
from backend.app.models.detection_event import DetectionEvent
from backend.app.models.user import User

router = APIRouter(prefix="/events", tags=["events"])


class DetectionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    camera_id: uuid.UUID
    event_type: str
    student_id: Optional[uuid.UUID] = None
    blacklist_entry_id: Optional[uuid.UUID] = None
    similarity: Optional[float] = None
    bbox: Optional[list[int]] = None
    track_id: Optional[str] = None
    snapshot_path: Optional[str] = None
    created_at: datetime


class DetectionEventListResponse(BaseModel):
    items: list[DetectionEventResponse]
    total: int
    page: int
    size: int


@router.get("", response_model=DetectionEventListResponse)
async def list_events(
    camera_id: Optional[uuid.UUID] = Query(None),
    event_type: Optional[str] = Query(None, pattern="^(RECOGNIZED|UNKNOWN|BLACKLISTED)$"),
    student_id: Optional[uuid.UUID] = Query(None),
    event_date: Optional[date] = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> DetectionEventListResponse:
    query = select(DetectionEvent)
    count_query = select(func.count()).select_from(DetectionEvent)
    filters = []

    if camera_id is not None:
        filters.append(DetectionEvent.camera_id == camera_id)
    if event_type is not None:
        filters.append(DetectionEvent.event_type == event_type)
    if student_id is not None:
        filters.append(DetectionEvent.student_id == student_id)
    if event_date is not None:
        start = datetime.combine(event_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(event_date, time.max, tzinfo=timezone.utc)
        filters.extend([
            DetectionEvent.occurred_at >= start,
            DetectionEvent.occurred_at <= end,
        ])

    query = query.where(*filters).order_by(DetectionEvent.occurred_at.desc())
    count_query = count_query.where(*filters)
    total = int(db.execute(count_query).scalar_one())
    items = db.execute(query.offset((page - 1) * size).limit(size)).scalars().all()
    return DetectionEventListResponse(items=items, total=total, page=page, size=size)
