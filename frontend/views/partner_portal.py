from __future__ import annotations

import streamlit as st
from components.api import get_json, post_json
from components.ui import dataframe, empty_state, last_updated, page_header, status_chip


def _kpi_row(kpis: dict) -> None:
    if not kpis:
        return
    labels = ["open_submissions", "pending_review", "info_requested", "approved", "closed"]
    if not any(key in kpis for key in labels):
        labels = list(kpis.keys())[:5]
    columns = st.columns(5)
    for index, key in enumerate(labels[:5]):
        columns[index].metric(key.replace("_", " ").title(), kpis.get(key, 0))


def _submission_form() -> None:
    with st.form("partner_new_submission", border=True):
        st.write("New Submission")
        submission_type = st.selectbox(
            "Submission type",
            [
                "New Tissue Submission",
                "New Recovery Submission",
                "New Vendor Documentation",
                "New Qualification Request",
                "New Compliance Submission",
                "New Partner Inquiry",
            ],
        )
        title = st.text_input("Submission title", value="Recovery documentation packet")
        product_or_tissue = st.text_input("Product or tissue", value="Dermal Matrix")
        batch_or_reference = st.text_input("Batch or reference", value="EXT-REF-1044")
        priority = st.selectbox("Priority", ["Standard", "High", "Critical"], index=0)
        description = st.text_area(
            "Description",
            value="Partner submission package with supporting documentation for review.",
        )
        contact_email = st.text_input("Contact email", value="")
        attestation = st.checkbox("I certify this submission is accurate and complete.", value=True)
        submitted = st.form_submit_button("Submit for Review", width="stretch")
    if submitted:
        result = post_json(
            "/api/partners/submissions",
            {
                "submission_type": submission_type,
                "title": title,
                "description": description,
                "product_or_tissue": product_or_tissue,
                "batch_or_reference": batch_or_reference,
                "priority": priority,
                "contact_email": contact_email or None,
                "attestation": attestation,
            },
        )
        if result:
            st.success(f"Submission created: {result['submission_code']}")
            st.rerun()


def _complaint_form() -> None:
    with st.form("partner_quality_complaint", border=True):
        st.write("Quality Complaint")
        product_or_batch = st.text_input("Product or batch", value="Batch EXT-1044")
        issue_category = st.selectbox(
            "Issue category",
            ["Documentation discrepancy", "Packaging concern", "Temperature excursion", "Labeling issue", "Other"],
        )
        severity = st.selectbox("Severity", ["Low", "Medium", "High", "Critical"], index=1)
        description = st.text_area("Description", value="Describe the quality issue and known context.")
        impact = st.text_area("Impact assessment", value="No confirmed downstream impact at time of submission.")
        contact_email = st.text_input("Complaint contact email", value="")
        submitted = st.form_submit_button("Create Complaint", width="stretch")
    if submitted:
        result = post_json(
            "/api/partners/complaints",
            {
                "product_or_batch": product_or_batch,
                "issue_category": issue_category,
                "severity": severity,
                "description": description,
                "impact_assessment": impact,
                "contact_email": contact_email or None,
            },
        )
        if result:
            st.success(f"Quality complaint created: {result['complaint_code']}")
            st.rerun()


def _document_form(submissions: list[dict], complaints: list[dict]) -> None:
    submission_options = ["None"] + [
        f"{item['submission_id']} | {item['submission_code']} | {item['title']}" for item in submissions
    ]
    complaint_options = ["None"] + [
        f"{item['complaint_id']} | {item['complaint_code']} | {item['issue_category']}" for item in complaints
    ]
    with st.form("partner_document_upload", border=True):
        st.write("Document Center")
        target_type = st.radio("Attach to", ["Submission", "Complaint", "General"], horizontal=True)
        selected_submission = st.selectbox("Submission", submission_options, disabled=target_type != "Submission")
        selected_complaint = st.selectbox("Complaint", complaint_options, disabled=target_type != "Complaint")
        document_name = st.text_input("Document name", value="Partner evidence packet.pdf")
        document_type = st.selectbox(
            "Document type",
            ["Certification", "Audit Response", "CAPA Evidence", "Qualification Document", "SOP Acknowledgement", "Compliance Form"],
        )
        category = st.selectbox("Category", ["Submission Evidence", "Requested Document", "Complaint Attachment", "Qualification Evidence"])
        storage_reference = st.text_input("Storage reference", value="partner://pending-upload/evidence-packet.pdf")
        checksum = st.text_input("Checksum", value="")
        uploaded = st.form_submit_button("Upload Document", width="stretch")
    if uploaded:
        result = post_json(
            "/api/partners/documents",
            {
                "document_name": document_name,
                "document_type": document_type,
                "document_category": category,
                "storage_reference": storage_reference,
                "checksum_sha256": checksum or None,
                "submission_id": int(selected_submission.split(" | ")[0]) if target_type == "Submission" and selected_submission != "None" else None,
                "complaint_id": int(selected_complaint.split(" | ")[0]) if target_type == "Complaint" and selected_complaint != "None" else None,
            },
        )
        if result:
            st.success("Document uploaded for review.")
            st.rerun()


