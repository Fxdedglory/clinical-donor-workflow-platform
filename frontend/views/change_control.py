from datetime import date

import streamlit as st
from components.api import get_json, post_json
from components.ui import dataframe, page_header


def render() -> None:
    page_header(
        "Change Control",
        "QMS workflow for SOP revisions, risk classification, approvals, investigations, and CAPA flags.",
    )

    with st.expander("Create change request", expanded=False):
        with st.form("change_form"):
            request_id = st.text_input("Request ID", value=f"CCR-2026-{date.today().strftime('%m%d')}")
            requested_by_id = st.number_input("Requested by user ID", min_value=1, value=2)
            sop_id = st.number_input("SOP ID", min_value=1, value=1)
            risk_level = st.selectbox("Risk level", ["Low", "Moderate", "High", "Critical"])
            approval_status = st.selectbox("Approval status", ["Draft", "Investigation", "Pending Approval", "Approved"])
            capa_required = st.checkbox("CAPA required")
            reason = st.text_area("Reason", "Update donor screening SOP to clarify clinical escalation criteria.")
            investigation_notes = st.text_area("Investigation notes", "Impact assessment pending QMS owner review.")
            submitted = st.form_submit_button("Create Request")
        if submitted:
            result = post_json(
                "/api/change-control",
                {
                    "request_id": request_id,
                    "requested_by_id": int(requested_by_id),
                    "sop_id": int(sop_id),
                    "reason": reason,
                    "risk_level": risk_level,
                    "approval_status": approval_status,
                    "capa_required": capa_required,
                    "investigation_notes": investigation_notes,
                },
            )
            if result:
                st.success("Change request created and audit log updated.")
                st.rerun()

    records = get_json("/api/change-control?limit=250") or []
    dataframe(
        records,
        columns=[
            "change_id",
            "request_id",
            "risk_level",
            "approval_status",
            "capa_required",
            "requested_by_id",
            "sop_id",
            "created_at",
            "implementation_due_date",
            "reason",
        ],
        height=560,
    )

