"""
WebcamSource implementation using OpenCV VideoCapture.
Supports DirectShow backend on Windows (cv2.CAP_DSHOW) and thread-safe frame reading.
"""
import logging
import sys
import threading
from typing import Optional, Tuple
import cv2
import numpy as np

from backend.app.cameras.source import CameraSource

logger = logging.getLogger(__name__)


class WebcamSource(CameraSource):
    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()

    def open(self) -> bool:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return True

            logger.info("Opening webcam at index %s", self.camera_index)
            # Use CAP_DSHOW on Windows for fast opening
            if sys.platform.startswith("win"):
                cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(self.camera_index)

            if not cap.isOpened():
                # Fallback to default backend
                cap = cv2.VideoCapture(self.camera_index)

            if not cap.isOpened():
                logger.error("Failed to open camera index %s", self.camera_index)
                self._cap = None
                return False

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)

            self._cap = cap
            return True

    def is_open(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened()

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return False, None
            ret, frame = self._cap.read()
            if not ret or frame is None:
                return False, None
            return True, frame

    def release(self) -> None:
        with self._lock:
            if self._cap is not None:
                logger.info("Releasing camera index %s", self.camera_index)
                try:
                    self._cap.release()
                except Exception as e:
                    logger.warning("Error releasing camera: %s", e)
                finally:
                    self._cap = None
