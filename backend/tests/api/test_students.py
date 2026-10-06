"""
Tests for Student Management endpoints (/api/v1/students).
"""
import uuid
from sqlalchemy import select
from backend.app.models.audit_log import AuditLog
from backend.app.models.student import Student


def test_create_student_admin_ok(client, admin_token, db_session):
    """Admin can create a new student successfully."""
    payload = {
        "student_id": "001",
        "name": "Alice Johnson",
        "department": "Computer Science",
        "year": 3,
        "consent": True,
        "consent_version": "v1.0",
    }
    res = client.post(
        "/api/v1/students",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["student_id"] == "001"
    assert data["name"] == "Alice Johnson"
    assert data["department"] == "Computer Science"
    assert data["year"] == 3
    assert data["status"] == "ACTIVE"
    assert data["consent_given_at"] is not None
    assert data["consent_version"] == "v1.0"
    assert data["face_registered"] is False
    assert data["sample_count"] == 0

    # Verify audit log was recorded
    logs = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "STUDENT_CREATE",
            AuditLog.entity_id == "001",
        )
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].entity_type == "STUDENT"


def test_create_student_duplicate_id_409(client, admin_token):
    """Creating student with existing student_id returns 409 Conflict."""
    payload = {
        "student_id": "002",
        "name": "Bob Smith",
        "department": "IT",
        "year": 2,
        "consent": False,
    }
    res1 = client.post(
        "/api/v1/students",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/students",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"


def test_create_student_validation_errors(client, admin_token):
    """Invalid year, empty name, or invalid student_id regex returns 422."""
    # Invalid year (>8)
    res = client.post(
        "/api/v1/students",
        json={"student_id": "003", "name": "Eve", "department": "EE", "year": 9},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422

    # Invalid student_id format (spaces or special characters)
    res = client.post(
        "/api/v1/students",
        json={"student_id": "003 invalid!", "name": "Eve", "department": "EE", "year": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422


def test_operator_cannot_create_or_edit_or_delete_403(client, operator_token, admin_token):
    """Operator cannot create, edit, or delete students; gets 403 Forbidden."""
    # Operator create -> 403
    res_create = client.post(
        "/api/v1/students",
        json={"student_id": "004", "name": "Charlie", "department": "ME", "year": 1},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res_create.status_code == 403
    assert res_create.json()["error"]["code"] == "FORBIDDEN"

    # Admin creates student first
    res_adm = client.post(
        "/api/v1/students",
        json={"student_id": "004", "name": "Charlie", "department": "ME", "year": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    student_uuid = res_adm.json()["id"]

    # Operator update -> 403
    res_update = client.patch(
        f"/api/v1/students/{student_uuid}",
        json={"name": "Charlie Updated"},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res_update.status_code == 403

    # Operator delete -> 403
    res_del = client.delete(
        f"/api/v1/students/{student_uuid}",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res_del.status_code == 403


def test_operator_and_admin_can_list_and_search_students(client, admin_token, operator_token):
    """Both admin and operator can list and filter students."""
    # Seed 2 students via admin
    client.post(
        "/api/v1/students",
        json={"student_id": "CSE-101", "name": "David Miller", "department": "CSE", "year": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    client.post(
        "/api/v1/students",
        json={"student_id": "ECE-201", "name": "Diana Ross", "department": "ECE", "year": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Operator lists all
    res_op = client.get("/api/v1/students", headers={"Authorization": f"Bearer {operator_token}"})
    assert res_op.status_code == 200
    data = res_op.json()
    assert data["total"] >= 2

    # Operator searches by name fragment
    res_search = client.get(
        "/api/v1/students?q=david",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res_search.status_code == 200
    items = res_search.json()["items"]
    assert any(s["student_id"] == "CSE-101" for s in items)

    # Filter by department
    res_dept = client.get(
        "/api/v1/students?department=ECE",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_dept.status_code == 200
    assert all(s["department"] == "ECE" for s in res_dept.json()["items"])


def test_pagination_limits(client, admin_token):
    """Page size > 100 is rejected with 422."""
    res = client.get(
        "/api/v1/students?size=101",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422


def test_student_deactivate_sets_inactive_keeps_row(client, admin_token, db_session):
    """Deleting a student soft-deactivates (status='INACTIVE') and retains DB row."""
    res_create = client.post(
        "/api/v1/students",
        json={"student_id": "DEL-01", "name": "To Delete", "department": "Civil", "year": 4},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    student_id = res_create.json()["id"]

    res_del = client.delete(
        f"/api/v1/students/{student_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_del.status_code == 204

    # Verify student is now INACTIVE in DB
    db_student = db_session.get(Student, uuid.UUID(student_id))
    assert db_student is not None
    assert db_student.status == "INACTIVE"

    # Verify audit log was recorded
    logs = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "STUDENT_DEACTIVATE",
            AuditLog.entity_id == "DEL-01",
        )
    ).scalars().all()
    assert len(logs) == 1
