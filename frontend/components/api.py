import os
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
ACCESS_COOKIE = "cdwp_fe_access_token"
REFRESH_COOKIE = "cdwp_fe_refresh_token"
SIDEBAR_COOKIE = "cdwp_sidebar_compact"


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
        persist_auth_cookies()
        return True
    except requests.RequestException:
        st.session_state.pop("access_token", None)
        st.session_state.pop("refresh_token", None)
        st.session_state.pop("user", None)
        return False


def _cookie_value(name: str) -> str | None:
    cookies = getattr(getattr(st, "context", None), "cookies", {}) or {}
    value = cookies.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _set_cookie_script(assignments: dict[str, str | None], *, days: int = 14) -> None:
    commands: list[str] = []
    for key, value in assignments.items():
        if value is None:
            commands.append(f"document.cookie = '{key}=; Max-Age=0; path=/; SameSite=Lax';")
        else:
            safe_value = str(value).replace("\\", "\\\\").replace("'", "\\'")
            commands.append(
                "document.cookie = "
                f"'{key}=' + encodeURIComponent('{safe_value}') + '; Max-Age={days * 86400}; path=/; SameSite=Lax';"
            )
    components.html(f"<script>{''.join(commands)}</script>", height=0)


def persist_auth_cookies() -> None:
    access = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if access and refresh:
        _set_cookie_script({ACCESS_COOKIE: access, REFRESH_COOKIE: refresh})


def clear_auth_cookies() -> None:
    _set_cookie_script({ACCESS_COOKIE: None, REFRESH_COOKIE: None})


def persist_sidebar_state() -> None:
    compact = "1" if st.session_state.get("sidebar_compact") else "0"
    _set_cookie_script({SIDEBAR_COOKIE: compact}, days=30)


def restored_sidebar_compact() -> bool:
    return _cookie_value(SIDEBAR_COOKIE) == "1"


def restore_session_from_cookies() -> bool:
    if st.session_state.get("user"):
        return True
    access = _cookie_value(ACCESS_COOKIE)
    refresh = _cookie_value(REFRESH_COOKIE)
    if not access and not refresh:
        return False
    if access:
        st.session_state.access_token = access
    if refresh:
        st.session_state.refresh_token = refresh
    try:
        response = requests.get(f"{API_URL}/api/auth/me", timeout=12, headers=_auth_headers())
        if response.status_code == 401 and _refresh_token():
            response = requests.get(f"{API_URL}/api/auth/me", timeout=12, headers=_auth_headers())
        response.raise_for_status()
        st.session_state.user = response.json()
        persist_auth_cookies()
        return True
    except requests.RequestException:
        st.session_state.pop("access_token", None)
        st.session_state.pop("refresh_token", None)
        st.session_state.pop("user", None)
        clear_auth_cookies()
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
    if payload.get("mfa_required"):
        st.session_state.pending_mfa = payload
        st.session_state.pending_mfa_username = username
        return False
    st.session_state.access_token = payload["access_token"]
    st.session_state.refresh_token = payload["refresh_token"]
    st.session_state.user = payload["user"]
    st.session_state.pop("pending_mfa", None)
    st.session_state.pop("pending_mfa_username", None)
    persist_auth_cookies()
    return True


def verify_mfa(code: str) -> bool:
    challenge = st.session_state.get("pending_mfa") or {}
    token = challenge.get("mfa_token")
    if not token:
        st.error("MFA challenge expired. Sign in again.")
        return False
    try:
        response = requests.post(
            f"{API_URL}/api/auth/mfa/verify",
            json={"mfa_token": token, "code": code},
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        st.error(f"MFA verification failed: {exc}")
        return False
    payload = response.json()
    st.session_state.access_token = payload["access_token"]
    st.session_state.refresh_token = payload["refresh_token"]
    st.session_state.user = payload["user"]
    st.session_state.pop("pending_mfa", None)
    st.session_state.pop("pending_mfa_username", None)
    persist_auth_cookies()
    return True


def logout() -> None:
    if st.session_state.get("access_token"):
        api_request("POST", "/api/auth/logout")
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.session_state.pop("user", None)
    st.session_state.pop("pending_mfa", None)
    clear_auth_cookies()

