from urllib.parse import urlencode

import streamlit as st
from components.api import get_json
from components.ui import dataframe, page_header


def render() -> None:
    page_header(
        "Donor Queue",
        "Review intake status, queue aging, risk level, and reviewer assignment.",
    )

    filters = st.columns([1, 1, 2])
    status = filters[0].selectbox(
        "Intake status",
        [
            "All",
            "Draft Intake",
            "Pending Intake Validation",
            "Pending Clinical Review",
            "Clinical Review In Progress",
            "Pending Additional Information",
            "QA Investigation",
            "Operations Escalation",
            "Approved",
            "Rejected",
            "Closed",
        ],
    )
    risk = filters[1].selectbox("Risk level", ["All", "Low", "Moderate", "High", "Critical"])
    limit = filters[2].slider("Records", 25, 500, 200, 25)

    params = {"limit": limit}
    if status != "All":
        params["intake_status"] = status
    if risk != "All":
        params["risk_level"] = risk

    records = get_json(f"/api/donors?{urlencode(params)}") or []
    dataframe(
        records,
        columns=[
            "review_id",
            "donor_id",
            "donor_name",
            "age",
            "blood_type",
            "risk_score",
            "risk_level",
            "review_priority",
            "intake_status",
            "reviewer_id",
            "created_at",
        ],
        height=560,
    )

