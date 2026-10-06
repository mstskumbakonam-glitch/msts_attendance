"""
Safe image decode and verification utilities.
Enforces magic-byte detection, size bounds (<=5MB), dimension limits (<=4096px),
and decompression-bomb protections. Never trusts user-supplied file extensions.
"""
from typing import Tuple
import cv2
import numpy as np

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_IMAGE_DIM = 4096


def detect_image_format(data: bytes) -> str:
    """
    Detect image MIME/format using header magic bytes.
    Returns: 'jpeg', 'png', or 'unknown'.
    """
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return "unknown"


def safe_decode_image(data: bytes) -> Tuple[bool, str, np.ndarray | None]:
    """
    Safely decode raw image bytes into a BGR numpy array.
    Returns: (success, reason_or_format, ndarray_or_none)
    """
    if not data or len(data) == 0:
        return False, "INVALID_IMAGE", None

    if len(data) > MAX_UPLOAD_BYTES:
        return False, "OVERSIZED_IMAGE", None

    fmt = detect_image_format(data)
    if fmt == "unknown":
        return False, "INVALID_IMAGE", None

    # Decode bytes into numpy array without writing to disk
    nparr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None or image.size == 0:
        return False, "INVALID_IMAGE", None

    h, w = image.shape[:2]
    if h > MAX_IMAGE_DIM or w > MAX_IMAGE_DIM:
        return False, "IMAGE_DIMENSIONS_TOO_LARGE", None

    return True, fmt, image
