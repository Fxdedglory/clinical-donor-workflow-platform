import os
from typing import Any

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")


def _auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _refresh_token() -> bool:
    refresh = st.session_state.get("refresh_token")
    if not refresh:
        return False
    try:
        response = requests.post(
            f"{API_URL}/api/auth/refresh",
            json={"refresh_token": refresh},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        st.session_state.access_token = payload["access_token"]
        st.session_state.refresh_token = payload["refresh_token"]
        st.session_state.user = payload["user"]
        return True
    except requests.RequestException:
        st.session_state.pop("access_token", None)
        st.session_state.pop("refresh_token", None)
        st.session_state.pop("user", None)
        return False


def api_request(method: str, path: str, **kwargs: Any) -> Any | None:
    url = f"{API_URL}{path}"
    headers = kwargs.pop("headers", {})
    headers.update(_auth_headers())
    try:
        response = requests.request(method, url, timeout=12, headers=headers, **kwargs)
        if response.status_code == 401 and _refresh_token():
            headers = kwargs.pop("headers", {})
            headers.update(_auth_headers())
            response = requests.request(method, url, timeout=12, headers=headers, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return None
    except requests.RequestException as exc:
        st.error(f"API request failed: {url} ({exc})")
        return None


def get_json(path: str) -> Any | None:
    return api_request("GET", path)


def post_json(path: str, payload: dict[str, Any]) -> Any | None:
    return api_request("POST", path, json=payload)


def patch_json(path: str, payload: dict[str, Any]) -> Any | None:
    return api_request("PATCH", path, json=payload)


def login(username: str, password: str) -> bool:
    try:
        response = requests.post(
            f"{API_URL}/api/auth/login",
            data={"username": username, "password": password},
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        st.error(f"Login failed: {exc}")
        return False

    payload = response.json()
    st.session_state.access_token = payload["access_token"]
    st.session_state.refresh_token = payload["refresh_token"]
    st.session_state.user = payload["user"]
    return True


def logout() -> None:
    if st.session_state.get("access_token"):
        api_request("POST", "/api/auth/logout")
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.session_state.pop("user", None)

