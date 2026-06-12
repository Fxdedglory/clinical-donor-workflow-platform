from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import Patient, PatientConsent, PatientContact, PatientInsurance, User
from app.schemas.clinical_patients import (
    PatientCommitResponse,
    PatientConsentRequest,
    PatientContactRequest,
    PatientCreatePreviewRequest,
    PatientCreateRequest,
    PatientInsuranceRequest,
    PatientListResponse,
    PatientPreviewResponse,
    PatientResponse,
    PatientUpdatePreviewRequest,
    PatientUpdateRequest,
)
from app.services.clinical_patients import (
    actor_label,
    append_patient_workflow_audit,
    apply_patient_children,
    new_patient_identifier,
    patient_field_payload,
    preview_patient_create,
    preview_patient_update,
)
from app.services.clinical_workflows import preview_hash, require_generation_confirmation

router = APIRouter(prefix="/api/clinical/patients", tags=["Clinical Patients"])

READ_PERMISSIONS = {"system.admin", "patients.read", "patients.manage", "donors.read", "eligibility.read"}
MUTATION_PERMISSIONS = {
    "system.admin",
    "patients.create",
    "patients.manage",
    "donors.create",
    "donors.review",
    "eligibility.review",
}
EXTERNAL_ROLES = {"Partner External User", "Supplier External User"}


def _is_external_user(user: User) -> bool:
    return bool(
        user.is_external
        or user.external_user_flag
        or user.account_type in {"partner", "supplier", "external"}
        or user.user_type in {"partner", "supplier", "external"}
        or user.role in EXTERNAL_ROLES
    )


def _permission_set(db: Session, user: User) -> set[str]:
    return set(getattr(user, "permissions", []) or []) | set(get_user_permissions(db, user))


def require_patient_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access patient registration")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient read permission required")
    return current_user


def require_patient_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate patient registration")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient mutation permission required")
    return current_user


def _patient_or_404(db: Session, patient_id: str) -> Patient:
    patient = db.execute(
        select(Patient).where(Patient.patient_id == patient_id, Patient.is_deleted.is_(False))
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient/donor profile not found")
    return patient


@router.get("", response_model=PatientListResponse)
def list_patients(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_patient_read),
    db: Session = Depends(get_db),
) -> PatientListResponse:
    query = select(Patient).where(Patient.is_deleted.is_(False))
    if status_filter:
        query = query.where(Patient.status == status_filter)
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
                func.lower(Patient.email).like(like),
                Patient.phone.like(f"%{q.strip()}%"),
            )
        )
    rows = list(db.execute(query.order_by(Patient.updated_at.desc()).offset(offset).limit(limit)).scalars().all())
    return PatientListResponse(patients=rows, total=len(rows))


