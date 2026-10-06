"""
Image validation and quality preprocessing for face pipeline.
Pure functions computing blur (Laplacian variance), brightness, minimum resolution,
and optional enhancements (CLAHE, augmentations - default OFF).
"""
from dataclasses import dataclass
from typing import Optional
import cv2
import numpy as np

# Configurable defaults
MIN_IMAGE_SIDE = 240
BLUR_MIN_LAPLACIAN = 60.0
BRIGHTNESS_MIN = 40.0
BRIGHTNESS_MAX = 220.0


@dataclass
class QualityMetrics:
    blur_score: float
    brightness: float
    width: int
    height: int


@dataclass
class ValidationResult:
    ok: bool
    reason: Optional[str] = None
    metrics: Optional[QualityMetrics] = None


def compute_blur_laplacian(image_bgr: np.ndarray) -> float:
    """Compute variance of the Laplacian of the grayscale image."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def compute_brightness(image_bgr: np.ndarray) -> float:
    """Compute average luminance/brightness in Y channel."""
    # Convert BGR to YCrCb or Grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def validate_image_quality(
    image: np.ndarray,
    min_side: int = MIN_IMAGE_SIDE,
    min_blur: float = BLUR_MIN_LAPLACIAN,
    min_brightness: float = BRIGHTNESS_MIN,
    max_brightness: float = BRIGHTNESS_MAX,
) -> ValidationResult:
    """
    Validate image resolution, sharpness, and illumination.
    Reasons: TOO_SMALL, TOO_BLURRY, TOO_DARK, TOO_BRIGHT.
    """
    if image is None or image.size == 0 or len(image.shape) < 2:
        return ValidationResult(ok=False, reason="INVALID_IMAGE")

    h, w = image.shape[:2]
    if h < min_side or w < min_side:
        return ValidationResult(
            ok=False,
            reason="TOO_SMALL",
            metrics=QualityMetrics(blur_score=0.0, brightness=0.0, width=w, height=h),
        )

    blur_score = compute_blur_laplacian(image)
    brightness = compute_brightness(image)
    metrics = QualityMetrics(blur_score=blur_score, brightness=brightness, width=w, height=h)

    if brightness < min_brightness:
        return ValidationResult(ok=False, reason="TOO_DARK", metrics=metrics)

    if brightness > max_brightness:
        return ValidationResult(ok=False, reason="TOO_BRIGHT", metrics=metrics)

    if blur_score < min_blur:
        return ValidationResult(ok=False, reason="TOO_BLURRY", metrics=metrics)

    return ValidationResult(ok=True, reason=None, metrics=metrics)


def apply_optional_preprocessing(
    image: np.ndarray,
    enable_clahe: bool = False,
    enable_flip: bool = False,
) -> np.ndarray:
    """
    Apply optional quality enhancements.
    Default OFF to preserve raw pixel data unless specifically enabled.
    """
    if not enable_clahe and not enable_flip:
        return image

    processed = image.copy()

    if enable_clahe:
        # Convert to LAB, apply CLAHE to L channel, convert back
        lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_chan)
        merged = cv2.merge((cl, a_chan, b_chan))
        processed = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    if enable_flip:
        processed = cv2.flip(processed, 1)

    return processed
