"""
Student service layer handling business logic, validation, and audit trail creation.
"""
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.repositories.student_repo import StudentRepository
from backend.app.models.user import User
from backend.app.schemas.student import (
    StudentCreate,
    StudentListResponse,
    StudentResponse,
    StudentUpdate,
)
from backend.app.services.audit_service import create_audit_log


class StudentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StudentRepository(db)

    def create_student(
        self, data: StudentCreate, actor: User, client_ip: Optional[str] = None
    ) -> StudentResponse:
        existing = self.repo.get_by_student_id(data.student_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student with student_id '{data.student_id}' already exists",
            )

        student = self.repo.create(
            student_id=data.student_id,
            name=data.name,
            department=data.department,
            year=data.year,
            consent=data.consent,
            consent_version=data.consent_version,
            created_by=actor.id,
        )

        create_audit_log(
            db=self.db,
            action="STUDENT_CREATE",
            entity_type="STUDENT",
            actor_user_id=actor.id,
            entity_id=student.student_id,
            ip=client_ip,
            details={
                "name": student.name,
                "department": student.department,
                "year": student.year,
                "consent": data.consent,
            },
        )

        return StudentResponse(
            id=student.id,
            student_id=student.student_id,
            name=student.name,
            department=student.department,
            year=student.year,
            status=student.status,
            consent_given_at=student.consent_given_at,
            consent_version=student.consent_version,
            face_registered=False,
            sample_count=0,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )

    def get_student(self, student_uuid: uuid.UUID) -> StudentResponse:
        student = self.repo.get_by_id(student_uuid)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with id '{student_uuid}' not found",
            )
        face_registered, sample_count = self.repo.get_face_stats(student.id)
        return StudentResponse(
            id=student.id,
            student_id=student.student_id,
            name=student.name,
            department=student.department,
            year=student.year,
            status=student.status,
            consent_given_at=student.consent_given_at,
            consent_version=student.consent_version,
            face_registered=face_registered,
            sample_count=sample_count,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )

    def list_students(
        self,
        q: Optional[str] = None,
        department: Optional[str] = None,
        year: Optional[int] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> StudentListResponse:
        if size > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page size cannot exceed 100",
            )
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page must be >= 1",
            )

        pairs, total = self.repo.list_students(
            q=q,
            department=department,
            year=year,
            status=status_filter,
            page=page,
            size=size,
        )

        items = [
            StudentResponse(
                id=s.id,
                student_id=s.student_id,
                name=s.name,
                department=s.department,
                year=s.year,
                status=s.status,
                consent_given_at=s.consent_given_at,
                consent_version=s.consent_version,
                face_registered=count > 0,
                sample_count=count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s, count in pairs
        ]

        return StudentListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
        )

    def update_student(
        self,
        student_uuid: uuid.UUID,
        data: StudentUpdate,
        actor: User,
        client_ip: Optional[str] = None,
    ) -> StudentResponse:
        student = self.repo.get_by_id(student_uuid)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with id '{student_uuid}' not found",
            )

        updated = self.repo.update(
            student=student,
            name=data.name,
            department=data.department,
            year=data.year,
            status=data.status,
            consent=data.consent,
            consent_version=data.consent_version,
        )

        create_audit_log(
            db=self.db,
            action="STUDENT_UPDATE",
            entity_type="STUDENT",
            actor_user_id=actor.id,
            entity_id=updated.student_id,
            ip=client_ip,
            details=data.model_dump(exclude_unset=True),
        )

        face_registered, sample_count = self.repo.get_face_stats(updated.id)
        return StudentResponse(
            id=updated.id,
            student_id=updated.student_id,
            name=updated.name,
            department=updated.department,
            year=updated.year,
            status=updated.status,
            consent_given_at=updated.consent_given_at,
            consent_version=updated.consent_version,
            face_registered=face_registered,
            sample_count=sample_count,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    def deactivate_student(
        self, student_uuid: uuid.UUID, actor: User, client_ip: Optional[str] = None
    ) -> None:
        student = self.repo.get_by_id(student_uuid)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with id '{student_uuid}' not found",
            )

        self.repo.deactivate(student)

        create_audit_log(
            db=self.db,
            action="STUDENT_DEACTIVATE",
            entity_type="STUDENT",
            actor_user_id=actor.id,
            entity_id=student.student_id,
            ip=client_ip,
            details={"previous_status": "ACTIVE", "new_status": "INACTIVE"},
        )
