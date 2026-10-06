"""
FastAPI Application Entrypoint
Application factory with request ID, security headers, CORS,
uniform error handling, and structured logging.
"""
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.v1.router import api_v1_router
from backend.app.core.config import Settings, get_settings
from slowapi.errors import RateLimitExceeded
from backend.app.core.rate_limit import limiter
from backend.app.core.errors import (
    http_exception_handler,
    rate_limit_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)

from backend.app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    if settings is None:
        settings = get_settings()

    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # -------------------------------------------------------------------------
    # Middleware: Request ID
    # -------------------------------------------------------------------------
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # -------------------------------------------------------------------------
    # Middleware: Security Headers
    # -------------------------------------------------------------------------
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    # -------------------------------------------------------------------------
    # Middleware: CORS
    # -------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Attach slowapi rate limiter
    app.state.limiter = limiter

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    app.include_router(api_v1_router)

    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect root to OpenAPI documentation."""
        return RedirectResponse(url="/docs")

    return app


app = create_app()
