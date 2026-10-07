"""Detection/movement consumer for FaceObserved events."""
from __future__ import annotations

import logging
import threading
import time

from backend.app.db.session import SessionLocal
from backend.app.events.types import FaceObserved, ObservationKind
from backend.app.models.detection_event import DetectionEvent

logger = logging.getLogger(__name__)

_EVENT_TYPE = {
    ObservationKind.STUDENT: "RECOGNIZED",
    ObservationKind.UNKNOWN: "UNKNOWN",
    ObservationKind.BLACKLISTED: "BLACKLISTED",
}


class DetectionHandler:
    """Persist raw sightings with a small in-memory per-track throttle."""

    def __init__(self, throttle_seconds: float = 1.0) -> None:
        self.throttle_seconds = max(0.0, throttle_seconds)
        self._last_seen: dict[tuple[str, str], float] = {}
        self._lock = threading.Lock()

    def __call__(self, event: FaceObserved) -> None:
        key = (
            str(event.camera_id),
            event.track_id or str(event.student_id or event.blacklist_id or event.kind.value),
        )
        now = time.monotonic()
        with self._lock:
            last = self._last_seen.get(key)
            if last is not None and now - last < self.throttle_seconds:
                return
            self._last_seen[key] = now

        db = SessionLocal()
        try:
            db.add(
                DetectionEvent(
                    occurred_at=event.occurred_at,
                    camera_id=event.camera_id,
                    event_type=_EVENT_TYPE[event.kind],
                    student_id=event.student_id,
                    blacklist_entry_id=event.blacklist_id,
                    similarity=event.similarity,
                    bbox=list(event.bbox) if event.bbox is not None else None,
                    track_id=event.track_id,
                    snapshot_path=event.snapshot_path,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Detection handler failed for camera_id=%s", event.camera_id)
        finally:
            db.close()
