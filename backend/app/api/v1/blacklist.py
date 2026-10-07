"""Blacklist management API (ADMIN write, ADMIN/OPERATOR read)."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.core.deps import get_db, require_role
from backend.app.models.user import User
from backend.app.schemas.blacklist import (
    BlacklistCreate,
    BlacklistListResponse,
    BlacklistResponse,
    BlacklistUpdate,
)
from backend.app.services.blacklist_service import BlacklistService

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


@router.post("", response_model=BlacklistResponse, status_code=status.HTTP_201_CREATED)
async def create_blacklist_entry(
    request: Request,
    payload: BlacklistCreate,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> BlacklistResponse:
    client_ip = request.client.host if request.client else "unknown"
    return BlacklistService(db).create(payload, actor=current_user, client_ip=client_ip)


@router.get("", response_model=BlacklistListResponse)
async def list_blacklist(
    q: Optional[str] = Query(None, min_length=1),
    status_filter: Optional[str] = Query(None, alias="status", pattern=r"^(ACTIVE|INACTIVE)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> BlacklistListResponse:
    return BlacklistService(db).list(q=q, status_filter=status_filter, page=page, size=size)


@router.get("/{entry_id}", response_model=BlacklistResponse)
async def get_blacklist_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> BlacklistResponse:
    return BlacklistService(db).get(entry_id)


@router.patch("/{entry_id}", response_model=BlacklistResponse)
async def update_blacklist_entry(
    request: Request,
    entry_id: uuid.UUID,
    payload: BlacklistUpdate,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> BlacklistResponse:
    client_ip = request.client.host if request.client else "unknown"
    return BlacklistService(db).update(entry_id, payload, actor=current_user, client_ip=client_ip)


@router.post("/{entry_id}/deactivate", response_model=BlacklistResponse)
async def deactivate_blacklist_entry(
    request: Request,
    entry_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> BlacklistResponse:
    client_ip = request.client.host if request.client else "unknown"
    return BlacklistService(db).deactivate(entry_id, actor=current_user, client_ip=client_ip)
