"""
Student management endpoints.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.core.deps import get_db, require_role
from backend.app.models.user import User
from backend.app.schemas.student import (
    StudentCreate,
    StudentListResponse,
    StudentResponse,
    StudentUpdate,
)
from backend.app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["students"])


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    request: Request,
    payload: StudentCreate,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> StudentResponse:
    """Create a new student (ADMIN only)."""
    client_ip = request.client.host if request.client else "unknown"
    service = StudentService(db)
    return service.create_student(payload, actor=current_user, client_ip=client_ip)


@router.get("", response_model=StudentListResponse)
async def list_students(
    q: Optional[str] = Query(None, description="Search term for name or student_id"),
    department: Optional[str] = Query(None, description="Filter by department"),
    year: Optional[int] = Query(None, ge=1, le=8, description="Filter by year"),
    status: Optional[str] = Query(None, pattern="^(ACTIVE|INACTIVE)$", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> StudentListResponse:
    """List students with pagination, search, and filters (ADMIN or OPERATOR)."""
    service = StudentService(db)
    return service.list_students(
        q=q,
        department=department,
        year=year,
        status_filter=status,
        page=page,
        size=size,
    )


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> StudentResponse:
    """Get single student by UUID (ADMIN or OPERATOR)."""
    service = StudentService(db)
    return service.get_student(student_id)


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(
    request: Request,
    student_id: uuid.UUID,
    payload: StudentUpdate,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> StudentResponse:
    """Update student fields (ADMIN only)."""
    client_ip = request.client.host if request.client else "unknown"
    service = StudentService(db)
    return service.update_student(student_id, payload, actor=current_user, client_ip=client_ip)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_student(
    request: Request,
    student_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> Response:
    """Soft-delete / deactivate student (ADMIN only)."""
    client_ip = request.client.host if request.client else "unknown"
    service = StudentService(db)
    service.deactivate_student(student_id, actor=current_user, client_ip=client_ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
