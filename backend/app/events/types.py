"""Typed events emitted by the recognition/camera pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional, Sequence
from uuid import UUID


class ObservationKind(StrEnum):
    STUDENT = "STUDENT"
    UNKNOWN = "UNKNOWN"
    BLACKLISTED = "BLACKLISTED"


@dataclass(frozen=True, slots=True)
class FaceObserved:
    """A single face observation produced by the shared camera/recognition engine."""

    camera_id: UUID
    kind: ObservationKind
    occurred_at: datetime
    student_id: Optional[UUID] = None
    blacklist_id: Optional[UUID] = None
    similarity: Optional[float] = None
    bbox: Optional[Sequence[int]] = None
    track_id: Optional[str] = None
    snapshot_path: Optional[str] = None

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            object.__setattr__(self, "occurred_at", self.occurred_at.replace(tzinfo=timezone.utc))
