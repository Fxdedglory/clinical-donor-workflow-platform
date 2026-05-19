import streamlit as st
from components.api import get_json, post_json
from components.ui import dataframe, page_header


def render() -> None:
    page_header(
        "Compliance Dashboard",
        "SOP training, audit exceptions, CAPA aging, unresolved investigations, and QMS workload.",
    )
    enterprise = get_json("/api/enterprise-dashboard") or {}
    assignments = get_json("/api/training/assignments") or []
    audit = get_json("/api/audit-logs?limit=120") or []
    changes = get_json("/api/change-control?limit=120") or []

    compliance = enterprise.get("compliance", {})
    cols = st.columns(4)
    cols[0].metric("Change Controls", compliance.get("change_controls", 0))
    cols[1].metric("CAPA Required", compliance.get("capa_required", 0))
    cols[2].metric("Open Investigations", compliance.get("open_investigations", 0))
    cols[3].metric("Training Assignments", len(assignments))

    st.subheader("SOP Training Assignments")
    dataframe(assignments, height=260)

    if assignments:
        with st.expander("Complete training acknowledgement", expanded=False):
            selected = st.selectbox(
                "Assignment",
                [f"{row['assignment_id']} | SOP {row['sop_id']} | {row['acknowledgment_status']}" for row in assignments],
            )
            user_id = st.number_input("Completed by user ID", min_value=1, value=1)
            if st.button("Record Acknowledgement"):
                assignment_id = int(selected.split(" | ")[0])
                result = post_json(
                    "/api/training/complete",
                    {
                        "assignment_id": assignment_id,
                        "completed_by_user_id": int(user_id),
                    },
                )
                if result:
                    st.success("Training acknowledgement recorded.")
                    st.rerun()

    st.subheader("QMS Change Controls")
    dataframe(
        changes,
        columns=["request_id", "risk_level", "approval_status", "capa_required", "created_at", "reason"],
        height=280,
    )

    st.subheader("Audit Review")
    dataframe(audit, columns=["audit_id", "action_type", "entity_type", "entity_id", "ip_address", "timestamp"], height=280)

