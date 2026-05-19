import streamlit as st
from components.api import get_json, post_json
from components.ui import RISK_COLORS, page_header, status_chip


def render() -> None:
    page_header(
        "Donor Review",
        "Detailed intake packet review with clinical decision capture and audit logging.",
    )

    queue = get_json("/api/reviews?queue=active&limit=250") or []
    if not queue:
        st.info("No active donor reviews.")
        return

    options = {
        f"{row['donor_id']} | {row['donor_name']} | {row['risk_level']} | {row['intake_status']}": row[
            "review_id"
        ]
        for row in queue
    }
    selected = st.selectbox("Active review", list(options.keys()))
    donor = get_json(f"/api/donors/{options[selected]}")
    if not donor:
        return

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Clinical Intake")
        st.markdown(
            f"""
            <div class="clinical-panel">
                <div><strong>Donor ID:</strong> {donor['donor_id']}</div>
                <div><strong>Name:</strong> {donor['donor_name']}</div>
                <div><strong>Age:</strong> {donor.get('age', '')}</div>
                <div><strong>Blood type:</strong> {donor.get('blood_type', '')}</div>
                <div><strong>Status:</strong> {status_chip(donor['intake_status'])}</div>
                <div><strong>Risk:</strong> {status_chip(donor['risk_level'], RISK_COLORS)} score {donor['risk_score']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_area("Clinical notes", donor.get("clinical_notes", ""), height=160, disabled=True)
        st.write("Flagged conditions")
        for flag in donor.get("risk_flags", []):
            st.write(f"- {flag}")

    with right:
        st.subheader("Decision")
        st.write(f"Recommended action: **{donor['recommended_action']}**")
        st.write(f"Review priority: **{donor['review_priority']}**")
        with st.form("decision_form"):
            decision = st.selectbox("Decision", ["Approved", "Rejected", "Deferred", "Under Review"])
            reviewer_id = st.number_input("Reviewer user ID", min_value=1, value=donor.get("reviewer_id") or 1)
            rejection_reason = st.text_area("Decision rationale", value=donor.get("rejection_reason") or "")
            ai_override = st.checkbox("Human override of AI recommendation")
            ai_override_reason = st.text_area(
                "Override reason",
                value="Clinical reviewer documented context not represented in the AI rule evaluation."
                if ai_override
                else "",
            )
            submitted = st.form_submit_button("Record Decision")
        if submitted:
            result = post_json(
                f"/api/donors/{donor['review_id']}/decision",
                {
                    "intake_status": decision,
                    "reviewer_id": int(reviewer_id),
                    "rejection_reason": rejection_reason or None,
                    "ai_override": ai_override,
                    "ai_override_reason": ai_override_reason or None,
                },
            )
            if result:
                st.success("Decision recorded and audit log updated.")
                st.rerun()

