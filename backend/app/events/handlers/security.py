"""Security consumer for FaceObserved events.

Alert policy is intentionally kept for the dedicated security-alert phase;
this handler provides the event-layer extension point without inventing a new
policy here.
"""
from __future__ import annotations

import logging

from backend.app.events.types import FaceObserved, ObservationKind

logger = logging.getLogger(__name__)


class SecurityHandler:
    def __call__(self, event: FaceObserved) -> None:
        if event.kind in (ObservationKind.UNKNOWN, ObservationKind.BLACKLISTED):
            logger.info(
                "Security observation received camera_id=%s kind=%s track_id=%s",
                event.camera_id,
                event.kind.value,
                event.track_id,
            )
