"""
Tests for Streamlit dashboard login-gate and authentication requirement.
"""
from streamlit.testing.v1 import AppTest


def test_unauthenticated_visit_shows_only_login_form():
    """Unauthenticated visitor is presented with login form and no dashboard content."""
    at = AppTest.from_file("frontend/app.py", default_timeout=15)
    at.run()

    # Should not throw uncaught exceptions
    assert not at.exception

    # Check for login form inputs
    text_inputs = [ti.label for ti in at.text_input]
    assert "Username" in text_inputs
    assert "Password" in text_inputs

    # Navigation sidebar radio should not be rendered when unauthenticated (due to st.stop())
    assert len(at.radio) == 0
