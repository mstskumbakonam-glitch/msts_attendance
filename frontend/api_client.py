"""
Frontend API Client for communicating with the FastAPI backend.
Handles JWT authentication, headers, error wrapping, and auto-logout on 401.
"""
import os
from typing import Any, Dict, Optional
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = st.session_state.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        if response.status_code == 401:
            # Clear token on 401 and trigger re-auth
            st.session_state["token"] = None
            st.session_state["user"] = None
            try:
                err_data = response.json()
                msg = err_data.get("error", {}).get("message", "Session expired. Please log in again.")
            except Exception:
                msg = "Session expired. Please log in again."
            raise ValueError(msg)

        if not response.ok:
            try:
                err_data = response.json()
                msg = err_data.get("error", {}).get("message", f"HTTP Error {response.status_code}")
            except Exception:
                msg = f"HTTP Error {response.status_code}: {response.text}"
            raise ValueError(msg)

        if response.status_code == 204:
            return {}

        return response.json()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/login"
        res = requests.post(url, json={"username": username, "password": password})
        data = self._handle_response(res)
        st.session_state["token"] = data["access_token"]
        # Fetch profile
        user_info = self.get_me()
        st.session_state["user"] = user_info
        return user_info

    def logout(self) -> None:
        try:
            url = f"{self.base_url}/auth/logout"
            requests.post(url, headers=self._get_headers())
        except Exception:
            pass
        finally:
            st.session_state["token"] = None
            st.session_state["user"] = None

    def get_me(self) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/me"
        res = requests.get(url, headers=self._get_headers())
        return self._handle_response(res)

    def list_students(
        self,
        q: Optional[str] = None,
        department: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/students"
        params: Dict[str, Any] = {"page": page, "size": size}
        if q:
            params["q"] = q
        if department:
            params["department"] = department
        if year:
            params["year"] = year
        if status:
            params["status"] = status

        res = requests.get(url, params=params, headers=self._get_headers())
        return self._handle_response(res)

    def get_student(self, student_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/students/{student_id}"
        res = requests.get(url, headers=self._get_headers())
        return self._handle_response(res)

    def create_student(
        self,
        student_id: str,
        name: str,
        department: str,
        year: int,
        consent: bool,
        consent_version: str = "v1.0",
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/students"
        payload = {
            "student_id": student_id,
            "name": name,
            "department": department,
            "year": year,
            "consent": consent,
            "consent_version": consent_version,
        }
        res = requests.post(url, json=payload, headers=self._get_headers())
        return self._handle_response(res)

    def update_student(self, student_uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/students/{student_uuid}"
        res = requests.patch(url, json=data, headers=self._get_headers())
        return self._handle_response(res)

    def deactivate_student(self, student_uuid: str) -> None:
        url = f"{self.base_url}/students/{student_uuid}"
        res = requests.delete(url, headers=self._get_headers())
        self._handle_response(res)

    def get_stream_ticket(self, camera_id: str = "0") -> str:
        url = f"{self.base_url}/stream/ticket"
        res = requests.post(url, json={"camera_id": camera_id}, headers=self._get_headers())
        data = self._handle_response(res)
        return data["ticket"]

    def create_face_session(self, student_uuid: str, target_samples: int = 30) -> Dict[str, Any]:
        url = f"{self.base_url}/students/{student_uuid}/face/session"
        res = requests.post(url, json={"target_samples": target_samples}, headers=self._get_headers())
        return self._handle_response(res)

    def capture_face_sample(self, student_uuid: str, session_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/students/{student_uuid}/face/session/{session_id}/capture"
        res = requests.post(url, headers=self._get_headers())
        return self._handle_response(res)

    def cancel_face_session(self, student_uuid: str, session_id: str) -> None:
        url = f"{self.base_url}/students/{student_uuid}/face/session/{session_id}"
        res = requests.delete(url, headers=self._get_headers())
        self._handle_response(res)
