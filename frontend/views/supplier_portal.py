from __future__ import annotations

import pandas as pd
import streamlit as st
from components.api import get_json, post_json
from components.ui import dataframe, empty_state, last_updated, page_header, status_chip


def _kpi_row(kpis: dict) -> None:
    if not kpis:
        return
    columns = st.columns(min(5, len(kpis)))
    for index, (label, value) in enumerate(list(kpis.items())[:5]):
        columns[index].metric(label.replace("_", " ").title(), value)


def _task_table(tasks: list[dict], *, key: str) -> None:
    if not tasks:
        empty_state("No supplier tasks are currently assigned.")
        return
    columns = [
        "task_id",
        "task_type",
        "title",
        "priority",
        "status",
        "workflow_state",
        "queue_name",
        "due_date",
        "related_record_type",
        "related_record_id",
    ]
    dataframe(tasks, columns=columns, height=300)

    options = [f"{task['task_id']} | {task['title']}" for task in tasks]
    selected = st.selectbox("Respond to task", options, key=key)
    task_id = int(selected.split(" | ")[0])
    task = next((item for item in tasks if item["task_id"] == task_id), {})
    with st.form(f"supplier_task_response_{task_id}", border=True):
        status = st.selectbox("Response status", ["In Progress", "Completed", "Blocked"], index=1)
        note = st.text_area("Response note", value=f"Supplier response provided for {task.get('title', 'task')}.")
        submitted = st.form_submit_button("Submit Response", width="stretch")
    if submitted:
        result = post_json(f"/api/suppliers/tasks/{task_id}/respond", {"status": status, "response_note": note})
        if result:
            st.success("Task response recorded.")
            st.rerun()


def _document_uploader() -> None:
    with st.form("supplier_document_upload", border=True):
        st.write("Submit Document")
        record_type = st.selectbox(
            "Record type",
            ["SupplierReview", "DocumentRequest", "ExternalCAPAResponse", "VendorIncident", "Qualification"],
        )
        record_id = st.text_input("Record ID", value="SUP-QUAL-001")
        document_name = st.text_input("Document name", value="Supplier certification packet.pdf")
        document_type = st.selectbox(
            "Document type",
            ["Supplier Certification", "CAPA Evidence", "Lab Report", "Qualification Doc", "Audit Evidence"],
        )
        storage_reference = st.text_input("Storage reference", value="supplier://pending-upload/certification-packet.pdf")
        checksum = st.text_input("Checksum", value="")
        uploaded = st.form_submit_button("Submit Document", width="stretch")
    if uploaded:
        result = post_json(
            "/api/suppliers/documents",
            {
                "record_type": record_type,
                "record_id": record_id,
                "document_name": document_name,
                "document_type": document_type,
                "storage_reference": storage_reference,
                "checksum_sha256": checksum or None,
            },
        )
        if result:
            st.success(f"Document submitted for review: #{result['document_id']}")
            st.rerun()


def _document_review(documents: list[dict]) -> None:
    st.markdown("<div class='section-title'>Supplier Document Review</div>", unsafe_allow_html=True)
    if not documents:
        empty_state("No supplier documents are awaiting review.")
        return
    dataframe(
        documents,
        columns=[
            "document_id",
            "organization_name",
            "document_name",
            "document_type",
            "approval_status",
            "review_note",
            "uploaded_by",
            "created_at",
        ],
        height=260,
    )
    options = [
        f"{document['document_id']} | {document.get('organization_name', '')} | {document['document_name']}"
        for document in documents
    ]
    with st.form("review_supplier_document", border=True):
        selected = st.selectbox("Document", options)
        approval_status = st.selectbox("Review outcome", ["Approved", "Needs Rework", "Hold", "Rejected"])
        review_note = st.text_area(
            "Review note",
            value="Document reviewed for supplier qualification and workflow evidence completeness.",
        )
        reviewed = st.form_submit_button("Record Review", width="stretch")
    if reviewed:
        document_id = int(selected.split(" | ")[0])
        result = post_json(
            f"/api/suppliers/documents/{document_id}/review",
            {"approval_status": approval_status, "review_note": review_note},
        )
        if result:
            st.success("Supplier document review recorded.")
            st.rerun()


def _signature_form(tasks: list[dict]) -> None:
    with st.form("supplier_signature", border=True):
        st.write("Electronic Signature")
        task_options = [f"WorkflowTask | {task['task_id']} | {task['title']}" for task in tasks]
        selected = st.selectbox(
            "Record",
            task_options or ["SupplierReview | SUP-QUAL-001 | Supplier qualification acknowledgement"],
        )
        record_type, record_id, _ = selected.split(" | ", 2)
        reason = st.text_area("Signature reason", value="Supplier response reviewed and approved.")
        meaning = st.text_area(
            "Signature meaning",
            value="I certify this supplier response is complete and attributable to my authenticated identity.",
        )
        password = st.text_input("Re-enter password", type="password")
        signed = st.form_submit_button("Apply Signature", width="stretch")
    if signed:
        result = post_json(
            "/api/suppliers/signatures",
            {
                "record_type": record_type,
                "record_id": record_id,
                "signature_type": "Supplier Approval",
                "reason": reason,
                "meaning": meaning,
                "password": password,
                "prior_state": "Pending Supplier Approval",
                "new_state": "Supplier Approved",
            },
        )
        if result:
            st.success("Electronic signature captured.")
            st.rerun()


