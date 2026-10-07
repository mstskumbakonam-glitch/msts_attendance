"""
Cameras page (Phase 22 — Camera Management).

Rendered from the single dashboard router in frontend/app.py so it stays behind
the login gate. All calls go through frontend/api_client.py. ADMIN users can
add, edit, test, enable/disable and delete cameras; OPERATOR users are read-only.
The backend remains the authority for RBAC — the UI only hides admin actions.

Credential rules (docs/RTSP_SETUP.md):
- The UI never asks for, shows or sends RTSP usernames/passwords.
- RTSP cameras reference an environment variable by name (credentials_ref);
  only that NAME is handled here, never its value.
- Source URLs are masked again on the client as defence in depth, even though
  the backend already rejects and masks embedded credentials.
"""
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import requests
import streamlit as st

from frontend.api_client import APIClient

SOURCE_TYPES = ["WEBCAM", "VIDEO_FILE", "RTSP"]

SOURCE_TYPE_LABELS = {
    "WEBCAM": "Webcam",
    "VIDEO_FILE": "Video file",
    "RTSP": "RTSP / CCTV",
}

STATUS_BADGES = {
    "ONLINE": "🟢 ONLINE",
    "OFFLINE": "⚫ OFFLINE",
    "ERROR": "🔴 ERROR",
    "DISABLED": "⏸️ DISABLED",
    "UNKNOWN": "⚪ UNKNOWN",
}

FLASH_KEY = "camera_flash"

# Errors raised by APIClient (HTTP errors) or by requests (backend unreachable).
API_ERRORS = (ValueError, requests.RequestException)


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested in frontend/tests/test_cameras_page.py)
# ---------------------------------------------------------------------------

def has_embedded_credentials(url: Optional[str]) -> bool:
    """True if a URL carries a user/password part (e.g. rtsp://user:pass@host)."""
    if not url:
        return False
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return False
    return parsed.username is not None or parsed.password is not None or "@" in parsed.netloc


def mask_source_url(url: Optional[str]) -> str:
    """Return the URL with any user/password part removed. Never returns credentials."""
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "[hidden]"
    if not parsed.netloc or "@" not in parsed.netloc:
        return url
    host = parsed.netloc.rsplit("@", 1)[1]
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def format_status(status: Optional[str]) -> str:
    status = (status or "UNKNOWN").upper()
    return STATUS_BADGES.get(status, status)


