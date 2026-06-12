from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Patient, PatientConsent, PatientContact, PatientInsurance, User
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_patients import (
    DuplicateRiskWarning,
    PatientCreatePreviewRequest,
    PatientPreviewResponse,
    PatientUpdatePreviewRequest,
)
from app.services.clinical_workflows import append_workflow_operation, preview_hash

PATIENT_FIELDS = [
    "donor_reference",
    "first_name",
    "middle_name",
    "last_name",
    "date_of_birth",
    "sex_at_birth",
    "gender_identity",
    "preferred_language",
    "phone",
    "email",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "postal_code",
    "status",
]


def actor_label(user: User) -> str:
    return user.email or user.username or user.full_name or f"user:{user.user_id}"


def new_patient_identifier() -> str:
    return f"PT-{uuid4().hex[:10].upper()}"


def patient_name(patient: Patient) -> str:
    parts = [patient.first_name, patient.middle_name, patient.last_name]
    return " ".join(part for part in parts if part)


def patient_field_payload(payload: PatientCreatePreviewRequest | PatientUpdatePreviewRequest) -> dict[str, Any]:
    return payload.model_dump(exclude={"contacts", "insurance", "consents", "preview_hash", "reason"}, exclude_unset=True)


def duplicate_risk_warnings(
    db: Session,
    payload: PatientCreatePreviewRequest | PatientUpdatePreviewRequest,
    *,
    exclude_patient_pk: int | None = None,
) -> list[DuplicateRiskWarning]:
    data = payload.model_dump(exclude_unset=True)
    conditions = []
    first_name = str(data.get("first_name") or "").strip().lower()
    last_name = str(data.get("last_name") or "").strip().lower()
    date_of_birth = data.get("date_of_birth")
    phone = str(data.get("phone") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    if first_name and last_name and date_of_birth:
        conditions.append(
            and_(
                func.lower(Patient.first_name) == first_name,
                func.lower(Patient.last_name) == last_name,
                Patient.date_of_birth == date_of_birth,
            )
        )
    if phone:
        conditions.append(Patient.phone == phone)
    if email:
        conditions.append(func.lower(Patient.email) == email)
    if not conditions:
        return []

    query = select(Patient).where(Patient.is_deleted.is_(False), or_(*conditions)).limit(10)
    if exclude_patient_pk is not None:
        query = query.where(Patient.patient_pk != exclude_patient_pk)
    matches = list(db.execute(query).scalars().all())
    warnings: list[DuplicateRiskWarning] = []
    for patient in matches:
        matched_fields = []
        if first_name and last_name and date_of_birth:
            if (
                patient.first_name.lower() == first_name
                and patient.last_name.lower() == last_name
                and patient.date_of_birth == date_of_birth
            ):
                matched_fields.extend(["first_name", "last_name", "date_of_birth"])
        if phone and patient.phone == phone:
            matched_fields.append("phone")
        if email and patient.email and patient.email.lower() == email:
            matched_fields.append("email")
        warnings.append(
            DuplicateRiskWarning(
                patient_id=patient.patient_id,
                patient_pk=patient.patient_pk,
                display_name=patient_name(patient),
                date_of_birth=patient.date_of_birth,
                matched_fields=matched_fields,
                message=f"Possible duplicate patient/donor profile: {patient.patient_id}.",
            )
        )
    return warnings


def preview_patient_create(db: Session, payload: PatientCreatePreviewRequest) -> PatientPreviewResponse:
    duplicate_warnings = duplicate_risk_warnings(db, payload)
    changes = payload.model_dump(mode="json")
    return PatientPreviewResponse(
        workflow="patient.create",
        entity_id="draft",
        preview_hash=preview_hash({"workflow": "patient.create", "changes": changes}),
        validation_status="warning" if duplicate_warnings else "passed",
        duplicate_warnings=duplicate_warnings,
        summary="Patient/donor profile is ready for commit.",
        changes=changes,
    )


def preview_patient_update(
    db: Session,
    patient: Patient,
    payload: PatientUpdatePreviewRequest,
) -> PatientPreviewResponse:
    updates = patient_field_payload(payload)
    changes = {
        field: {"before": getattr(patient, field), "after": value}
        for field, value in updates.items()
        if getattr(patient, field) != value
    }
    merged_payload = PatientUpdatePreviewRequest(
        first_name=updates.get("first_name", patient.first_name),
        last_name=updates.get("last_name", patient.last_name),
        date_of_birth=updates.get("date_of_birth", patient.date_of_birth),
        phone=updates.get("phone", patient.phone),
        email=updates.get("email", patient.email),
    )
    duplicate_warnings = duplicate_risk_warnings(db, merged_payload, exclude_patient_pk=patient.patient_pk)
    return PatientPreviewResponse(
        workflow="patient.update_demographics",
        entity_id=patient.patient_id,
        preview_hash=preview_hash({"workflow": "patient.update_demographics", "changes": changes}),
        validation_status="warning" if duplicate_warnings else "passed",
        duplicate_warnings=duplicate_warnings,
        summary="Patient/donor demographic changes are ready for commit.",
        changes=changes,
    )


def append_patient_workflow_audit(
    *,
    workflow: str,
    patient: Patient,
    actor: str,
    preview_value: str,
    status_before: str | None,
    status_after: str | None,
    reason: str,
    changes: dict[str, Any],
) -> tuple[WorkflowOperation, str]:
    operation = WorkflowOperation(
        workflow=workflow,
        entity_type="patient",
        entity_id=patient.patient_id,
        actor=actor,
        preview_hash=preview_value,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        changes=changes,
    )
    operation, audit_path = append_workflow_operation(operation)
    return operation, str(audit_path)


def apply_patient_children(
    patient: Patient,
    *,
    contacts: list[dict[str, Any]],
    insurance: list[dict[str, Any]],
    consents: list[dict[str, Any]],
    user_id: int | None,
) -> None:
    for contact_payload in contacts:
        if "relationship" in contact_payload:
            contact_payload["contact_relationship"] = contact_payload.pop("relationship")
        patient.contacts.append(PatientContact(**contact_payload, created_by=user_id, updated_by=user_id))
    for insurance_payload in insurance:
        patient.insurance_profiles.append(PatientInsurance(**insurance_payload, created_by=user_id, updated_by=user_id))
    for consent_payload in consents:
        patient.consents.append(PatientConsent(**consent_payload, created_by=user_id, updated_by=user_id))
