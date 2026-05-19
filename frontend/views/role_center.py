import streamlit as st
from components.api import get_json
from components.ui import page_header


def render() -> None:
    page_header(
        "Responsibility Center",
        "Role definitions, job responsibilities, assigned workflows, and operational KPIs embedded in the platform.",
    )
    records = get_json("/api/admin/role-responsibilities") or []
    if not records:
        st.info("No role responsibility records found.")
        return

    for record in records:
        with st.expander(record["role_name"], expanded=record["role_name"] == "Clinical Reviewer"):
            st.write(record["job_description"])
            left, mid, right = st.columns(3)
            left.write("Responsibilities")
            for item in record["responsibilities"]:
                left.write(f"- {item}")
            mid.write("Assigned Workflows")
            for item in record["assigned_workflows"]:
                mid.write(f"- {item}")
            right.write("Operational KPIs")
            for item in record["operational_kpis"]:
                right.write(f"- {item}")

