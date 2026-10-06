"""
API tests for face registration session, preview stream ticket, and biometric consent enforcement.
"""
import os
import time
import pytest

from backend.app.services.registration_session import session_manager


@pytest.fixture(autouse=True)
def clean_sessions():
    """Ensure in-memory sessions are wiped clean between tests."""
    with session_manager._lock:
        session_manager._sessions.clear()
        session_manager._tickets.clear()
        session_manager._active_cameras.clear()
    yield
    with session_manager._lock:
        session_manager._sessions.clear()
        session_manager._tickets.clear()
        session_manager._active_cameras.clear()


def test_session_creation_requires_consent_400(client, admin_token):
    """Creating a face registration session without student consent returns 400 Bad Request."""
    # Create student without consent
    res_student = client.post(
        "/api/v1/students",
        json={"student_id": "NO-CONSENT-01", "name": "No Consent", "department": "CSE", "year": 1, "consent": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    student_id = res_student.json()["id"]

    # Try creating face session
    res = client.post(
        f"/api/v1/students/{student_id}/face/session",
        json={"target_samples": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "consent" in res.json()["error"]["message"].lower()


def test_session_creation_with_consent_ok(client, admin_token):
    """Creating a face session for consented student returns 201 with session_id."""
    res_student = client.post(
        "/api/v1/students",
        json={"student_id": "CONSENT-01", "name": "Consented", "department": "CSE", "year": 1, "consent": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    student_id = res_student.json()["id"]

    res = client.post(
        f"/api/v1/students/{student_id}/face/session",
        json={"target_samples": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["target_samples"] == 30
    assert data["current_samples"] == 0


def test_two_concurrent_sessions_same_camera_returns_409(client, admin_token):
    """Two concurrent face registration sessions on camera 0 return 409 Conflict."""
    s1 = client.post(
        "/api/v1/students",
        json={"student_id": "CONC-01", "name": "Student 1", "department": "CSE", "year": 1, "consent": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["id"]
    s2 = client.post(
        "/api/v1/students",
        json={"student_id": "CONC-02", "name": "Student 2", "department": "CSE", "year": 1, "consent": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["id"]

    # First session on camera 0
    res1 = client.post(
        f"/api/v1/students/{s1}/face/session?camera_id=0",
        json={"target_samples": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res1.status_code == 201

    # Second session on camera 0 should conflict
    res2 = client.post(
        f"/api/v1/students/{s2}/face/session?camera_id=0",
        json={"target_samples": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res2.status_code == 409
    assert "in use" in res2.json()["error"]["message"].lower()


def test_stream_ticket_validation_and_expiry(client, admin_token):
    """Stream ticket generated expires and cannot access mismatched cameras."""
    # 1. Generate ticket for camera '0'
    res = client.post(
        "/api/v1/stream/ticket",
        json={"camera_id": "0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    ticket = res.json()["ticket"]

    # 2. Access stream without ticket -> 401
    res_no_ticket = client.get("/api/v1/stream/0")
    assert res_no_ticket.status_code == 422 or res_no_ticket.status_code == 401

    # 3. Access stream with ticket for wrong camera -> 401
    res_wrong_cam = client.get(f"/api/v1/stream/1?ticket={ticket}")
    assert res_wrong_cam.status_code == 401

    # 4. Invalidate / expire ticket
    with session_manager._lock:
        session_manager._tickets[ticket]["expires_at"] = time.time() - 10

    res_expired = client.get(f"/api/v1/stream/0?ticket={ticket}")
    assert res_expired.status_code == 401


def test_session_cancel_releases_camera_and_no_data_files(client, admin_token):
    """Session cancellation drops frames and writes no files to disk."""
    s1 = client.post(
        "/api/v1/students",
        json={"student_id": "CANCEL-01", "name": "Student Cancel", "department": "CSE", "year": 1, "consent": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["id"]

    res_sess = client.post(
        f"/api/v1/students/{s1}/face/session",
        json={"target_samples": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    session_id = res_sess.json()["session_id"]

    # Cancel session
    res_cancel = client.delete(
        f"/api/v1/students/{s1}/face/session/{session_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_cancel.status_code == 204

    # Ensure session is deleted from memory
    assert session_manager.get_session(session_id) is None

    # Assert no files written under data/ (ADR-11)
    if os.path.exists("data"):
        data_files = [f for _, _, files in os.walk("data") for f in files if f.endswith((".jpg", ".png", ".bin"))]
        assert len(data_files) == 0
