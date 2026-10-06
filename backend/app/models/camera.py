"""
Camera Model
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Boolean, DateTime,
    CheckConstraint, func, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('WEBCAM', 'VIDEO_FILE', 'RTSP')",
            name="chk_cameras_source_type",
        ),
        CheckConstraint(
            "status IN ('UNKNOWN', 'ONLINE', 'OFFLINE', 'ERROR', 'DISABLED')",
            name="chk_cameras_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credentials_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="UNKNOWN", server_default=text("'UNKNOWN'")
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
