import streamlit as st
from components.api import get_json, patch_json
from components.ui import dataframe, page_header


def render() -> None:
    page_header(
        "Notification Center",
        "In-app operational notifications for assignments, escalations, SLA breaches, and SOP training.",
    )
    unread_only = st.toggle("Unread only", value=False)
    notifications = get_json(f"/api/notifications?unread_only={str(unread_only).lower()}&limit=200") or []

    dataframe(
        notifications,
        columns=[
            "notification_id",
            "title",
            "notification_type",
            "priority",
            "is_read",
            "created_at",
            "message",
        ],
        height=460,
    )

    unread = [item for item in notifications if not item.get("is_read")]
    if unread:
        options = {f"{item['notification_id']} | {item['title']}": item["notification_id"] for item in unread}
        selected = st.selectbox("Mark notification as read", list(options.keys()))
        if st.button("Mark Read"):
            result = patch_json(f"/api/notifications/{options[selected]}/read", {})
            if result:
                st.success("Notification marked as read.")
                st.rerun()

