"""
Tests for health check endpoints, security headers, CORS, and settings validation.
"""
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import Settings


@pytest.fixture
def client():
    return TestClient(app)


def test_health_returns_200(client):
    """GET /api/v1/health returns 200 with status ok, version, and env."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "env" in data


def test_health_db_connected(client):
    """GET /api/v1/health/db returns 200 when database is available."""
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"


def test_health_db_disconnected(client):
    """GET /api/v1/health/db returns 503 generic error when database is down."""
    with patch("backend.app.api.v1.health.engine.connect", side_effect=Exception("Connection refused")):
        response = client.get("/api/v1/health/db")
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Database is currently unavailable" in data["error"]["message"]
        # Ensure no internal error strings or host details leaked
        assert "Connection refused" not in response.text


def test_security_headers_present(client):
    """Verify security headers and request ID are added to responses."""
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
    assert "X-Request-ID" in response.headers


def test_request_id_passthrough(client):
    """Client-provided X-Request-ID should be preserved in response."""
    custom_id = "test-req-12345"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("X-Request-ID") == custom_id


def test_cors_origins():
    """Allowed origin gets CORS header; unauthorized origin does not."""
    client = TestClient(app)

    # Allowed origin: http://localhost:8501
    res_allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:8501"})
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:8501"

    # Disallowed origin: http://malicious-site.com
    res_disallowed = client.get("/api/v1/health", headers={"Origin": "http://malicious-site.com"})
    assert res_disallowed.headers.get("access-control-allow-origin") != "http://malicious-site.com"


def test_settings_fail_fast_on_default_secret_in_production():
    """Settings must fail fast if SECRET_KEY is default in production/staging."""
    with pytest.raises(ValueError, match="SECRET_KEY must be changed"):
        Settings(
            app_env="production",
            secret_key="CHANGE_ME",
        )

    with pytest.raises(ValueError, match="SECRET_KEY must be changed"):
        Settings(
            app_env="staging",
            secret_key="change_this_to_a_secure_random_string_in_production",
        )

    # In development, default secret is accepted
    dev_settings = Settings(
        app_env="development",
        secret_key="CHANGE_ME",
    )
    assert dev_settings.secret_key == "CHANGE_ME"