def format_last_seen(value: Optional[str]) -> str:
    """Format an ISO timestamp in the app timezone; 'Never' when missing."""
    if not value:
        return "Never"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    tz_name = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    try:
        from zoneinfo import ZoneInfo

        local = parsed.astimezone(ZoneInfo(tz_name))
        return local.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def build_camera_rows(cameras: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Table rows for the camera list. Deliberately excludes source URLs and credential refs."""
    return [
        {
            "Name": cam.get("name", ""),
            "Location": cam.get("location", ""),
            "Source Type": SOURCE_TYPE_LABELS.get(cam.get("source_type", ""), cam.get("source_type", "")),
            "Status": format_status(cam.get("status")),
            "Enabled": "✅ Enabled" if cam.get("enabled") else "⛔ Disabled",
            "Last Seen": format_last_seen(cam.get("last_seen_at")),
        }
        for cam in cameras
    ]


def build_camera_payload(
    name: str,
    location: str,
    source_type: str,
    source_url: str,
    credentials_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build and pre-validate a create/update payload.

    Raises ValueError with a message that never echoes the URL, so a mistakenly
    pasted password is not displayed back to the user.
    """
    name = (name or "").strip()
    location = (location or "").strip()
    source_url = (source_url or "").strip()
    credentials_ref = (credentials_ref or "").strip() or None

    if not name or not location:
        raise ValueError("Name and Location are required.")
    if source_type not in SOURCE_TYPES:
        raise ValueError("Unsupported source type.")
    if not source_url:
        raise ValueError("Source is required.")

    if source_type == "RTSP":
        if has_embedded_credentials(source_url):
            raise ValueError(
                "The RTSP URL must not contain a username or password. "
                "Remove them and store the credentials in the server environment "
                "variable referenced by 'Credentials reference'."
            )
        if not source_url.lower().startswith("rtsp://"):
            raise ValueError("RTSP source must start with rtsp://")
        if not credentials_ref:
            raise ValueError("RTSP cameras require a credentials reference (e.g. CAMERA_1_CREDENTIALS).")
    else:
        credentials_ref = None
        if source_type == "WEBCAM" and not source_url.isdigit():
            raise ValueError("Webcam source must be a numeric camera index.")

    return {
        "name": name,
        "location": location,
        "source_type": source_type,
        "source_url": source_url,
        "credentials_ref": credentials_ref,
    }


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def _flash(message: str, level: str = "success") -> None:
    st.session_state[FLASH_KEY] = (level, message)


def _show_flash() -> None:
    flash = st.session_state.pop(FLASH_KEY, None)
    if flash:
        level, message = flash
        getattr(st, level, st.info)(message)


def _source_fields(source_type: str, key_prefix: str, defaults: Optional[Dict[str, Any]] = None):
    """Render source-type specific inputs. Returns (source_url, credentials_ref)."""
    defaults = defaults or {}
    current_url = mask_source_url(defaults.get("source_url")) if defaults.get("source_type") == source_type else ""
    current_ref = (defaults.get("credentials_ref") or "") if defaults.get("source_type") == source_type else ""

    if source_type == "WEBCAM":
        index_default = int(current_url) if current_url.isdigit() else 0
        index = st.number_input(
            "Webcam index", min_value=0, max_value=16, value=index_default, step=1,
            key=f"{key_prefix}_webcam_index",
            help="0 is usually the built-in laptop webcam.",
        )
        return str(int(index)), None

    if source_type == "VIDEO_FILE":
        path = st.text_input(
            "Video file path", value=current_url, key=f"{key_prefix}_video_path",
            help="Path relative to data/videos (files outside data/videos are rejected).",
            placeholder="sample.mp4",
        )
        return path, None

    url = st.text_input(
        "RTSP URL (no username/password)", value=current_url, key=f"{key_prefix}_rtsp_url",
        placeholder="rtsp://192.168.1.10:554/Streaming/Channels/101",
        help="Never put credentials in the URL. They are read on the server from the variable below.",
    )
    ref = st.text_input(
        "Credentials reference", value=current_ref, key=f"{key_prefix}_credentials_ref",
        placeholder="CAMERA_1_CREDENTIALS",
        help="Name of the server environment variable holding username:password. "
             "Enter the variable NAME only — never the password.",
    )
    return url, ref


def _render_list(cameras: List[Dict[str, Any]]) -> None:
    st.subheader("Camera Registry")
    if not cameras:
        st.info("No cameras configured yet.")
        return

    online = sum(1 for c in cameras if (c.get("status") or "").upper() == "ONLINE")
    enabled = sum(1 for c in cameras if c.get("enabled"))
    c1, c2, c3 = st.columns(3)
    c1.metric("Cameras", len(cameras))
    c2.metric("Enabled", enabled)
    c3.metric("Online", online)

    st.dataframe(build_camera_rows(cameras), use_container_width=True, hide_index=True)
    st.caption(
        "Status is reported by the camera worker heartbeat (about every 10 s). "
        "A camera shows UNKNOWN until a worker has reported on it."
    )


def _render_add(api: APIClient) -> None:
    st.subheader("Add Camera")
    source_type = st.selectbox(
        "Source type", SOURCE_TYPES, format_func=lambda s: SOURCE_TYPE_LABELS[s], key="cam_add_source_type"
    )
    with st.form("camera_add_form", clear_on_submit=False):
        name = st.text_input("Camera name", key="cam_add_name", placeholder="Main Gate - Entry")
        location = st.text_input("Location", key="cam_add_location", placeholder="Main Gate")
        source_url, credentials_ref = _source_fields(source_type, "cam_add")
        enabled = st.checkbox("Enabled", value=True, key="cam_add_enabled")
        submitted = st.form_submit_button("Add Camera", use_container_width=True)

    if submitted:
        try:
            payload = build_camera_payload(name, location, source_type, source_url, credentials_ref)
        except API_ERRORS as exc:
            st.error(str(exc))
            return
        try:
            created = api.create_camera(enabled=enabled, **payload)
            _flash(f"Camera '{created.get('name', payload['name'])}' added.")
            st.rerun()
        except API_ERRORS as exc:
            st.error(f"Could not add camera: {exc}")


def _render_manage(api: APIClient, cameras: List[Dict[str, Any]]) -> None:
    st.subheader("Manage Camera")
    if not cameras:
        st.info("No cameras configured yet.")
        return

    by_id = {c["id"]: c for c in cameras}
    camera_id = st.selectbox(
        "Select camera",
        list(by_id.keys()),
        format_func=lambda cid: f"{by_id[cid].get('name', '')} — {by_id[cid].get('location', '')}",
        key="cam_manage_select",
    )
    cam = by_id[camera_id]
    prefix = f"cam_edit_{camera_id}"

    m1, m2, m3 = st.columns(3)
    m1.metric("Status", format_status(cam.get("status")))
    m2.metric("Enabled", "Yes" if cam.get("enabled") else "No")
    m3.metric("Last seen", format_last_seen(cam.get("last_seen_at")))

    # --- Actions: test / enable-disable ---
    a1, a2 = st.columns(2)
    with a1:
        if st.button("🔌 Test Connection", key=f"{prefix}_test", use_container_width=True):
            with st.spinner("Testing connection (may take a few seconds)..."):
                try:
                    result = api.test_camera(camera_id)
                except API_ERRORS as exc:
                    result = None
                    st.error(f"Connection test failed: {exc}")
            if result is not None:
                if result.get("ok"):
                    details = []
                    if result.get("width") and result.get("height"):
                        details.append(f"{result['width']}×{result['height']}")
                    if result.get("fps"):
                        details.append(f"{float(result['fps']):.1f} fps")
                    suffix = f" ({', '.join(details)})" if details else ""
                    st.success(f"Connection OK{suffix}")
                else:
                    st.error(f"Connection failed: {result.get('error') or 'unknown error'}")
    with a2:
        is_enabled = bool(cam.get("enabled"))
        label = "⏸️ Disable Camera" if is_enabled else "▶️ Enable Camera"
        if st.button(label, key=f"{prefix}_toggle", use_container_width=True):
            try:
                api.update_camera(camera_id, {"enabled": not is_enabled})
                _flash(f"Camera '{cam.get('name')}' {'disabled' if is_enabled else 'enabled'}.")
                st.rerun()
            except API_ERRORS as exc:
                st.error(f"Could not update camera: {exc}")

    # --- Edit form ---
    st.markdown("#### Edit configuration")
    current_type = cam.get("source_type") if cam.get("source_type") in SOURCE_TYPES else "WEBCAM"
    source_type = st.selectbox(
        "Source type", SOURCE_TYPES, index=SOURCE_TYPES.index(current_type),
        format_func=lambda s: SOURCE_TYPE_LABELS[s], key=f"{prefix}_source_type",
    )
    with st.form(f"{prefix}_form"):
        name = st.text_input("Camera name", value=cam.get("name", ""), key=f"{prefix}_name")
        location = st.text_input("Location", value=cam.get("location", ""), key=f"{prefix}_location")
        source_url, credentials_ref = _source_fields(source_type, prefix, defaults=cam)
        saved = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if saved:
        try:
            payload = build_camera_payload(name, location, source_type, source_url, credentials_ref)
        except API_ERRORS as exc:
            st.error(str(exc))
        else:
            try:
                api.update_camera(camera_id, payload)
                _flash(f"Camera '{payload['name']}' updated.")
                st.rerun()
            except API_ERRORS as exc:
                st.error(f"Could not update camera: {exc}")

    # --- Delete ---
    st.markdown("#### Danger Zone")
    st.caption("Cameras referenced by attendance, detection or alert records are disabled instead of deleted.")
    confirm = st.checkbox(f"I understand — delete '{cam.get('name')}'", key=f"{prefix}_confirm_delete")
    if st.button("🗑️ Delete Camera", key=f"{prefix}_delete", type="primary", disabled=not confirm):
        try:
            api.delete_camera(camera_id)
            # The backend returns 204 either way; check whether it was kept (disabled).
            try:
                remaining = {c["id"] for c in api.list_cameras().get("items", [])}
            except API_ERRORS:
                remaining = set()
            if camera_id in remaining:
                _flash(
                    f"Camera '{cam.get('name')}' is referenced by existing records, "
                    "so it was disabled instead of deleted.",
                    "warning",
                )
            else:
                _flash(f"Camera '{cam.get('name')}' deleted.")
            st.session_state.pop("cam_manage_select", None)
            st.rerun()
        except API_ERRORS as exc:
            st.error(f"Could not delete camera: {exc}")


def render_cameras_page(api: APIClient, role: str) -> None:
    st.header("📷 Camera Management")
    _show_flash()

    try:
        cameras = api.list_cameras().get("items", [])
    except API_ERRORS as exc:
        st.error(f"Failed to load cameras: {exc}")
        return

    is_admin = role == "ADMIN"
    tabs = st.tabs(["Camera List", "Add Camera", "Manage Camera"])

    with tabs[0]:
        _render_list(cameras)
        if not is_admin:
            st.caption("🔒 Read-only view. ADMIN role is required to change cameras.")

    with tabs[1]:
        if not is_admin:
            st.warning("⚠️ Only ADMIN users have permission to add cameras.")
        else:
            _render_add(api)

    with tabs[2]:
        if not is_admin:
            st.warning("⚠️ Only ADMIN users have permission to edit, test, enable/disable or delete cameras.")
        else:
            _render_manage(api, cameras)
