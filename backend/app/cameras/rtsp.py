"""
RTSP camera source.

Credentials are resolved from credentials_ref and only injected into the
authenticated URL in memory. Full authenticated URLs must never be logged.
"""

import logging
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from backend.app.cameras.credentials import (
    build_authenticated_url,
    mask_url,
)
from backend.app.cameras.source import CameraSource

logger = logging.getLogger(__name__)


class RtspSource(CameraSource):
    def __init__(
        self,
        source_url: str,
        credentials_ref: str,
        open_timeout_ms: int = 5000,
        reconnect_max_seconds: int = 30,
        buffer_size: int = 1,
    ):
        self.source_url = source_url
        self.credentials_ref = credentials_ref
        self.open_timeout_ms = open_timeout_ms
        self.reconnect_max_seconds = reconnect_max_seconds
        self.buffer_size = buffer_size

        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.RLock()

        self._retry_delay = 1
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def _release_unlocked(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as exc:
                logger.warning("RTSP release failed: %s", exc)
            finally:
                self._cap = None

    def _connect_once(self) -> bool:
        authenticated_url = None

        try:
            authenticated_url = build_authenticated_url(
                self.source_url,
                self.credentials_ref,
            )

            logger.info(
                "Opening RTSP stream %s",
                mask_url(authenticated_url),
            )

            params = [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                float(self.open_timeout_ms),
                cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                float(self.open_timeout_ms),
                cv2.CAP_PROP_BUFFERSIZE,
                float(self.buffer_size),
            ]

            try:
                cap = cv2.VideoCapture(
                    authenticated_url,
                    cv2.CAP_FFMPEG,
                    params,
                )
            except (TypeError, cv2.error):
                # Compatibility fallback for OpenCV builds that do not
                # support the parameterized constructor.
                cap = cv2.VideoCapture(
                    authenticated_url,
                    cv2.CAP_FFMPEG,
                )

                if cap.isOpened():
                    cap.set(
                        cv2.CAP_PROP_BUFFERSIZE,
                        self.buffer_size,
                    )

            if not cap.isOpened():
                cap.release()
                self._last_error = "Failed to open RTSP stream"
                logger.error(
                    "Failed to open RTSP stream %s",
                    mask_url(authenticated_url),
                )
                return False

            self._cap = cap
            self._last_error = None
            self._retry_delay = 1

            logger.info(
                "RTSP stream connected %s",
                mask_url(authenticated_url),
            )
            return True

        except Exception as exc:
            self._last_error = str(exc)

            safe_url = (
                mask_url(authenticated_url)
                if authenticated_url
                else self.source_url
            )

            logger.error(
                "RTSP connection error for %s: %s",
                safe_url,
                exc,
            )

            self._release_unlocked()
            return False

    def open(self) -> bool:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return True

            if self._retry_delay > 1:
                delay = self._retry_delay
                logger.warning(
                    "Retrying RTSP connection in %s seconds",
                    delay,
                )
                time.sleep(delay)

            success = self._connect_once()

            if not success:
                self._retry_delay = min(
                    self._retry_delay * 2,
                    self.reconnect_max_seconds,
                )

            return success

    def is_open(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened()

    def read_frame(
        self,
    ) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                if not self.open():
                    return False, None

            ret, frame = self._cap.read()

            if ret and frame is not None:
                return True, frame

            logger.warning(
                "RTSP frame read failed for %s; reconnecting",
                mask_url(self.source_url),
            )

            self._release_unlocked()

            if not self.open():
                return False, None

            ret, frame = self._cap.read()

            if not ret or frame is None:
                self._last_error = "RTSP frame read failed after reconnect"
                self._release_unlocked()
                return False, None

            return True, frame

    def release(self) -> None:
        with self._lock:
            logger.info(
                "Releasing RTSP stream %s",
                mask_url(self.source_url),
            )
            self._release_unlocked()