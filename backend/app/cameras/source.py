"""
Abstract Camera Source interface.
Provides open, read, is_open, and release methods with resource cleanup guarantees.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np


class CameraSource(ABC):
    @abstractmethod
    def open(self) -> bool:
        """Open camera hardware / connection. Return True if successful."""
        pass

    @abstractmethod
    def is_open(self) -> bool:
        """Check if camera is currently opened."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read latest frame. Returns (success, frame_bgr)."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release underlying hardware handles and cleanup."""
        pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
