from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import (
    ClinicalEncounter,
    ClinicalEncounterDiagnosis,
    ClinicalEncounterNote,
    ClinicalPatientAllergy,
    ClinicalPatientMedication,
    Patient,
    User,
)
from app.schemas.clinical_encounters import (
    EncounterAmendCommitRequest,
    EncounterAmendPreviewRequest,
    EncounterCommitResponse,
    EncounterCreatePreviewRequest,
    EncounterCreateRequest,
    EncounterDiagnosisRequest,
    EncounterDiagnosisResponse,
    EncounterListResponse,
    EncounterNoteCommitRequest,
    EncounterNotePreviewRequest,
    EncounterNoteResponse,
    EncounterPreviewResponse,
    EncounterResponse,
    EncounterSignCommitRequest,
    EncounterSignPreviewRequest,
    NoteTemplateResponse,
    PatientAllergyRequest,
    PatientAllergyResponse,
    PatientMedicationRequest,
    PatientMedicationResponse,
)
from app.services.clinical_encounters import (
    allergy_preview,
    amendment_preview,
    append_encounter_workflow_audit,
    append_status_history,
    appointment_by_id,
    encounter_actor,
    encounter_by_id,
    encounter_create_preview,
    diagnosis_preview,
    latest_signed_note,
    latest_unsigned_note,
    list_note_templates,
    medication_preview,
    new_encounter_number,
    note_by_id,
    note_changes,
    note_save_preview,
    now_utc,
    patient_by_identifier,
    screening_session_by_id,
    sign_preview,
    template_by_id,
    update_encounter_status,
)
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical", tags=["Clinical Encounters"])

READ_PERMISSIONS = {
    "system.admin",
    "encounters.read",
    "encounters.manage",
    "encounters.sign",
    "patients.read",
}
MUTATION_PERMISSIONS = {"system.admin", "encounters.manage"}
SIGN_PERMISSIONS = {"system.admin", "encounters.sign"}
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


def require_encounter_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access encounters")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Encounter read permission required")
    return current_user


def require_encounter_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate encounters")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Encounter mutation permission required")
    return current_user


def require_encounter_signature(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot sign or amend encounters")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(SIGN_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Encounter signature permission required")
    return current_user


def _encounter_or_404(db: Session, encounter_id: int) -> ClinicalEncounter:
    encounter = encounter_by_id(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return encounter


def _patient_or_404(db: Session, patient_id: str) -> Patient:
    patient = patient_by_identifier(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient/donor profile not found")
    return patient


def _reject_blocking(preview: EncounterPreviewResponse) -> None:
    if preview.blocking_issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "encounter_validation_failed",
                "message": "Blocking encounter issues prevent commit.",
                "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues],
            },
        )


@router.get("/encounters", response_model=EncounterListResponse)
def list_encounters(
    q: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    patient_id: str | None = Query(default=None),
    appointment_context: bool | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_encounter_read),
    db: Session = Depends(get_db),
) -> EncounterListResponse:
    query = select(ClinicalEncounter).where(ClinicalEncounter.is_deleted.is_(False))
    if date_filter:
        start_of_day = datetime.combine(date_filter, time.min)
        end_of_day = datetime.combine(date_filter, time.max)
        query = query.where(ClinicalEncounter.started_at >= start_of_day, ClinicalEncounter.started_at <= end_of_day)
    if status_filter:
        query = query.where(ClinicalEncounter.status == status_filter)
    if patient_id:
        query = query.join(Patient).where(Patient.patient_id == patient_id)
    if appointment_context is True:
        query = query.where(ClinicalEncounter.appointment_id.is_not(None))
    if appointment_context is False:
        query = query.where(ClinicalEncounter.appointment_id.is_(None))
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.join(Patient).where(
            or_(
                func.lower(ClinicalEncounter.encounter_number).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
                func.lower(Patient.donor_reference).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalEncounter.updated_at.desc()).offset(offset).limit(limit)).scalars().all())
    return EncounterListResponse(encounters=rows, total=len(rows))


@router.get("/encounters/templates", response_model=list[NoteTemplateResponse])
def encounter_note_templates(
    current_user: User = Depends(require_encounter_read),
    db: Session = Depends(get_db),
) -> list[NoteTemplateResponse]:
    return list_note_templates(db)


