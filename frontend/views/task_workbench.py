import pandas as pd
import streamlit as st
from components.api import get_json, patch_json, post_json
from components.ui import dataframe, page_header


def render() -> None:
    page_header(
        "Workflow Task Workbench",
        "Assigned operational work with ownership, deadlines, status, and escalation potential.",
    )
    status = st.selectbox(
        "Task status",
        ["All", "Pending", "Assigned", "In Progress", "Blocked", "Escalated", "Completed", "Rejected"],
    )
    path = "/api/workflow-tasks?limit=300"
    if status != "All":
        path += f"&status={status}"
    tasks = get_json(path) or []

    with st.expander("Create workflow task", expanded=False):
        with st.form("task_create"):
            task_type = st.selectbox(
                "Task type",
                ["Donor Review Task", "SLA Investigation Task", "SOP Deviation Investigation"],
            )
            title = st.text_input("Title", "Investigate overdue clinical review")
            related_record_type = st.selectbox("Related record type", ["DonorReview", "VendorIncident", "ChangeControl"])
            related_record_id = st.text_input("Related record ID", "1")
            priority = st.selectbox("Priority", ["Routine", "Standard", "High", "Critical", "STAT"])
            submitted = st.form_submit_button("Create Task")
        if submitted:
            result = post_json(
                "/api/workflow-tasks",
                {
                    "task_type": task_type,
                    "title": title,
                    "related_record_type": related_record_type,
                    "related_record_id": related_record_id,
                    "priority": priority,
                    "status": "Assigned",
                },
            )
            if result:
                st.success("Workflow task created.")
                st.rerun()

    dataframe(
        tasks,
        columns=[
            "task_id",
            "task_type",
            "title",
            "assigned_to_user_id",
            "assigned_role_id",
            "priority",
            "status",
            "due_date",
            "related_record_type",
            "related_record_id",
            "escalation_level",
        ],
        height=430,
    )

    if tasks:
        st.subheader("Update Task")
        task_options = {f"{row['task_id']} | {row['title']}": row["task_id"] for row in tasks}
        selected = st.selectbox("Task", list(task_options.keys()))
        new_status = st.selectbox("New status", ["Assigned", "In Progress", "Blocked", "Escalated", "Completed", "Rejected"])
        if st.button("Update Status"):
            result = patch_json(f"/api/workflow-tasks/{task_options[selected]}", {"status": new_status})
            if result:
                st.success("Task updated.")
                st.rerun()

    if tasks:
        df = pd.DataFrame(tasks)
        st.caption(f"Queue aging proxy: {round(df['escalation_level'].mean(), 2)} average escalation level")

