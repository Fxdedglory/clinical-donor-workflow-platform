from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from components.api import get_json, patch_json, post_json
from components.ui import dataframe, empty_figure, page_header


def _safe_dataframe(records: list[dict[str, Any]], columns: list[str] | None = None, height: int = 380) -> None:
    if not records:
        st.info("No records are currently in this role queue.")
        return
    if columns:
        present = [column for column in columns if column in records[0]]
        dataframe(records, columns=present or None, height=height)
    else:
        dataframe(records, height=height)


AI_GOVERNANCE_PAGES = {
    "ai_risk_dashboard",
    "workflow_intelligence",
    "ai_governance",
    "workflow_analytics",
    "escalation_analytics",
    "operational_trends",
}


def _governance_payload(workspace: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = get_json("/api/ai-governance/dashboard") or {}
    return payload.get("kpis") or workspace.get("kpis", {}), payload.get("analytics") or workspace.get("widget_data", {})


def _plot_heatmap(
    records: list[dict[str, Any]],
    *,
    x: str,
    y: str,
    z: str,
    title: str,
    color_scale: str = "Teal",
) -> go.Figure:
    if not records:
        return empty_figure(title)
    frame = pd.DataFrame(records)
    pivot = frame.pivot_table(index=y, columns=x, values=z, aggfunc="sum", fill_value=0)
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=color_scale,
        labels={"x": x.replace("_", " ").title(), "y": y.replace("_", " ").title(), "color": z.replace("_", " ").title()},
    )
    fig.update_layout(title=title, height=360, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def _plot_sankey(records: list[dict[str, Any]], title: str) -> go.Figure:
    if not records:
        return empty_figure(title)
    labels = sorted({row["source"] for row in records} | {row["target"] for row in records})
    index = {label: idx for idx, label in enumerate(labels)}
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(label=labels, pad=18, thickness=16, color="#d9e1e8"),
                link=dict(
                    source=[index[row["source"]] for row in records],
                    target=[index[row["target"]] for row in records],
                    value=[row["value"] for row in records],
                    color="rgba(18,124,117,0.26)",
                ),
            )
        ]
    )
    fig.update_layout(title=title, height=390, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def _plot_line(records: list[dict[str, Any]], *, x: str, y: str, title: str) -> go.Figure:
    if not records:
        return empty_figure(title)
    fig = px.line(pd.DataFrame(records), x=x, y=y, markers=True)
    fig.update_traces(line_color="#127c75")
    fig.update_layout(title=title, height=320, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def _plot_sla_accuracy(records: list[dict[str, Any]]) -> go.Figure:
    if not records:
        return empty_figure("SLA Prediction Accuracy Chart")
    frame = pd.DataFrame(records)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame["date"], y=frame["predicted_breaches"], mode="lines+markers", name="Predicted"))
    fig.add_trace(go.Scatter(x=frame["date"], y=frame["actual_breaches"], mode="lines+markers", name="Actual"))
    fig.update_layout(title="SLA Prediction Accuracy Chart", height=320, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def _plot_rule_frequency(records: list[dict[str, Any]]) -> go.Figure:
    if not records:
        return empty_figure("Rule Trigger Frequency")
    frame = pd.DataFrame(records).sort_values("trigger_count", ascending=True)
    fig = px.bar(frame, x="trigger_count", y="rule_name", orientation="h", color="trigger_count", color_continuous_scale="Teal")
    fig.update_layout(title="Rule Trigger Frequency", height=360, margin=dict(l=20, r=20, t=50, b=20), showlegend=False)
    return fig


def _governance_metrics(kpis: dict[str, Any], labels: list[str]) -> None:
    values = {label: kpis.get(label, "0") for label in labels}
    columns = st.columns(min(max(len(values), 1), 5))
    for index, (label, value) in enumerate(values.items()):
        columns[index % len(columns)].metric(label, value)


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


def _ai_visual_workspace(workspace: dict, page_key: str, title: str) -> None:
    descriptions = {
        "ai_risk_dashboard": "Monitor AI-assisted donor screening signals, risk concentration, overrides, and rule activity.",
        "workflow_intelligence": "Analyze operational routing, stalled work, queue pressure, and bottleneck patterns across departments.",
        "ai_governance": "Review governed AI performance, explainability signals, override behavior, and rule performance risk.",
        "workflow_analytics": "Inspect workflow flow, queue imbalance, and operational recommendations for process optimization.",
        "escalation_analytics": "Locate escalation root causes by workflow stage and monitor unresolved escalation pressure.",
        "operational_trends": "Track AI override behavior, SLA prediction quality, and high-risk operational trends over time.",
    }
    page_header(title, descriptions.get(page_key, workspace["workspace"]["workspace_purpose"]))
    kpis, analytics = _governance_payload(workspace)

    if page_key in {"ai_risk_dashboard", "ai_governance", "operational_trends"}:
        _governance_metrics(
            kpis,
            [
                "False Positive Rate",
                "False Negative Rate",
                "Human Override Frequency",
                "Escalated AI Decisions",
                "Avg Risk Score",
            ],
        )
    elif page_key in {"workflow_intelligence", "workflow_analytics"}:
        _governance_metrics(
            kpis,
            [
                "Queue Bottlenecks",
                "Workflow Delays",
                "Routing Inefficiencies",
                "SLA Prediction Accuracy",
                "Workload Imbalance",
            ],
        )
    else:
        _governance_metrics(
            kpis,
            [
                "Escalation Frequency",
                "Queue Bottlenecks",
                "Workflow Delays",
                "Human Override Frequency",
                "SLA Prediction Accuracy",
            ],
        )

    if page_key == "ai_risk_dashboard":
        left, right = st.columns([1.1, 0.9])
        with left:
            st.plotly_chart(
                _plot_heatmap(
                    analytics.get("risk_distribution_heatmap", []),
                    x="workflow_stage",
                    y="risk_category",
                    z="volume",
                    title="Risk Distribution Heatmap",
                    color_scale="YlOrRd",
                ),
                use_container_width=True,
            )
        with right:
            st.plotly_chart(
                _plot_line(
                    analytics.get("human_override_trend", []),
                    x="date",
                    y="override_count",
                    title="Human Override Trend",
                ),
                use_container_width=True,
            )
        st.plotly_chart(_plot_rule_frequency(analytics.get("rule_trigger_frequency", [])), use_container_width=True)
        st.markdown("<div class='section-title'>Recent AI Decisions</div>", unsafe_allow_html=True)
        _safe_dataframe(workspace.get("widget_data", {}).get("ai_risk_dashboard", []), columns=workspace["workspace"].get("workbench_columns"), height=300)
        return

    if page_key in {"workflow_intelligence", "workflow_analytics"}:
        st.plotly_chart(
            _plot_sankey(analytics.get("workflow_bottleneck_sankey", []), "Workflow Bottleneck Sankey Diagram"),
            use_container_width=True,
        )
        left, right = st.columns(2)
        with left:
            st.plotly_chart(
                _plot_heatmap(
                    analytics.get("workflow_queue_heatmap", []),
                    x="department",
                    y="workflow_stage",
                    z="queue_volume",
                    title="Workflow Queue Heatmap",
                    color_scale="Teal",
                ),
                use_container_width=True,
            )
        with right:
            st.markdown("<div class='section-title'>Operational Recommendation Engine</div>", unsafe_allow_html=True)
            _safe_dataframe(analytics.get("operational_recommendations", []), height=360)
        return

    if page_key == "escalation_analytics":
        left, right = st.columns(2)
        with left:
            st.plotly_chart(
                _plot_heatmap(
                    analytics.get("escalation_root_cause_matrix", []),
                    x="escalation_reason",
                    y="workflow_stage",
                    z="frequency",
                    title="Escalation Root Cause Matrix",
                    color_scale="OrRd",
                ),
                use_container_width=True,
            )
        with right:
            st.plotly_chart(
                _plot_sankey(analytics.get("workflow_bottleneck_sankey", []), "Escalation Routing Pattern"),
                use_container_width=True,
            )
        st.markdown("<div class='section-title'>Escalation Intelligence Findings</div>", unsafe_allow_html=True)
        _safe_dataframe(analytics.get("operational_recommendations", []), height=280)
        return

    if page_key == "operational_trends":
        left, right = st.columns(2)
        with left:
            st.plotly_chart(
                _plot_line(
                    analytics.get("human_override_trend", []),
                    x="date",
                    y="override_count",
                    title="Human Override Trend",
                ),
                use_container_width=True,
            )
        with right:
            st.plotly_chart(_plot_sla_accuracy(analytics.get("sla_prediction_accuracy", [])), use_container_width=True)
        st.plotly_chart(_plot_rule_frequency(analytics.get("rule_trigger_frequency", [])), use_container_width=True)
        return

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_plot_sla_accuracy(analytics.get("sla_prediction_accuracy", [])), use_container_width=True)
        st.plotly_chart(_plot_rule_frequency(analytics.get("rule_trigger_frequency", [])), use_container_width=True)
    with right:
        st.plotly_chart(
            _plot_heatmap(
                analytics.get("escalation_root_cause_matrix", []),
                x="escalation_reason",
                y="workflow_stage",
                z="frequency",
                title="Escalation Root Cause Matrix",
                color_scale="OrRd",
            ),
            use_container_width=True,
        )
        st.markdown("<div class='section-title'>Operational Recommendations</div>", unsafe_allow_html=True)
        _safe_dataframe(analytics.get("operational_recommendations", []), height=300)


