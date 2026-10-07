"""
Tests for the Phase 22 Cameras page (frontend/components/cameras.py).

The real dashboard (frontend/app.py) is driven with streamlit.testing.v1.AppTest.
APIClient camera methods are patched with an in-memory fake backend, so no
network or database is needed.
"""
import copy

import pytest
from streamlit.proto.TextInput_pb2 import TextInput as TextInputProto
from streamlit.testing.v1 import AppTest

from frontend.api_client import APIClient
from frontend.components.cameras import (
    build_camera_payload,
    build_camera_rows,
    format_last_seen,
    has_embedded_credentials,
    mask_source_url,
)

CAMERAS_PAGE = "📷 Cameras"

# Simulates a misbehaving backend that leaks credentials in source_url.
# The page must never render these values anywhere.
LEAK_USER = "leakuser"
LEAK_PASSWORD = "supersecretpw"

SAMPLE_CAMERAS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Main Gate Entry",
        "location": "Main Gate",
        "source_type": "RTSP",
        "source_url": f"rtsp://{LEAK_USER}:{LEAK_PASSWORD}@10.0.0.5:554/Streaming/Channels/101",
        "credentials_ref": "CAMERA_1_CREDENTIALS",
        "enabled": True,
        "status": "ONLINE",
        "last_seen_at": "2026-10-07T09:00:00+00:00",
        "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-07T09:00:00+00:00",
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Lab Webcam",
        "location": "CS Lab",
        "source_type": "WEBCAM",
        "source_url": "0",
        "credentials_ref": None,
        "enabled": False,
        "status": "DISABLED",
        "last_seen_at": None,
        "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-01T00:00:00+00:00",
    },
]


class FakeBackend:
    """Records camera API calls and serves a mutable camera list."""

    def __init__(self, cameras=None, referenced_ids=()):
        self.cameras = copy.deepcopy(cameras if cameras is not None else SAMPLE_CAMERAS)
        self.referenced_ids = set(referenced_ids)
        self.calls = []
        self.fail_list = False

    def list_cameras(self, client):
        self.calls.append(("list",))
        if self.fail_list:
            raise ValueError("Backend unavailable")
        return {"items": copy.deepcopy(self.cameras), "total": len(self.cameras)}

    def create_camera(self, client, **kwargs):
        self.calls.append(("create", kwargs))
        cam = dict(kwargs, id="33333333-3333-3333-3333-333333333333", status="UNKNOWN", last_seen_at=None)
        self.cameras.append(cam)
        return cam

    def update_camera(self, client, camera_id, data):
        self.calls.append(("update", camera_id, data))
        cam = next(c for c in self.cameras if c["id"] == camera_id)
        cam.update(data)
        return cam

    def delete_camera(self, client, camera_id):
        self.calls.append(("delete", camera_id))
        if camera_id in self.referenced_ids:
            cam = next(c for c in self.cameras if c["id"] == camera_id)
            cam["enabled"] = False
            cam["status"] = "DISABLED"
        else:
            self.cameras = [c for c in self.cameras if c["id"] != camera_id]

    def test_camera(self, client, camera_id):
        self.calls.append(("test", camera_id))
        return {"ok": True, "width": 1920, "height": 1080, "fps": 25.0, "error": None}

    def mutating_calls(self):
        return [c for c in self.calls if c[0] in {"create", "update", "delete", "test"}]


@pytest.fixture
def backend(monkeypatch):
    fake = FakeBackend()
    for name in ("list_cameras", "create_camera", "update_camera", "delete_camera", "test_camera"):
        method = getattr(fake, name)
        monkeypatch.setattr(APIClient, name, lambda self, *a, _m=method, **kw: _m(self, *a, **kw))
    return fake


def open_cameras_page(role: str) -> AppTest:
    at = AppTest.from_file("frontend/app.py", default_timeout=15)
    at.session_state["token"] = "test-token"
    at.session_state["user"] = {"username": f"{role.lower()}_user", "role": role}
    at.run()
    at.sidebar.radio[0].set_value(CAMERAS_PAGE).run()
    assert not at.exception, at.exception
    return at


def rendered_text(at: AppTest) -> str:
    """Concatenate everything visible: text, widget labels/values/options, tables, alerts."""
    parts = []
    for group in (at.markdown, at.caption, at.header, at.subheader, at.error, at.warning,
                  at.success, at.info):
        parts.extend(str(e.value) for e in group)
    for group in (at.text_input, at.number_input, at.checkbox):
        parts.extend(f"{e.label} {e.value}" for e in group)
    for sb in at.selectbox:
        parts.append(sb.label)
        parts.extend(str(o) for o in sb.options)
    for m in at.metric:
        parts.append(f"{m.label} {m.value}")
    for df in at.dataframe:
        parts.append(df.value.to_string())
    return "\n".join(parts)


def button(at: AppTest, label: str):
    matches = [b for b in at.button if b.label == label]
    assert matches, f"button {label!r} not found; have {[b.label for b in at.button]}"
    return matches[0]


