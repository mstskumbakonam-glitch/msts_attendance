"""
Health check router — /api/v1/health and /api/v1/health/db
"""
import logging
from typing import Any, Dict

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.db.session import engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health() -> Dict[str, Any]:
    """Basic liveness check — always returns 200 if the process is running."""
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
    }


@router.get("/db", status_code=status.HTTP_200_OK)
async def health_db() -> JSONResponse:
    """
    Readiness check — tests the database connection.
    Returns 200 with 'ok' if healthy, 503 with generic error if not.
    Never leaks connection details in the response body.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "db": "connected"},
        )
    except Exception:  # noqa: BLE001
        logger.error("Database health check failed", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Database is currently unavailable.",
                }
            },
        )
