"""Blacklist management page."""
from __future__ import annotations

import streamlit as st


def render_blacklist_page(api, role: str) -> None:
    st.header("🚫 Blacklist Management")
    st.warning("Use only with institutional authorization.")

    search_col, status_col = st.columns([3, 1])

    with search_col:
        q = st.text_input("Search by name")

    with status_col:
        status = st.selectbox(
            "Status",
            ["", "ACTIVE", "INACTIVE"],
        )

    if role == "ADMIN":
        with st.expander("➕ Add blacklist entry"):
            with st.form("blacklist_create"):
                full_name = st.text_input("Name")
                reason = st.text_area("Reason")
                category = st.text_input("Category")
                severity = st.selectbox(
                    "Severity",
                    ["HIGH", "CRITICAL"],
                )
                notes = st.text_area("Notes")

                submitted = st.form_submit_button("Create")

                if submitted:
                    if not full_name.strip() or not reason.strip():
                        st.error("Name and reason are required.")
                    else:
                        try:
                            api.create_blacklist(
                                full_name=full_name.strip(),
                                reason=reason.strip(),
                                category=category.strip() or None,
                                severity=severity,
                                notes=notes.strip() or None,
                            )
                            st.success("Blacklist entry created.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Create failed: {exc}")

    try:
        data = api.list_blacklist(
            q=q.strip() or None,
            status=status or None,
            page=1,
            size=100,
        )
    except Exception as exc:
        st.error(f"Failed to load blacklist entries: {exc}")
        return

    items = data.get("items", [])
    st.caption(f"Total entries: {data.get('total', 0)}")

    if not items:
        st.info("No blacklist entries found.")
        return

    st.dataframe(
        [
            {
                "ID": item["id"],
                "Name": item["full_name"],
                "Reason": item["reason"],
                "Category": item.get("category") or "-",
                "Severity": item["severity"],
                "Status": item["status"],
                "Created": item["created_at"],
            }
            for item in items
        ],
        use_container_width=True,
        hide_index=True,
    )

    if role != "ADMIN":
        return

    st.divider()
    entry_id = st.text_input("Entry UUID to manage")

    if not entry_id.strip():
        return

    try:
        entry = api.get_blacklist(entry_id.strip())
    except Exception as exc:
        st.error(f"Unable to load entry: {exc}")
        return

    st.write(
        f"Managing **{entry['full_name']}** "
        f"({entry['status']})"
    )

    col1, col2 = st.columns(2)

    with col1:
        new_reason = st.text_area(
            "Reason",
            value=entry["reason"],
        )

        new_category = st.text_input(
            "Category",
            value=entry.get("category") or "",
        )

        new_severity = st.selectbox(
            "Severity",
            ["HIGH", "CRITICAL"],
            index=0 if entry["severity"] == "HIGH" else 1,
        )

        new_notes = st.text_area(
            "Notes",
            value=entry.get("notes") or "",
        )

        if st.button("Save Changes"):
            try:
                api.update_blacklist(
                    entry_id.strip(),
                    {
                        "reason": new_reason.strip(),
                        "category": new_category.strip() or None,
                        "severity": new_severity,
                        "notes": new_notes.strip() or None,
                    },
                )
                st.success("Blacklist entry updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Update failed: {exc}")

    with col2:
        if entry["status"] == "ACTIVE":
            if st.button(
                "Deactivate",
                type="primary",
            ):
                try:
                    api.deactivate_blacklist(entry_id.strip())
                    st.warning("Blacklist entry deactivated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Deactivation failed: {exc}")
