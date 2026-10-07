"""
Camera service layer.
Handles camera CRUD, validation, connection testing, and audit logging.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import cv2
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.cameras.credentials import build_authenticated_url, mask_url
from backend.app.cameras.rtsp import RtspSource
from backend.app.models.attendance import AttendanceRecord
from backend.app.models.camera import Camera
from backend.app.models.detection_event import DetectionEvent
from backend.app.models.security_alert import SecurityAlert
from backend.app.models.user import User
from backend.app.schemas.camera import (
    CameraCreate,
    CameraListResponse,
    CameraResponse,
    CameraTestResponse,
    CameraUpdate,
    _validate_source_configuration,
)
from backend.app.services.audit_service import create_audit_log


VIDEO_ROOT = Path("data/videos").resolve()


class CameraService:
    def __init__(self, db: Session):
        self.db = db

    def create_camera(
        self,
        data: CameraCreate,
        actor: User,
        client_ip: Optional[str] = None,
    ) -> CameraResponse:
        self._validate_source_path(data.source_type, data.source_url)

        existing = self.db.execute(
            select(Camera).where(Camera.name == data.name)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Camera with name '{data.name}' already exists",
            )

        camera = Camera(
            name=data.name,
            location=data.location,
            source_type=data.source_type,
            source_url=data.source_url,
            credentials_ref=data.credentials_ref,
            enabled=data.enabled,
            status="UNKNOWN" if data.enabled else "DISABLED",
        )

        self.db.add(camera)

        try:
            self.db.flush()

            create_audit_log(
                db=self.db,
                action="CAMERA_CREATE",
                entity_type="CAMERA",
                actor_user_id=actor.id,
                entity_id=str(camera.id),
                ip=client_ip,
                details={
                    "name": camera.name,
                    "location": camera.location,
                    "source_type": camera.source_type,
                    "source_url": mask_url(camera.source_url)
                    if camera.source_url
                    else None,
                    "credentials_ref": camera.credentials_ref,
                    "enabled": camera.enabled,
                },
            )

            self.db.commit()
            self.db.refresh(camera)

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Camera could not be created because the name already exists",
            )

        return self._to_response(camera)

    def list_cameras(self) -> CameraListResponse:
        cameras = self.db.execute(
            select(Camera).order_by(Camera.name.asc())
        ).scalars().all()

        return CameraListResponse(
            items=[self._to_response(camera) for camera in cameras],
            total=len(cameras),
        )

    def get_camera(self, camera_id: uuid.UUID) -> CameraResponse:
        camera = self._get_camera(camera_id)
        return self._to_response(camera)

    def update_camera(
        self,
        camera_id: uuid.UUID,
        data: CameraUpdate,
        actor: User,
        client_ip: Optional[str] = None,
    ) -> CameraResponse:
        camera = self._get_camera(camera_id)

        values = data.model_dump(exclude_unset=True)

        new_source_type = values.get("source_type", camera.source_type)
        new_source_url = values.get("source_url", camera.source_url)
        new_credentials_ref = values.get(
            "credentials_ref", camera.credentials_ref
        )

        try:
            _validate_source_configuration(
                new_source_type,
                new_source_url,
                new_credentials_ref,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        self._validate_source_path(new_source_type, new_source_url)

        if "name" in values and values["name"] != camera.name:
            existing = self.db.execute(
                select(Camera).where(
                    Camera.name == values["name"],
                    Camera.id != camera.id,
                )
            ).scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Camera with name '{values['name']}' already exists",
                )

        old_enabled = camera.enabled

        for field, value in values.items():
            setattr(camera, field, value)

        if not camera.enabled:
            camera.status = "DISABLED"
        elif not old_enabled and camera.enabled:
            camera.status = "UNKNOWN"
        elif camera.status == "DISABLED":
            camera.status = "UNKNOWN"

        create_audit_log(
            db=self.db,
            action="CAMERA_UPDATE",
            entity_type="CAMERA",
            actor_user_id=actor.id,
            entity_id=str(camera.id),
            ip=client_ip,
            details={
                key: (
                    mask_url(value)
                    if key == "source_url" and value
                    else value
                )
                for key, value in values.items()
                if key != "credentials_ref" or value is not None
            },
        )

        try:
            self.db.commit()
            self.db.refresh(camera)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Camera update conflicts with an existing camera",
            )

        return self._to_response(camera)

    def delete_camera(
        self,
        camera_id: uuid.UUID,
        actor: User,
        client_ip: Optional[str] = None,
    ) -> None:
        camera = self._get_camera(camera_id)

        referenced = any(
            [
                self.db.execute(
                    select(AttendanceRecord.id)
                    .where(AttendanceRecord.camera_id == camera.id)
                    .limit(1)
                ).scalar_one_or_none()
                is not None,
                self.db.execute(
                    select(DetectionEvent.id)
                    .where(DetectionEvent.camera_id == camera.id)
                    .limit(1)
                ).scalar_one_or_none()
                is not None,
                self.db.execute(
                    select(SecurityAlert.id)
                    .where(SecurityAlert.camera_id == camera.id)
                    .limit(1)
                ).scalar_one_or_none()
                is not None,
            ]
        )

        if referenced:
            camera.enabled = False
            camera.status = "DISABLED"

            create_audit_log(
                db=self.db,
                action="CAMERA_DISABLE",
                entity_type="CAMERA",
                actor_user_id=actor.id,
                entity_id=str(camera.id),
                ip=client_ip,
                details={"reason": "camera_is_referenced"},
            )

            self.db.commit()
            return

        self.db.delete(camera)

        create_audit_log(
            db=self.db,
            action="CAMERA_DELETE",
            entity_type="CAMERA",
            actor_user_id=actor.id,
            entity_id=str(camera.id),
            ip=client_ip,
        )

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

            camera.enabled = False
            camera.status = "DISABLED"

            create_audit_log(
                db=self.db,
                action="CAMERA_DISABLE",
                entity_type="CAMERA",
                actor_user_id=actor.id,
                entity_id=str(camera.id),
                ip=client_ip,
                details={"reason": "delete_conflict"},
            )

            self.db.commit()

    def test_connection(self, camera_id: uuid.UUID) -> CameraTestResponse:
        camera = self._get_camera(camera_id)

        if camera.source_type == "WEBCAM":
            return self._test_webcam(camera)

        if camera.source_type == "VIDEO_FILE":
            return self._test_video_file(camera)

        if camera.source_type == "RTSP":
            return self._test_rtsp(camera)

        return CameraTestResponse(
            ok=False,
            error="Unsupported camera source type",
        )

    def _test_webcam(self, camera: Camera) -> CameraTestResponse:
        try:
            index = int(camera.source_url or "0")
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)

            try:
                if not capture.isOpened():
                    return CameraTestResponse(
                        ok=False,
                        error="Could not open webcam",
                    )

                ok, frame = capture.read()

                if not ok or frame is None:
                    return CameraTestResponse(
                        ok=False,
                        error="Webcam opened but no frame was received",
                    )

                return CameraTestResponse(
                    ok=True,
                    width=int(frame.shape[1]),
                    height=int(frame.shape[0]),
                    fps=float(capture.get(cv2.CAP_PROP_FPS) or 0.0) or None,
                )
            finally:
                capture.release()

        except Exception:
            return CameraTestResponse(
                ok=False,
                error="Webcam connection test failed",
            )

    def _test_video_file(self, camera: Camera) -> CameraTestResponse:
        try:
            path = self._resolve_video_path(camera.source_url)

            if path is None or not path.is_file():
                return CameraTestResponse(
                    ok=False,
                    error="Video file not found",
                )

            capture = cv2.VideoCapture(str(path))

            try:
                if not capture.isOpened():
                    return CameraTestResponse(
                        ok=False,
                        error="Could not open video file",
                    )

                ok, frame = capture.read()

                if not ok or frame is None:
                    return CameraTestResponse(
                        ok=False,
                        error="Video file opened but no frame was received",
                    )

                return CameraTestResponse(
                    ok=True,
                    width=int(frame.shape[1]),
                    height=int(frame.shape[0]),
                    fps=float(capture.get(cv2.CAP_PROP_FPS) or 0.0) or None,
                )
            finally:
                capture.release()

        except Exception:
            return CameraTestResponse(
                ok=False,
                error="Video connection test failed",
            )

    def _test_rtsp(self, camera: Camera) -> CameraTestResponse:
        try:
            source = RtspSource(
                source_url=camera.source_url or "",
                credentials_ref=camera.credentials_ref or "",
            )

            try:
                if not source.open():
                    return CameraTestResponse(
                        ok=False,
                        error="Could not open RTSP stream",
                    )

                frame = source.read_frame()

                if frame is None:
                    return CameraTestResponse(
                        ok=False,
                        error="RTSP stream opened but no frame was received",
                    )

                return CameraTestResponse(
                    ok=True,
                    width=int(frame.shape[1]),
                    height=int(frame.shape[0]),
                )
            finally:
                source.release()

        except Exception:
            return CameraTestResponse(
                ok=False,
                error="RTSP connection test failed",
            )

    def _get_camera(self, camera_id: uuid.UUID) -> Camera:
        camera = self.db.get(Camera, camera_id)

        if camera is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera with id '{camera_id}' not found",
            )

        return camera

    def _to_response(self, camera: Camera) -> CameraResponse:
        source_url = camera.source_url

        if source_url and camera.source_type == "RTSP":
            source_url = mask_url(source_url)

        return CameraResponse(
            id=camera.id,
            name=camera.name,
            location=camera.location,
            source_type=camera.source_type,
            source_url=source_url,
            credentials_ref=camera.credentials_ref,
            enabled=camera.enabled,
            status=camera.status,
            last_seen_at=camera.last_seen_at,
            created_at=camera.created_at,
            updated_at=camera.updated_at,
        )

    @staticmethod
    def _resolve_video_path(source_url: Optional[str]) -> Optional[Path]:
        if not source_url:
            return None

        candidate = Path(source_url)

        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (VIDEO_ROOT / candidate).resolve()

        try:
            resolved.relative_to(VIDEO_ROOT)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Video path must stay inside data/videos",
            )

        return resolved

    @classmethod
    def _validate_source_path(
        cls,
        source_type: str,
        source_url: Optional[str],
    ) -> None:
        if source_type == "VIDEO_FILE":
            cls._resolve_video_path(source_url)
