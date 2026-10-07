"""Attendance consumer for FaceObserved events."""
from __future__ import annotations

import logging
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.session import SessionLocal
from backend.app.events.types import FaceObserved, ObservationKind
from backend.app.models.attendance import AttendanceRecord

logger = logging.getLogger(__name__)


class AttendanceHandler:
    """Mark one daily DEFAULT attendance record for recognized students."""

    def __call__(self, event: FaceObserved) -> None:
        if event.kind is not ObservationKind.STUDENT or event.student_id is None:
            return

        db = SessionLocal()
        try:
            attendance_date = event.occurred_at.astimezone(timezone.utc).date()
            existing = db.execute(
                select(AttendanceRecord.id).where(
                    AttendanceRecord.student_id == event.student_id,
                    AttendanceRecord.attendance_date == attendance_date,
                    AttendanceRecord.session_label == "DEFAULT",
                )
            ).scalar_one_or_none()
            if existing is not None:
                return

            db.add(
                AttendanceRecord(
                    student_id=event.student_id,
                    camera_id=event.camera_id,
                    attendance_date=attendance_date,
                    session_label="DEFAULT",
                    marked_at=event.occurred_at,
                    status="PRESENT",
                    similarity=float(event.similarity or 0.0),
                    method="AUTO",
                )
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Attendance handler failed for camera_id=%s", event.camera_id)
        finally:
            db.close()
