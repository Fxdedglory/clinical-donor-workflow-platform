import streamlit as st
from components.api import get_json, login, logout
from components.ui import apply_theme
from views import (
    admin_portal,
    ai_risk_analysis,
    audit_logs,
    change_control,
    compliance_dashboard,
    dashboard,
    donor_queue,
    donor_review,
    enterprise_operations,
    notification_center,
    role_center,
    task_workbench,
    vendor_sla,
)

st.set_page_config(
    page_title="Clinical Donor Workflow",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

PAGES = {
    "Enterprise Ops": ("dashboard.view", enterprise_operations.render),
    "Dashboard": ("dashboard.view", dashboard.render),
    "Task Workbench": ("tasks.read", task_workbench.render),
    "Notifications": ("notifications.read", notification_center.render),
    "Donor Queue": ("donors.read", donor_queue.render),
    "Donor Review": ("donors.review", donor_review.render),
    "AI Risk Analysis": ("donors.review", ai_risk_analysis.render),
    "Compliance": ("audit.review", compliance_dashboard.render),
    "Audit Logs": ("audit.review", audit_logs.render),
    "Change Control": ("change_control.manage", change_control.render),
    "Vendor SLA": ("vendors.manage", vendor_sla.render),
    "Admin Portal": ("users.manage", admin_portal.render),
    "Responsibility Center": ("dashboard.view", role_center.render),
}


def render_login() -> None:
    left, right = st.columns([0.75, 1.25])
    with left:
        st.title("Clinical Donor Workflow")
        st.caption("Enterprise healthcare operations login")
        with st.form("login_form"):
            username = st.text_input("Username", value="sysadmin")
            password = st.text_input("Password", value="ClinicalDemo!2026", type="password")
            submitted = st.form_submit_button("Sign In")
        if submitted and login(username, password):
            st.rerun()
    with right:
        st.subheader("Demo Roles")
        st.write("Default password: `ClinicalDemo!2026`")
        st.write("Try `sysadmin`, `clinical`, `intake`, `qa`, `vendorops`, or `opsmanager`.")
        st.info("JWT-backed sessions unlock RBAC-protected workflow, admin, notification, and dashboard APIs.")


if "user" not in st.session_state:
    render_login()
    st.stop()

user = st.session_state.user
permissions = set(user.get("permissions", []))

with st.sidebar:
    st.title("Clinical Donor Workflow")
    st.caption(user["full_name"])
    st.caption(user["role_name"])
    unread = get_json("/api/notifications/unread-count") or {"unread_count": 0}
    st.markdown(
        f"""
        <div class="sidebar-notice">
            <div>Unread Notices</div>
            <strong>{unread.get("unread_count", 0)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    visible_pages = {
        label: renderer
        for label, (permission, renderer) in PAGES.items()
        if permission in permissions or "system.admin" in permissions
    }
    selection = st.radio("Navigation", list(visible_pages.keys()), label_visibility="collapsed")
    st.divider()
    if st.button("Logout"):
        logout()
        st.rerun()
    st.caption("FastAPI - PostgreSQL - Streamlit - QMS")

visible_pages[selection]()
