"""
Security Alert Model
"""
import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import (
    String, Text, Integer, Float, DateTime, ForeignKey,
    CheckConstraint, Index, func, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class SecurityAlert(Base):
    __tablename__ = "security_alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('UNKNOWN_PERSON', 'BLACKLISTED_PERSON', 'CAMERA_OFFLINE')",
            name="chk_alerts_type",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_alerts_severity",
        ),
        CheckConstraint(
            "status IN ('NEW', 'ACKNOWLEDGED', 'RESOLVED')",
            name="chk_alerts_status",
        ),
        Index(
            "idx_alerts_unresolved_dedup",
            "dedup_key",
            unique=True,
            postgresql_where=text("status <> 'RESOLVED'"),
        ),
        Index(
            "idx_alerts_status_severity",
            "status",
            "severity",
            text("last_seen_at DESC"),
        ),
        Index("idx_alerts_camera_created", "camera_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    alert_type: Mapped[str] = mapped_column(String(24), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        String(14), nullable=False, default="NEW", server_default=text("'NEW'")
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False
    )
    blacklist_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blacklist_entries.id"), nullable=True
    )
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id"), nullable=True
    )
    dedup_key: Mapped[str] = mapped_column(String(128), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    max_similarity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