def _task_response(tasks: list[dict]) -> None:
    st.markdown("<div class='section-title'>Pending Actions</div>", unsafe_allow_html=True)
    if not tasks:
        empty_state("No partner actions are currently waiting.")
        return
    dataframe(tasks, columns=["task_id", "title", "priority", "review_status", "due_date"], height=240)
    options = [f"{task['task_id']} | {task['title']}" for task in tasks]
    with st.form("partner_task_response", border=True):
        selected = st.selectbox("Respond to request", options)
        response_status = st.selectbox("Response status", ["Submitted", "In Progress", "Blocked"], index=0)
        note = st.text_area("Response note", value="Requested information has been provided for review.")
        submitted = st.form_submit_button("Send Response", width="stretch")
    if submitted:
        task_id = int(selected.split(" | ")[0])
        result = post_json(
            f"/api/partners/tasks/{task_id}/respond",
            {"status": response_status, "response_note": note},
        )
        if result:
            st.success("Response submitted.")
            st.rerun()


def _message_form(submissions: list[dict], complaints: list[dict]) -> None:
    records = ["General"] + [
        f"Submission | {item['submission_id']} | {item['submission_code']}" for item in submissions
    ] + [
        f"Complaint | {item['complaint_id']} | {item['complaint_code']}" for item in complaints
    ]
    with st.form("partner_message", border=True):
        st.write("Message Center")
        selected = st.selectbox("Related record", records)
        subject = st.text_input("Subject", value="Follow-up information")
        body = st.text_area("Message", value="Please review the attached partner response.")
        sent = st.form_submit_button("Send Message", width="stretch")
    if sent:
        payload = {"subject": subject, "body": body}
        if selected.startswith("Submission"):
            payload["submission_id"] = int(selected.split(" | ")[1])
        elif selected.startswith("Complaint"):
            payload["complaint_id"] = int(selected.split(" | ")[1])
        result = post_json("/api/partners/messages", payload)
        if result:
            st.success("Message sent.")
            st.rerun()


def render_dashboard() -> None:
    page_header("Partner Portal", "Submissions, review status, document requests, quality complaints, and messages.")
    payload = get_json("/api/partners/dashboard") or {}
    if not payload:
        st.error("Partner portal data is unavailable.")
        return

    organization = payload.get("organization") or {}
    relationship = payload.get("relationship") or {}
    last_updated()
    left, right = st.columns([0.72, 0.28])
    with left:
        st.markdown(f"### {organization.get('organization_name', 'Partner Organization')}")
        st.caption(organization.get("organization_type", "Partner"))
    with right:
        st.markdown(
            status_chip(relationship.get("status") or organization.get("approval_status", "Approved")),
            unsafe_allow_html=True,
        )
        st.caption(f"Onboarding: {relationship.get('onboarding_status', 'Active')}")

    _kpi_row(payload.get("kpis", {}))
    st.divider()

    submissions = payload.get("submissions", [])
    complaints = payload.get("complaints", [])
    tasks = payload.get("tasks", [])

    main_left, main_right = st.columns([0.62, 0.38])
    with main_left:
        st.markdown("<div class='section-title'>Submission Lifecycle</div>", unsafe_allow_html=True)
        dataframe(
            submissions,
            columns=[
                "submission_code",
                "submission_type",
                "title",
                "status",
                "estimated_completion_at",
                "submitted_at",
            ],
            height=280,
        )
        _task_response(tasks)
    with main_right:
        _submission_form()
        _complaint_form()

    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.markdown("<div class='section-title'>Quality Complaints</div>", unsafe_allow_html=True)
        dataframe(
            complaints,
            columns=["complaint_code", "product_or_batch", "issue_category", "severity", "status", "submitted_at"],
            height=250,
        )
        _document_form(submissions, complaints)
    with lower_right:
        st.markdown("<div class='section-title'>Document Center</div>", unsafe_allow_html=True)
        dataframe(
            payload.get("documents", []),
            columns=["document_name", "document_type", "document_category", "approval_status", "review_note", "created_at"],
            height=250,
        )
        st.markdown("<div class='section-title'>Messages</div>", unsafe_allow_html=True)
        dataframe(payload.get("messages", []), columns=["subject", "audience", "created_at", "is_read"], height=190)
        _message_form(submissions, complaints)

    st.markdown("<div class='section-title'>Notifications</div>", unsafe_allow_html=True)
    dataframe(payload.get("notifications", []), columns=["title", "priority", "is_read", "created_at"], height=220)


