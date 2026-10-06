"""
Comprehensive unit tests for image validation, quality metrics, and safe decoding.
Uses purely synthetic generated images (numpy/OpenCV) — NO real face data committed.
"""
import cv2
import numpy as np

from backend.app.vision.image_io import (
    MAX_UPLOAD_BYTES,
    detect_image_format,
    safe_decode_image,
)
from backend.app.vision.preprocess import (
    apply_optional_preprocessing,
    validate_image_quality,
)


def test_random_bytes_returns_invalid_image():
    """Arbitrary random bytes fail magic-byte verification and return INVALID_IMAGE."""
    random_junk = b"this is not an image at all but random ascii junk"
    ok, reason, img = safe_decode_image(random_junk)
    assert ok is False
    assert reason == "INVALID_IMAGE"
    assert img is None


def test_png_disguised_handled_by_magic_bytes():
    """A valid PNG encoded array is recognized by magic bytes, regardless of filename extension."""
    synthetic_arr = np.zeros((300, 300, 3), dtype=np.uint8)
    synthetic_arr[:, :] = [120, 120, 120]  # Mid-gray
    ret, png_bytes = cv2.imencode(".png", synthetic_arr)
    assert ret is True

    # Magic byte check
    fmt = detect_image_format(png_bytes.tobytes())
    assert fmt == "png"

    ok, reason, img = safe_decode_image(png_bytes.tobytes())
    assert ok is True
    assert reason == "png"
    assert img is not None
    assert img.shape == (300, 300, 3)


def test_small_image_returns_too_small():
    """Image below min_side (e.g. 50x50) returns TOO_SMALL."""
    small_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
    res = validate_image_quality(small_img, min_side=240)
    assert res.ok is False
    assert res.reason == "TOO_SMALL"


def test_gaussian_blurred_image_returns_too_blurry():
    """Gaussian-blurred smooth image fails sharpness check; sharp noise image passes."""
    # 1. Very blurry image
    smooth = np.ones((300, 300, 3), dtype=np.uint8) * 128
    blurred = cv2.GaussianBlur(smooth, (51, 51), 0)
    res_blur = validate_image_quality(blurred, min_blur=60.0)
    assert res_blur.ok is False
    assert res_blur.reason == "TOO_BLURRY"

    # 2. Sharp high-frequency noise image
    np.random.seed(42)
    sharp_noise = np.random.randint(50, 200, (300, 300, 3), dtype=np.uint8)
    res_sharp = validate_image_quality(sharp_noise, min_blur=60.0)
    assert res_sharp.ok is True
    assert res_sharp.reason is None
    assert res_sharp.metrics.blur_score > 60.0


def test_black_image_returns_too_dark_and_white_returns_too_bright():
    """Completely black frame returns TOO_DARK; pure white frame returns TOO_BRIGHT."""
    # Black
    black = np.zeros((300, 300, 3), dtype=np.uint8)
    res_dark = validate_image_quality(black, min_brightness=40.0)
    assert res_dark.ok is False
    assert res_dark.reason == "TOO_DARK"

    # White
    white = np.ones((300, 300, 3), dtype=np.uint8) * 255
    res_bright = validate_image_quality(white, max_brightness=220.0)
    assert res_bright.ok is False
    assert res_bright.reason == "TOO_BRIGHT"


def test_oversized_upload_rejected():
    """Upload exceeding MAX_UPLOAD_BYTES is rejected immediately."""
    oversized = b"\xff\xd8\xff" + b"0" * (MAX_UPLOAD_BYTES + 100)
    ok, reason, img = safe_decode_image(oversized)
    assert ok is False
    assert reason == "OVERSIZED_IMAGE"
    assert img is None


def test_enhancements_off_by_default_no_pixel_change():
    """With default arguments (flags=False), array is untouched."""
    img = np.random.randint(60, 180, (300, 300, 3), dtype=np.uint8)
    processed = apply_optional_preprocessing(img, enable_clahe=False, enable_flip=False)
    assert np.array_equal(img, processed)


def test_clahe_on_preserves_shape():
    """When CLAHE is enabled, output shape and dtype remain identical."""
    img = np.random.randint(60, 180, (300, 300, 3), dtype=np.uint8)
    processed = apply_optional_preprocessing(img, enable_clahe=True, enable_flip=False)
    assert processed.shape == img.shape
    assert processed.dtype == img.dtype
