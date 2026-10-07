"""Identity decision helpers for the shared recognition pipeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class IdentityKind(StrEnum):
    STUDENT = "STUDENT"
    BLACKLISTED = "BLACKLISTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class IdentityCandidate:
    kind: IdentityKind
    similarity: float
    student_id: Optional[UUID] = None
    blacklist_id: Optional[UUID] = None


def resolve_identity(
    student: Optional[IdentityCandidate],
    blacklist: Optional[IdentityCandidate],
    threshold: float = 0.45,
) -> IdentityCandidate:
    """Choose the strongest accepted identity; ties prefer BLACKLISTED."""
    candidates = [c for c in (student, blacklist) if c is not None and c.similarity >= threshold]
    if not candidates:
        return IdentityCandidate(kind=IdentityKind.UNKNOWN, similarity=0.0)
    best_score = max(c.similarity for c in candidates)
    tied = [c for c in candidates if c.similarity == best_score]
    if any(c.kind == IdentityKind.BLACKLISTED for c in tied):
        return next(c for c in tied if c.kind == IdentityKind.BLACKLISTED)
    return tied[0]
