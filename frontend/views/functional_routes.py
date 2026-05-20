from __future__ import annotations

import json
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from components.api import post_json
from components.ui import dataframe, empty_figure, page_header

from views.role_workspace import _plot_heatmap, _plot_sankey, _safe_dataframe


def route_to(path: str) -> None:
    st.query_params["route"] = path
    for key in ["action"]:
        if key in st.query_params:
            del st.query_params[key]


def _breadcrumb(context: dict[str, Any]) -> None:
    labels = [item["label"] for item in context.get("breadcrumbs", [])]
    if labels:
        st.caption(" / ".join(labels))


def _route_open_button(path: str, *, label: str = "Open", key: str) -> None:
    if st.button(label, key=key):
        route_to(path)
        st.rerun()


def _workflow_summary(context: dict[str, Any]) -> None:
    workflow = context.get("workflow") or {}
    lens = context.get("role_lens") or {}
    cols = st.columns(4)
    cols[0].metric("Function Route", context.get("route_path", ""))
    cols[1].metric("Workflow State", workflow.get("workflow_state") or "Context")
    cols[2].metric("Task", workflow.get("task_id") or "No active task")
    cols[3].metric("Role Lens", lens.get("role", ""))
    st.info(lens.get("focus", "Role-aware operational context is loaded for this route."))


def _action_dialog(action: dict[str, Any]) -> None:
    @st.dialog(action["action_label"])
    def dialog() -> None:
        st.write(f"Transition: **{action['from_state']}** to **{action['to_state']}**")
        note = st.text_area("Operational rationale", value="", height=120)
        metadata: dict[str, Any] = {}
        action_name = action["action_name"]

        if "override" in action_name:
            metadata["human_override"] = True
            metadata["override_reason"] = st.text_area("Override reason", height=100)
            metadata["severity_acknowledged"] = st.checkbox("Severity reviewed and acknowledged")
            metadata["reviewer_signature"] = st.text_input("Reviewer signature")
        elif "capa" in action_name:
            metadata["deviation_category"] = st.selectbox(
                "Deviation category",
                ["Documentation", "Clinical Review", "SOP Compliance", "Vendor/System", "Other"],
            )
            metadata["severity"] = st.selectbox("Severity", ["Low", "Moderate", "High", "Critical"], index=1)
            metadata["corrective_action_owner"] = st.text_input("Corrective action owner")
            metadata["investigation_notes"] = st.text_area("Investigation notes", height=100)
        elif "reassign" in action_name:
            metadata["reassignment_reason"] = st.text_area("Reassignment reason", height=100)
            metadata["staffing_impact"] = st.selectbox("Staffing impact", ["Low", "Moderate", "High"])
        elif "escalate" in action_name:
            metadata["escalation_reason"] = st.text_area("Escalation reason", height=100)
            metadata["severity_acknowledged"] = st.checkbox("SLA/quality impact acknowledged")

        cols = st.columns([1, 1])
        if cols[0].button("Trigger Workflow Transition", key=f"confirm_{action_name}"):
            result = post_json(
                "/api/workspaces/transition",
                {
                    "action_name": action_name,
                    "related_record_type": action["record_type"],
                    "related_record_id": str(action["record_id"]),
                    "task_id": action.get("task_id"),
                    "note": note,
                    "metadata": metadata,
                },
            )
            if result:
                st.success(f"Workflow routed to {result['to_state']}.")
                if "action" in st.query_params:
                    del st.query_params["action"]
                st.rerun()
        if cols[1].button("Cancel", key=f"cancel_{action_name}"):
            if "action" in st.query_params:
                del st.query_params["action"]
            st.rerun()

    dialog()


def _action_ribbon(context: dict[str, Any]) -> None:
    actions = context.get("actions", [])
    st.markdown("<div class='section-title'>Contextual Action Ribbon</div>", unsafe_allow_html=True)
    if not actions:
        st.caption("No workflow transitions are authorized for this role and workflow state.")
        return
    columns = st.columns(min(len(actions), 5))
    for index, action in enumerate(actions):
        if columns[index % len(columns)].button(action["action_label"], key=f"action_{action['action_name']}"):
            st.query_params["action"] = action["action_name"]
            st.rerun()

    selected_action = st.query_params.get("action")
    if isinstance(selected_action, list):
        selected_action = selected_action[0] if selected_action else None
    if selected_action:
        match = next((item for item in actions if item["action_name"] == selected_action), None)
        if match:
            _action_dialog(match)


def _detail_table(entity: dict[str, Any]) -> None:
    rows = [
        {
            "field": key.replace("_", " ").title(),
            "value": json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value or ""),
        }
        for key, value in entity.items()
    ]
    dataframe(rows, height=360)


def _timeline_panel(context: dict[str, Any]) -> None:
    timeline = context.get("timeline", [])
    st.markdown("<div class='section-title'>Workflow Timeline</div>", unsafe_allow_html=True)
    if not timeline:
        st.info("No workflow timeline events have been captured for this record.")
        return
    _safe_dataframe(timeline, columns=["timestamp", "event_type", "summary"], height=280)


