"""
Camera worker manager.

Starts camera workers for enabled cameras and maintains
ONLINE/OFFLINE/ERROR status plus last_seen_at heartbeat.
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

import cv2

from backend.app.cameras.rtsp import RtspSource
from backend.app.cameras.webcam import WebcamSource
from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.models.camera import Camera


logger = logging.getLogger(__name__)


class CameraManager:
    HEARTBEAT_SECONDS = 10.0
    RETRY_SECONDS = 2.0

    def __init__(self) -> None:
        self._workers: Dict[uuid.UUID, threading.Thread] = {}
        self._stop_events: Dict[uuid.UUID, threading.Event] = {}
        self._lock = threading.RLock()
        self._running = False

    def start(self) -> None:
        """Start manager and all enabled cameras."""
        with self._lock:
            if self._running:
                return

            self._running = True

        self.start_enabled_cameras()

    def stop(self) -> None:
        """Stop all camera workers."""
        with self._lock:
            self._running = False
            stop_events = list(self._stop_events.values())

        for event in stop_events:
            event.set()

        with self._lock:
            workers = list(self._workers.values())

        for worker in workers:
            worker.join(timeout=3)

        with self._lock:
            self._workers.clear()
            self._stop_events.clear()

    def start_enabled_cameras(self) -> None:
        """Read enabled cameras from DB and start missing workers."""
        db = SessionLocal()

        try:
            cameras = db.query(Camera).filter(Camera.enabled.is_(True)).all()

            for camera in cameras:
                self.start_camera(camera.id)
        finally:
            db.close()

    def start_camera(self, camera_id: uuid.UUID) -> bool:
        """Start a worker for one camera."""
        with self._lock:
            worker = self._workers.get(camera_id)

            if worker and worker.is_alive():
                return False

            stop_event = threading.Event()

            worker = threading.Thread(
                target=self._worker_loop,
                args=(camera_id, stop_event),
                daemon=True,
                name=f"camera-worker-{camera_id}",
            )

            self._stop_events[camera_id] = stop_event
            self._workers[camera_id] = worker

            worker.start()

        return True

    def stop_camera(self, camera_id: uuid.UUID) -> bool:
        """Stop one camera worker."""
        with self._lock:
            stop_event = self._stop_events.get(camera_id)
            worker = self._workers.get(camera_id)

        if stop_event is None:
            return False

        stop_event.set()

        if worker:
            worker.join(timeout=3)

        with self._lock:
            self._stop_events.pop(camera_id, None)
            self._workers.pop(camera_id, None)

        self._set_status(camera_id, "DISABLED", heartbeat=False)

        return True

    def is_running(self, camera_id: uuid.UUID) -> bool:
        """Return whether a camera worker is alive."""
        with self._lock:
            worker = self._workers.get(camera_id)
            return bool(worker and worker.is_alive())

    def worker_states(self) -> dict[str, str]:
        """Return worker state by camera UUID."""
        with self._lock:
            return {
                str(camera_id): (
                    "RUNNING" if worker.is_alive() else "STOPPED"
                )
                for camera_id, worker in self._workers.items()
            }

    def _worker_loop(
        self,
        camera_id: uuid.UUID,
        stop_event: threading.Event,
    ) -> None:
        source = None
        last_heartbeat = 0.0

        try:
            while not stop_event.is_set():
                camera = self._get_camera(camera_id)

                if camera is None:
                    break

                if not camera.enabled:
                    self._set_status(camera_id, "DISABLED", heartbeat=False)
                    break

                if source is None:
                    source = self._build_source(camera)

                if source is None:
                    self._set_status(camera_id, "ERROR", heartbeat=False)
                    stop_event.wait(self.RETRY_SECONDS)
                    continue

                try:
                    if not source.is_open():
                        opened = source.open()

                        if not opened:
                            self._set_status(
                                camera_id,
                                "ERROR",
                                heartbeat=False,
                            )
                            stop_event.wait(self.RETRY_SECONDS)
                            continue

                    frame = source.read_frame()

                    if frame is None:
                        self._set_status(
                            camera_id,
                            "ERROR",
                            heartbeat=False,
                        )

                        try:
                            source.release()
                        except Exception:
                            pass

                        source = None
                        stop_event.wait(self.RETRY_SECONDS)
                        continue

                    now = time.monotonic()

                    if now - last_heartbeat >= self.HEARTBEAT_SECONDS:
                        self._set_status(
                            camera_id,
                            "ONLINE",
                            heartbeat=True,
                        )
                        last_heartbeat = now

                except Exception:
                    logger.exception(
                        "Camera worker failed for camera_id=%s",
                        camera_id,
                    )

                    self._set_status(
                        camera_id,
                        "ERROR",
                        heartbeat=False,
                    )

                    try:
                        source.release()
                    except Exception:
                        pass

                    source = None
                    stop_event.wait(self.RETRY_SECONDS)

        finally:
            if source is not None:
                try:
                    source.release()
                except Exception:
                    pass

            with self._lock:
                self._workers.pop(camera_id, None)
                self._stop_events.pop(camera_id, None)

    def _build_source(self, camera: Camera):
        settings = get_settings()

        if camera.source_type == "WEBCAM":
            try:
                camera_index = int(camera.source_url or "0")
            except ValueError:
                return None

            return WebcamSource(camera_index)

        if camera.source_type == "RTSP":
            return RtspSource(
                source_url=camera.source_url or "",
                credentials_ref=camera.credentials_ref or "",
                open_timeout_ms=settings.rtsp_open_timeout_ms,
                reconnect_max_seconds=settings.rtsp_reconnect_max_seconds,
            )

        if camera.source_type == "VIDEO_FILE":
            return _VideoFileSource(camera.source_url or "")

        return None

    @staticmethod
    def _get_camera(camera_id: uuid.UUID) -> Optional[Camera]:
        db = SessionLocal()

        try:
            return db.get(Camera, camera_id)
        finally:
            db.close()

    @staticmethod
    def _set_status(
        camera_id: uuid.UUID,
        status: str,
        heartbeat: bool,
    ) -> None:
        db = SessionLocal()

        try:
            camera = db.get(Camera, camera_id)

            if camera is None:
                return

            camera.status = status

            if heartbeat and status == "ONLINE":
                camera.last_seen_at = datetime.now(timezone.utc)

            db.commit()

        except Exception:
            db.rollback()
            logger.exception(
                "Failed to update camera status for camera_id=%s",
                camera_id,
            )
        finally:
            db.close()


class _VideoFileSource:
    """Small OpenCV-backed source for local video files."""

    def __init__(self, source_url: str) -> None:
        self.source_url = source_url
        self.capture = None

    def open(self) -> bool:
        self.release()
        self.capture = cv2.VideoCapture(self.source_url)
        return bool(self.capture.isOpened())

    def is_open(self) -> bool:
        return bool(self.capture and self.capture.isOpened())

    def read_frame(self):
        if not self.capture:
            return None

        ok, frame = self.capture.read()

        if not ok:
            return None

        return frame

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()

        self.capture = None


camera_manager = CameraManager()
