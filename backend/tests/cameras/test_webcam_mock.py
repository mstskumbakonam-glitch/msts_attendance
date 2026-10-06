"""
Unit tests for CameraSource abstraction and WebcamSource with mocked cv2.VideoCapture.
"""
from unittest.mock import MagicMock, patch
import numpy as np

from backend.app.cameras.source import CameraSource
from backend.app.cameras.webcam import WebcamSource


def test_camera_source_context_manager():
    """Ensure context manager opens and releases camera."""
    mock_cam = MagicMock(spec=CameraSource)
    mock_cam.open.return_value = True

    # Call concrete context methods
    CameraSource.__enter__(mock_cam)
    mock_cam.open.assert_called_once()

    CameraSource.__exit__(mock_cam, None, None, None)
    mock_cam.release.assert_called_once()


@patch("backend.app.cameras.webcam.cv2.VideoCapture")
def test_webcam_source_open_read_release(mock_video_capture):
    """WebcamSource opens hardware, reads frames, and releases correctly."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cap.read.return_value = (True, fake_frame)
    mock_video_capture.return_value = mock_cap

    cam = WebcamSource(camera_index=0, width=640, height=480, fps=30)
    assert not cam.is_open()

    opened = cam.open()
    assert opened is True
    assert cam.is_open() is True

    ret, frame = cam.read_frame()
    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)

    cam.release()
    assert not cam.is_open()
    mock_cap.release.assert_called_once()


@patch("backend.app.cameras.webcam.cv2.VideoCapture")
def test_webcam_source_open_failure(mock_video_capture):
    """WebcamSource handles camera unavailable gracefully."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_video_capture.return_value = mock_cap

    cam = WebcamSource(camera_index=99)
    assert cam.open() is False
    assert not cam.is_open()
    ret, frame = cam.read_frame()
    assert ret is False
    assert frame is None
