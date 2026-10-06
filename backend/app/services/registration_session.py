"""
In-memory store for face registration sessions and stream preview tickets.
Enforces TTL expiration, single active session per camera, and raw image minimization (ADR-11).
"""
import secrets
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
import numpy as np

# Guided pose prompts for registration
POSE_PROMPTS = [
    "Look directly at the camera (Frontal view)",
    "Slightly turn head to the left",
    "Slightly turn head to the right",
    "Tilt head slightly upward",
    "Tilt head slightly downward",
    "Smile naturally",
    "Neutral expression",
    "Slight head tilt to the left shoulder",
    "Slight head tilt to the right shoulder",
]


class RegistrationSession:
    def __init__(
        self,
        session_id: str,
        student_uuid: uuid.UUID,
        student_id: str,
        camera_id: str,
        target_samples: int = 30,
        ttl_seconds: int = 600,
    ):
        self.session_id = session_id
        self.student_uuid = student_uuid
        self.student_id = student_id
        self.camera_id = camera_id
        self.target_samples = target_samples
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.frames: List[np.ndarray] = []
        self.lock = threading.Lock()

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def add_frame(self, frame: np.ndarray) -> int:
        with self.lock:
            self.frames.append(frame)
            return len(self.frames)

    def current_prompt(self) -> str:
        with self.lock:
            idx = len(self.frames) % len(POSE_PROMPTS)
            return POSE_PROMPTS[idx]

    def clear(self) -> None:
        with self.lock:
            self.frames.clear()


class RegistrationSessionManager:
    _instance: Optional["RegistrationSessionManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._sessions: Dict[str, RegistrationSession] = {}
                cls._instance._tickets: Dict[str, Dict[str, Any]] = {}
                cls._instance._active_cameras: Dict[str, str] = {}  # camera_id -> session_id
                cls._instance._lock = threading.Lock()
        return cls._instance

    def _cleanup_expired(self) -> None:
        now = time.time()
        # Clean sessions
        expired_sessions = [
            sid for sid, s in self._sessions.items() if s.is_expired()
        ]
        for sid in expired_sessions:
            s = self._sessions.pop(sid, None)
            if s:
                s.clear()
                if self._active_cameras.get(s.camera_id) == sid:
                    self._active_cameras.pop(s.camera_id, None)

        # Clean tickets
        expired_tickets = [
            t for t, data in self._tickets.items() if data["expires_at"] < now
        ]
        for t in expired_tickets:
            self._tickets.pop(t, None)

    def create_session(
        self,
        student_uuid: uuid.UUID,
        student_id: str,
        camera_id: str = "0",
        target_samples: int = 30,
        ttl_seconds: int = 600,
    ) -> RegistrationSession:
        with self._lock:
            self._cleanup_expired()
            # Check if camera is currently in use
            if camera_id in self._active_cameras:
                existing_sid = self._active_cameras[camera_id]
                existing_session = self._sessions.get(existing_sid)
                if existing_session and not existing_session.is_expired():
                    raise ValueError(f"Camera '{camera_id}' is already in use by session {existing_sid}")

            session_id = secrets.token_hex(16)
            session = RegistrationSession(
                session_id=session_id,
                student_uuid=student_uuid,
                student_id=student_id,
                camera_id=camera_id,
                target_samples=target_samples,
                ttl_seconds=ttl_seconds,
            )
            self._sessions[session_id] = session
            self._active_cameras[camera_id] = session_id
            return session

    def get_session(self, session_id: str) -> Optional[RegistrationSession]:
        with self._lock:
            self._cleanup_expired()
            session = self._sessions.get(session_id)
            if session and session.is_expired():
                session.clear()
                self._sessions.pop(session_id, None)
                self._active_cameras.pop(session.camera_id, None)
                return None
            return session

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.clear()
                if self._active_cameras.get(session.camera_id) == session_id:
                    self._active_cameras.pop(session.camera_id, None)

    def create_stream_ticket(self, camera_id: str, user_id: str, ttl_seconds: int = 60) -> str:
        with self._lock:
            self._cleanup_expired()
            ticket = secrets.token_hex(32)
            self._tickets[ticket] = {
                "camera_id": str(camera_id),
                "user_id": str(user_id),
                "expires_at": time.time() + ttl_seconds,
            }
            return ticket

    def validate_stream_ticket(self, ticket: str, camera_id: str) -> bool:
        with self._lock:
            self._cleanup_expired()
            ticket_data = self._tickets.get(ticket)
            if not ticket_data:
                return False
            if ticket_data["camera_id"] != str(camera_id):
                return False
            if ticket_data["expires_at"] < time.time():
                self._tickets.pop(ticket, None)
                return False
            return True


session_manager = RegistrationSessionManager()
