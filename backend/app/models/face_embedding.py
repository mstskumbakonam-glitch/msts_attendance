"""
Face Embedding Model
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Float, Boolean, DateTime, ForeignKey,
    CheckConstraint, Index, func, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from backend.app.db.base import Base


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    __table_args__ = (
        CheckConstraint(
            "((student_id IS NOT NULL)::int + (blacklist_entry_id IS NOT NULL)::int) = 1",
            name="chk_face_embeddings_owner",
        ),
        Index("idx_face_embeddings_student", "student_id"),
        Index("idx_face_embeddings_blacklist", "blacklist_entry_id"),
        Index("idx_face_embeddings_is_active", "is_active"),
        Index(
            "idx_face_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=True
    )
    blacklist_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blacklist_entries.id", ondelete="CASCADE"), nullable=True
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(512), nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(40), nullable=False, default="buffalo_l", server_default=text("'buffalo_l'")
    )
    model_version: Mapped[str] = mapped_column(
        String(40), nullable=False, default="w600k_r50", server_default=text("'w600k_r50'")
    )
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_label: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
