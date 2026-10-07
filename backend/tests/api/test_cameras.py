"""
Camera management API tests.
"""
import uuid
from datetime import datetime, timezone

from backend.app.models.camera import Camera
from backend.app.models.detection_event import DetectionEvent
from backend.app.schemas.camera import CameraTestResponse
from backend.app.services.camera_service import CameraService


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def camera_name(prefix: str = "CAM") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def test_create_webcam_camera(client, admin_token):
    response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name(),
            "location": "Main Entrance",
            "source_type": "WEBCAM",
            "source_url": "0",
            "enabled": True,
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["source_type"] == "WEBCAM"
    assert data["source_url"] == "0"
    assert data["enabled"] is True
    assert data["status"] == "UNKNOWN"


def test_create_rtsp_camera_without_embedded_credentials(client, admin_token):
    response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("RTSP"),
            "location": "Main Gate",
            "source_type": "RTSP",
            "source_url": "rtsp://192.168.1.59:554/Streaming/Channels/101",
            "credentials_ref": "CAMERA_1_CREDENTIALS",
            "enabled": True,
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["source_type"] == "RTSP"
    assert data["credentials_ref"] == "CAMERA_1_CREDENTIALS"
    assert data["source_url"] == (
        "rtsp://192.168.1.59:554/Streaming/Channels/101"
    )
    assert "@" not in data["source_url"]


def test_camera_rejects_embedded_credentials(client, admin_token):
    response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("BADRTSP"),
            "location": "Invalid Camera",
            "source_type": "RTSP",
            "source_url": "rtsp://user:password@192.168.1.59:554/stream",
            "credentials_ref": "CAMERA_1_CREDENTIALS",
        },
    )

    assert response.status_code == 422


def test_operator_can_list_but_cannot_modify_camera(
    client,
    admin_token,
    operator_token,
):
    create_response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("RBAC"),
            "location": "Reception",
            "source_type": "WEBCAM",
            "source_url": "0",
            "enabled": True,
        },
    )

    assert create_response.status_code == 201

    camera_id = create_response.json()["id"]

    list_response = client.get(
        "/api/v1/cameras",
        headers=auth_headers(operator_token),
    )

    assert list_response.status_code == 200

    patch_response = client.patch(
        f"/api/v1/cameras/{camera_id}",
        headers=auth_headers(operator_token),
        json={"location": "Changed"},
    )

    assert patch_response.status_code == 403

    delete_response = client.delete(
        f"/api/v1/cameras/{camera_id}",
        headers=auth_headers(operator_token),
    )

    assert delete_response.status_code == 403


def test_camera_get_and_update(client, admin_token):
    create_response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("UPDATE"),
            "location": "Old Location",
            "source_type": "WEBCAM",
            "source_url": "0",
            "enabled": True,
        },
    )

    assert create_response.status_code == 201
    camera_id = create_response.json()["id"]

    get_response = client.get(
        f"/api/v1/cameras/{camera_id}",
        headers=auth_headers(admin_token),
    )

    assert get_response.status_code == 200
    assert get_response.json()["location"] == "Old Location"

    update_response = client.patch(
        f"/api/v1/cameras/{camera_id}",
        headers=auth_headers(admin_token),
        json={
            "location": "New Location",
            "enabled": False,
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()
    assert data["location"] == "New Location"
    assert data["enabled"] is False
    assert data["status"] == "DISABLED"


def test_camera_list(client, admin_token):
    response = client.get(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= len(data["items"])


def test_camera_not_found(client, admin_token):
    missing_id = str(uuid.uuid4())

    response = client.get(
        f"/api/v1/cameras/{missing_id}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 404


def test_camera_delete_unused(client, admin_token):
    create_response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("DELETE"),
            "location": "Temporary",
            "source_type": "WEBCAM",
            "source_url": "0",
            "enabled": False,
        },
    )

    assert create_response.status_code == 201
    camera_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/cameras/{camera_id}",
        headers=auth_headers(admin_token),
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/api/v1/cameras/{camera_id}",
        headers=auth_headers(admin_token),
    )

    assert get_response.status_code == 404


def test_referenced_camera_is_disabled_instead_of_deleted(
    client,
    admin_token,
    db_session,
):
    create_response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("REF"),
            "location": "Referenced Camera",
            "source_type": "WEBCAM",
            "source_url": "0",
            "enabled": True,
        },
    )

    assert create_response.status_code == 201

    camera_id = uuid.UUID(create_response.json()["id"])

    event = DetectionEvent(
        occurred_at=datetime.now(timezone.utc),
        camera_id=camera_id,
        event_type="UNKNOWN",
    )

    db_session.add(event)
    db_session.flush()

    delete_response = client.delete(
        f"/api/v1/cameras/{camera_id}",
        headers=auth_headers(admin_token),
    )

    assert delete_response.status_code == 204

    camera = db_session.get(Camera, camera_id)
    assert camera is not None
    assert camera.enabled is False
    assert camera.status == "DISABLED"


def test_rtsp_connection_failure_returns_ok_false(
    client,
    admin_token,
    monkeypatch,
):
    create_response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("TEST"),
            "location": "Connection Test",
            "source_type": "RTSP",
            "source_url": "rtsp://192.0.2.1:554/stream",
            "credentials_ref": "CAMERA_1_CREDENTIALS",
            "enabled": False,
        },
    )

    assert create_response.status_code == 201
    camera_id = create_response.json()["id"]

    def fake_test_connection(self, camera_uuid):
        return CameraTestResponse(
            ok=False,
            error="Could not open RTSP stream",
        )

    monkeypatch.setattr(
        CameraService,
        "test_connection",
        fake_test_connection,
    )

    response = client.post(
        f"/api/v1/cameras/{camera_id}/test",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["error"] == "Could not open RTSP stream"


def test_operator_cannot_test_camera(client, admin_token, operator_token):
    create_response = client.post(
        "/api/v1/cameras",
        headers=auth_headers(admin_token),
        json={
            "name": camera_name("OPTEST"),
            "location": "Operator Test",
            "source_type": "WEBCAM",
            "source_url": "0",
            "enabled": False,
        },
    )

    assert create_response.status_code == 201
    camera_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/cameras/{camera_id}/test",
        headers=auth_headers(operator_token),
    )

    assert response.status_code == 403


def test_rtsp_response_never_exposes_embedded_credentials(
    client,
    admin_token,
    db_session,
):
    camera = Camera(
        name=camera_name("MASK"),
        location="Mask Test",
        source_type="RTSP",
        source_url="rtsp://internaluser:internalpassword@192.168.1.59:554/stream",
        credentials_ref="CAMERA_1_CREDENTIALS",
        enabled=False,
        status="DISABLED",
    )

    db_session.add(camera)
    db_session.flush()

    response = client.get(
        f"/api/v1/cameras/{camera.id}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200

    data = response.json()
    assert data["source_url"] == "rtsp://192.168.1.59:554/stream"
    assert "internaluser" not in data["source_url"]
    assert "internalpassword" not in data["source_url"]
