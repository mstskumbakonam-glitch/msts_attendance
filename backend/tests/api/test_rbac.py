"""
Tests for Role-Based Access Control (RBAC).
"""
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from backend.app.core.deps import require_role
from backend.app.main import create_app
from backend.app.models.user import User


@pytest.fixture
def rbac_client(db_session):
    """Create test application with role-guarded endpoints."""
    rbac_router = APIRouter()

    @rbac_router.get("/admin-only")
    async def admin_only_route(current_user: User = Depends(require_role("ADMIN"))):
        return {"access": "granted", "role": current_user.role}

    @rbac_router.get("/operator-or-admin")
    async def shared_route(current_user: User = Depends(require_role("ADMIN", "OPERATOR"))):
        return {"access": "granted", "role": current_user.role}

    app = create_app()
    app.include_router(rbac_router)

    from backend.app.core.deps import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_admin_can_access_admin_only_route(rbac_client, admin_token):
    """ADMIN role accessing ADMIN-only route returns 200."""
    res = rbac_client.get("/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["role"] == "ADMIN"


def test_operator_forbidden_from_admin_only_route(rbac_client, operator_token):
    """OPERATOR role accessing ADMIN-only route returns 403 Forbidden."""
    res = rbac_client.get("/admin-only", headers={"Authorization": f"Bearer {operator_token}"})
    assert res.status_code == 403
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "FORBIDDEN"
    assert "Forbidden" in data["error"]["message"]


def test_operator_and_admin_can_access_shared_route(rbac_client, admin_token, operator_token):
    """Both ADMIN and OPERATOR can access route with require_role('ADMIN', 'OPERATOR')."""
    res_admin = rbac_client.get("/operator-or-admin", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200

    res_op = rbac_client.get("/operator-or-admin", headers={"Authorization": f"Bearer {operator_token}"})
    assert res_op.status_code == 200


def test_unauthenticated_request_to_guarded_route_returns_401(rbac_client):
    """Unauthenticated request to guarded route returns 401."""
    res = rbac_client.get("/admin-only")
    assert res.status_code == 401
