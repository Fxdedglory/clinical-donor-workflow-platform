import pandas as pd
import plotly.express as px
import streamlit as st
from components.api import get_json
from components.ui import RISK_COLORS, dataframe, empty_figure, page_header


def render() -> None:
    page_header(
        "Executive Dashboard",
        "Operational view of donor screening, QMS activity, audit traceability, and vendor health.",
    )
    payload = get_json("/api/dashboard") or {}
    kpis = payload.get("kpis", {})

    cols = st.columns(6)
    cols[0].metric("Pending Reviews", kpis.get("pending_donor_reviews", 0))
    cols[1].metric("Avg Review Hours", kpis.get("avg_review_time_hours", 0))
    cols[2].metric("Avg Risk Score", kpis.get("avg_risk_score", 0))
    cols[3].metric("Approval Rate", f"{kpis.get('approval_rate', 0)}%")
    cols[4].metric("SLA Compliance", f"{kpis.get('sla_compliance', 0)}%")
    cols[5].metric("Open Investigations", kpis.get("open_investigations", 0))

    left, right = st.columns([1.1, 1])
    with left:
        risk_df = pd.DataFrame(payload.get("risk_distribution", []))
        if risk_df.empty:
            st.plotly_chart(empty_figure("Risk Distribution"), use_container_width=True)
        else:
            risk_order = ["Low", "Moderate", "High", "Critical"]
            risk_df["risk_level"] = pd.Categorical(
                risk_df["risk_level"], categories=risk_order, ordered=True
            )
            risk_df = risk_df.sort_values("risk_level")
            fig = px.bar(
                risk_df,
                x="risk_level",
                y="count",
                color="risk_level",
                color_discrete_map=RISK_COLORS,
                title="Risk Distribution",
                labels={"risk_level": "Risk Level", "count": "Donors"},
            )
            fig.update_layout(height=330, margin=dict(l=20, r=20, t=55, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        daily_df = pd.DataFrame(payload.get("daily_review_trend", []))
        if daily_df.empty:
            st.plotly_chart(empty_figure("Daily Review Trend"), use_container_width=True)
        else:
            fig = px.line(daily_df, x="date", y="count", markers=True, title="Daily Review Trend")
            fig.update_traces(line_color="#127c75")
            fig.update_layout(height=330, margin=dict(l=20, r=20, t=55, b=20))
            st.plotly_chart(fig, use_container_width=True)

    queue, vendor = st.columns([1.2, 1])
    with queue:
        st.subheader("Priority Donor Queue")
        queue_rows = [
            {
                "Review": row["review_id"],
                "Donor": row["donor_id"],
                "Name": row["donor_name"],
                "Score": row["risk_score"],
                "Risk": row["risk_level"],
                "Priority": row["review_priority"],
            }
            for row in payload.get("priority_queue", [])
        ]
        dataframe(
            queue_rows,
            height=330,
        )

    with vendor:
        st.subheader("Vendor Health")
        vendor_rows = [
            {
                "Vendor": row["vendor_name"],
                "Uptime %": row["uptime_percent"],
                "Breaches": row["sla_breaches"],
                "Incidents": row["incident_count"],
            }
            for row in payload.get("vendor_health", [])
        ]
        dataframe(
            vendor_rows,
            height=330,
        )

    st.subheader("Recent Audit Activity")
    dataframe(
        payload.get("recent_audit", []),
        columns=["audit_id", "action_type", "table_name", "record_id", "timestamp"],
        height=260,
    )
