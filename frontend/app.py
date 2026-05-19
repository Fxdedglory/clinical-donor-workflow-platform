import streamlit as st
from components.api import get_json, login, logout, patch_json
from components.ui import apply_theme
from views import admin_portal, audit_logs, role_center, role_workspace

st.set_page_config(
    page_title="Clinical Donor Workflow",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


ADMIN_PAGE_RENDERERS = {
    "admin_users": admin_portal.render,
    "audit_administration": audit_logs.render,
    "responsibility_center": role_center.render,
}


def render_login() -> None:
    left, right = st.columns([0.75, 1.25])
    with left:
        st.title("Clinical Donor Workflow")
        st.caption("Role-centered enterprise operations login")
        with st.form("login_form"):
            username = st.text_input("Username", value="sysadmin")
            password = st.text_input("Password", value="ClinicalDemo!2026", type="password")
            submitted = st.form_submit_button("Sign In")
        if submitted and login(username, password):
            st.rerun()
    with right:
        st.subheader("Department Workspaces")
        st.write("Default password: `ClinicalDemo!2026`")
        st.write("Try `intake`, `clinical`, `qa`, `vendorops`, `opsmanager`, `analyst`, or `sysadmin`.")
        st.info("Each role now receives a different workspace, queue, navigation model, KPI set, and workflow action surface.")


def workspace_request_path(preview_role_id: int | None) -> str:
    if preview_role_id:
        return f"/api/workspaces/me?preview_role_id={preview_role_id}"
    return "/api/workspaces/me"


def render_notification_bell(workspace: dict, navigation: list[dict]) -> None:
    notifications = workspace.get("notifications", [])
    unread = sum(1 for item in notifications if not item.get("is_read"))
    route_to_label = {item["page_key"]: item["tab_label"] for item in navigation}
    with st.popover(f"Notifications ({unread})", use_container_width=True):
        if not notifications:
            st.caption("No current workflow notifications.")
            return
        for item in notifications[:8]:
            severity = item.get("priority", "Normal")
            st.markdown(f"**{item['title']}**")
            st.caption(f"{severity} - {item['notification_type']}")
            st.write(item["message"])
            target = route_to_label.get(item.get("action_route") or "")
            cols = st.columns([1, 1])
            if target and cols[0].button("Open", key=f"open_notice_{item['notification_id']}"):
                patch_json(f"/api/notifications/{item['notification_id']}/read", {})
                st.session_state.workspace_nav = target
                st.rerun()
            if not item.get("is_read") and cols[1].button("Mark read", key=f"read_notice_{item['notification_id']}"):
                patch_json(f"/api/notifications/{item['notification_id']}/read", {})
                st.rerun()
            st.divider()


if "user" not in st.session_state:
    render_login()
    st.stop()

user = st.session_state.user
permissions = set(user.get("permissions", []))
preview_role_id = None
roles = []

with st.sidebar:
    st.title("Clinical Donor Workflow")
    st.caption(user["full_name"])
    st.caption(user["role_name"])
    if "system.admin" in permissions:
        roles = get_json("/api/admin/roles") or []
        role_options = {role["role_name"]: role["role_id"] for role in roles}
        default_role = user["role_name"] if user["role_name"] in role_options else "System Administrator"
        selected_role = st.radio(
            "Workspace mode",
            list(role_options.keys()) or [default_role],
            index=list(role_options.keys()).index(default_role) if default_role in role_options else 0,
        )
        preview_role_id = role_options.get(selected_role)
        if selected_role != user["role_name"]:
            st.caption("Preview mode: operational queues are shown as role workspace previews.")

workspace = get_json(workspace_request_path(preview_role_id)) or {}
if not workspace:
    st.error("Workspace configuration is unavailable. Run database migrations and seed data.")
    st.stop()

navigation = workspace.get("navigation", [])
nav_labels = [item["tab_label"] for item in navigation]
if not nav_labels:
    st.error("No visible workspace tabs are configured for this role.")
    st.stop()
if st.session_state.get("workspace_nav") not in nav_labels:
    st.session_state.workspace_nav = nav_labels[0]

with st.sidebar:
    st.markdown(
        f"""
        <div class="workspace-card">
            <div>{workspace["active_role"]}</div>
            <strong>{workspace["workspace"]["workspace_name"]}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selection = st.radio("Navigation", nav_labels, label_visibility="collapsed", key="workspace_nav")
    st.divider()
    if st.button("Logout"):
        logout()
        st.rerun()
    st.caption("FastAPI - PostgreSQL - Streamlit - QMS")

selected_page = next(item for item in navigation if item["tab_label"] == selection)
top_left, top_right = st.columns([0.78, 0.22])
with top_right:
    render_notification_bell(workspace, navigation)

renderer = ADMIN_PAGE_RENDERERS.get(selected_page["page_key"])
if renderer:
    renderer()
else:
    role_workspace.render(workspace, selected_page["page_key"], selected_page["tab_label"])