def _risk_rule_configuration(workspace: dict) -> None:
    page_header(
        "Risk Rule Configuration",
        "Govern database-driven AI risk rules, activation status, score deltas, auto-escalation behavior, and sandbox impact.",
    )
    rules = get_json("/api/ai-governance/rules") or []
    _safe_dataframe(
        rules,
        columns=[
            "rule_id",
            "rule_name",
            "risk_category",
            "condition_type",
            "condition_operator",
            "condition_value",
            "risk_score_delta",
            "severity",
            "auto_escalate",
            "is_active",
        ],
        height=270,
    )

    if rules:
        selected_label = st.selectbox(
            "Governed rule",
            [f"{rule['rule_id']} | {rule['rule_name']}" for rule in rules],
        )
        selected = next(rule for rule in rules if selected_label.startswith(f"{rule['rule_id']} |"))
        with st.form("ai_rule_edit"):
            left, right = st.columns(2)
            risk_category = left.text_input("Risk category", value=selected["risk_category"])
            condition_type = left.selectbox(
                "Condition type",
                ["age", "blood_type", "infectious_history", "travel_risk", "missing_required_fields", "clinical_notes", "donor_name"],
                index=["age", "blood_type", "infectious_history", "travel_risk", "missing_required_fields", "clinical_notes", "donor_name"].index(selected["condition_type"])
                if selected["condition_type"] in ["age", "blood_type", "infectious_history", "travel_risk", "missing_required_fields", "clinical_notes", "donor_name"]
                else 0,
            )
            condition_operator = left.selectbox(
                "Condition operator",
                ["equals", "gt", "gte", "lt", "lte", "in", "contains_any", "missing"],
                index=["equals", "gt", "gte", "lt", "lte", "in", "contains_any", "missing"].index(selected["condition_operator"])
                if selected["condition_operator"] in ["equals", "gt", "gte", "lt", "lte", "in", "contains_any", "missing"]
                else 0,
            )
            condition_value = left.text_input("Condition value", value=selected["condition_value"])
            risk_score_delta = right.number_input("Risk score delta", min_value=-50, max_value=100, value=int(selected["risk_score_delta"]))
            severity = right.selectbox(
                "Severity",
                ["Low", "Moderate", "High", "Critical"],
                index=["Low", "Moderate", "High", "Critical"].index(selected["severity"])
                if selected["severity"] in ["Low", "Moderate", "High", "Critical"]
                else 0,
            )
            auto_escalate = right.checkbox("Auto-escalate", value=bool(selected["auto_escalate"]))
            is_active = right.checkbox("Active in production", value=bool(selected["is_active"]))
            submitted = st.form_submit_button("Save Governed Rule")
        if submitted:
            result = patch_json(
                f"/api/ai-governance/rules/{selected['rule_id']}",
                {
                    "risk_category": risk_category,
                    "condition_type": condition_type,
                    "condition_operator": condition_operator,
                    "condition_value": condition_value,
                    "risk_score_delta": int(risk_score_delta),
                    "severity": severity,
                    "auto_escalate": auto_escalate,
                    "is_active": is_active,
                },
            )
            if result:
                st.success("Governed AI risk rule updated with audit trail.")
                st.rerun()

    with st.expander("Add Governed AI Rule"):
        with st.form("ai_rule_create"):
            rule_name = st.text_input("Rule name", value="Sandbox Governance Rule")
            risk_category = st.text_input("Risk category", value="Operational Governance")
            condition_type = st.selectbox("Condition type", ["age", "blood_type", "infectious_history", "travel_risk", "missing_required_fields", "clinical_notes"])
            condition_operator = st.selectbox("Condition operator", ["equals", "gt", "gte", "lt", "lte", "in", "contains_any", "missing"])
            condition_value = st.text_input("Condition value", value="true")
            risk_score_delta = st.number_input("Risk score delta", min_value=-50, max_value=100, value=15)
            severity = st.selectbox("Severity", ["Low", "Moderate", "High", "Critical"], index=1)
            auto_escalate = st.checkbox("Auto-escalate")
            is_active = st.checkbox("Active in production", value=False)
            created = st.form_submit_button("Create Governed Rule")
        if created:
            result = post_json(
                "/api/ai-governance/rules",
                {
                    "rule_name": rule_name,
                    "risk_category": risk_category,
                    "condition_type": condition_type,
                    "condition_operator": condition_operator,
                    "condition_value": condition_value,
                    "risk_score_delta": int(risk_score_delta),
                    "severity": severity,
                    "auto_escalate": auto_escalate,
                    "is_active": is_active,
                },
            )
            if result:
                st.success("Governed AI risk rule created.")
                st.rerun()

    st.markdown("<div class='section-title'>Rule Simulation Sandbox</div>", unsafe_allow_html=True)
    with st.form("rule_simulation"):
        left, right = st.columns(2)
        condition_type = left.selectbox("Sandbox condition type", ["age", "blood_type", "infectious_history", "travel_risk", "missing_required_fields", "clinical_notes"], index=0)
        condition_operator = left.selectbox("Sandbox operator", ["equals", "gt", "gte", "lt", "lte", "in", "contains_any", "missing"], index=1)
        condition_value = left.text_input("Sandbox condition value", value="70")
        risk_score_delta = right.number_input("Sandbox risk score delta", min_value=-50, max_value=100, value=20)
        sample_size = right.slider("Sample size", min_value=25, max_value=500, value=120, step=25)
        simulated = st.form_submit_button("Simulate Rule Impact")
    if simulated:
        result = post_json(
            "/api/ai-governance/simulate-rule",
            {
                "condition_type": condition_type,
                "condition_operator": condition_operator,
                "condition_value": condition_value,
                "risk_score_delta": int(risk_score_delta),
                "sample_size": int(sample_size),
            },
        )
        if result:
            columns = st.columns(5)
            columns[0].metric("Sample Size", result["sample_size"])
            columns[1].metric("Impacted Records", result["impacted_records"])
            columns[2].metric("Baseline High Risk", result["baseline_high_risk"])
            columns[3].metric("Simulated High Risk", result["simulated_high_risk"])
            columns[4].metric("Queue Impact", result["queue_impact"])
            st.info(f"SLA effect: {result['sla_effect']}")


