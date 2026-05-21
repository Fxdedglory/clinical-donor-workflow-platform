import streamlit as st
from components.api import get_json
from components.ui import dataframe, last_updated, page_header


def render() -> None:
    page_header("System Health", "Production readiness, service status, sessions, and backup posture.")
    payload = get_json("/api/admin/system-health") or {}
    if not payload:
        st.error("System health is unavailable.")
        return

    last_updated()
    cols = st.columns(4)
    cols[0].metric("Status", payload.get("status", "Unknown"))
    cols[1].metric("Environment", str(payload.get("environment", "")).upper())
    cols[2].metric("Active Sessions", payload.get("active_sessions", 0))
    cols[3].metric("Uptime", f"{int(payload.get('uptime_seconds', 0) / 60)} min")

    st.markdown("<div class='section-title'>Service Checks</div>", unsafe_allow_html=True)
    dataframe(payload.get("checks", []), height=260)

    st.markdown("<div class='section-title'>Deployment Context</div>", unsafe_allow_html=True)
    dataframe(
        [
            {"setting": "Base URL", "value": payload.get("base_url")},
            {"setting": "Version", "value": payload.get("version")},
            {"setting": "Database", "value": payload.get("database_url_masked")},
            {"setting": "Failed Login Events", "value": payload.get("failed_login_events")},
        ],
        height=180,
    )
