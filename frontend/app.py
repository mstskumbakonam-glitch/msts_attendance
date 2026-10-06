"""
Smart Attendance & Security System - Streamlit Dashboard Shell
Unified dashboard with strict RBAC, multi-page sidebar navigation, and session auth.
"""
import streamlit as st
from frontend.api_client import APIClient
from frontend.components.auth import require_auth

# Configure Streamlit page
st.set_page_config(
    page_title="Smart Attendance & Security",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize API client
api = APIClient()

# Check authentication gate
if not require_auth(api):
    st.stop()

# User is authenticated
current_user = st.session_state.get("user", {})
role = current_user.get("role", "OPERATOR")
username = current_user.get("username", "User")

# Top Header / User Info in Sidebar
st.sidebar.markdown(f"### 👤 Logged in as: **{username}**")
st.sidebar.caption(f"Role: **{role}**")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    api.logout()
    st.rerun()

st.sidebar.markdown("---")

# Navigation Sidebar exactly per Playbook Section 8:
# LOGIN
# Dashboard                      (7 real KPIs + recent attendance + recent alerts + live tile)
# ATTENDANCE   Live Attendance | Students | Attendance Records | Reports
# SECURITY     Live Monitoring | Alerts | Blacklist | Detection Events | Movement Tracking
# SYSTEM       Cameras | Users | Settings

NAV_SECTIONS = [
    "📊 Dashboard",
    "--- ATTENDANCE ---",
    "📹 Live Attendance",
    "👥 Students",
    "📋 Attendance Records",
    "📈 Reports",
    "--- SECURITY ---",
    "🛡️ Live Monitoring",
    "⚠️ Alerts",
    "🚫 Blacklist",
    "🔍 Detection Events",
    "📍 Movement Tracking",
    "--- SYSTEM ---",
    "📷 Cameras",
    "👤 Users",
    "⚙️ Settings",
]

# Clean display list (selectable options)
selectable_options = [
    opt for opt in NAV_SECTIONS if not opt.startswith("---")
]

selected_page = st.sidebar.radio("Navigation", selectable_options)

# Router
if selected_page == "👥 Students":
    st.header("👥 Student Management")
    tabs = st.tabs(["Search & List", "Register New Student", "Edit / Manage", "📸 Register Face (Webcam)"])

    with tabs[0]:
        st.subheader("Student Directory")
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            search_query = st.text_input("Search by Name or Student ID", "")
        with col2:
            dept_filter = st.text_input("Filter Department", "")
        with col3:
            status_filter = st.selectbox("Status", ["", "ACTIVE", "INACTIVE"])

        try:
            res = api.list_students(
                q=search_query or None,
                department=dept_filter or None,
                status=status_filter or None,
                page=1,
                size=50,
            )
            items = res.get("items", [])
            total = res.get("total", 0)
            st.caption(f"Total students found: {total}")

            if items:
                table_data = [
                    {
                        "UUID": s["id"],
                        "Student ID": s["student_id"],
                        "Name": s["name"],
                        "Department": s["department"],
                        "Year": s["year"],
                        "Status": s["status"],
                        "Consent": "✅ Yes" if s.get("consent_given_at") else "❌ No",
                        "Face Enrolled": "✅ Yes" if s.get("face_registered") else "❌ No",
                        "Samples": s.get("sample_count", 0),
                    }
                    for s in items
                ]
                st.dataframe(table_data, use_container_width=True)
            else:
                st.info("No students found matching current criteria.")
        except Exception as e:
            st.error(f"Failed to fetch students: {e}")

    with tabs[1]:
        st.subheader("Enroll New Student")
        if role != "ADMIN":
            st.warning("⚠️ Only ADMIN users have permission to enroll students.")
        else:
            with st.form("new_student_form"):
                stu_id = st.text_input("Student ID (e.g. 001, CSE-2024-01)")
                name = st.text_input("Full Name")
                dept = st.text_input("Department (e.g. Computer Science)")
                year = st.number_input("Year of Study", min_value=1, max_value=8, value=1)
                consent = st.checkbox("Student has provided Biometric Consent (DPDP Act compliance)", value=True)
                consent_ver = st.text_input("Consent Document Version", value="v1.0")

                submitted = st.form_submit_button("Register Student", use_container_width=True)
                if submitted:
                    if not stu_id or not name or not dept:
                        st.error("Please fill in Student ID, Name, and Department.")
                    else:
                        try:
                            created = api.create_student(
                                student_id=stu_id,
                                name=name,
                                department=dept,
                                year=int(year),
                                consent=consent,
                                consent_version=consent_ver,
                            )
                            st.success(f"Student '{created['name']}' ({created['student_id']}) created successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    with tabs[2]:
        st.subheader("Manage Existing Student")
        if role != "ADMIN":
            st.warning("⚠️ Only ADMIN users have permission to update or deactivate students.")
        else:
            search_id = st.text_input("Enter Student UUID or search above to find UUID", "")
            if search_id:
                try:
                    student = api.get_student(search_id)
                    st.write(f"Editing: **{student['name']}** ({student['student_id']})")
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input("Update Name", value=student["name"])
                        new_dept = st.text_input("Update Department", value=student["department"])
                        new_year = st.number_input("Update Year", min_value=1, max_value=8, value=student["year"])
                        new_status = st.selectbox("Update Status", ["ACTIVE", "INACTIVE"], index=0 if student["status"] == "ACTIVE" else 1)
                        if st.button("Save Changes"):
                            api.update_student(student["id"], {
                                "name": new_name,
                                "department": new_dept,
                                "year": int(new_year),
                                "status": new_status,
                            })
                            st.success("Student updated successfully!")
                            st.rerun()
                    with col2:
                        st.markdown("#### Danger Zone")
                        if st.button("🛑 Deactivate Student (Soft Delete)", type="primary"):
                            api.deactivate_student(student["id"])
                            st.warning(f"Student {student['student_id']} deactivated.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Could not load student: {e}")

    with tabs[3]:
        st.subheader("Webcam Face Registration")
        if role != "ADMIN":
            st.warning("⚠️ Only ADMIN users have permission to register biometrics.")
        else:
            target_stu_id = st.text_input("Enter Student UUID to Enroll Face", key="face_reg_stu_id")
            if target_stu_id:
                try:
                    stu = api.get_student(target_stu_id)
                    st.write(f"Enrolling: **{stu['name']}** ({stu['student_id']})")
                    if not stu.get("consent_given_at"):
                        st.error("❌ Cannot register biometrics: Student has NOT provided biometric consent. Please update student profile with consent first.")
                    else:
                        st.success("✅ Consent verified. Ready for webcam enrollment.")
                        target_samples = st.slider("Target Samples", min_value=5, max_value=50, value=10)

                        if "face_session" not in st.session_state or st.session_state["face_session"].get("student_uuid") != target_stu_id:
                            if st.button("▶️ Start Camera Registration Session"):
                                try:
                                    sess = api.create_face_session(target_stu_id, target_samples=target_samples)
                                    ticket = api.get_stream_ticket("0")
                                    st.session_state["face_session"] = {
                                        "session_id": sess["session_id"],
                                        "student_uuid": target_stu_id,
                                        "target_samples": target_samples,
                                        "current_samples": 0,
                                        "ticket": ticket,
                                        "prompt": "Look directly at camera",
                                    }
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Could not start session: {ex}")
                        else:
                            active_sess = st.session_state["face_session"]
                            col_preview, col_controls = st.columns([3, 2])
                            with col_preview:
                                stream_url = f"{api.base_url}/stream/0?ticket={active_sess['ticket']}"
                                st.markdown(f'<img src="{stream_url}" width="100%" style="border-radius:8px; border:2px solid #4CAF50;" />', unsafe_allow_html=True)
                            with col_controls:
                                st.markdown(f"#### Prompt: **{active_sess.get('prompt', 'Look at camera')}**")
                                progress = min(1.0, active_sess["current_samples"] / active_sess["target_samples"])
                                st.progress(progress)
                                st.caption(f"Captured: {active_sess['current_samples']} / {active_sess['target_samples']}")

                                if st.button("📸 Capture Frame Sample", use_container_width=True):
                                    try:
                                        cap_res = api.capture_face_sample(target_stu_id, active_sess["session_id"])
                                        active_sess["current_samples"] = cap_res["current_samples"]
                                        active_sess["prompt"] = cap_res["pose_prompt"]
                                        if active_sess["current_samples"] >= active_sess["target_samples"]:
                                            st.balloons()
                                            st.success("🎉 Target face samples reached! (Proceed to commit in Phase 11-12)")
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Capture failed: {ex}")

                                if st.button("❌ Cancel & Release Camera", use_container_width=True):
                                    api.cancel_face_session(target_stu_id, active_sess["session_id"])
                                    del st.session_state["face_session"]
                                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading student: {e}")

elif selected_page == "📊 Dashboard":
    st.header("📊 System Overview")
    st.info("System Dashboard KPIs and recent activity (Coming in Phase 16 & 26)")

elif selected_page == "📹 Live Attendance":
    st.header("📹 Live Attendance Recognition")
    st.info("Live webcam face recognition & attendance marking (Coming in Phase 14-15)")

elif selected_page == "📋 Attendance Records":
    st.header("📋 Attendance Records")
    st.info("Historical attendance records and filters (Coming in Phase 15)")

elif selected_page == "📈 Reports":
    st.header("📈 Reports & Exports")
    st.info("Attendance reporting & CSV exports (Coming in Phase 30)")

elif selected_page == "🛡️ Live Monitoring":
    st.header("🛡️ Campus Security Monitoring")
    st.info("Multi-camera live surveillance (Security Module - Friend's scope)")

elif selected_page == "⚠️ Alerts":
    st.header("⚠️ Security Alerts")
    st.info("Real-time intrusion & blacklist alerts (Security Module - Friend's scope)")

elif selected_page == "🚫 Blacklist":
    st.header("🚫 Blacklist Management")
    st.info("Campus blacklist registry (Security Module - Friend's scope)")

elif selected_page == "🔍 Detection Events":
    st.header("🔍 Detection Events")
    st.info("All raw detection sightings (Security Module - Friend's scope)")

elif selected_page == "📍 Movement Tracking":
    st.header("📍 Movement Tracking")
    st.info("Sightings timeline (Security Module - Friend's scope)")

elif selected_page == "📷 Cameras":
    st.header("📷 Camera Management")
    st.info("Camera registry & status (Coming in Phase 22)")

elif selected_page == "👤 Users":
    st.header("👤 User Management")
    st.info("System administrator & operator accounts")

elif selected_page == "⚙️ Settings":
    st.header("⚙️ System Settings")
    st.info("Recognition thresholds and system parameters")
