from urllib.parse import quote

import streamlit as st
from components.api import get_json, login, logout, patch_json, post_json
from components.ui import apply_theme
from views import admin_portal, audit_logs, functional_routes, role_center, role_workspace

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


def _query_value(key: str) -> str | None:
    value = st.query_params.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _preview_param(preview_role_id: int | None) -> str:
    return f"&preview_role_id={preview_role_id}" if preview_role_id else ""


def set_route(route_path: str) -> None:
    st.query_params["route"] = route_path


def render_login() -> None:
    left, right = st.columns([0.75, 1.25])
    with left:
        st.title("Clinical Donor Workflow")
        st.caption("Function-first enterprise operations login")
        with st.form("login_form"):
            username = st.text_input("Username", value="sysadmin")
            password = st.text_input("Password", value="ClinicalDemo!2026", type="password")
            submitted = st.form_submit_button("Sign In")
        if submitted and login(username, password):
            set_route("/")
            st.rerun()
    with right:
        st.subheader("Enterprise Functional Routes")
        st.write("Default password: `ClinicalDemo!2026`")
        st.write("Try `intake`, `clinical`, `qa`, `vendorops`, `opsmanager`, `analyst`, or `sysadmin`.")
        st.info("Routes now model enterprise functions and master data. Role determines visibility, actions, widgets, and operational context.")


def workspace_request_path(preview_role_id: int | None) -> str:
    if preview_role_id:
        return f"/api/workspaces/me?preview_role_id={preview_role_id}"
    return "/api/workspaces/me"


def navigation_request_path(preview_role_id: int | None) -> str:
    if preview_role_id:
        return f"/api/routes/navigation?preview_role_id={preview_role_id}"
    return "/api/routes/navigation"


def route_context_request_path(route_path: str, preview_role_id: int | None) -> str:
    return f"/api/routes/resolve?route={quote(route_path, safe='')}{_preview_param(preview_role_id)}"


def search_request_path(query: str, preview_role_id: int | None) -> str:
    return f"/api/routes/search?q={quote(query, safe='')}{_preview_param(preview_role_id)}"


def render_notification_bell(workspace: dict) -> None:
    notifications = workspace.get("notifications", [])
    unread = sum(1 for item in notifications if not item.get("is_read"))
    with st.popover(f"Notifications ({unread})", width="stretch"):
        if not notifications:
            st.caption("No current workflow notifications.")
            return
        for item in notifications[:10]:
            severity = item.get("priority", "Normal")
            st.markdown(f"**{item['title']}**")
            st.caption(f"{severity} - {item['notification_type']}")
            st.write(item["message"])
            context = item.get("workflow_context") or {}
            state = context.get("workflow_state")
            queue = context.get("queue_name")
            route_path = context.get("route_path") or item.get("action_route")
            if state or queue:
                st.caption(" | ".join(part for part in [state, queue] if part))
            cols = st.columns([1, 1])
            if (route_path or item.get("related_record_id")) and cols[0].button("Open", key=f"open_notice_{item['notification_id']}"):
                route = post_json(f"/api/notifications/{item['notification_id']}/open", {})
                if route and route.get("route_path"):
                    set_route(route["route_path"])
                st.rerun()
            if not item.get("is_read") and cols[1].button("Mark read", key=f"read_notice_{item['notification_id']}"):
                patch_json(f"/api/notifications/{item['notification_id']}/read", {})
                st.rerun()
            st.divider()


def render_functional_navigation(navigation: dict) -> None:
    current_route = _query_value("route") or navigation.get("default_route") or "/dashboard"
    for group in navigation.get("groups", []):
        st.markdown(f"**{group['group']}**")
        for item in group["items"]:
            active = current_route == item["route_path"] or current_route.startswith(f"{item['route_path']}/")
            label = f"{'[x]' if active else '[ ]'} {item['label']}"
            if st.button(label, key=f"nav_{item['route_path']}", width="stretch"):
                set_route(item["route_path"])
                st.rerun()
        st.divider()


def render_enterprise_search(preview_role_id: int | None) -> None:
    with st.form("enterprise_search_form"):
        query = st.text_input("Enterprise Search", placeholder="Donor, CAPA, incident, AI rule, workflow...")
        submitted = st.form_submit_button("Search")
    if submitted and query:
        st.query_params["search"] = query
    active_query = _query_value("search")
    if not active_query:
        return
    results = get_json(search_request_path(active_query, preview_role_id)) or []
    st.caption(f"Results for `{active_query}`")
    if not results:
        st.info("No matching enterprise records.")
        return
    for index, result in enumerate(results[:8]):
        st.write(f"**{result['title']}**")
        st.caption(f"{result['entity_type']} - {result['subtitle']}")
        if st.button("Open", key=f"search_{index}_{result['route_path']}", width="stretch"):
            set_route(result["route_path"])
            if "search" in st.query_params:
                del st.query_params["search"]
            st.rerun()


if "user" not in st.session_state:
    render_login()
    st.stop()

user = st.session_state.user
permissions = set(user.get("permissions", []))
preview_role_id = None

with st.sidebar:
    st.title("Clinical Donor Workflow")
    st.caption(user["full_name"])
    st.caption(user["role_name"])
    if "system.admin" in permissions:
        roles = get_json("/api/admin/roles") or []
        role_options = {role["role_name"]: role["role_id"] for role in roles}
        default_role = user["role_name"] if user["role_name"] in role_options else "System Administrator"
        selected_role = st.radio(
            "Visibility lens",
            list(role_options.keys()) or [default_role],
            index=list(role_options.keys()).index(default_role) if default_role in role_options else 0,
        )
        preview_role_id = role_options.get(selected_role)
        if selected_role != user["role_name"]:
            st.caption("Preview mode: routes stay function-based while visibility changes by role.")

navigation = get_json(navigation_request_path(preview_role_id)) or {}
if not navigation:
    st.error("Functional route configuration is unavailable. Run database migrations and seed data.")
    st.stop()

current_route = _query_value("route") or navigation.get("default_route") or "/dashboard"
if current_route == "/":
    current_route = navigation.get("default_route") or "/dashboard"
    st.query_params["route"] = current_route

workspace = get_json(workspace_request_path(preview_role_id)) or {}
if not workspace:
    st.error("Workspace configuration is unavailable. Run database migrations and seed data.")
    st.stop()

with st.sidebar:
    st.markdown(
        f"""
        <div class="workspace-card">
            <div>{navigation["active_role"]}</div>
            <strong>Functional Route Visibility</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_enterprise_search(preview_role_id)
    st.divider()
    render_functional_navigation(navigation)
    if st.button("Logout"):
        logout()
        st.query_params.clear()
        st.rerun()
    st.caption("FastAPI - PostgreSQL - Streamlit - QMS")

context = get_json(route_context_request_path(current_route, preview_role_id)) or {}
if not context:
    st.error("Route context could not be resolved.")
    st.stop()

top_left, top_right = st.columns([0.78, 0.22])
with top_left:
    st.caption(f"Route: `{context['route_path']}`")
with top_right:
    render_notification_bell(workspace)

page_key = context.get("page_key")
if context.get("kind") == "admin":
    renderer = ADMIN_PAGE_RENDERERS.get(page_key)
    if renderer:
        renderer()
    else:
        role_workspace.render(workspace, page_key, context["label"])
else:
    functional_routes.render(context)
