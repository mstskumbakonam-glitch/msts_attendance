"""
SQLAlchemy Models Package
Exports all 11 database models.
"""
from backend.app.models.user import User
from backend.app.models.revoked_token import RevokedToken
from backend.app.models.student import Student
from backend.app.models.blacklist import BlacklistEntry
from backend.app.models.face_embedding import FaceEmbedding
from backend.app.models.camera import Camera
from backend.app.models.attendance import AttendanceRecord
from backend.app.models.detection_event import DetectionEvent
from backend.app.models.security_alert import SecurityAlert
from backend.app.models.audit_log import AuditLog
from backend.app.models.system_setting import SystemSetting

__all__ = [
    "User",
    "RevokedToken",
    "Student",
    "BlacklistEntry",
    "FaceEmbedding",
    "Camera",
    "AttendanceRecord",
    "DetectionEvent",
    "SecurityAlert",
    "AuditLog",
    "SystemSetting",
]
