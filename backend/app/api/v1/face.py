"""
Face registration and capture session endpoints.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.api.v1.stream import get_preview_webcam
from backend.app.core.deps import get_db, require_role
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.schemas.face import (
    FaceCaptureResponse,
    FaceSessionCreateRequest,
    FaceSessionResponse,
    FaceStatusResponse,
)
from backend.app.services.audit_service import create_audit_log
from backend.app.services.registration_session import session_manager

router = APIRouter(prefix="/students/{student_id}/face", tags=["face"])


@router.post("/session", response_model=FaceSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_face_session(
    student_id: uuid.UUID,
    payload: FaceSessionCreateRequest,
    camera_id: str = Query("0", description="Camera index or identifier"),
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> FaceSessionResponse:
    """Initialize an in-memory face registration session. Enforces consent."""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    if not student.consent_given_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student has not granted biometric consent. Consent must be recorded prior to face capture.",
        )

    try:
        session = session_manager.create_session(
            student_uuid=student.id,
            student_id=student.student_id,
            camera_id=camera_id,
            target_samples=payload.target_samples,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return FaceSessionResponse(
        session_id=session.session_id,
        student_id=student.student_id,
        target_samples=session.target_samples,
        current_samples=len(session.frames),
        expires_in=int(session.expires_at - session.created_at),
    )


@router.post("/session/{session_id}/capture", response_model=FaceCaptureResponse)
async def capture_frame(
    student_id: uuid.UUID,
    session_id: str,
    current_user: User = Depends(require_role("ADMIN")),
) -> FaceCaptureResponse:
    """Capture a single frame from the camera and store in-memory in the session."""
    session = session_manager.get_session(session_id)
    if not session or session.student_uuid != student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active registration session not found or expired",
        )

    try:
        cam_idx = int(session.camera_id)
    except ValueError:
        cam_idx = 0

    cam = get_preview_webcam(cam_idx)
    if not cam.is_open():
        cam.open()

    from backend.app.vision.preprocess import validate_image_quality

    success, frame = cam.read_frame()
    if not success or frame is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture frame from camera",
        )

    # Validate image quality (resolution, brightness, blur)
    val_res = validate_image_quality(frame)
    if not val_res.ok:
        return FaceCaptureResponse(
            accepted=False,
            current_samples=len(session.frames),
            target_samples=session.target_samples,
            reason=val_res.reason,
            quality_score=val_res.metrics.blur_score if val_res.metrics else None,
            pose_prompt=session.current_prompt(),
        )

    # Add frame in memory
    count = session.add_frame(frame)
    next_prompt = session.current_prompt()

    return FaceCaptureResponse(
        accepted=True,
        current_samples=count,
        target_samples=session.target_samples,
        quality_score=val_res.metrics.blur_score if val_res.metrics else None,
        pose_prompt=next_prompt,
    )


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_session(
    student_id: uuid.UUID,
    session_id: str,
    current_user: User = Depends(require_role("ADMIN")),
) -> Response:
    """Cancel and clear registration session frames from memory."""
    session = session_manager.get_session(session_id)
    if session:
        session_manager.delete_session(session_id)
    # Release camera
    cam = get_preview_webcam()
    cam.release()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/status", response_model=FaceStatusResponse)
async def get_face_status(
    student_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> FaceStatusResponse:
    """Check face registration status for a student (never returns vectors)."""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    from backend.app.db.repositories.student_repo import StudentRepository
    repo = StudentRepository(db)
    registered, count = repo.get_face_stats(student.id)

    return FaceStatusResponse(
        registered=registered,
        sample_count=count,
        model_name="buffalo_l (ArcFace w600k_r50)",
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_face_biometrics(
    request: Request,
    student_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> Response:
    """Hard-delete all face embeddings for student (consent withdrawal)."""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    from backend.app.models.face_embedding import FaceEmbedding
    from sqlalchemy import delete
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.student_id == student.id))
    db.commit()

    client_ip = request.client.host if request.client else "unknown"
    create_audit_log(
        db=db,
        action="FACE_DELETE",
        entity_type="STUDENT",
        actor_user_id=current_user.id,
        entity_id=student.student_id,
        ip=client_ip,
        details={"reason": "Biometric withdrawal"},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