def _document_review(documents: list[dict]) -> None:
    st.markdown("<div class='section-title'>Partner Document Review</div>", unsafe_allow_html=True)
    if not documents:
        empty_state("No partner documents are awaiting review.")
        return
    dataframe(
        documents,
        columns=["document_id", "organization_name", "document_name", "document_type", "approval_status", "review_note", "uploaded_by", "created_at"],
        height=240,
    )
    options = [
        f"{document['document_id']} | {document.get('organization_name', '')} | {document['document_name']}"
        for document in documents
    ]
    with st.form("review_partner_document", border=True):
        selected = st.selectbox("Document", options)
        approval_status = st.selectbox("Review outcome", ["Approved", "Needs Rework", "Hold", "Rejected"])
        review_note = st.text_area("Review note", value="Document reviewed for partner submission completeness.")
        reviewed = st.form_submit_button("Record Review", width="stretch")
    if reviewed:
        document_id = int(selected.split(" | ")[0])
        result = post_json(
            f"/api/suppliers/documents/{document_id}/review",
            {"approval_status": approval_status, "review_note": review_note},
        )
        if result:
            st.success("Partner document review recorded.")
            st.rerun()


def render_admin() -> None:
    page_header("Partner Administration", "Organizations, lifecycle submissions, complaints, document reviews, and onboarding.")
    overview = get_json("/api/partners/admin/overview") or {}
    organizations = get_json("/api/suppliers/organizations") or overview.get("organizations", [])
    last_updated()
    _kpi_row(overview.get("kpis", {}))

    tab_orgs, tab_lifecycle, tab_documents, tab_onboarding = st.tabs(
        ["Organizations", "Lifecycle", "Documents", "Onboarding"]
    )
    org_options = {
        f"{org['organization_id']} | {org['organization_name']}": org["organization_id"]
        for org in organizations
    }
    with tab_orgs:
        dataframe(organizations, height=260)
        left, right = st.columns(2)
        with left:
            with st.form("create_partner_org", border=True):
                st.write("Create Partner Organization")
                organization_name = st.text_input("Organization name", value="New Partner Organization")
                organization_type = st.selectbox("Organization type", ["Partner", "Recovery Organization", "Supplier", "Auditor", "Customer"])
                contact_email = st.text_input("Contact email", value="partner-contact@example.org")
                risk_tier = st.selectbox("Risk tier", ["Low", "Medium", "High", "Critical"], index=1)
                created = st.form_submit_button("Create Organization", width="stretch")
            if created:
                result = post_json(
                    "/api/suppliers/organizations",
                    {
                        "organization_name": organization_name,
                        "organization_type": organization_type,
                        "contact_email": contact_email,
                        "risk_tier": risk_tier,
                        "approval_status": "Pending Approval",
                    },
                )
                if result:
                    st.success("Partner organization created.")
                    st.rerun()
        with right:
            with st.form("invite_partner_user", border=True):
                st.write("Invite Partner User")
                selected_org = st.selectbox("Organization", list(org_options.keys()) or ["No organizations"])
                email = st.text_input("Invite email", value="partner.user@example.org")
                invited = st.form_submit_button("Send Invitation", width="stretch")
            if invited and org_options:
                result = post_json(
                    "/api/suppliers/invitations",
                    {
                        "organization_id": org_options[selected_org],
                        "email": email,
                        "role_name": "Partner External User",
                    },
                )
                if result:
                    st.success("Partner invitation created.")
                    if result.get("demo_invitation_url"):
                        st.code(result["demo_invitation_url"])

    with tab_lifecycle:
        st.markdown("<div class='section-title'>Partner Submissions</div>", unsafe_allow_html=True)
        dataframe(overview.get("submissions", []), height=260)
        st.markdown("<div class='section-title'>Quality Complaints</div>", unsafe_allow_html=True)
        dataframe(overview.get("complaints", []), height=260)
        st.markdown("<div class='section-title'>Internal Tasks From Partner Portal</div>", unsafe_allow_html=True)
        dataframe(overview.get("tasks", []), height=220)

    with tab_documents:
        documents = get_json("/api/suppliers/documents") or []
        _document_review(documents)

    with tab_onboarding:
        invitations = get_json("/api/suppliers/invitations") or []
        dataframe(
            invitations,
            columns=["invitation_id", "organization_name", "email", "status", "created_user", "expires_at", "accepted_at"],
            height=240,
        )
        accepted = [item for item in invitations if item.get("created_user") and item.get("status") in {"Pending Approval"}]
        if accepted:
            with st.form("approve_partner_invitation", border=True):
                selected = st.selectbox(
                    "Approval request",
                    [f"{item['invitation_id']} | {item['email']} | {item.get('organization_name', '')}" for item in accepted],
                )
                approval_status = st.selectbox("Approval status", ["Approved", "Rejected", "Suspended", "Revoked"])
                approved = st.form_submit_button("Apply Approval", width="stretch")
            if approved:
                invitation_id = int(selected.split(" | ")[0])
                result = post_json(
                    f"/api/suppliers/invitations/{invitation_id}/approve",
                    {"approval_status": approval_status, "relationship_status": approval_status},
                )
                if result:
                    st.success("Partner approval updated.")
                    st.rerun()
