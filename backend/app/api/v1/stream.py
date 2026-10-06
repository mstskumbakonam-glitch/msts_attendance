"""
MJPEG Stream endpoints.
Provides short-lived ticket generation and authenticated MJPEG video streaming.
"""
import time
from typing import Generator
import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.app.cameras.webcam import WebcamSource
from backend.app.core.deps import require_role
from backend.app.models.user import User
from backend.app.schemas.face import StreamTicketRequest, StreamTicketResponse
from backend.app.services.registration_session import session_manager

router = APIRouter(tags=["stream"])

# Global preview webcam instance
_preview_webcam: WebcamSource | None = None


def get_preview_webcam(camera_index: int = 0) -> WebcamSource:
    global _preview_webcam
    if _preview_webcam is None:
        _preview_webcam = WebcamSource(camera_index=camera_index)
    return _preview_webcam


@router.post("/stream/ticket", response_model=StreamTicketResponse)
async def generate_stream_ticket(
    payload: StreamTicketRequest,
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
) -> StreamTicketResponse:
    """Generate a single-use, 60-second ticket for camera stream access."""
    ticket = session_manager.create_stream_ticket(
        camera_id=payload.camera_id,
        user_id=str(current_user.id),
        ttl_seconds=60,
    )
    return StreamTicketResponse(ticket=ticket, camera_id=payload.camera_id, expires_in=60)


def _generate_mjpeg_frames(cam: WebcamSource) -> Generator[bytes, None, None]:
    if not cam.is_open():
        cam.open()
    try:
        while True:
            success, frame = cam.read_frame()
            if not success or frame is None:
                time.sleep(0.05)
                continue
            ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            time.sleep(0.03)  # ~30 fps cap
    finally:
        pass


@router.get("/stream/{camera_id}")
async def stream_camera(
    camera_id: str,
    ticket: str = Query(..., description="Short-lived stream ticket"),
):
    """Serve MJPEG stream for the requested camera with valid ticket."""
    if not session_manager.validate_stream_ticket(ticket, camera_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or mismatched stream ticket",
        )

    try:
        cam_idx = int(camera_id)
    except ValueError:
        cam_idx = 0

    cam = get_preview_webcam(cam_idx)
    return StreamingResponse(
        _generate_mjpeg_frames(cam),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