def render_dashboard() -> None:
    page_header("Supplier Portal", "Assigned collaboration work, document requests, approvals, and activity.")
    payload = get_json("/api/suppliers/dashboard") or {}
    if not payload:
        st.error("Supplier portal data is unavailable.")
        return

    organization = payload.get("organization") or {}
    relationship = payload.get("relationship") or {}
    last_updated()
    left, right = st.columns([0.7, 0.3])
    with left:
        st.markdown(f"### {organization.get('organization_name', 'Supplier Organization')}")
        st.caption(organization.get("organization_type", "Supplier"))
    with right:
        st.markdown(
            status_chip(relationship.get("status") or organization.get("approval_status", "Pending")),
            unsafe_allow_html=True,
        )
        st.caption(f"Onboarding: {relationship.get('onboarding_status', 'Active')}")

    _kpi_row(payload.get("kpis", {}))
    st.divider()

    tasks = payload.get("tasks", [])
    left, right = st.columns([0.62, 0.38])
    with left:
        st.markdown("<div class='section-title'>Supplier Task Queue</div>", unsafe_allow_html=True)
        _task_table(tasks, key="supplier_response_select")
    with right:
        _document_uploader()
        _signature_form(tasks)

    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.markdown("<div class='section-title'>Submitted Documents</div>", unsafe_allow_html=True)
        dataframe(
            payload.get("documents", []),
            columns=[
                "document_id",
                "document_name",
                "document_type",
                "approval_status",
                "review_note",
                "created_at",
            ],
            height=260,
        )
    with lower_right:
        st.markdown("<div class='section-title'>Activity Feed</div>", unsafe_allow_html=True)
        activity = payload.get("activity", [])
        if activity:
            dataframe(activity, columns=["event_type", "record_type", "record_id", "created_at"], height=260)
        else:
            empty_state("No supplier activity has been recorded yet.")

    notifications = payload.get("notifications", [])
    st.markdown("<div class='section-title'>Notifications</div>", unsafe_allow_html=True)
    dataframe(notifications, columns=["title", "priority", "is_read", "created_at"], height=220)


def render_admin() -> None:
    page_header("Supplier Administration", "Supplier organizations, invitations, approvals, and collaboration controls.")
    organizations = get_json("/api/suppliers/organizations") or []
    last_updated()
    dataframe(organizations, height=260)

    org_options = {
        f"{org['organization_id']} | {org['organization_name']}": org["organization_id"]
        for org in organizations
    }
    left, right = st.columns(2)
    with left:
        st.write("Create Supplier Organization")
        with st.form("create_supplier_org", border=True):
            organization_name = st.text_input("Organization name", value="New Supplier Partner")
            organization_type = st.selectbox("Organization type", ["Supplier", "Partner", "Recovery Organization", "Auditor"])
            contact_email = st.text_input("Contact email", value="supplier-contact@example.org")
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
                st.success("Supplier organization created.")
                st.rerun()

    with right:
        st.write("Invite Supplier User")
        with st.form("invite_supplier", border=True):
            selected_org = st.selectbox("Organization", list(org_options.keys()) or ["No organizations"])
            email = st.text_input("Invite email", value="supplier.user@example.org")
            invited = st.form_submit_button("Send Invitation", width="stretch")
        if invited and org_options:
            result = post_json(
                "/api/suppliers/invitations",
                {"organization_id": org_options[selected_org], "email": email},
            )
            if result:
                st.success("Supplier invitation created.")
                if result.get("demo_invitation_url"):
                    st.code(result["demo_invitation_url"])

    jobs = get_json("/api/suppliers/background-jobs") or {}
    st.markdown("<div class='section-title'>Background Event Queue</div>", unsafe_allow_html=True)
    summary = jobs.get("summary", [])
    if summary:
        st.dataframe(pd.DataFrame(summary), width="stretch", height=160, hide_index=True)
    dataframe(jobs.get("recent", []), height=260)

    documents = get_json("/api/suppliers/documents") or []
    _document_review(documents)

    invitations = get_json("/api/suppliers/invitations") or []
    st.markdown("<div class='section-title'>Supplier Invitations</div>", unsafe_allow_html=True)
    dataframe(
        invitations,
        columns=[
            "invitation_id",
            "organization_name",
            "email",
            "status",
            "created_user",
            "expires_at",
            "accepted_at",
        ],
        height=240,
    )
    accepted = [item for item in invitations if item.get("created_user") and item.get("status") in {"Pending Approval"}]
    if accepted:
        with st.form("approve_supplier_invitation", border=True):
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
                st.success("Supplier approval updated.")
                st.rerun()
