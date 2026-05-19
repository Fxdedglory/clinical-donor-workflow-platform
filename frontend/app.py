import streamlit as st
from components.ui import apply_theme
from views import (
    ai_risk_analysis,
    audit_logs,
    change_control,
    dashboard,
    donor_queue,
    donor_review,
    vendor_sla,
)

st.set_page_config(
    page_title="Clinical Donor Workflow",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

PAGES = {
    "Dashboard": dashboard.render,
    "Donor Queue": donor_queue.render,
    "Donor Review": donor_review.render,
    "AI Risk Analysis": ai_risk_analysis.render,
    "Audit Logs": audit_logs.render,
    "Change Control": change_control.render,
    "Vendor SLA": vendor_sla.render,
}

with st.sidebar:
    st.title("Clinical Donor Workflow")
    st.caption("Regulated healthcare operations")
    selection = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("FastAPI · PostgreSQL · Streamlit · QMS")

PAGES[selection]()
