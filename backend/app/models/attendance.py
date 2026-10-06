"""
Attendance Record Model
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    String, Date, DateTime, Float, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, func, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "attendance_date", "session_label",
            name="uq_attendance_student_date_session",
        ),
        CheckConstraint("status IN ('PRESENT', 'LATE')", name="chk_attendance_status"),
        CheckConstraint("method IN ('AUTO', 'MANUAL')", name="chk_attendance_method"),
        Index("idx_attendance_date", "attendance_date"),
        Index("idx_attendance_student_date", "student_id", text("attendance_date DESC")),
        Index("idx_attendance_camera", "camera_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="RESTRICT"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_label: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DEFAULT", server_default=text("'DEFAULT'")
    )
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default="PRESENT", server_default=text("'PRESENT'")
    )
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(
        String(8), nullable=False, default="AUTO", server_default=text("'AUTO'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
