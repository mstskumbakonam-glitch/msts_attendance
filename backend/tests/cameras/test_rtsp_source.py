import logging
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.app.cameras.credentials import (
    build_authenticated_url,
    mask_url,
    reject_embedded_credentials,
)
from backend.app.cameras.rtsp import RtspSource


def test_embedded_credentials_rejected():
    with pytest.raises(ValueError, match="embedded credentials"):
        reject_embedded_credentials(
            "rtsp://user:password@192.168.1.59:554/Streaming/Channels/101"
        )


def test_mask_url_removes_credentials():
    url = "rtsp://user:password@192.168.1.59:554/Streaming/Channels/101"

    masked = mask_url(url)

    assert masked == "rtsp://192.168.1.59:554/Streaming/Channels/101"
    assert "user" not in masked
    assert "password" not in masked


def test_authenticated_url_is_built_from_credentials():
    with patch.dict(
        "os.environ",
        {"CAMERA_1_CREDENTIALS": "testuser:testpass"},
        clear=True,
    ):
        url = build_authenticated_url(
            "rtsp://192.168.1.59:554/Streaming/Channels/101",
            "CAMERA_1_CREDENTIALS",
        )

    assert "testuser:testpass@" in url
    assert "192.168.1.59:554" in url


@patch("backend.app.cameras.rtsp.cv2.VideoCapture")
def test_rtsp_open_success(mock_video_capture):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_video_capture.return_value = mock_cap

    cam = RtspSource(
        source_url="rtsp://192.168.1.59:554/Streaming/Channels/101",
        credentials_ref="CAMERA_1_CREDENTIALS",
    )

    with patch(
        "backend.app.cameras.rtsp.build_authenticated_url",
        return_value="rtsp://testuser:testpass@192.168.1.59:554/Streaming/Channels/101",
    ):
        assert cam.open() is True

    assert cam.is_open() is True


@patch("backend.app.cameras.rtsp.cv2.VideoCapture")
def test_rtsp_open_failure(mock_video_capture):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_video_capture.return_value = mock_cap

    cam = RtspSource(
        source_url="rtsp://192.168.1.59:554/Streaming/Channels/101",
        credentials_ref="CAMERA_1_CREDENTIALS",
    )

    with patch(
        "backend.app.cameras.rtsp.build_authenticated_url",
        return_value="rtsp://testuser:testpass@192.168.1.59:554/Streaming/Channels/101",
    ):
        assert cam.open() is False

    assert cam.is_open() is False
    assert cam.last_error == "Failed to open RTSP stream"


@patch("backend.app.cameras.rtsp.cv2.VideoCapture")
def test_rtsp_read_success(mock_video_capture):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (
        True,
        np.zeros((480, 640, 3), dtype=np.uint8),
    )
    mock_video_capture.return_value = mock_cap

    cam = RtspSource(
        source_url="rtsp://192.168.1.59:554/Streaming/Channels/101",
        credentials_ref="CAMERA_1_CREDENTIALS",
    )

    with patch(
        "backend.app.cameras.rtsp.build_authenticated_url",
        return_value="rtsp://testuser:testpass@192.168.1.59:554/Streaming/Channels/101",
    ):
        assert cam.open() is True
        ret, frame = cam.read_frame()

    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)


def test_missing_credentials_fails_cleanly():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="not set"):
            build_authenticated_url(
                "rtsp://192.168.1.59:554/Streaming/Channels/101",
                "CAMERA_DOES_NOT_EXIST",
            )


def test_masked_url_never_contains_password(caplog):
    caplog.set_level(logging.INFO)

    safe_url = mask_url(
        "rtsp://user:secret123@192.168.1.59:554/Streaming/Channels/101"
    )

    assert "secret123" not in safe_url
    assert "user" not in safe_url

@patch("backend.app.cameras.rtsp.cv2.VideoCapture")
def test_rtsp_reconnect_after_read_failure(mock_video_capture):
    first_cap = MagicMock()
    first_cap.isOpened.return_value = True
    first_cap.read.return_value = (False, None)

    second_cap = MagicMock()
    second_cap.isOpened.return_value = True
    second_cap.read.return_value = (
        True,
        np.zeros((480, 640, 3), dtype=np.uint8),
    )

    mock_video_capture.side_effect = [first_cap, second_cap]

    cam = RtspSource(
        source_url="rtsp://192.168.1.59:554/Streaming/Channels/101",
        credentials_ref="CAMERA_1_CREDENTIALS",
    )

    with patch(
        "backend.app.cameras.rtsp.build_authenticated_url",
        return_value="rtsp://testuser:testpass@192.168.1.59:554/Streaming/Channels/101",
    ):
        assert cam.open() is True

        ret, frame = cam.read_frame()

    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    assert mock_video_capture.call_count == 2
    first_cap.release.assert_called_once()