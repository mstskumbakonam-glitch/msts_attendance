"""
Uniform error handling: error body schema, exception handlers.
No stack traces are ever returned to clients.
"""
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error response schema
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _error_body(
    code: str,
    message: str,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


# ---------------------------------------------------------------------------
# Exception handlers (registered on the app in main.py)
# ---------------------------------------------------------------------------

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log with request_id, return 500 without stack trace."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(
        "Unhandled exception",
        extra={"request_id": request_id, "path": str(request.url)},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
            request_id=request_id,
        ),
    )


async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """Convert HTTPException to uniform error body."""

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            code=_status_to_code(exc.status_code),
            message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            request_id=request_id,
        ),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """Convert RequestValidationError to 422 uniform body."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            request_id=request_id,
        ),
    )


async def rate_limit_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """Convert RateLimitExceeded to 429 uniform body."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=_error_body(
            code="RATE_LIMITED",
            message=f"Rate limit exceeded: {getattr(exc, 'detail', 'Too many requests')}",
            request_id=request_id,
        ),
    )



def _status_to_code(status_code: int) -> str:
    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        503: "SERVICE_UNAVAILABLE",
    }
    return codes.get(status_code, "ERROR")
