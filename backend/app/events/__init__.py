"""In-process application event layer."""
from backend.app.events.bus import EventBus, event_bus
from backend.app.events.types import FaceObserved, ObservationKind

__all__ = ["EventBus", "event_bus", "FaceObserved", "ObservationKind"]
