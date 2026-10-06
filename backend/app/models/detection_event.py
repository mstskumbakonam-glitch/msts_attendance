"""
Detection Event Model
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger, String, Text, DateTime, Float, ForeignKey,
    SmallInteger, CheckConstraint, Index, Identity, func, text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class DetectionEvent(Base):
    __tablename__ = "detection_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('RECOGNIZED', 'UNKNOWN', 'BLACKLISTED')",
            name="chk_detection_events_type",
        ),
        Index("idx_events_occurred", text("occurred_at DESC")),
        Index("idx_events_student_occurred", "student_id", text("occurred_at DESC")),
        Index("idx_events_camera_occurred", "camera_id", text("occurred_at DESC")),
        Index("idx_events_type_occurred", "event_type", text("occurred_at DESC")),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(12), nullable=False)
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    blacklist_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blacklist_entries.id", ondelete="SET NULL"), nullable=True
    )
    similarity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox: Mapped[Optional[List[int]]] = mapped_column(ARRAY(SmallInteger), nullable=True)
    track_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    snapshot_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