@router.get("/encounters/{encounter_id}", response_model=EncounterResponse)
def get_encounter(
    encounter_id: int,
    current_user: User = Depends(require_encounter_read),
    db: Session = Depends(get_db),
) -> ClinicalEncounter:
    return _encounter_or_404(db, encounter_id)


@router.post("/encounters/preview", response_model=EncounterPreviewResponse)
def preview_create_encounter(
    payload: EncounterCreatePreviewRequest,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterPreviewResponse:
    return encounter_create_preview(db, payload)


@router.post("/encounters", response_model=EncounterCommitResponse, status_code=status.HTTP_201_CREATED)
def create_encounter(
    payload: EncounterCreateRequest,
    request: Request,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterCommitResponse:
    require_generation_confirmation(request)
    preview = encounter_create_preview(db, payload)
    _reject_blocking(preview)
    patient = patient_by_identifier(db, payload.patient_id)
    appointment = appointment_by_id(db, payload.appointment_id)
    screening = screening_session_by_id(db, payload.screening_session_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient/donor reference changed after preview")
    encounter = ClinicalEncounter(
        encounter_number=new_encounter_number(),
        patient_pk=patient.patient_pk,
        patient=patient,
        appointment_id=appointment.appointment_id if appointment else None,
        appointment=appointment,
        screening_session_id=screening.session_id if screening else None,
        screening_session=screening,
        encounter_type=payload.encounter_type,
        status="in_progress",
        chief_complaint=payload.chief_complaint,
        reason=payload.reason,
        started_at=payload.started_at or now_utc(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    append_status_history(
        encounter,
        from_status=None,
        to_status="in_progress",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Encounter created",
    )
    db.add(encounter)
    db.flush()
    db.commit()
    db.refresh(encounter)
    operation, audit_path = append_encounter_workflow_audit(
        workflow="encounter.create",
        entity_type="encounter",
        entity_id=encounter.encounter_number,
        actor=encounter_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=encounter.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    return EncounterCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, encounter=encounter)


@router.post("/encounters/{encounter_id}/notes/preview", response_model=EncounterPreviewResponse)
def preview_save_note(
    encounter_id: int,
    payload: EncounterNotePreviewRequest,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterPreviewResponse:
    encounter = _encounter_or_404(db, encounter_id)
    return note_save_preview(encounter, payload, db)


@router.post("/encounters/{encounter_id}/notes", response_model=EncounterCommitResponse)
def save_note(
    encounter_id: int,
    payload: EncounterNoteCommitRequest,
    request: Request,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterCommitResponse:
    require_generation_confirmation(request)
    encounter = _encounter_or_404(db, encounter_id)
    preview = note_save_preview(encounter, payload, db)
    _reject_blocking(preview)
    status_before = encounter.status
    template = template_by_id(db, payload.template_id)
    note = note_by_id(db, payload.note_id)
    if note:
        note.template_id = payload.template_id
        note.template = template
        note.note_type = payload.note_type
        note.title = payload.title
        note.content = payload.content
        note.status = "ready_for_signature"
        note.updated_by = current_user.user_id
    else:
        note = ClinicalEncounterNote(
            encounter_id=encounter.encounter_id,
            template_id=payload.template_id,
            template=template,
            note_type=payload.note_type,
            title=payload.title,
            content=payload.content,
            status="ready_for_signature",
            created_by=current_user.user_id,
            updated_by=current_user.user_id,
        )
        encounter.notes.append(note)
    update_encounter_status(
        encounter,
        next_status="ready_for_signature",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Draft note saved",
    )
    db.flush()
    db.commit()
    db.refresh(encounter)
    operation, audit_path = append_encounter_workflow_audit(
        workflow="encounter.note_save",
        entity_type="encounter_note",
        entity_id=str(note.note_id),
        actor=encounter_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=encounter.status,
        reason=payload.reason,
        changes=note_changes(note),
        db=db,
    )
    return EncounterCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, encounter=encounter, note=note)


@router.post("/encounters/{encounter_id}/sign/preview", response_model=EncounterPreviewResponse)
def preview_sign_encounter(
    encounter_id: int,
    payload: EncounterSignPreviewRequest,
    current_user: User = Depends(require_encounter_signature),
    db: Session = Depends(get_db),
) -> EncounterPreviewResponse:
    encounter = _encounter_or_404(db, encounter_id)
    return sign_preview(encounter, payload, db)


@router.post("/encounters/{encounter_id}/sign", response_model=EncounterCommitResponse)
def sign_encounter(
    encounter_id: int,
    payload: EncounterSignCommitRequest,
    request: Request,
    current_user: User = Depends(require_encounter_signature),
    db: Session = Depends(get_db),
) -> EncounterCommitResponse:
    require_generation_confirmation(request)
    encounter = _encounter_or_404(db, encounter_id)
    preview = sign_preview(encounter, payload, db)
    _reject_blocking(preview)
    status_before = encounter.status
    note = note_by_id(db, payload.note_id) if payload.note_id is not None else latest_unsigned_note(encounter)
    if not note:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Encounter note changed after preview")
    signed_at = now_utc()
    note.status = "signed"
    note.signed_at = signed_at
    note.signed_by = current_user.user_id
    note.updated_by = current_user.user_id
    encounter.signed_at = signed_at
    encounter.signed_by = current_user.user_id
    update_encounter_status(
        encounter,
        next_status="signed",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Encounter note signed and locked",
    )
    db.flush()
    db.commit()
    db.refresh(encounter)
    operation, audit_path = append_encounter_workflow_audit(
        workflow="encounter.sign",
        entity_type="encounter",
        entity_id=encounter.encounter_number,
        actor=encounter_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=encounter.status,
        reason=payload.reason,
        changes={"note_id": note.note_id, "attestation": payload.attestation, "signed_at": signed_at.isoformat()},
        db=db,
    )
    return EncounterCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, encounter=encounter, note=note)


@router.post("/encounters/{encounter_id}/amend/preview", response_model=EncounterPreviewResponse)
def preview_amend_encounter(
    encounter_id: int,
    payload: EncounterAmendPreviewRequest,
    current_user: User = Depends(require_encounter_signature),
    db: Session = Depends(get_db),
) -> EncounterPreviewResponse:
    encounter = _encounter_or_404(db, encounter_id)
    return amendment_preview(encounter, payload, db)


@router.post("/encounters/{encounter_id}/amend", response_model=EncounterCommitResponse)
def amend_encounter(
    encounter_id: int,
    payload: EncounterAmendCommitRequest,
    request: Request,
    current_user: User = Depends(require_encounter_signature),
    db: Session = Depends(get_db),
) -> EncounterCommitResponse:
    require_generation_confirmation(request)
    encounter = _encounter_or_404(db, encounter_id)
    preview = amendment_preview(encounter, payload, db)
    _reject_blocking(preview)
    status_before = encounter.status
    target = note_by_id(db, payload.note_id) if payload.note_id is not None else latest_signed_note(encounter)
    if not target:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Signed note changed after preview")
    target.status = "amended"
    target.updated_by = current_user.user_id
    signed_at = now_utc()
    addendum = ClinicalEncounterNote(
        encounter_id=encounter.encounter_id,
        note_type="addendum",
        title=payload.title,
        content=payload.amendment_text,
        status="signed",
        version=target.version + 1,
        is_addendum=True,
        amended_from_note_id=target.note_id,
        amendment_reason=payload.reason,
        signed_at=signed_at,
        signed_by=current_user.user_id,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    encounter.notes.append(addendum)
    update_encounter_status(
        encounter,
        next_status="amended",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Signed note amended with addendum",
    )
    db.flush()
    db.commit()
    db.refresh(encounter)
    operation, audit_path = append_encounter_workflow_audit(
        workflow="encounter.amend",
        entity_type="encounter_note",
        entity_id=str(target.note_id),
        actor=encounter_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=encounter.status,
        reason=payload.reason,
        changes={"amended_note_id": target.note_id, "addendum_note_id": addendum.note_id, "version": addendum.version},
        db=db,
    )
    return EncounterCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, encounter=encounter, note=addendum)


@router.post("/encounters/{encounter_id}/diagnoses/preview", response_model=EncounterPreviewResponse)
def preview_add_diagnosis(
    encounter_id: int,
    payload: EncounterDiagnosisRequest,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterPreviewResponse:
    encounter = _encounter_or_404(db, encounter_id)
    return diagnosis_preview(encounter, payload)


@router.post("/encounters/{encounter_id}/diagnoses", response_model=EncounterCommitResponse)
def add_diagnosis(
    encounter_id: int,
    payload: EncounterDiagnosisRequest,
    request: Request,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterCommitResponse:
    require_generation_confirmation(request)
    encounter = _encounter_or_404(db, encounter_id)
    preview = diagnosis_preview(encounter, payload)
    _reject_blocking(preview)
    diagnosis = ClinicalEncounterDiagnosis(
        encounter_id=encounter.encounter_id,
        code=payload.code,
        display=payload.display,
        diagnosis_type=payload.diagnosis_type,
        status=payload.status,
        onset_date=payload.onset_date,
        notes=payload.notes,
        created_by=current_user.user_id,
    )
    encounter.diagnoses.append(diagnosis)
    db.flush()
    db.commit()
    db.refresh(encounter)
    operation, audit_path = append_encounter_workflow_audit(
        workflow="encounter.diagnosis_add",
        entity_type="encounter_diagnosis",
        entity_id=str(diagnosis.diagnosis_id),
        actor=encounter_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=encounter.status,
        status_after=encounter.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    return EncounterCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, encounter=encounter, diagnosis=diagnosis)


@router.post("/patients/{patient_id}/allergies/preview", response_model=EncounterPreviewResponse)
def preview_add_allergy(
    patient_id: str,
    payload: PatientAllergyRequest,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterPreviewResponse:
    patient = _patient_or_404(db, patient_id)
    return allergy_preview(patient, payload)


@router.post("/patients/{patient_id}/allergies", response_model=EncounterCommitResponse)
def add_allergy(
    patient_id: str,
    payload: PatientAllergyRequest,
    request: Request,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterCommitResponse:
    require_generation_confirmation(request)
    patient = _patient_or_404(db, patient_id)
    preview = allergy_preview(patient, payload)
    allergy = ClinicalPatientAllergy(
        patient_pk=patient.patient_pk,
        allergen=payload.allergen,
        reaction=payload.reaction,
        severity=payload.severity,
        status=payload.status,
        onset_date=payload.onset_date,
        notes=payload.notes,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    patient.allergies.append(allergy)
    db.flush()
    db.commit()
    db.refresh(patient)
    operation, audit_path = append_encounter_workflow_audit(
        workflow="patient.allergy_add",
        entity_type="patient_allergy",
        entity_id=str(allergy.allergy_id),
        actor=encounter_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=allergy.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    return EncounterCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, allergy=allergy)


@router.post("/patients/{patient_id}/medications/preview", response_model=EncounterPreviewResponse)
def preview_add_medication(
    patient_id: str,
    payload: PatientMedicationRequest,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterPreviewResponse:
    patient = _patient_or_404(db, patient_id)
    return medication_preview(patient, payload)


@router.post("/patients/{patient_id}/medications", response_model=EncounterCommitResponse)
def add_medication(
    patient_id: str,
    payload: PatientMedicationRequest,
    request: Request,
    current_user: User = Depends(require_encounter_mutation),
    db: Session = Depends(get_db),
) -> EncounterCommitResponse:
    require_generation_confirmation(request)
    patient = _patient_or_404(db, patient_id)
    preview = medication_preview(patient, payload)
    medication = ClinicalPatientMedication(
        patient_pk=patient.patient_pk,
        medication_name=payload.medication_name,
        dose=payload.dose,
        route=payload.route,
        frequency=payload.frequency,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        indication=payload.indication,
        notes=payload.notes,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    patient.medications.append(medication)
    db.flush()
    db.commit()
    db.refresh(patient)
    operation, audit_path = append_encounter_workflow_audit(
        workflow="patient.medication_add",
        entity_type="patient_medication",
        entity_id=str(medication.medication_id),
        actor=encounter_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=medication.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    return EncounterCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, medication=medication)
