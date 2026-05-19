import streamlit as st
from components.api import post_json
from components.ui import RISK_COLORS, page_header, status_chip


def render() -> None:
    page_header(
        "AI Risk Analysis",
        "Rule-based screening simulation for clinical risk score, flags, priority, and recommended action.",
    )

    with st.form("risk_form"):
        left, right = st.columns(2)
        donor_name = left.text_input("Donor name", "Sample Donor")
        age = left.number_input("Age", min_value=0, max_value=120, value=72)
        blood_type = left.selectbox("Blood type", ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Unknown"])
        infectious_history = right.checkbox("Infectious disease history")
        travel_risk = right.checkbox("Recent travel risk", value=True)
        missing_required_fields = right.checkbox("Missing required fields")
        clinical_notes = st.text_area(
            "Clinical notes",
            "Recent travel documented; donor disclosed fever within prior screening window.",
            height=140,
        )
        submitted = st.form_submit_button("Run Screening")

    if submitted:
        result = post_json(
            "/api/risk-analysis",
            {
                "donor_name": donor_name,
                "age": int(age),
                "blood_type": blood_type,
                "infectious_history": infectious_history,
                "travel_risk": travel_risk,
                "missing_required_fields": missing_required_fields,
                "clinical_notes": clinical_notes,
            },
        )
        if result:
            cols = st.columns(4)
            cols[0].metric("Risk Score", result["risk_score"])
            cols[1].markdown(status_chip(result["risk_level"], RISK_COLORS), unsafe_allow_html=True)
            cols[2].metric("Priority", result["review_priority"])
            cols[3].metric("Recommended Action", result["recommended_action"])
            st.subheader("Flagged Conditions")
            for condition in result["flagged_conditions"]:
                st.write(f"- {condition}")

