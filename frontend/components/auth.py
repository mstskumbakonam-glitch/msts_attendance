"""
Authentication components for Streamlit frontend.
"""
import streamlit as st
from frontend.api_client import APIClient


def render_login(api: APIClient) -> None:
    st.markdown("## 🔐 Smart Attendance & Security System")
    st.markdown("Please log in to continue.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
                return

            try:
                user = api.login(username, password)
                st.success(f"Welcome, {user.get('username')} ({user.get('role')})!")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def require_auth(api: APIClient) -> bool:
    """Returns True if authenticated, else renders login form and returns False."""
    token = st.session_state.get("token")
    user = st.session_state.get("user")

    if not token or not user:
        render_login(api)
        return False
    return True
