"""
Student Model
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, SmallInteger, DateTime, ForeignKey,
    CheckConstraint, Index, func, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("year BETWEEN 1 AND 8", name="chk_students_year"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="chk_students_status"),
        Index("idx_students_dept_year", "department", "year"),
        Index("idx_students_name", func.lower(text("name"))),
        Index("idx_students_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    consent_given_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_version: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
