"""
Pydantic schemas for Student endpoints.
"""
import re
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

STUDENT_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


class StudentCreate(BaseModel):
    student_id: str = Field(..., description="Unique student ID (1-32 chars: alphanumeric, _, -)")
    name: str = Field(..., min_length=1, max_length=120)
    department: str = Field(..., min_length=1, max_length=80)
    year: int = Field(..., ge=1, le=8, description="Academic year (1 to 8)")
    consent: bool = Field(False, description="Whether biometric consent has been granted")
    consent_version: Optional[str] = Field("v1.0", max_length=16)

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        v = v.strip()
        if not STUDENT_ID_REGEX.match(v):
            raise ValueError("student_id must match regex '^[A-Za-z0-9_-]{1,32}$'")
        return v

    @field_validator("name", "department")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    department: Optional[str] = Field(None, min_length=1, max_length=80)
    year: Optional[int] = Field(None, ge=1, le=8)
    status: Optional[str] = Field(None, pattern="^(ACTIVE|INACTIVE)$")
    consent: Optional[bool] = None
    consent_version: Optional[str] = Field(None, max_length=16)

    @field_validator("name", "department")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Field cannot be empty or whitespace only")
            return s
        return v


class StudentResponse(BaseModel):
    id: uuid.UUID
    student_id: str
    name: str
    department: str
    year: int
    status: str
    consent_given_at: Optional[datetime] = None
    consent_version: Optional[str] = None
    face_registered: bool = False
    sample_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentListResponse(BaseModel):
    items: List[StudentResponse]
    total: int
    page: int
    size: int
