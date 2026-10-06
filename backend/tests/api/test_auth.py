from datetime import timedelta
import pytest
import jwt
from sqlalchemy import select

from backend.app.core.rate_limit import reset_limiter
from backend.app.core.security import create_access_token
from backend.app.models.audit_log import AuditLog



@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset rate limiter before and after each test."""
    reset_limiter()
    yield
    reset_limiter()



def test_login_success(client, admin_user):
    """Correct credentials return 200, access_token, and token_type."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "AdminSecret123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # Ensure password is never in response
    assert "AdminSecret123!" not in res.text


def test_login_unknown_user_and_wrong_password_identical_response(client, admin_user):
    """Wrong password and unknown username return identical 401 error body."""
    # Unknown user
    res_unknown = client.post(
        "/api/v1/auth/login",
        json={"username": "non_existent_user_999", "password": "RandomPassword123!"},
    )
    assert res_unknown.status_code == 401
    err_unknown = res_unknown.json()["error"]

    # Wrong password for existing user
    res_wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "WrongPassword123!"},
    )
    assert res_wrong_pw.status_code == 401
    err_wrong_pw = res_wrong_pw.json()["error"]

    # Codes and messages must be strictly identical
    assert err_unknown["code"] == err_wrong_pw["code"] == "UNAUTHORIZED"
    assert err_unknown["message"] == err_wrong_pw["message"] == "Invalid username or password"


def test_login_rate_limiting(client):
    """6th login attempt within a minute returns 429 RATE_LIMITED."""
    # Use distinct dummy client or loop
    status_codes = []
    for _ in range(6):
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "rate_limit_test", "password": "Password123456!"},
        )
        status_codes.append(res.status_code)

    assert 429 in status_codes
    assert status_codes[-1] == 429


def test_auth_me_valid_token(client, admin_token, admin_user):
    """GET /api/v1/auth/me with valid Bearer token returns user profile."""
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == admin_user.username
    assert data["role"] == admin_user.role
    assert "password" not in data
    assert "password_hash" not in data


def test_auth_no_token(client):
    """Request without token returns 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_auth_garbage_token(client):
    """Request with malformed token returns 401."""
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_auth_expired_token(client, admin_user):
    """Request with expired token returns 401."""
    expired_token, _, _ = create_access_token(
        data={"sub": str(admin_user.id), "username": admin_user.username, "role": admin_user.role},
        expires_delta=timedelta(seconds=-10),
    )
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["error"]["message"].lower()


def test_auth_tampered_payload_or_alg_none(client, admin_user):
    """Token with alg=none or wrong signature is rejected with 401."""

    # Unsigned token with alg=none
    unsigned_token = jwt.encode(
        {"sub": str(admin_user.id), "username": admin_user.username, "role": admin_user.role, "exp": 9999999999, "iat": 1000000, "jti": "00000000-0000-0000-0000-000000000001"},
        key="",
        algorithm="none",
    )
    res_none = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {unsigned_token}"},
    )
    assert res_none.status_code == 401

    # Token signed with wrong secret
    tampered_token = jwt.encode(
        {"sub": str(admin_user.id), "username": admin_user.username, "role": admin_user.role, "exp": 9999999999, "iat": 1000000, "jti": "00000000-0000-0000-0000-000000000002"},
        key="wrong-secret-key-that-does-not-match",
        algorithm="HS256",
    )
    res_tampered = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res_tampered.status_code == 401


def test_logout_and_revocation(client, admin_user):
    """Logout invalidates the token so subsequent requests fail with 401."""
    # 1. Login to get fresh token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "AdminSecret123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Check /me works
    res_before = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_before.status_code == 200

    # 3. Call logout
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"

    # 4. Check /me now fails with 401 Token revoked
    res_after = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_after.status_code == 401
    assert "revoked" in res_after.json()["error"]["message"].lower()


def test_deactivated_user_token_rejected(client, db_session, admin_user):
    """A deactivated user's token is rejected with 401."""
    token, _, _ = create_access_token({"sub": str(admin_user.id), "username": admin_user.username, "role": admin_user.role})

    # Deactivate user
    admin_user.is_active = False
    db_session.flush()

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "deactivated" in res.json()["error"]["message"].lower()


def test_password_hash_stored_not_plaintext(admin_user):
    """Database contains Argon2 hash, never plaintext."""
    assert admin_user.password_hash.startswith("$argon2id$")
    assert "AdminSecret123!" not in admin_user.password_hash


def test_audit_logs_recorded(client, db_session, admin_user):
    """Audit logs are recorded for login success and failures without sensitive data."""
    # Success
    client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "AdminSecret123!"},
    )

    # Failure
    client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "WrongPassword!"},
    )

    logs = db_session.execute(
        select(AuditLog).where(AuditLog.entity_id.in_([str(admin_user.id), admin_user.username]))
    ).scalars().all()

    actions = [log_entry.action for log_entry in logs]
    assert "LOGIN_SUCCESS" in actions
    assert "LOGIN_FAILED" in actions

    # Verify no plaintext passwords in any audit details
    for log_entry in logs:
        details_str = str(log_entry.details)
        assert "AdminSecret123!" not in details_str
        assert "WrongPassword!" not in details_str