# ---------------------------------------------------------------------------
# Pure helper tests
# ---------------------------------------------------------------------------

def test_mask_source_url_strips_credentials():
    masked = mask_source_url("rtsp://admin:p%40ss@192.168.1.10:554/Streaming/Channels/101")
    assert masked == "rtsp://192.168.1.10:554/Streaming/Channels/101"
    assert "admin" not in masked and "p%40ss" not in masked


def test_mask_source_url_leaves_clean_values_unchanged():
    assert mask_source_url("rtsp://10.0.0.5:554/x") == "rtsp://10.0.0.5:554/x"
    assert mask_source_url("0") == "0"
    assert mask_source_url("sample.mp4") == "sample.mp4"
    assert mask_source_url(None) == ""


def test_has_embedded_credentials():
    assert has_embedded_credentials("rtsp://u:p@10.0.0.5/x")
    assert has_embedded_credentials("rtsp://u@10.0.0.5/x")
    assert not has_embedded_credentials("rtsp://10.0.0.5:554/x")
    assert not has_embedded_credentials("0")
    assert not has_embedded_credentials(None)


def test_build_camera_rows_has_required_columns_and_no_secrets():
    rows = build_camera_rows(SAMPLE_CAMERAS)
    assert list(rows[0].keys()) == ["Name", "Location", "Source Type", "Status", "Enabled", "Last Seen"]
    joined = repr(rows)
    assert LEAK_PASSWORD not in joined and LEAK_USER not in joined
    assert "CAMERA_1_CREDENTIALS" not in joined
    assert rows[1]["Last Seen"] == "Never"
    assert "Disabled" in rows[1]["Enabled"]


def test_format_last_seen_uses_app_timezone(monkeypatch):
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Kolkata")
    assert format_last_seen("2026-10-07T09:00:00+00:00") == "2026-10-07 14:30:00"


def test_build_payload_rejects_embedded_rtsp_credentials_without_echoing_them():
    with pytest.raises(ValueError) as exc:
        build_camera_payload("Gate", "Main", "RTSP", "rtsp://bob:hunter22pw@10.0.0.9/x", "CAMERA_1_CREDENTIALS")
    assert "hunter22pw" not in str(exc.value) and "bob" not in str(exc.value)


def test_build_payload_rules_per_source_type():
    with pytest.raises(ValueError):
        build_camera_payload("Gate", "Main", "RTSP", "rtsp://10.0.0.9/x", "")  # ref required
    with pytest.raises(ValueError):
        build_camera_payload("Gate", "Main", "RTSP", "http://10.0.0.9/x", "CAM_REF")
    with pytest.raises(ValueError):
        build_camera_payload("Cam", "Lab", "WEBCAM", "abc")
    with pytest.raises(ValueError):
        build_camera_payload("  ", "Lab", "WEBCAM", "0")

    webcam = build_camera_payload("Cam", "Lab", "WEBCAM", "0", "SHOULD_BE_DROPPED")
    assert webcam["credentials_ref"] is None

    rtsp = build_camera_payload(" Gate ", " Main ", "RTSP", " rtsp://10.0.0.9:554/x ", " CAMERA_2_CREDENTIALS ")
    assert rtsp == {
        "name": "Gate",
        "location": "Main",
        "source_type": "RTSP",
        "source_url": "rtsp://10.0.0.9:554/x",
        "credentials_ref": "CAMERA_2_CREDENTIALS",
    }


# ---------------------------------------------------------------------------
# Page tests (AppTest)
# ---------------------------------------------------------------------------

def test_admin_sees_camera_list_with_required_columns(backend):
    at = open_cameras_page("ADMIN")
    df = at.dataframe[0].value
    assert list(df.columns) == ["Name", "Location", "Source Type", "Status", "Enabled", "Last Seen"]
    assert set(df["Name"]) == {"Main Gate Entry", "Lab Webcam"}
    assert "🟢 ONLINE" in set(df["Status"])
    # Admin controls are present
    for label in ("Add Camera", "🔌 Test Connection", "⏸️ Disable Camera", "💾 Save Changes", "🗑️ Delete Camera"):
        button(at, label)


def test_credentials_never_rendered_even_if_backend_leaks_them(backend):
    for role in ("ADMIN", "OPERATOR"):
        text = rendered_text(open_cameras_page(role))
        assert LEAK_PASSWORD not in text, role
        assert LEAK_USER not in text, role
    # The admin edit form shows the masked URL only.
    at = open_cameras_page("ADMIN")
    rtsp_inputs = [t.value for t in at.text_input if t.label.startswith("RTSP URL")]
    assert "rtsp://10.0.0.5:554/Streaming/Channels/101" in rtsp_inputs
    # No password-type input field is ever offered on the Cameras page.
    assert not any(t.proto.type == TextInputProto.PASSWORD for t in at.text_input)