def _ai_audit_review() -> None:
    page_header(
        "AI Audit Review",
        "Trace AI recommendations, triggered rules, human overrides, workflow impact, and decision timeline events.",
    )
    decisions = get_json("/api/ai-governance/decisions?limit=150") or []
    overrides = get_json("/api/ai-governance/overrides?limit=150") or []
    left, right = st.columns([1.2, 0.8])
    with left:
        st.markdown("<div class='section-title'>AI Recommendation Review</div>", unsafe_allow_html=True)
        _safe_dataframe(
            decisions,
            columns=[
                "decision_id",
                "donor_id",
                "risk_score",
                "recommendation",
                "workflow_stage",
                "confidence_level",
                "human_override",
                "final_decision",
                "created_at",
            ],
            height=330,
        )
    with right:
        st.markdown("<div class='section-title'>Human Override Events</div>", unsafe_allow_html=True)
        _safe_dataframe(
            overrides,
            columns=["override_id", "decision_id", "previous_decision", "new_decision", "override_reason", "timestamp"],
            height=330,
        )

    if not decisions:
        return
    selected_label = st.selectbox(
        "Explainability trace",
        [f"{item['decision_id']} | {item['donor_id']} | score {item['risk_score']}" for item in decisions],
    )
    selected_id = int(selected_label.split(" | ")[0])
    trace = get_json(f"/api/ai-governance/decisions/{selected_id}/explainability") or {}
    decision = trace.get("decision", {})
    explainability = trace.get("explainability", {})
    timeline = trace.get("timeline", [])

    columns = st.columns(4)
    columns[0].metric("Risk Score", decision.get("risk_score", ""))
    columns[1].metric("Confidence", decision.get("confidence_level", ""))
    columns[2].metric("Human Override", "Yes" if decision.get("human_override") else "No")
    columns[3].metric("Final Decision", decision.get("final_decision") or "Pending")
    st.write(f"Recommendation: **{decision.get('recommendation', '')}**")
    st.write(f"Workflow impact: {explainability.get('workflow_impact', '')}")

    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("<div class='section-title'>Triggered Rules and Score Contributions</div>", unsafe_allow_html=True)
        _safe_dataframe(
            explainability.get("score_contributions", []),
            columns=["rule_name", "score_delta", "severity"],
            height=240,
        )
        escalation_reasons = explainability.get("escalation_reasons", [])
        if escalation_reasons:
            st.write("Escalation reasons")
            for reason in escalation_reasons:
                st.write(f"- {reason}")
    with right:
        st.markdown("<div class='section-title'>Workflow Timeline Integration</div>", unsafe_allow_html=True)
        _safe_dataframe(
            timeline,
            columns=["created_at", "event_type", "event_summary", "created_by"],
            height=300,
        )


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
        if workspace.get("active_role") == "Business Technology Analyst":
            _ai_visual_workspace(workspace, "ai_governance", "AI Governance")
        else:
            _dashboard(workspace)
    elif page_key == "donor_intake_form":
        _donor_intake_form(workspace)
    elif page_key in AI_GOVERNANCE_PAGES:
        _ai_visual_workspace(workspace, page_key, title)
    elif page_key == "risk_rule_configuration":
        _risk_rule_configuration(workspace)
    elif page_key == "ai_audit_review":
        _ai_audit_review()
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
