from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import streamlit as st
from components.api import get_json, patch_json, post_json
from components.ui import dataframe, page_header


def _safe_dataframe(records: list[dict[str, Any]], columns: list[str] | None = None, height: int = 380) -> None:
    if not records:
        st.info("No records are currently in this role queue.")
        return
    if columns:
        present = [column for column in columns if column in records[0]]
        dataframe(records, columns=present or None, height=height)
    else:
        dataframe(records, height=height)


def _page_records(workspace: dict, page_key: str) -> list[dict[str, Any]]:
    widget_data = workspace.get("widget_data", {})
    if page_key in widget_data:
        return widget_data[page_key] or []
    if page_key == "role_tasks":
        return widget_data.get("role_tasks") or workspace.get("queue", [])
    if page_key == "role_escalations":
        return widget_data.get("role_escalations") or []
    return []


def _first_queue_task(workspace: dict, page_records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if page_records:
        for row in page_records:
            if row.get("task_id") and row.get("related_record_type") and row.get("related_record_id"):
                return row
    for row in workspace.get("widget_data", {}).get("role_tasks", []):
        if row.get("task_id") and row.get("related_record_type") and row.get("related_record_id"):
            return row
    for row in workspace.get("queue", []):
        if row.get("task_id") and row.get("related_record_type") and row.get("related_record_id"):
            return row
    return None


def _transition_panel(workspace: dict, page_records: list[dict[str, Any]]) -> None:
    actions = workspace.get("allowed_actions", [])
    if not actions:
        return

    st.markdown("<div class='section-title'>Workflow Actions</div>", unsafe_allow_html=True)
    default_task = _first_queue_task(workspace, page_records)
    task_options = {
        f"{row.get('task_id')} | {row.get('title', row.get('donor_id', row.get('ticket_number', 'record')))}": row
        for row in workspace.get("widget_data", {}).get("role_tasks", [])
        if row.get("task_id") and row.get("related_record_type") and row.get("related_record_id")
    }
    with st.form(f"transition_form_{workspace['active_role']}_{len(page_records)}"):
        action_map = {action["action_label"]: action for action in actions}
        action_label = st.selectbox("Action", list(action_map.keys()))
        selected_task = None
        if task_options:
            selected_task_label = st.selectbox("Task or case", list(task_options.keys()))
            selected_task = task_options[selected_task_label]
        record_type = st.text_input(
            "Related record type",
            value=(selected_task or default_task or {}).get("related_record_type", "DonorReview"),
        )
        record_id = st.text_input(
            "Related record ID",
            value=str((selected_task or default_task or {}).get("related_record_id", "")),
        )
        note = st.text_area("Transition note", value="")
        submitted = st.form_submit_button("Route Workflow")
    if submitted:
        task_id = (selected_task or default_task or {}).get("task_id")
        result = post_json(
            "/api/workspaces/transition",
            {
                "action_name": action_map[action_label]["action_name"],
                "related_record_type": record_type,
                "related_record_id": record_id,
                "task_id": task_id,
                "note": note,
            },
        )
        if result:
            st.success(f"Workflow routed to {result['to_state']}.")
            st.rerun()


def _dashboard(workspace: dict) -> None:
    config = workspace["workspace"]
    page_header(config["workspace_name"], config["workspace_purpose"])
    if workspace.get("is_preview"):
        st.info(f"System Administrator previewing the {workspace['active_role']} workspace.")

    kpis = workspace.get("kpis", {})
    metric_columns = st.columns(min(max(len(kpis), 1), 5))
    for index, (label, value) in enumerate(kpis.items()):
        metric_columns[index % len(metric_columns)].metric(label, value)

    widgets = [widget for widget in workspace.get("widgets", []) if widget.get("widget_type") == "table"]
    widget_data = workspace.get("widget_data", {})
    for row_index in range(0, min(len(widgets), 4), 2):
        left, right = st.columns(2)
        for container, widget in zip([left, right], widgets[row_index : row_index + 2], strict=False):
            with container:
                st.markdown(f"<div class='section-title'>{widget['widget_title']}</div>", unsafe_allow_html=True)
                _safe_dataframe(widget_data.get(widget["widget_key"], []), height=260)


def _queue_page(workspace: dict, page_key: str, title: str) -> None:
    config = workspace["workspace"]
    records = _page_records(workspace, page_key)
    page_header(title, f"{workspace['active_role']} ownership view for {config['default_queue']}.")
    _safe_dataframe(records, columns=config.get("workbench_columns"), height=430)
    _transition_panel(workspace, records)


def _donor_intake_form(workspace: dict) -> None:
    page_header("Donor Intake Form", "Create a draft intake packet and hold it in the intake workbench until ready for clinical routing.")
    with st.form("role_centered_donor_intake"):
        donor_id = st.text_input("Donor ID", value=f"DNR-2026-DEMO-{datetime.now().strftime('%H%M%S')}")
        donor_name = st.text_input("Donor name")
        age = st.number_input("Age", min_value=0, max_value=120, value=42)
        blood_type = st.selectbox("Blood type", ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Unknown"])
        infectious_history = st.checkbox("Infectious history disclosed")
        travel_risk = st.checkbox("Travel risk disclosed")
        missing_required_fields = st.checkbox("Missing required documentation")
        clinical_notes = st.text_area("Intake notes", value="Draft intake packet created by Donor Intake Coordinator.")
        submitted = st.form_submit_button("Create Intake")
    if submitted:
        result = post_json(
            "/api/donors",
            {
                "donor_id": donor_id,
                "donor_name": donor_name or "Demo Intake Donor",
                "age": int(age),
                "blood_type": blood_type,
                "infectious_history": infectious_history,
                "travel_risk": travel_risk,
                "missing_required_fields": missing_required_fields,
                "clinical_notes": clinical_notes,
                "attachment_placeholder": "intake_packet_placeholder.pdf",
            },
        )
        if result:
            st.success("Draft intake created and assigned to the intake workbench.")
            st.rerun()

    _transition_panel(workspace, _page_records(workspace, "role_tasks"))


def _workspace_configuration() -> None:
    page_header(
        "Workspace Configuration",
        "Govern role navigation, widgets, workbench columns, notification routing, and default operational queues.",
    )
    configs = get_json("/api/workspaces/configs") or []
    matrix = [
        {
            "config_id": item["config_id"],
            "role_id": item["role_id"],
            "workspace_name": item["workspace_name"],
            "default_queue": item["default_queue"],
            "tabs": len(item["visible_tabs"]),
            "widgets": len(item["enabled_widgets"]),
        }
        for item in configs
    ]
    _safe_dataframe(matrix, height=260)

    if not configs:
        return
    options = {f"{item['config_id']} | {item['workspace_name']}": item for item in configs}
    selected_label = st.selectbox("Configure workspace", list(options.keys()))
    selected = options[selected_label]
    with st.form("workspace_config_edit"):
        workspace_name = st.text_input("Workspace name", value=selected["workspace_name"])
        workspace_purpose = st.text_area("Workspace purpose", value=selected["workspace_purpose"], height=90)
        default_queue = st.text_input("Default queue", value=selected["default_queue"])
        visible_tabs = st.text_area("Visible tabs JSON", value=json.dumps(selected["visible_tabs"], indent=2), height=160)
        enabled_widgets = st.text_area("Enabled widgets JSON", value=json.dumps(selected["enabled_widgets"], indent=2), height=120)
        workbench_columns = st.text_area("Workbench columns JSON", value=json.dumps(selected["workbench_columns"], indent=2), height=120)
        notification_types = st.text_area("Notification types JSON", value=json.dumps(selected["notification_types"], indent=2), height=120)
        submitted = st.form_submit_button("Save Workspace Configuration")
    if submitted:
        try:
            payload = {
                "workspace_name": workspace_name,
                "workspace_purpose": workspace_purpose,
                "default_queue": default_queue,
                "visible_tabs": json.loads(visible_tabs),
                "enabled_widgets": json.loads(enabled_widgets),
                "workbench_columns": json.loads(workbench_columns),
                "notification_types": json.loads(notification_types),
            }
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
            return
        result = patch_json(f"/api/workspaces/configs/{selected['config_id']}", payload)
        if result:
            st.success("Workspace configuration updated.")
            st.rerun()


def _role_configuration() -> None:
    page_header(
        "Role Configuration",
        "Govern operational identity, workspace ownership, navigation access, and responsibility boundaries by role.",
    )
    roles = get_json("/api/admin/roles") or []
    responsibilities = get_json("/api/admin/role-responsibilities") or []
    configs = get_json("/api/workspaces/configs") or []
    config_by_role = {item["role_id"]: item for item in configs}
    responsibility_by_role = {item["role_name"]: item for item in responsibilities}
    rows = []
    for role in roles:
        config = config_by_role.get(role["role_id"], {})
        responsibility = responsibility_by_role.get(role["role_name"], {})
        rows.append(
            {
                "role": role["role_name"],
                "description": role["description"],
                "workspace": config.get("workspace_name", ""),
                "default_queue": config.get("default_queue", ""),
                "visible_tabs": len(config.get("visible_tabs", [])),
                "widgets": len(config.get("enabled_widgets", [])),
                "responsibilities": len(responsibility.get("responsibilities", [])),
            }
        )
    _safe_dataframe(rows, height=360)

    for record in responsibilities:
        with st.expander(record["role_name"], expanded=record["role_name"] == "Clinical Reviewer"):
            st.write(record["job_description"])
            left, middle, right = st.columns(3)
            left.write("Responsibilities")
            for item in record["responsibilities"]:
                left.write(f"- {item}")
            middle.write("Workflow Ownership")
            for item in record["assigned_workflows"]:
                middle.write(f"- {item}")
            right.write("Operational KPIs")
            for item in record["operational_kpis"]:
                right.write(f"- {item}")


def _workflow_configuration() -> None:
    page_header(
        "Workflow Configuration",
        "State-machine transitions that route work between intake, clinical review, QA, vendor operations, and management.",
    )
    transitions = get_json("/api/workspaces/transitions") or []
    _safe_dataframe(
        transitions,
        columns=[
            "action_name",
            "action_label",
            "from_state",
            "to_state",
            "task_type",
            "notification_type",
            "sla_hours",
            "is_active",
        ],
        height=540,
    )


def _system_health() -> None:
    page_header("System Health", "Governance view of platform services, workspace readiness, and configuration coverage.")
    health = get_json("/health") or {}
    st.metric("API Health", health.get("status", "unknown"))
    workspace = get_json("/api/workspaces/me") or {}
    _safe_dataframe(workspace.get("widget_data", {}).get("system_health", []))


def _integration_management() -> None:
    page_header("Integration Management", "Demo ownership view for healthcare-system interfaces and future enterprise integrations.")
    _safe_dataframe(
        [
            {"integration": "Clinical Eligibility Interface", "status": "Monitored", "owner": "Healthcare Technology", "future_channel": "API"},
            {"integration": "Document Repository", "status": "Monitored", "owner": "Quality Systems", "future_channel": "SharePoint"},
            {"integration": "Notification Delivery", "status": "In-App MVP", "owner": "System Administrator", "future_channel": "Email/Teams"},
            {"integration": "Vendor Support Feed", "status": "Simulated", "owner": "Vendor Operations", "future_channel": "Ticketing API"},
        ],
        height=260,
    )


def render(workspace: dict, page_key: str, title: str) -> None:
    if page_key == "role_dashboard":
        _dashboard(workspace)
    elif page_key == "donor_intake_form":
        _donor_intake_form(workspace)
    elif page_key == "workspace_configuration":
        _workspace_configuration()
    elif page_key == "admin_roles":
        _role_configuration()
    elif page_key == "workflow_configuration":
        _workflow_configuration()
    elif page_key == "system_health":
        _system_health()
    elif page_key == "integration_management":
        _integration_management()
    else:
        _queue_page(workspace, page_key, title)
