"""
Tests for error handling, exception redaction, and logging security.
"""
import io
import json
import logging
import pytest
from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.core.logging import RedactingFilter, JsonFormatter


@pytest.fixture
def error_app_client():
    """Create test application with an endpoint that deliberately raises an unhandled exception."""
    test_router = APIRouter()

    @test_router.get("/test-500")
    async def raise_server_error():
        raise RuntimeError("Sensitive internal database traceback details!")

    @test_router.get("/test-404")
    async def raise_not_found():
        raise HTTPException(status_code=404, detail="Requested item does not exist")

    test_app = create_app()
    test_app.include_router(test_router)
    return TestClient(test_app, raise_server_exceptions=False)


def test_unhandled_exception_returns_500_without_traceback(error_app_client):
    """
    A deliberately raised exception returns 500 with uniform error body,
    contains request_id, and never leaks the exception message or Python traceback.
    """
    response = error_app_client.get("/test-500")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "An unexpected error occurred. Please try again later."
    assert "request_id" in data["error"]
    assert data["error"]["request_id"] is not None

    # Verify sensitive traceback strings are NEVER exposed
    assert "RuntimeError" not in response.text
    assert "Sensitive internal database traceback" not in response.text
    assert "Traceback" not in response.text


def test_http_exception_returns_uniform_error_body(error_app_client):
    """HTTPException returns uniform error body with proper code and message."""
    response = error_app_client.get("/test-404")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Requested item does not exist"
    assert "request_id" in data["error"]


def test_redacting_logger_masks_sensitive_keys():
    """Verify RedactingFilter masks sensitive dictionary fields."""
    filter_instance = RedactingFilter()
    formatter = JsonFormatter()

    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(formatter)
    handler.addFilter(filter_instance)

    logger = logging.getLogger("test_redaction")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    test_payload = {
        "event": "user_login",
        "username": "admin",
        "password": "SuperSecretPassword123!",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "embedding": [0.1, 0.2, 0.3],
        "safe_detail": "login_attempt",
    }

    # Log record with sensitive payload
    logger.info(test_payload)

    output = log_buffer.getvalue()
    assert output.strip() != ""
    log_data = json.loads(output.strip())

    # Check that message contains redacted fields
    msg = log_data.get("message")
    # Formatter might serialize dict in message or string representation
    if isinstance(msg, dict):
        assert msg["password"] == "[REDACTED]"
        assert msg["token"] == "[REDACTED]"
        assert msg["embedding"] == "[REDACTED]"
        assert msg["safe_detail"] == "login_attempt"
    else:
        assert "SuperSecretPassword123!" not in output
        assert "[REDACTED]" in output
