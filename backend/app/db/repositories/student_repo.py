"""
Student repository for data access.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.face_embedding import FaceEmbedding
from backend.app.models.student import Student


class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, student_uuid: uuid.UUID) -> Optional[Student]:
        return self.db.get(Student, student_uuid)

    def get_by_student_id(self, student_id: str) -> Optional[Student]:
        stmt = select(Student).where(Student.student_id == student_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_face_stats(self, student_uuid: uuid.UUID) -> Tuple[bool, int]:
        stmt = select(func.count(FaceEmbedding.id)).where(
            FaceEmbedding.student_id == student_uuid,
            FaceEmbedding.is_active.is_(True),
        )
        count = self.db.execute(stmt).scalar_one() or 0
        return (count > 0, count)

    def list_students(
        self,
        q: Optional[str] = None,
        department: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Tuple[Student, int]], int]:
        query = select(Student)

        if q:
            term = f"%{q.lower().strip()}%"
            query = query.where(
                (func.lower(Student.name).like(term))
                | (func.lower(Student.student_id).like(term))
            )
        if department:
            query = query.where(Student.department == department)
        if year is not None:
            query = query.where(Student.year == year)
        if status:
            query = query.where(Student.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        # Paging + ordering
        query = query.order_by(Student.student_id.asc())
        query = query.offset((page - 1) * size).limit(size)
        students = self.db.execute(query).scalars().all()

        # Fetch face sample counts for each student
        result: List[Tuple[Student, int]] = []
        for s in students:
            _, count = self.get_face_stats(s.id)
            result.append((s, count))

        return result, total

    def create(
        self,
        student_id: str,
        name: str,
        department: str,
        year: int,
        consent: bool,
        consent_version: Optional[str],
        created_by: Optional[uuid.UUID],
    ) -> Student:
        consent_time = datetime.now(timezone.utc) if consent else None
        student = Student(
            student_id=student_id,
            name=name,
            department=department,
            year=year,
            status="ACTIVE",
            consent_given_at=consent_time,
            consent_version=consent_version if consent else None,
            created_by=created_by,
        )
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        return student

    def update(
        self,
        student: Student,
        name: Optional[str] = None,
        department: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None,
        consent: Optional[bool] = None,
        consent_version: Optional[str] = None,
    ) -> Student:
        if name is not None:
            student.name = name
        if department is not None:
            student.department = department
        if year is not None:
            student.year = year
        if status is not None:
            student.status = status
        if consent is not None:
            if consent:
                student.consent_given_at = datetime.now(timezone.utc)
                student.consent_version = consent_version or student.consent_version or "v1.0"
            else:
                student.consent_given_at = None
                student.consent_version = None

        self.db.commit()
        self.db.refresh(student)
        return student

    def deactivate(self, student: Student) -> Student:
        student.status = "INACTIVE"
        # Deactivate associated face embeddings
        embeddings = self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.student_id == student.id)
        ).scalars().all()
        for emb in embeddings:
            emb.is_active = False
        self.db.commit()
        self.db.refresh(student)
        return student
