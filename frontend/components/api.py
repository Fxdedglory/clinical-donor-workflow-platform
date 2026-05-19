import os
from typing import Any

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")


def api_request(method: str, path: str, **kwargs: Any) -> Any | None:
    url = f"{API_URL}{path}"
    try:
        response = requests.request(method, url, timeout=12, **kwargs)
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