def _related_records(context: dict[str, Any]) -> None:
    related = context.get("related_records", {})
    st.markdown("<div class='section-title'>Related Records</div>", unsafe_allow_html=True)
    if not related:
        st.info("No related records are linked to this route context.")
        return
    for label, rows in related.items():
        with st.expander(label.replace("_", " ").title(), expanded=label == "workflows"):
            if not rows:
                st.caption("None")
                continue
            _safe_dataframe(rows, height=220)
            route_rows = [row for row in rows if row.get("route_path")]
            if route_rows:
                selected = st.selectbox(
                    f"Open related {label}",
                    [f"{row.get('route_path')} | {row.get('title') or row.get('task_type') or row.get('request_id') or row.get('ticket_number') or row.get('workflow_state')}" for row in route_rows],
                    key=f"related_{label}",
                )
                path = selected.split(" | ")[0]
                _route_open_button(path, label="Open Related Record", key=f"open_related_{label}")


def _collection_visuals(context: dict[str, Any]) -> None:
    analytics = context.get("analytics", {})
    rows = analytics.get("task_heatmap", [])
    if not rows:
        return
    st.markdown("<div class='section-title'>Operational Visualization</div>", unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            _plot_heatmap(rows, x="queue", y="workflow_state", z="volume", title="Queue Aging Heatmap"),
            width="stretch",
        )
    with right:
        st.plotly_chart(
            _plot_sankey(analytics.get("workflow_sankey", []), "Workflow Sankey Diagram"),
            width="stretch",
        )


def render_collection(context: dict[str, Any]) -> None:
    _breadcrumb(context)
    page_header(context["label"], f"{context['route_group']} function route: {context['route_path']}")
    _workflow_summary(context)
    records = context.get("records", [])
    if records:
        _safe_dataframe(records, height=430)
        selectable = [row for row in records if row.get("route_path")]
        if selectable:
            selected = st.selectbox(
                "Open record",
                [f"{row['route_path']} | {row.get('donor_id') or row.get('request_id') or row.get('ticket_number') or row.get('title') or row.get('vendor_name') or row.get('rule_name') or row.get('task_id')}" for row in selectable],
            )
            _route_open_button(selected.split(" | ")[0], key=f"open_{context['route_key']}")
    else:
        st.info("No records are available for this function route.")
    _collection_visuals(context)


def render_detail(context: dict[str, Any]) -> None:
    entity = context.get("entity") or {}
    _breadcrumb(context)
    title = context["label"]
    if entity.get("donor_id"):
        title = f"Donor {entity['donor_id']}"
    elif entity.get("request_id"):
        title = entity["request_id"]
    elif entity.get("ticket_number"):
        title = entity["ticket_number"]
    elif entity.get("vendor_name"):
        title = entity["vendor_name"]
    elif entity.get("rule_name"):
        title = entity["rule_name"]
    page_header(title, f"{context['route_group']} detail route: {context['route_path']}")
    _workflow_summary(context)
    _action_ribbon(context)

    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown("<div class='section-title'>Master Data / Operational Record</div>", unsafe_allow_html=True)
        _detail_table(entity)
    with right:
        _timeline_panel(context)
    _related_records(context)


def render_analytics_context(context: dict[str, Any]) -> None:
    _breadcrumb(context)
    page_header(context["label"], f"{context['route_group']} route: {context['route_path']}")
    _workflow_summary(context)
    analytics = context.get("analytics", {})
    task_rows = analytics.get("task_heatmap", [])
    donor_states = analytics.get("donor_state_distribution", [])
    incident_severity = analytics.get("incident_severity", [])
    left, right = st.columns(2)
    with left:
        if task_rows:
            st.plotly_chart(
                _plot_heatmap(task_rows, x="queue", y="workflow_state", z="volume", title="Enterprise Queue Heatmap"),
                width="stretch",
            )
        else:
            st.plotly_chart(empty_figure("Enterprise Queue Heatmap"), width="stretch")
    with right:
        if donor_states:
            fig = px.bar(pd.DataFrame(donor_states), x="state", y="count", title="Workflow State Distribution")
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, width="stretch")
        else:
            st.plotly_chart(empty_figure("Workflow State Distribution"), width="stretch")
    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.plotly_chart(
            _plot_sankey(analytics.get("workflow_sankey", []), "Operational Bottleneck Analysis"),
            width="stretch",
        )
    with lower_right:
        if incident_severity:
            fig = px.treemap(pd.DataFrame(incident_severity), path=["severity"], values="count", title="SLA Severity Treemap")
            fig.update_layout(height=390, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, width="stretch")
        else:
            st.plotly_chart(empty_figure("SLA Severity Treemap"), width="stretch")


def render(context: dict[str, Any]) -> None:
    if context.get("kind") == "detail":
        render_detail(context)
    elif context.get("kind") == "collection":
        render_collection(context)
    else:
        render_analytics_context(context)
