"""Detection Events page."""
from __future__ import annotations

from datetime import date

import streamlit as st


def render_detection_events_page(api) -> None:
    st.header("🔍 Detection Events")
    st.caption("Raw recognition/detection sightings emitted by the event layer.")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        event_type = st.selectbox("Type", ["", "RECOGNIZED", "UNKNOWN", "BLACKLISTED"])
    with col2:
        camera_id = st.text_input("Camera UUID", placeholder="Optional")
    with col3:
        student_id = st.text_input("Student UUID", placeholder="Optional")
    with col4:
        selected_date = st.date_input("Date", value=date.today())

    try:
        data = api.list_events(
            camera_id=camera_id.strip() or None,
            event_type=event_type or None,
            student_id=student_id.strip() or None,
            event_date=selected_date.isoformat(),
            page=1,
            size=200,
        )
        items = data.get("items", [])
        st.caption(f"Total events: {data.get('total', 0)}")
        if not items:
            st.info("No detection events found for the selected filters.")
            return
        st.dataframe(
            [
                {
                    "Time": item.get("occurred_at"),
                    "Type": item.get("event_type"),
                    "Camera": item.get("camera_id"),
                    "Student": item.get("student_id") or "-",
                    "Similarity": item.get("similarity"),
                    "Track": item.get("track_id") or "-",
                }
                for item in items
            ],
            use_container_width=True,
            hide_index=True,
        )
    except Exception as exc:
        st.error(f"Failed to load detection events: {exc}")
