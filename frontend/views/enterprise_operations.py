import pandas as pd
import plotly.express as px
import streamlit as st
from components.api import get_json
from components.ui import dataframe, empty_figure, page_header


def render() -> None:
    page_header(
        "Enterprise Operations",
        "Cross-functional view of tasks, escalations, training, vendor operations, and compliance workload.",
    )
    payload = get_json("/api/enterprise-dashboard") or {}
    kpis = payload.get("kpis", {})

    cols = st.columns(7)
    cols[0].metric("Open Tasks", kpis.get("open_tasks", 0))
    cols[1].metric("Escalated", kpis.get("escalated_tasks", 0))
    cols[2].metric("Unread Notices", kpis.get("unread_notifications", 0))
    cols[3].metric("Open QMS", kpis.get("open_change_controls", 0))
    cols[4].metric("Open Incidents", kpis.get("open_vendor_incidents", 0))
    cols[5].metric("SLA Breaches", kpis.get("sla_breaches", 0))
    cols[6].metric("Audit Events", kpis.get("audit_events", 0))

    left, right = st.columns(2)
    task_df = pd.DataFrame(payload.get("tasks_by_status", []))
    with left:
        if task_df.empty:
            st.plotly_chart(empty_figure("Tasks by Status"), width="stretch")
        else:
            fig = px.bar(
                task_df,
                x="status",
                y="count",
                color="priority",
                title="Tasks by Status and Priority",
            )
            fig.update_layout(height=330, margin=dict(l=20, r=20, t=55, b=20))
            st.plotly_chart(fig, width="stretch")

    workload_df = pd.DataFrame(payload.get("workload_by_user", []))
    with right:
        if workload_df.empty:
            st.plotly_chart(empty_figure("Workload by User"), width="stretch")
        else:
            fig = px.bar(
                workload_df,
                x="user",
                y="task_count",
                color="role",
                title="Workload Distribution",
            )
            fig.update_layout(height=330, margin=dict(l=20, r=20, t=55, b=80), xaxis_tickangle=-25)
            st.plotly_chart(fig, width="stretch")

    st.subheader("Compliance and Training")
    training_cols = st.columns(2)
    training_cols[0].write("SOP Training")
    dataframe(payload.get("training", []), height=220)
    training_cols[1].write("Compliance Summary")
    st.json(payload.get("compliance", {}), expanded=False)

