from __future__ import annotations

from urllib.parse import quote

import pandas as pd
import streamlit as st
from components.api import get_json, login, logout, patch_json, post_json
from components.ui import (
    apply_theme,
    dataframe,
    empty_state,
    last_updated,
    page_header,
)
from views import admin_portal, audit_logs, functional_routes, role_center, role_workspace

st.set_page_config(
    page_title="Clinical Donor Workflow",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

if "sidebar_compact" not in st.session_state:
    st.session_state.sidebar_compact = False
if "pinned_records" not in st.session_state:
    st.session_state.pinned_records = []
if "recently_viewed" not in st.session_state:
    st.session_state.recently_viewed = []
if "profile_preferences" not in st.session_state:
    st.session_state.profile_preferences = {
        "digest": True,
        "sla_alerts": True,
        "qms_alerts": True,
        "ai_governance_alerts": True,
    }

apply_theme(compact_sidebar=st.session_state.sidebar_compact)


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


def _clear_query_value(key: str) -> None:
    if key in st.query_params:
        del st.query_params[key]


def _route_button(label: str, route_path: str, key: str, *, width: str = "stretch") -> bool:
    if st.button(label, key=key, width=width):
        set_route(route_path)
        st.rerun()
        return True
    return False


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


def _current_route(navigation: dict | None = None) -> str:
    route = _query_value("route")
    if route:
        return route
    if navigation:
        return navigation.get("default_route") or "/dashboard"
    return "/dashboard"


def _all_available_routes(navigation: dict) -> dict[str, dict]:
    routes: dict[str, dict] = {}
    for group in navigation.get("groups", []):
        for item in group.get("items", []):
            routes[item["route_path"]] = item
    return routes


def render_login() -> None:
    st.markdown("<div style='height: 7vh'></div>", unsafe_allow_html=True)
    left, center, right = st.columns([0.55, 1.05, 0.55])
    with center:
        st.title("Clinical Donor Workflow Platform")
        st.caption(
            "Donor eligibility, recovery suitability, processing release, and QMS workflow operations"
        )
        with st.form("login_form", border=True):
            username = st.text_input("Username", value="sysadmin")
            password = st.text_input("Password", value="ClinicalDemo!2026", type="password")
            submitted = st.form_submit_button("Sign In", width="stretch")
        if submitted and login(username, password):
            set_route("/")
            st.rerun()

        with st.expander("Demo Accounts", expanded=True):
            st.write("Default password: `ClinicalDemo!2026`")
            st.write("`intake`  `clinical`  `qa`  `vendorops`  `opsmanager`  `analyst`  `sysadmin`")


def render_notification_bell(workspace: dict) -> None:
    notifications = workspace.get("notifications", [])
    unread = sum(1 for item in notifications if not item.get("is_read"))
    label = f"Alerts {unread}" if unread else "Alerts"
    with st.popover(label, width="stretch"):
        if not notifications:
            empty_state("No workflow notifications are waiting.")
            return
        for item in notifications[:12]:
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
            if (route_path or item.get("related_record_id")) and cols[0].button(
                "Open", key=f"open_notice_{item['notification_id']}"
            ):
                route = post_json(f"/api/notifications/{item['notification_id']}/open", {})
                if route and route.get("route_path"):
                    set_route(route["route_path"])
                st.rerun()
            if not item.get("is_read") and cols[1].button(
                "Mark read", key=f"read_notice_{item['notification_id']}"
            ):
                patch_json(f"/api/notifications/{item['notification_id']}/read", {})
                st.rerun()
            st.divider()


def _render_quick_actions(active_role: str | None) -> None:
    if active_role == "System Administrator":
        actions = [
            ("New User", "/admin/users"),
            ("Workflow Configuration", "/admin/workflow-engine"),
            ("Eligibility Rules", "/eligibility-rule"),
            ("Audit Logs", "/admin/audit-logs"),
        ]
    else:
        actions = [
            ("New Referral", "/referral"),
            ("Open CAPA", "/capa"),
            ("Create Investigation", "/investigation"),
            ("Create Vendor Incident", "/incident"),
            ("Run Eligibility Review", "/screening"),
        ]
    with st.popover("+ New", width="stretch"):
        for label, path in actions:
            _route_button(label, path, key=f"quick_{path}")


def _render_user_menu(user: dict) -> None:
    with st.popover(user["full_name"], width="stretch"):
        _route_button("Profile", "/profile", key="profile_link")
        if st.button("Preferences", key="preferences_link", width="stretch"):
            set_route("/profile")
            st.query_params["profile_tab"] = "preferences"
            st.rerun()
        _route_button("Notifications", "/notification", key="notifications_link")
        st.divider()
        if st.button("Sign Out", key="sign_out", width="stretch"):
            logout()
            st.query_params.clear()
            st.rerun()


def _render_global_search(preview_role_id: int | None) -> None:
    with st.form("global_search_form", border=False):
        cols = st.columns([0.82, 0.18])
        query = cols[0].text_input(
            "Global search",
            label_visibility="collapsed",
            placeholder="Search donors, CAPAs, investigations, releases...",
        )
        submitted = cols[1].form_submit_button("Search", width="stretch")
    if submitted and query:
        st.query_params["search"] = query


def _render_search_results(preview_role_id: int | None) -> None:
    active_query = _query_value("search")
    if not active_query:
        return
    results = get_json(search_request_path(active_query, preview_role_id)) or []
    st.markdown("<div class='operational-card'>", unsafe_allow_html=True)
    cols = st.columns([0.8, 0.2])
    cols[0].markdown(f"**Search results for `{active_query}`**")
    if cols[1].button("Clear", key="clear_search", width="stretch"):
        _clear_query_value("search")
        st.rerun()
    if not results:
        empty_state("No matching operational records found.")
    else:
        for index, result in enumerate(results[:10]):
            row = st.columns([0.72, 0.18, 0.10])
            row[0].markdown(f"**{result['title']}**")
            row[0].caption(f"{result['entity_type']} - {result['subtitle']}")
            row[1].write(result["entity_type"])
            if row[2].button("Open", key=f"search_{index}_{result['route_path']}"):
                set_route(result["route_path"])
                _clear_query_value("search")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_system_notice() -> None:
    st.markdown(
        "<div class='system-notice'><strong>System Notice:</strong> "
        "NorthStar Labs imports are delayed; NAT result packets may require manual verification.</div>",
        unsafe_allow_html=True,
    )


def render_top_bar(user: dict, workspace: dict, preview_role_id: int | None) -> None:
    left, search, quick, notices, profile = st.columns([0.06, 0.47, 0.10, 0.14, 0.23])
    if left.button("☰", key="toggle_sidebar", width="stretch"):
        st.session_state.sidebar_compact = not st.session_state.sidebar_compact
        st.rerun()
    with search:
        _render_global_search(preview_role_id)
    with quick:
        _render_quick_actions(workspace.get("active_role"))
    with notices:
        render_notification_bell(workspace)
    with profile:
        _render_user_menu(user)
    _render_system_notice()
    _render_search_results(preview_role_id)


def _preferred_route(routes: dict[str, dict], options: list[str]) -> str | None:
    for path in options:
        if path in routes:
            return path
    return None


def _sidebar_label(icon: str, label: str) -> str:
    return icon if st.session_state.sidebar_compact else f"{icon} {label}"


def _nav_item(label: str, route_path: str, icon: str, current_route: str, key_prefix: str) -> None:
    active = current_route == route_path or current_route.startswith(f"{route_path}/")
    prefix = ">" if active else " "
    _route_button(
        _sidebar_label(icon, f"{prefix} {label}"),
        route_path,
        key=f"nav_{key_prefix}_{route_path}",
    )


def render_operational_navigation(navigation: dict) -> None:
    routes = _all_available_routes(navigation)
    current_route = _current_route(navigation)
    admin_only = navigation.get("active_role") == "System Administrator"

    work_items: list[tuple[str, str, str]] = []
    for label, options, icon in [
        ("Assigned Tasks", ["/task"], "☑"),
        ("Pending Reviews", ["/medical-review", "/qa-review", "/referral", "/screening"], "◇"),
        ("Escalations", ["/escalation"], "!"),
        ("SLA Risks", ["/sla", "/incident"], "⧖"),
        ("Recent Notifications", ["/notification"], "•"),
        ("Dashboard", ["/dashboard"], "▦"),
    ]:
        path = _preferred_route(routes, options)
        if path:
            work_items.append((label, path, icon))

    record_items: list[tuple[str, str, str]] = []
    for label, path, icon in [
        ("Donors", "/donor", "○"),
        ("Reviews", "/medical-review", "◇"),
        ("Processing Release", "/processing-release", "▤"),
        ("CAPAs", "/capa", "△"),
        ("Investigations", "/investigation", "?"),
        ("Notifications", "/notification", "•"),
    ]:
        if path in routes:
            record_items.append((label, path, icon))

    admin_items: list[tuple[str, str, str]] = []
    for label, path, icon in [
        ("Users", "/admin/users", "○"),
        ("Roles", "/admin/roles", "◇"),
        ("Workflow Configuration", "/admin/workflow-engine", "▦"),
        ("System Health", "/admin/system-health", "+"),
        ("Eligibility Rules", "/eligibility-rule", "✓"),
        ("Audit Logs", "/admin/audit-logs", "▤"),
    ]:
        if path in routes:
            admin_items.append((label, path, icon))

    if not admin_only:
        st.markdown("**My Work**")
        for label, path, icon in work_items:
            _nav_item(label, path, icon, current_route, "work")

        st.divider()
        if not st.session_state.sidebar_compact:
            st.markdown("**Operations**")
        for label, path, icon in record_items:
            _nav_item(label, path, icon, current_route, "records")

    if admin_items:
        if not admin_only:
            st.divider()
        if not st.session_state.sidebar_compact:
            st.markdown("**Administration**")
        for label, path, icon in admin_items:
            _nav_item(label, path, icon, current_route, "admin")


def _record_title(context: dict) -> str:
    entity = context.get("entity") or {}
    for field in [
        "donor_identifier",
        "release_identifier",
        "deviation_code",
        "capa_code",
        "request_id",
        "ticket_number",
        "rule_name",
        "test_name",
        "tissue_name",
        "username",
    ]:
        if entity.get(field):
            return str(entity[field])
    if context.get("record_id"):
        return f"{context.get('label', 'Record')} {context['record_id']}"
    return context.get("label", "Record")


def _remember_context(context: dict) -> None:
    if context.get("kind") != "detail":
        return
    item = {"title": _record_title(context), "route_path": context["route_path"]}
    recent = [row for row in st.session_state.recently_viewed if row["route_path"] != item["route_path"]]
    st.session_state.recently_viewed = [item, *recent][:8]


def _render_record_shortcuts(context: dict | None = None) -> None:
    if context and context.get("kind") == "detail":
        item = {"title": _record_title(context), "route_path": context["route_path"]}
        pinned_routes = {row["route_path"] for row in st.session_state.pinned_records}
        label = "Unpin Record" if item["route_path"] in pinned_routes else "Pin Record"
        if st.button(label, key=f"pin_{item['route_path']}", width="stretch"):
            if item["route_path"] in pinned_routes:
                st.session_state.pinned_records = [
                    row for row in st.session_state.pinned_records if row["route_path"] != item["route_path"]
                ]
            else:
                st.session_state.pinned_records = [item, *st.session_state.pinned_records][:10]
            st.rerun()

    if st.session_state.pinned_records:
        st.markdown("**Pinned**")
        for index, item in enumerate(st.session_state.pinned_records[:6]):
            _route_button(item["title"], item["route_path"], key=f"pin_open_{index}")
    if st.session_state.recently_viewed:
        st.markdown("**Recently Viewed**")
        for index, item in enumerate(st.session_state.recently_viewed[:6]):
            _route_button(item["title"], item["route_path"], key=f"recent_open_{index}")


def render_profile(user: dict, permissions: set[str]) -> None:
    page_header("Profile", "Manage personal preferences and account settings.")
    tab = _query_value("profile_tab") or "profile"
    profile_tab, pref_tab, security_tab = st.tabs(["Profile", "Preferences", "Security"])
    with profile_tab:
        with st.form("profile_form"):
            display_name = st.text_input("Display name", value=user["full_name"])
            email = st.text_input("Email", value=user["email"])
            avatar = st.file_uploader("Avatar", type=["png", "jpg", "jpeg"])
            submitted = st.form_submit_button("Save Profile")
        if submitted:
            updated = patch_json("/api/auth/me", {"full_name": display_name, "email": email})
            if updated:
                st.session_state.user = updated
                st.success("Profile updated.")
                st.rerun()
            elif avatar:
                st.success("Avatar preference saved for this session.")

        st.markdown("<div class='section-title'>Account Details</div>", unsafe_allow_html=True)
        rows = [
            {"field": "User ID", "value": user["user_id"]},
            {"field": "Username", "value": user["username"]},
            {"field": "Role", "value": user["role_name"]},
            {"field": "Last Login", "value": user.get("last_login") or ""},
        ]
        dataframe(rows, height=180)
        with st.expander("Permissions", expanded="system.admin" in permissions):
            dataframe([{"permission": item} for item in sorted(permissions)], height=260)

    with pref_tab:
        prefs = st.session_state.profile_preferences
        with st.form("preference_form"):
            prefs["digest"] = st.checkbox("Daily operations digest", value=prefs.get("digest", True))
            prefs["sla_alerts"] = st.checkbox("SLA and overdue work alerts", value=prefs.get("sla_alerts", True))
            prefs["qms_alerts"] = st.checkbox("QMS, CAPA, and deviation alerts", value=prefs.get("qms_alerts", True))
            prefs["ai_governance_alerts"] = st.checkbox(
                "AI governance and rule performance alerts",
                value=prefs.get("ai_governance_alerts", True),
            )
            saved = st.form_submit_button("Save Preferences")
        if saved:
            st.session_state.profile_preferences = prefs
            st.success("Notification preferences updated for this session.")

    with security_tab:
        with st.form("password_form"):
            current_password = st.text_input("Current password", type="password")
            new_password = st.text_input("New password", type="password")
            confirmed_password = st.text_input("Confirm new password", type="password")
            changed = st.form_submit_button("Update Password")
        if changed:
            if not new_password or new_password != confirmed_password:
                st.error("New password confirmation does not match.")
            else:
                result = patch_json(
                    "/api/auth/me/password",
                    {"current_password": current_password, "new_password": new_password},
                )
                if result:
                    st.success("Password updated.")

    if tab == "preferences":
        st.caption("Preferences are available in the Preferences tab.")


def _task_dataframe(records: list[dict], key: str) -> None:
    if not records:
        empty_state("No work is currently assigned.")
        return
    columns = [
        "task_id",
        "title",
        "priority",
        "status",
        "workflow_state",
        "queue_name",
        "due_date",
        "route_path",
    ]
    frame = pd.DataFrame(records)
    keep = [column for column in columns if column in frame.columns]
    st.dataframe(frame[keep], width="stretch", height=280, hide_index=True)
    selectable = [row for row in records if row.get("route_path")]
    if selectable:
        selected = st.selectbox(
            "Open work item",
            [f"{row['route_path']} | {row.get('title') or row.get('task_id')}" for row in selectable],
            key=key,
        )
        _route_button("Open Selected", selected.split(" | ")[0], key=f"open_{key}")


def render_todays_operations(workspace: dict, context: dict) -> None:
    page_header("Today's Operations", "Assigned work, SLA risks, escalations, and recent activity.")
    last_updated()
    kpis = workspace.get("kpis", {})
    metrics = list(kpis.items())[:5]
    if metrics:
        columns = st.columns(len(metrics))
        for index, (label, value) in enumerate(metrics):
            columns[index].metric(label, value)

    queue = workspace.get("queue", [])
    widget_data = workspace.get("widget_data", {})
    notifications = workspace.get("notifications", [])
    escalations = widget_data.get("role_escalations") or [
        row for row in queue if row.get("status") == "Escalated" or row.get("priority") in {"Critical", "High"}
    ]
    sla_risks = [
        row
        for row in queue
        if row.get("priority") in {"Critical", "High"} or row.get("status") in {"Blocked", "Escalated"}
    ][:40]

    left, right = st.columns([1.2, 0.8])
    with left:
        st.markdown("<div class='section-title'>Assigned Work</div>", unsafe_allow_html=True)
        _task_dataframe(queue[:60], "home_queue")
    with right:
        st.markdown("<div class='section-title'>SLA Risks</div>", unsafe_allow_html=True)
        _task_dataframe(sla_risks[:20], "home_sla")

    lower_left, lower_right = st.columns([0.95, 1.05])
    with lower_left:
        st.markdown("<div class='section-title'>Escalations</div>", unsafe_allow_html=True)
        if escalations:
            dataframe(escalations[:20], height=260)
        else:
            empty_state("No escalations currently assigned.")
    with lower_right:
        st.markdown("<div class='section-title'>Recent Activity</div>", unsafe_allow_html=True)
        timeline = context.get("timeline") or []
        if timeline:
            dataframe(timeline[:12], columns=["timestamp", "event_type", "summary"], height=260)
        else:
            rows = [
                {
                    "created_at": item.get("created_at"),
                    "priority": item.get("priority"),
                    "title": item.get("title"),
                    "type": item.get("notification_type"),
                }
                for item in notifications[:12]
            ]
            dataframe(rows, height=260) if rows else empty_state("No recent operational activity.")

    analytics = context.get("analytics", {})
    task_rows = analytics.get("task_heatmap", [])
    if task_rows:
        st.markdown("<div class='section-title'>Workflow Analytics</div>", unsafe_allow_html=True)
        functional_routes.render_analytics_visuals(analytics)


if "user" not in st.session_state:
    render_login()
    st.stop()

user = st.session_state.user
permissions = set(user.get("permissions", []))
preview_role_id = None

if "system.admin" in permissions:
    roles = get_json("/api/admin/roles") or []
    role_options = {role["role_name"]: role["role_id"] for role in roles}
    default_role = user["role_name"] if user["role_name"] in role_options else "System Administrator"
    selected_role = default_role
else:
    role_options = {}
    selected_role = user["role_name"]

navigation = get_json(navigation_request_path(preview_role_id)) or {}
if not navigation:
    st.error("Navigation is unavailable. Run database migrations and seed data.")
    st.stop()

current_route = _current_route(navigation)
if current_route == "/":
    current_route = navigation.get("default_route") or "/dashboard"
    st.query_params["route"] = current_route

workspace = get_json(workspace_request_path(preview_role_id)) or {}
if not workspace:
    st.error("Workspace data is unavailable. Run database migrations and seed data.")
    st.stop()

render_top_bar(user, workspace, preview_role_id)

with st.sidebar:
    if not st.session_state.sidebar_compact:
        st.markdown("### Clinical Operations")
    if "system.admin" in permissions and role_options:
        selected_role = st.selectbox(
            "View as",
            list(role_options.keys()) or [default_role],
            index=list(role_options.keys()).index(default_role) if default_role in role_options else 0,
        )
        preview_role_id = role_options.get(selected_role)
        if selected_role != user["role_name"]:
            workspace = get_json(workspace_request_path(preview_role_id)) or workspace
            navigation = get_json(navigation_request_path(preview_role_id)) or navigation
    render_operational_navigation(navigation)

if current_route == "/profile":
    with st.sidebar:
        st.divider()
        _render_record_shortcuts()
    render_profile(user, permissions)
    st.stop()

context = get_json(route_context_request_path(current_route, preview_role_id)) or {}
if not context:
    st.error("This workspace view could not be loaded.")
    st.stop()

_remember_context(context)

with st.sidebar:
    st.divider()
    _render_record_shortcuts(context)

page_key = context.get("page_key")
if context.get("kind") == "admin":
    renderer = ADMIN_PAGE_RENDERERS.get(page_key)
    if renderer:
        renderer()
    else:
        role_workspace.render(workspace, page_key, context["label"])
elif context.get("route_key") == "dashboard":
    render_todays_operations(workspace, context)
else:
    functional_routes.render(context)
