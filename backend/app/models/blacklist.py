"""
Blacklist Entry Model
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, DateTime, ForeignKey,
    CheckConstraint, Index, func, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class BlacklistEntry(Base):
    __tablename__ = "blacklist_entries"
    __table_args__ = (
        CheckConstraint("severity IN ('HIGH', 'CRITICAL')", name="chk_blacklist_severity"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="chk_blacklist_status"),
        Index("idx_blacklist_status", "status"),
        Index("idx_blacklist_name", func.lower(text("full_name"))),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="HIGH", server_default=text("'HIGH'")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