@router.post("/preview", response_model=PatientPreviewResponse)
def preview_create_patient(
    payload: PatientCreatePreviewRequest,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientPreviewResponse:
    return preview_patient_create(db, payload)


@router.post("", response_model=PatientCommitResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreateRequest,
    request: Request,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientCommitResponse:
    require_generation_confirmation(request)
    patient_data = patient_field_payload(payload)
    patient = Patient(
        **patient_data,
        patient_id=new_patient_identifier(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    apply_patient_children(
        patient,
        contacts=[contact.model_dump() for contact in payload.contacts],
        insurance=[insurance.model_dump() for insurance in payload.insurance],
        consents=[consent.model_dump() for consent in payload.consents],
        user_id=current_user.user_id,
    )
    db.add(patient)
    db.flush()
    db.commit()
    db.refresh(patient)
    preview_value = payload.preview_hash or preview_hash({"workflow": "patient.create", "changes": payload.model_dump(mode="json")})
    operation, audit_path = append_patient_workflow_audit(
        workflow="patient.create",
        patient=patient,
        actor=actor_label(current_user),
        preview_value=preview_value,
        status_before=None,
        status_after=patient.status,
        reason=payload.reason,
        changes=payload.model_dump(mode="json"),
    )
    return PatientCommitResponse(patient=patient, operation_id=operation.operation_id, audit_path=audit_path)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    current_user: User = Depends(require_patient_read),
    db: Session = Depends(get_db),
) -> Patient:
    return _patient_or_404(db, patient_id)


@router.post("/{patient_id}/edit/preview", response_model=PatientPreviewResponse)
def preview_update_patient(
    patient_id: str,
    payload: PatientUpdatePreviewRequest,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientPreviewResponse:
    patient = _patient_or_404(db, patient_id)
    return preview_patient_update(db, patient, payload)


@router.patch("/{patient_id}", response_model=PatientCommitResponse)
def update_patient(
    patient_id: str,
    payload: PatientUpdateRequest,
    request: Request,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientCommitResponse:
    require_generation_confirmation(request)
    patient = _patient_or_404(db, patient_id)
    status_before = patient.status
    updates = patient_field_payload(payload)
    changes = {}
    for field, value in updates.items():
        old_value = getattr(patient, field)
        if old_value != value:
            changes[field] = {"before": old_value, "after": value}
            setattr(patient, field, value)
    patient.updated_by = current_user.user_id
    patient.version += 1
    db.flush()
    db.commit()
    db.refresh(patient)
    preview_value = payload.preview_hash or preview_hash({"workflow": "patient.update_demographics", "changes": changes})
    operation, audit_path = append_patient_workflow_audit(
        workflow="patient.update_demographics",
        patient=patient,
        actor=actor_label(current_user),
        preview_value=preview_value,
        status_before=status_before,
        status_after=patient.status,
        reason=payload.reason,
        changes=changes,
    )
    return PatientCommitResponse(patient=patient, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/{patient_id}/contacts/preview", response_model=PatientPreviewResponse)
def preview_contact(
    patient_id: str,
    payload: PatientContactRequest,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientPreviewResponse:
    patient = _patient_or_404(db, patient_id)
    changes = payload.model_dump(mode="json")
    return PatientPreviewResponse(
        workflow="patient.add_contact",
        entity_id=patient.patient_id,
        preview_hash=preview_hash({"workflow": "patient.add_contact", "changes": changes}),
        validation_status="passed",
        summary="Contact is ready for commit.",
        changes=changes,
    )


@router.post("/{patient_id}/contacts", response_model=PatientCommitResponse, status_code=status.HTTP_201_CREATED)
def add_contact(
    patient_id: str,
    payload: PatientContactRequest,
    request: Request,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientCommitResponse:
    require_generation_confirmation(request)
    patient = _patient_or_404(db, patient_id)
    contact_payload = payload.model_dump()
    if "relationship" in contact_payload:
        contact_payload["contact_relationship"] = contact_payload.pop("relationship")
    contact = PatientContact(
        **contact_payload,
        patient_pk=patient.patient_pk,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(contact)
    db.flush()
    db.commit()
    db.refresh(patient)
    changes = payload.model_dump(mode="json")
    operation, audit_path = append_patient_workflow_audit(
        workflow="patient.add_contact",
        patient=patient,
        actor=actor_label(current_user),
        preview_value=preview_hash({"workflow": "patient.add_contact", "changes": changes}),
        status_before=patient.status,
        status_after=patient.status,
        reason="Add patient/donor contact",
        changes=changes,
    )
    return PatientCommitResponse(patient=patient, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/{patient_id}/insurance/preview", response_model=PatientPreviewResponse)
def preview_insurance(
    patient_id: str,
    payload: PatientInsuranceRequest,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientPreviewResponse:
    patient = _patient_or_404(db, patient_id)
    changes = payload.model_dump(mode="json")
    return PatientPreviewResponse(
        workflow="patient.add_insurance",
        entity_id=patient.patient_id,
        preview_hash=preview_hash({"workflow": "patient.add_insurance", "changes": changes}),
        validation_status="passed",
        summary="Insurance profile is ready for commit.",
        changes=changes,
    )


@router.post("/{patient_id}/insurance", response_model=PatientCommitResponse, status_code=status.HTTP_201_CREATED)
def add_insurance(
    patient_id: str,
    payload: PatientInsuranceRequest,
    request: Request,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientCommitResponse:
    require_generation_confirmation(request)
    patient = _patient_or_404(db, patient_id)
    insurance = PatientInsurance(
        **payload.model_dump(),
        patient_pk=patient.patient_pk,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(insurance)
    db.flush()
    db.commit()
    db.refresh(patient)
    changes = payload.model_dump(mode="json")
    operation, audit_path = append_patient_workflow_audit(
        workflow="patient.add_insurance",
        patient=patient,
        actor=actor_label(current_user),
        preview_value=preview_hash({"workflow": "patient.add_insurance", "changes": changes}),
        status_before=patient.status,
        status_after=patient.status,
        reason="Add patient/donor insurance",
        changes=changes,
    )
    return PatientCommitResponse(patient=patient, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/{patient_id}/consents/preview", response_model=PatientPreviewResponse)
def preview_consent(
    patient_id: str,
    payload: PatientConsentRequest,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientPreviewResponse:
    patient = _patient_or_404(db, patient_id)
    changes = payload.model_dump(mode="json")
    return PatientPreviewResponse(
        workflow="patient.capture_consent",
        entity_id=patient.patient_id,
        preview_hash=preview_hash({"workflow": "patient.capture_consent", "changes": changes}),
        validation_status="passed",
        summary="Consent is ready for commit.",
        changes=changes,
    )


@router.post("/{patient_id}/consents", response_model=PatientCommitResponse, status_code=status.HTTP_201_CREATED)
def add_consent(
    patient_id: str,
    payload: PatientConsentRequest,
    request: Request,
    current_user: User = Depends(require_patient_mutation),
    db: Session = Depends(get_db),
) -> PatientCommitResponse:
    require_generation_confirmation(request)
    patient = _patient_or_404(db, patient_id)
    consent = PatientConsent(**payload.model_dump(), patient_pk=patient.patient_pk, created_by=current_user.user_id, updated_by=current_user.user_id)
    db.add(consent)
    db.flush()
    db.commit()
    db.refresh(patient)
    changes = payload.model_dump(mode="json")
    operation, audit_path = append_patient_workflow_audit(
        workflow="patient.capture_consent",
        patient=patient,
        actor=actor_label(current_user),
        preview_value=preview_hash({"workflow": "patient.capture_consent", "changes": changes}),
        status_before=patient.status,
        status_after=patient.status,
        reason="Capture patient/donor consent",
        changes=changes,
    )
    return PatientCommitResponse(patient=patient, operation_id=operation.operation_id, audit_path=audit_path)
