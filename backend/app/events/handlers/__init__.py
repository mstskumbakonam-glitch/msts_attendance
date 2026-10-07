"""Event handlers."""
from backend.app.events.handlers.attendance import AttendanceHandler
from backend.app.events.handlers.detection import DetectionHandler
from backend.app.events.handlers.security import SecurityHandler

__all__ = ["AttendanceHandler", "DetectionHandler", "SecurityHandler"]
