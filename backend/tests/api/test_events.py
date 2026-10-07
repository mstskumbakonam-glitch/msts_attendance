import uuid
from datetime import datetime, timedelta, timezone

from backend.app.models.camera import Camera
from backend.app.models.detection_event import DetectionEvent
from backend.app.models.student import Student


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def seed_camera(db_session, suffix: str) -> Camera:
    camera = Camera(
        name=f"EVENT-CAM-{suffix}-{uuid.uuid4().hex[:6]}",
        location="Events Test",
        source_type="WEBCAM",
        source_url="0",
        enabled=False,
        status="DISABLED",
    )
    db_session.add(camera)
    db_session.flush()
    return camera


def seed_student(db_session, suffix: str) -> Student:
    student = Student(
        student_id=f"EVT-{suffix}-{uuid.uuid4().hex[:6]}",
        name="Event Test Student",
        department="CSE",
        year=3,
        status="ACTIVE",
    )
    db_session.add(student)
    db_session.flush()
    return student


def add_event(
    db_session,
    camera_id,
    event_type,
    occurred_at,
    student_id=None,
):
    event = DetectionEvent(
        occurred_at=occurred_at,
        camera_id=camera_id,
        event_type=event_type,
        student_id=student_id,
        similarity=0.91 if student_id else None,
        bbox=[10, 20, 100, 120],
        track_id="track-1",
    )
    db_session.add(event)
    db_session.flush()
    return event


def test_events_filter_by_camera(client, admin_token, db_session):
    cam1 = seed_camera(db_session, "A")
    cam2 = seed_camera(db_session, "B")
    now = datetime.now(timezone.utc)

    add_event(db_session, cam1.id, "UNKNOWN", now)
    add_event(db_session, cam2.id, "UNKNOWN", now)

    response = client.get(
        f"/api/v1/events?camera_id={cam1.id}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["camera_id"] == str(cam1.id)


def test_events_filter_by_type(client, admin_token, db_session):
    camera = seed_camera(db_session, "TYPE")
    now = datetime.now(timezone.utc)

    add_event(db_session, camera.id, "UNKNOWN", now)
    add_event(db_session, camera.id, "BLACKLISTED", now + timedelta(seconds=1))

    response = client.get(
        "/api/v1/events?event_type=BLACKLISTED",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "BLACKLISTED"


def test_events_filter_by_student(client, admin_token, db_session):
    camera = seed_camera(db_session, "STUDENT")
    student = seed_student(db_session, "S")
    now = datetime.now(timezone.utc)

    add_event(db_session, camera.id, "RECOGNIZED", now, student.id)
    add_event(db_session, camera.id, "UNKNOWN", now + timedelta(seconds=1))

    response = client.get(
        f"/api/v1/events?student_id={student.id}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["student_id"] == str(student.id)


def test_events_filter_by_date(client, admin_token, db_session):
    camera = seed_camera(db_session, "DATE")
    today = datetime.now(timezone.utc).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    yesterday = today - timedelta(days=1)

    add_event(db_session, camera.id, "UNKNOWN", today)
    add_event(db_session, camera.id, "UNKNOWN", yesterday)

    date_value = today.date().isoformat()

    response = client.get(
        f"/api/v1/events?date={date_value}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["occurred_at"].startswith(date_value)
