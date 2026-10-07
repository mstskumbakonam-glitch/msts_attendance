"""
Pydantic schemas for Camera management endpoints.
"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from urllib.parse import urlsplit

from backend.app.cameras.credentials import reject_embedded_credentials


CameraSourceType = Literal["WEBCAM", "VIDEO_FILE", "RTSP"]


class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    location: str = Field(..., min_length=1, max_length=160)
    source_type: CameraSourceType
    source_url: Optional[str] = None
    credentials_ref: Optional[str] = Field(
        default=None,
        max_length=64,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )
    enabled: bool = True

    @field_validator("name", "location")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty or whitespace only")
        return value

    @field_validator("source_url")
    @classmethod
    def normalize_source_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_source_configuration(self):
        _validate_source_configuration(
            self.source_type,
            self.source_url,
            self.credentials_ref,
        )
        return self


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    location: Optional[str] = Field(None, min_length=1, max_length=160)
    source_type: Optional[CameraSourceType] = None
    source_url: Optional[str] = None
    credentials_ref: Optional[str] = Field(
        default=None,
        max_length=64,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )
    enabled: Optional[bool] = None

    @field_validator("name", "location")
    @classmethod
    def strip_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty or whitespace only")
        return value

    @field_validator("source_url")
    @classmethod
    def normalize_source_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CameraResponse(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    source_type: CameraSourceType
    source_url: Optional[str] = None
    credentials_ref: Optional[str] = None
    enabled: bool
    status: str
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CameraListResponse(BaseModel):
    items: list[CameraResponse]
    total: int


class CameraTestResponse(BaseModel):
    ok: bool
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    error: Optional[str] = None


def _validate_source_configuration(
    source_type: str,
    source_url: Optional[str],
    credentials_ref: Optional[str],
) -> None:
    if not source_url:
        raise ValueError("source_url is required")

    if source_type == "WEBCAM":
        if not source_url.isdigit():
            raise ValueError("WEBCAM source_url must be a numeric camera index")
        if credentials_ref:
            raise ValueError("WEBCAM must not use credentials_ref")
        return

    if source_type == "VIDEO_FILE":
        if not source_url:
            raise ValueError("VIDEO_FILE source_url is required")
        if credentials_ref:
            raise ValueError("VIDEO_FILE must not use credentials_ref")
        return

    if source_type == "RTSP":
        parsed = urlsplit(source_url)

        if parsed.scheme.lower() != "rtsp":
            raise ValueError("RTSP source_url must use rtsp://")

        if not parsed.hostname:
            raise ValueError("RTSP source_url must contain a hostname")

        reject_embedded_credentials(source_url)

        if not credentials_ref:
            raise ValueError("RTSP cameras require credentials_ref")
        return

    raise ValueError("Unsupported camera source_type")
