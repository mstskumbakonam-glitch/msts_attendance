"""Blacklist management API tests."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.models.audit_log import AuditLog
from backend.app.models.blacklist import BlacklistEntry
from backend.app.models.face_embedding import FaceEmbedding


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def payload(name="Test Identity"):
    return {
        "full_name": name,
        "reason": "Authorized security test identity",
        "category": "TEST",
        "severity": "CRITICAL",
        "notes": "Consent obtained for system testing",
    }


def test_create_get_update_search_deactivate(client, admin_token, db_session):
    created = client.post("/api/v1/blacklist", json=payload(), headers=headers(admin_token))
    assert created.status_code == 201
    data = created.json()
    assert data["full_name"] == "Test Identity"
    assert "embedding" not in data
    assert "face" not in data

    entry_id = data["id"]
    fetched = client.get(f"/api/v1/blacklist/{entry_id}", headers=headers(admin_token))
    assert fetched.status_code == 200

    updated = client.patch(
        f"/api/v1/blacklist/{entry_id}",
        json={"reason": "Updated reason", "severity": "HIGH"},
        headers=headers(admin_token),
    )
    assert updated.status_code == 200
    assert updated.json()["reason"] == "Updated reason"

    listed = client.get("/api/v1/blacklist?q=test identity", headers=headers(admin_token))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    deactivated = client.post(
        f"/api/v1/blacklist/{entry_id}/deactivate",
        headers=headers(admin_token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"

    audit_actions = db_session.execute(
        select(AuditLog.action).where(AuditLog.entity_id == entry_id)
    ).scalars().all()
    assert "BLACKLIST_CREATE" in audit_actions
    assert "BLACKLIST_UPDATE" in audit_actions
    assert "BLACKLIST_DEACTIVATE" in audit_actions


def test_operator_read_and_write_rbac(client, admin_token, operator_token):
    created = client.post("/api/v1/blacklist", json=payload("RBAC Person"), headers=headers(admin_token))
    assert created.status_code == 201
    entry_id = created.json()["id"]

    assert client.get("/api/v1/blacklist", headers=headers(operator_token)).status_code == 200
    assert client.patch(
        f"/api/v1/blacklist/{entry_id}",
        json={"reason": "no"},
        headers=headers(operator_token),
    ).status_code == 403
    assert client.post(
        f"/api/v1/blacklist/{entry_id}/deactivate",
        headers=headers(operator_token),
    ).status_code == 403
    assert client.post(
        "/api/v1/blacklist",
        json=payload("No Write"),
        headers=headers(operator_token),
    ).status_code == 403


def test_deactivate_disables_blacklist_embeddings(client, admin_token, db_session):
    created = client.post("/api/v1/blacklist", json=payload("Embedding Disable"), headers=headers(admin_token))
    entry_id = uuid.UUID(created.json()["id"])
    embedding = FaceEmbedding(
        blacklist_entry_id=entry_id,
        embedding=[0.0] * 512,
        model_name="test",
        model_version="test",
        is_active=True,
    )
    db_session.add(embedding)
    db_session.flush()

    response = client.post(
        f"/api/v1/blacklist/{entry_id}/deactivate",
        headers=headers(admin_token),
    )
    assert response.status_code == 200
    db_session.refresh(embedding)
    assert embedding.is_active is False