def test_operator_is_read_only(backend):
    at = open_cameras_page("OPERATOR")
    assert len(at.dataframe) == 1  # list still visible
    labels = [b.label for b in at.button]
    for admin_label in ("Add Camera", "🔌 Test Connection", "⏸️ Disable Camera", "💾 Save Changes", "🗑️ Delete Camera"):
        assert admin_label not in labels
    warnings = " ".join(w.value for w in at.warning)
    assert "Only ADMIN users" in warnings
    assert backend.mutating_calls() == []


def test_empty_state(backend):
    backend.cameras = []
    at = open_cameras_page("ADMIN")
    assert any("No cameras configured yet." in i.value for i in at.info)
    assert len(at.dataframe) == 0


def test_list_error_is_shown(backend):
    backend.fail_list = True
    at = open_cameras_page("OPERATOR")
    assert any("Failed to load cameras" in e.value for e in at.error)


def test_admin_add_rtsp_rejects_embedded_credentials_client_side(backend):
    at = open_cameras_page("ADMIN")
    at.selectbox(key="cam_add_source_type").set_value("RTSP").run()
    at.text_input(key="cam_add_name").input("Back Gate")
    at.text_input(key="cam_add_location").input("Back Gate")
    at.text_input(key="cam_add_rtsp_url").input("rtsp://admin:topsecret99@10.0.0.7:554/x")
    at.text_input(key="cam_add_credentials_ref").input("CAMERA_2_CREDENTIALS")
    button(at, "Add Camera").click().run()

    assert not any(c[0] == "create" for c in backend.calls)
    errors = " ".join(e.value for e in at.error)
    assert "must not contain a username or password" in errors
    assert "topsecret99" not in errors


def test_admin_add_rtsp_camera_sends_reference_not_secret(backend):
    at = open_cameras_page("ADMIN")
    at.selectbox(key="cam_add_source_type").set_value("RTSP").run()
    at.text_input(key="cam_add_name").input("Back Gate")
    at.text_input(key="cam_add_location").input("Back Gate")
    at.text_input(key="cam_add_rtsp_url").input("rtsp://10.0.0.7:554/Streaming/Channels/101")
    at.text_input(key="cam_add_credentials_ref").input("CAMERA_2_CREDENTIALS")
    button(at, "Add Camera").click().run()

    creates = [c[1] for c in backend.calls if c[0] == "create"]
    assert creates == [{
        "name": "Back Gate",
        "location": "Back Gate",
        "source_type": "RTSP",
        "source_url": "rtsp://10.0.0.7:554/Streaming/Channels/101",
        "credentials_ref": "CAMERA_2_CREDENTIALS",
        "enabled": True,
    }]
    assert any("Back Gate" in s.value and "added" in s.value for s in at.success)


def test_admin_test_connection_shows_result(backend):
    at = open_cameras_page("ADMIN")
    button(at, "🔌 Test Connection").click().run()
    assert ("test", SAMPLE_CAMERAS[0]["id"]) in backend.calls
    assert any("Connection OK" in s.value and "1920×1080" in s.value for s in at.success)


def test_admin_disable_and_enable(backend):
    at = open_cameras_page("ADMIN")
    button(at, "⏸️ Disable Camera").click().run()
    assert ("update", SAMPLE_CAMERAS[0]["id"], {"enabled": False}) in backend.calls
    assert any("disabled" in s.value for s in at.success)
    # After rerun the same camera now offers Enable.
    button(at, "▶️ Enable Camera").click().run()
    assert ("update", SAMPLE_CAMERAS[0]["id"], {"enabled": True}) in backend.calls


def test_admin_edit_saves_partial_payload(backend):
    at = open_cameras_page("ADMIN")
    prefix = f"cam_edit_{SAMPLE_CAMERAS[0]['id']}"
    at.text_input(key=f"{prefix}_location").input("Main Gate (North)")
    button(at, "💾 Save Changes").click().run()
    updates = [c for c in backend.calls if c[0] == "update"]
    assert updates[-1][2] == {
        "name": "Main Gate Entry",
        "location": "Main Gate (North)",
        "source_type": "RTSP",
        "source_url": "rtsp://10.0.0.5:554/Streaming/Channels/101",  # masked, never the leaked secret
        "credentials_ref": "CAMERA_1_CREDENTIALS",
    }


def test_admin_delete_requires_confirmation(backend):
    at = open_cameras_page("ADMIN")
    assert button(at, "🗑️ Delete Camera").disabled
    at.checkbox(key=f"cam_edit_{SAMPLE_CAMERAS[0]['id']}_confirm_delete").check().run()
    button(at, "🗑️ Delete Camera").click().run()
    assert ("delete", SAMPLE_CAMERAS[0]["id"]) in backend.calls
    assert any("deleted" in s.value for s in at.success)


def test_admin_delete_of_referenced_camera_reports_disabled(backend):
    backend.referenced_ids = {SAMPLE_CAMERAS[0]["id"]}
    at = open_cameras_page("ADMIN")
    at.checkbox(key=f"cam_edit_{SAMPLE_CAMERAS[0]['id']}_confirm_delete").check().run()
    button(at, "🗑️ Delete Camera").click().run()
    assert any("disabled instead of deleted" in w.value for w in at.warning)
