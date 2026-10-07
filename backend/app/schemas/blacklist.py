"""Pydantic schemas for blacklist management."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BlacklistCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    reason: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=40)
    severity: str = Field("HIGH", pattern=r"^(HIGH|CRITICAL)$")
    notes: Optional[str] = None

    @field_validator("full_name", "reason")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty or whitespace only")
        return value

    @field_validator("category", "notes")
    @classmethod
    def strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            return value or None
        return value


class BlacklistUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=120)
    reason: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=40)
    severity: Optional[str] = Field(None, pattern=r"^(HIGH|CRITICAL)$")
    notes: Optional[str] = None

    @field_validator("full_name", "reason")
    @classmethod
    def strip_required_updates(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty or whitespace only")
        return value

    @field_validator("category", "notes")
    @classmethod
    def strip_optional_updates(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            return value or None
        return value


class BlacklistResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    reason: str
    category: Optional[str] = None
    severity: str
    status: str
    notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    deactivated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BlacklistListResponse(BaseModel):
    items: list[BlacklistResponse]
    total: int
    page: int
    size: int
