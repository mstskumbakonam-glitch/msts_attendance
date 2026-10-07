"""
API v1 Central Router
Aggregates all v1 endpoints under /api/v1.
"""
from fastapi import APIRouter

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.blacklist import router as blacklist_router
from backend.app.api.v1.cameras import router as cameras_router
from backend.app.api.v1.face import router as face_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.stream import router as stream_router
from backend.app.api.v1.students import router as students_router

api_v1_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(blacklist_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(face_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(stream_router)
api_v1_router.include_router(cameras_router)
