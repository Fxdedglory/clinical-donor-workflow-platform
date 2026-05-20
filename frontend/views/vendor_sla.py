import pandas as pd
import plotly.express as px
import streamlit as st
from components.api import get_json
from components.ui import dataframe, empty_figure, page_header


def render() -> None:
    page_header(
        "Vendor SLA",
        "Operational monitoring for vendor systems, incident aging, SLA breaches, and uptime trends.",
    )

    vendors = get_json("/api/vendors") or []
    incidents = get_json("/api/vendors/incidents?limit=300") or []

    open_count = sum(1 for row in incidents if row["status"] == "Open")
    breach_count = sum(1 for row in incidents if row["sla_breached"])
    mean_resolution = [
        row["resolution_minutes"] for row in incidents if row.get("resolution_minutes") is not None
    ]
    mean_resolution_hours = round(sum(mean_resolution) / len(mean_resolution) / 60, 1) if mean_resolution else 0

    cols = st.columns(4)
    cols[0].metric("Vendors", len(vendors))
    cols[1].metric("Open Incidents", open_count)
    cols[2].metric("SLA Breaches", breach_count)
    cols[3].metric("Mean Resolution Hours", mean_resolution_hours)

    left, right = st.columns([1, 1.1])
    with left:
        incident_df = pd.DataFrame(incidents)
        if incident_df.empty:
            st.plotly_chart(empty_figure("Incident Severity"), width="stretch")
        else:
            severity_df = incident_df.groupby("severity").size().reset_index(name="count")
            fig = px.bar(severity_df, x="severity", y="count", title="Incident Severity")
            fig.update_traces(marker_color="#127c75")
            fig.update_layout(height=320, margin=dict(l=20, r=20, t=55, b=20), showlegend=False)
            st.plotly_chart(fig, width="stretch")
    with right:
        dataframe(
            vendors,
            columns=[
                "vendor_id",
                "vendor_name",
                "system_name",
                "criticality",
                "sla_target_percent",
                "business_owner",
                "status",
            ],
            height=320,
        )

    st.subheader("Incident Register")
    dataframe(
        incidents,
        columns=[
            "incident_id",
            "ticket_number",
            "vendor_id",
            "severity",
            "status",
            "uptime_percent",
            "sla_breached",
            "ticket_age_hours",
            "resolution_minutes",
            "title",
        ],
        height=460,
    )

