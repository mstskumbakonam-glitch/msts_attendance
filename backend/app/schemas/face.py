"""
Pydantic schemas for face registration sessions and preview streaming.
"""
from typing import Optional
from pydantic import BaseModel, Field


class StreamTicketRequest(BaseModel):
    camera_id: str = Field(..., description="Camera identifier or index, e.g. '0' or camera UUID")


class StreamTicketResponse(BaseModel):
    ticket: str
    camera_id: str
    expires_in: int = 60


class FaceSessionCreateRequest(BaseModel):
    target_samples: int = Field(30, ge=5, le=50, description="Target number of face samples (5-50)")


class FaceSessionResponse(BaseModel):
    session_id: str
    student_id: str
    target_samples: int
    current_samples: int
    expires_in: int


class FaceCaptureResponse(BaseModel):
    accepted: bool
    current_samples: int
    target_samples: int
    reason: Optional[str] = None
    quality_score: Optional[float] = None
    pose_prompt: str


class FaceStatusResponse(BaseModel):
    registered: bool
    sample_count: int
    model_name: Optional[str] = None
    created_at: Optional[str] = None
