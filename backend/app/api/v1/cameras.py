"""
Camera management API endpoints.
"""
import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.core.deps import get_db, require_role
from backend.app.models.user import User
from backend.app.schemas.camera import (
    CameraCreate,
    CameraListResponse,
    CameraResponse,
    CameraTestResponse,
    CameraUpdate,
)
from backend.app.services.camera_service import CameraService


router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=CameraListResponse)
async def list_cameras(
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> CameraListResponse:
    """List all registered cameras."""
    return CameraService(db).list_cameras()


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_camera(
    request: Request,
    payload: CameraCreate,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> CameraResponse:
    """Create a new camera."""
    client_ip = request.client.host if request.client else "unknown"

    return CameraService(db).create_camera(
        payload,
        actor=current_user,
        client_ip=client_ip,
    )


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> CameraResponse:
    """Get a single camera."""
    return CameraService(db).get_camera(camera_id)


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    request: Request,
    camera_id: uuid.UUID,
    payload: CameraUpdate,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> CameraResponse:
    """Update camera configuration."""
    client_ip = request.client.host if request.client else "unknown"

    return CameraService(db).update_camera(
        camera_id,
        payload,
        actor=current_user,
        client_ip=client_ip,
    )


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    request: Request,
    camera_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> Response:
    """
    Delete a camera when unused.
    Referenced cameras are disabled instead of hard-deleted.
    """
    client_ip = request.client.host if request.client else "unknown"

    CameraService(db).delete_camera(
        camera_id,
        actor=current_user,
        client_ip=client_ip,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{camera_id}/test", response_model=CameraTestResponse)
async def test_camera(
    camera_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> CameraTestResponse:
    """Test camera connectivity without changing persistent configuration."""
    return CameraService(db).test_connection(camera_id)
