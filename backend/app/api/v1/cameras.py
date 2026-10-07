"""
Camera management API endpoints.

After a change is committed, the matching CameraManager worker is started,
stopped or restarted. Worker calls never undo a committed change; failures are
logged by camera id only (never URLs or credentials) and the heartbeat status
reflects the outcome.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.app.cameras.manager import camera_manager
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

logger = logging.getLogger(__name__)

# Fields whose change requires an enabled camera's worker to reopen its source.
_SOURCE_FIELDS = ("source_type", "source_url", "credentials_ref")


async def _sync_worker(action: str, camera_id: uuid.UUID) -> None:
    """
    Run a CameraManager action (start_camera / stop_camera / restart_camera).

    Runs in a thread because stopping joins the worker thread (up to a few
    seconds) and must not block the event loop.
    """
    try:
        await run_in_threadpool(getattr(camera_manager, action), camera_id)
    except Exception:
        logger.exception(
            "Camera worker action %s failed for camera_id=%s", action, camera_id
        )


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

    camera = CameraService(db).create_camera(
        payload,
        actor=current_user,
        client_ip=client_ip,
    )

    if camera.enabled:
        await _sync_worker("start_camera", camera.id)

    return camera


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
    service = CameraService(db)

    before = service.get_camera(camera_id)
    after = service.update_camera(
        camera_id,
        payload,
        actor=current_user,
        client_ip=client_ip,
    )

    if not after.enabled:
        # Disabled (or still disabled): make sure no worker keeps running.
        await _sync_worker("stop_camera", camera_id)
    elif not before.enabled:
        # false -> true
        await _sync_worker("start_camera", camera_id)
    elif any(getattr(before, f) != getattr(after, f) for f in _SOURCE_FIELDS):
        # Enabled camera whose source changed: reopen with the new configuration.
        await _sync_worker("restart_camera", camera_id)

    return after


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

    # Whether the camera was deleted or disabled because it is referenced,
    # its worker must stop. stop_camera is a no-op when no worker is running.
    await _sync_worker("stop_camera", camera_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{camera_id}/test", response_model=CameraTestResponse)
async def test_camera(
    camera_id: uuid.UUID,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> CameraTestResponse:
    """Test camera connectivity without changing persistent configuration."""
    return CameraService(db).test_connection(camera_id)
