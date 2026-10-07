"""Business logic and audit trail for blacklist entries."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.blacklist import BlacklistEntry
from backend.app.models.face_embedding import FaceEmbedding
from backend.app.models.user import User
from backend.app.schemas.blacklist import (
    BlacklistCreate,
    BlacklistListResponse,
    BlacklistResponse,
    BlacklistUpdate,
)
from backend.app.services.audit_service import create_audit_log


class BlacklistService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _response(entry: BlacklistEntry) -> BlacklistResponse:
        return BlacklistResponse.model_validate(entry)

    def create(self, data: BlacklistCreate, actor: User, client_ip: Optional[str] = None) -> BlacklistResponse:
        entry = BlacklistEntry(
            full_name=data.full_name,
            reason=data.reason,
            category=data.category,
            severity=data.severity,
            notes=data.notes,
            status="ACTIVE",
            created_by=actor.id,
        )
        self.db.add(entry)
        self.db.flush()
        create_audit_log(
            db=self.db,
            action="BLACKLIST_CREATE",
            entity_type="BLACKLIST",
            actor_user_id=actor.id,
            entity_id=str(entry.id),
            ip=client_ip,
            details={
                "full_name": entry.full_name,
                "category": entry.category,
                "severity": entry.severity,
            },
        )
        self.db.refresh(entry)
        return self._response(entry)

    def get(self, entry_id: uuid.UUID) -> BlacklistResponse:
        entry = self.db.get(BlacklistEntry, entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found")
        return self._response(entry)

    def list(
        self,
        q: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> BlacklistListResponse:
        if page < 1 or size < 1 or size > 100:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid pagination")
        filters = []
        if q:
            q = q.strip()
            if q:
                term = f"%{q.lower()}%"
                filters.append(func.lower(BlacklistEntry.full_name).like(term))
        if status_filter:
            filters.append(BlacklistEntry.status == status_filter)

        total = int(self.db.execute(select(func.count()).select_from(BlacklistEntry).where(*filters)).scalar_one())
        rows = self.db.execute(
            select(BlacklistEntry)
            .where(*filters)
            .order_by(BlacklistEntry.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).scalars().all()
        return BlacklistListResponse(
            items=[self._response(row) for row in rows],
            total=total,
            page=page,
            size=size,
        )

    def update(
        self,
        entry_id: uuid.UUID,
        data: BlacklistUpdate,
        actor: User,
        client_ip: Optional[str] = None,
    ) -> BlacklistResponse:
        entry = self.db.get(BlacklistEntry, entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found")
        changes = data.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(entry, key, value)
        self.db.flush()
        create_audit_log(
            db=self.db,
            action="BLACKLIST_UPDATE",
            entity_type="BLACKLIST",
            actor_user_id=actor.id,
            entity_id=str(entry.id),
            ip=client_ip,
            details=changes,
        )
        self.db.refresh(entry)
        return self._response(entry)

    def deactivate(
        self,
        entry_id: uuid.UUID,
        actor: User,
        client_ip: Optional[str] = None,
    ) -> BlacklistResponse:
        entry = self.db.get(BlacklistEntry, entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found")

        entry.status = "INACTIVE"
        entry.deactivated_at = datetime.now(timezone.utc)
        self.db.execute(
            FaceEmbedding.__table__.update()
            .where(FaceEmbedding.blacklist_entry_id == entry.id)
            .values(is_active=False)
        )
        self.db.flush()
        create_audit_log(
            db=self.db,
            action="BLACKLIST_DEACTIVATE",
            entity_type="BLACKLIST",
            actor_user_id=actor.id,
            entity_id=str(entry.id),
            ip=client_ip,
            details={"new_status": "INACTIVE", "embeddings_disabled": True},
        )
        self.db.refresh(entry)
        return self._response(entry)
