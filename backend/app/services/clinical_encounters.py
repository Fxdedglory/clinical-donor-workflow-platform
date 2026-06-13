from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    ClinicalEncounter,
    ClinicalEncounterDiagnosis,
    ClinicalEncounterNote,
    ClinicalEncounterStatusHistory,
    ClinicalNoteTemplate,
    ClinicalPatientAllergy,
    ClinicalPatientMedication,
    ClinicalScreeningSession,
    Patient,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_encounters import (
    EncounterAmendPreviewRequest,
    EncounterCreatePreviewRequest,
    EncounterDiagnosisRequest,
    EncounterNotePreviewRequest,
    EncounterPreviewResponse,
    EncounterSignPreviewRequest,
    EncounterValidationIssue,
    NoteTemplateResponse,
    PatientAllergyRequest,
    PatientMedicationRequest,
)
from app.services.clinical_patients import actor_label
from app.services.clinical_workflows import append_workflow_operation, preview_hash

ENCOUNTER_FINAL_STATUSES = {"signed", "amended", "cancelled"}
NOTE_LOCKED_STATUSES = {"signed", "amended"}
CHECKED_IN_APPOINTMENT_STATUSES = {"checked_in"}

DEFAULT_NOTE_TEMPLATES = [
    NoteTemplateResponse(
        template_id=1,
        template_key="donor_screening_encounter_v1",
        name="Donor screening encounter",
        note_type="clinical_note",
        body="Subjective:\n\nObjective:\n\nAssessment:\n\nPlan:\n",
        status="active",
        version=1,
    ),
    NoteTemplateResponse(
        template_id=2,
        template_key="clinical_review_addendum_v1",
        name="Clinical review addendum",
        note_type="addendum",
        body="Addendum:\n\nReason for amendment:\n",
        status="active",
        version=1,
    ),
]


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_encounter_number() -> str:
    return f"ENC-{uuid4().hex[:10].upper()}"


def _one_or_none(db: Session, statement) -> Any | None:
    return db.execute(statement).scalar_one_or_none()


def patient_by_identifier(db: Session, patient_id: str) -> Patient | None:
    return _one_or_none(db, select(Patient).where(Patient.patient_id == patient_id, Patient.is_deleted.is_(False)))


def appointment_by_id(db: Session, appointment_id: int | None) -> Appointment | None:
    if appointment_id is None:
        return None
    return _one_or_none(db, select(Appointment).where(Appointment.appointment_id == appointment_id, Appointment.is_deleted.is_(False)))


def screening_session_by_id(db: Session, session_id: int | None) -> ClinicalScreeningSession | None:
    if session_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalScreeningSession).where(
            ClinicalScreeningSession.session_id == session_id,
            ClinicalScreeningSession.is_deleted.is_(False),
        ),
    )


def encounter_by_id(db: Session, encounter_id: int) -> ClinicalEncounter | None:
    return _one_or_none(
        db,
        select(ClinicalEncounter).where(
            ClinicalEncounter.encounter_id == encounter_id,
            ClinicalEncounter.is_deleted.is_(False),
        ),
    )


def note_by_id(db: Session, note_id: int | None) -> ClinicalEncounterNote | None:
    if note_id is None:
        return None
    return _one_or_none(db, select(ClinicalEncounterNote).where(ClinicalEncounterNote.note_id == note_id))


def template_by_id(db: Session, template_id: int | None) -> ClinicalNoteTemplate | None:
    if template_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalNoteTemplate).where(
            ClinicalNoteTemplate.template_id == template_id,
            ClinicalNoteTemplate.is_deleted.is_(False),
        ),
    )


def list_note_templates(db: Session) -> list[ClinicalNoteTemplate | NoteTemplateResponse]:
    templates = list(
        db.execute(
            select(ClinicalNoteTemplate).where(
                ClinicalNoteTemplate.status == "active",
                ClinicalNoteTemplate.is_deleted.is_(False),
            )
        )
        .scalars()
        .all()
    )
    return templates or DEFAULT_NOTE_TEMPLATES


def encounter_actor(user: User) -> str:
    return actor_label(user)


def _issue(issue_type: str, field: str, message: str) -> EncounterValidationIssue:
    return EncounterValidationIssue(issue_type=issue_type, field=field, message=message, severity="error")


def _warning(issue_type: str, field: str, message: str) -> EncounterValidationIssue:
    return EncounterValidationIssue(issue_type=issue_type, field=field, message=message, severity="warning")


def _preview(
    *,
    workflow: str,
    entity_type: str,
    entity_id: str,
    changes: dict[str, Any],
    blocking_issues: list[EncounterValidationIssue] | None = None,
    warnings: list[EncounterValidationIssue] | None = None,
    summary: str,
) -> EncounterPreviewResponse:
    issues = blocking_issues or []
    warning_rows = warnings or []
    return EncounterPreviewResponse(
        workflow=workflow,
        entity_type=entity_type,
        entity_id=entity_id,
        preview_hash=preview_hash({"workflow": workflow, "entity_type": entity_type, "entity_id": entity_id, "changes": changes}),
        validation_status="failed" if issues else "warning" if warning_rows else "passed",
        blocking_issues=issues,
        warnings=warning_rows,
        summary=summary,
        changes=changes,
    )


def encounter_create_preview(db: Session, payload: EncounterCreatePreviewRequest) -> EncounterPreviewResponse:
    patient = patient_by_identifier(db, payload.patient_id)
    appointment = appointment_by_id(db, payload.appointment_id)
    screening = screening_session_by_id(db, payload.screening_session_id)
    issues: list[EncounterValidationIssue] = []
    warnings: list[EncounterValidationIssue] = []

    if patient is None:
        issues.append(_issue("unknown_patient", "patient_id", "Patient/donor profile was not found."))
    if payload.appointment_id is not None and appointment is None:
        issues.append(_issue("unknown_appointment", "appointment_id", "Scheduling appointment was not found."))
    if payload.screening_session_id is not None and screening is None:
        issues.append(_issue("unknown_screening_session", "screening_session_id", "Screening session was not found."))
    if patient and appointment and appointment.patient_pk != patient.patient_pk:
        issues.append(_issue("appointment_patient_mismatch", "appointment_id", "Appointment is linked to a different patient/donor."))
    if patient and screening and screening.patient_pk != patient.patient_pk:
        issues.append(_issue("screening_patient_mismatch", "screening_session_id", "Screening session is linked to a different patient/donor."))
    if appointment and appointment.status not in CHECKED_IN_APPOINTMENT_STATUSES:
        issues.append(_issue("appointment_not_checked_in", "appointment_id", "Encounter creation requires a checked-in appointment."))
    if not appointment:
        warnings.append(_warning("no_checked_in_appointment", "appointment_id", "Encounter will be created without checked-in appointment context."))
    if screening and screening.current_outcome is None:
        warnings.append(_warning("screening_outcome_pending", "screening_session_id", "Screening outcome is not committed yet."))

    changes = payload.model_dump(mode="json")
    return _preview(
        workflow="encounter.create",
        entity_type="encounter",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Encounter can be created." if not issues else "Encounter preview found blocking issues.",
    )


def note_save_preview(encounter: ClinicalEncounter, payload: EncounterNotePreviewRequest, db: Session) -> EncounterPreviewResponse:
    issues: list[EncounterValidationIssue] = []
    warnings: list[EncounterValidationIssue] = []
    note = note_by_id(db, payload.note_id)
    template = template_by_id(db, payload.template_id)
    if payload.note_id is not None and (note is None or note.encounter_id != encounter.encounter_id):
        issues.append(_issue("unknown_note", "note_id", "Encounter note was not found for this encounter."))
    if note and note.status in NOTE_LOCKED_STATUSES:
        issues.append(_issue("signed_note_locked", "note_id", "Signed notes are locked from direct editing; create an amendment instead."))
    if encounter.status in ENCOUNTER_FINAL_STATUSES:
        issues.append(_issue("encounter_locked", "encounter_id", "Signed or cancelled encounters cannot receive direct draft note edits."))
    if payload.template_id is not None and template is None:
        issues.append(_issue("unknown_template", "template_id", "Clinical note template was not found."))
    if len(payload.content.strip()) < 12:
        warnings.append(_warning("short_note_content", "content", "Note content is unusually short for an encounter note."))
    changes = payload.model_dump(mode="json")
    return _preview(
        workflow="encounter.note_save",
        entity_type="encounter_note",
        entity_id=str(note.note_id if note else "draft"),
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Draft encounter note can be saved." if not issues else "Note preview found blocking issues.",
    )


def latest_unsigned_note(encounter: ClinicalEncounter) -> ClinicalEncounterNote | None:
    candidates = [note for note in encounter.notes if note.status not in NOTE_LOCKED_STATUSES]
    if not candidates:
        return None
    return sorted(candidates, key=lambda note: note.updated_at or note.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)[0]


def latest_signed_note(encounter: ClinicalEncounter) -> ClinicalEncounterNote | None:
    candidates = [note for note in encounter.notes if note.status in NOTE_LOCKED_STATUSES]
    if not candidates:
        return None
    return sorted(candidates, key=lambda note: note.signed_at or note.updated_at or note.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)[0]


def sign_preview(encounter: ClinicalEncounter, payload: EncounterSignPreviewRequest, db: Session) -> EncounterPreviewResponse:
    note = note_by_id(db, payload.note_id) if payload.note_id is not None else latest_unsigned_note(encounter)
    issues: list[EncounterValidationIssue] = []
    if note is None:
        issues.append(_issue("no_unsigned_note", "note_id", "A draft or ready note is required before signing."))
    elif note.encounter_id != encounter.encounter_id:
        issues.append(_issue("note_encounter_mismatch", "note_id", "Note belongs to a different encounter."))
    elif note.status in NOTE_LOCKED_STATUSES:
        issues.append(_issue("note_already_signed", "note_id", "Selected note is already signed or amended."))
    elif not note.content.strip():
        issues.append(_issue("empty_note", "note_id", "Encounter note content is required before signing."))
    changes = {
        **payload.model_dump(mode="json"),
        "resolved_note_id": note.note_id if note else None,
    }
    return _preview(
        workflow="encounter.sign",
        entity_type="encounter",
        entity_id=encounter.encounter_number,
        changes=changes,
        blocking_issues=issues,
        summary="Encounter note is ready for signature." if not issues else "Signature preview found blocking issues.",
    )


def amendment_preview(encounter: ClinicalEncounter, payload: EncounterAmendPreviewRequest, db: Session) -> EncounterPreviewResponse:
    note = note_by_id(db, payload.note_id) if payload.note_id is not None else latest_signed_note(encounter)
    issues: list[EncounterValidationIssue] = []
    if note is None:
        issues.append(_issue("no_signed_note", "note_id", "A signed encounter note is required before amendment."))
    elif note.encounter_id != encounter.encounter_id:
        issues.append(_issue("note_encounter_mismatch", "note_id", "Note belongs to a different encounter."))
    elif note.status not in NOTE_LOCKED_STATUSES:
        issues.append(_issue("note_not_signed", "note_id", "Only signed notes can be amended."))
    changes = {
        **payload.model_dump(mode="json"),
        "resolved_note_id": note.note_id if note else None,
    }
    return _preview(
        workflow="encounter.amend",
        entity_type="encounter_note",
        entity_id=str(note.note_id if note else "draft"),
        changes=changes,
        blocking_issues=issues,
        summary="Signed note can be amended with an addendum." if not issues else "Amendment preview found blocking issues.",
    )


def diagnosis_preview(encounter: ClinicalEncounter, payload: EncounterDiagnosisRequest) -> EncounterPreviewResponse:
    return _preview(
        workflow="encounter.diagnosis_add",
        entity_type="encounter_diagnosis",
        entity_id=encounter.encounter_number,
        changes=payload.model_dump(mode="json", exclude={"preview_hash"}),
        summary="Diagnosis/problem is ready to add.",
    )


def allergy_preview(patient: Patient, payload: PatientAllergyRequest) -> EncounterPreviewResponse:
    return _preview(
        workflow="patient.allergy_add",
        entity_type="patient_allergy",
        entity_id=patient.patient_id,
        changes=payload.model_dump(mode="json", exclude={"preview_hash"}),
        summary="Allergy is ready to add.",
    )


def medication_preview(patient: Patient, payload: PatientMedicationRequest) -> EncounterPreviewResponse:
    warnings: list[EncounterValidationIssue] = []
    if payload.end_date and payload.start_date and payload.end_date < payload.start_date:
        warnings.append(_warning("medication_end_before_start", "end_date", "Medication end date is before the start date."))
    return _preview(
        workflow="patient.medication_add",
        entity_type="patient_medication",
        entity_id=patient.patient_id,
        changes=payload.model_dump(mode="json", exclude={"preview_hash"}),
        warnings=warnings,
        summary="Medication is ready to add.",
    )


def append_status_history(
    encounter: ClinicalEncounter,
    *,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    encounter.status_history.append(
        ClinicalEncounterStatusHistory(
            encounter_id=encounter.encounter_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            reason=reason,
            notes=notes,
        )
    )


def update_encounter_status(
    encounter: ClinicalEncounter,
    *,
    next_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> tuple[str, str]:
    status_before = encounter.status
    if status_before != next_status:
        encounter.status = next_status
        append_status_history(
            encounter,
            from_status=status_before,
            to_status=next_status,
            user_id=user_id,
            reason=reason,
            notes=notes,
        )
    encounter.updated_by = user_id
    encounter.version += 1
    return status_before, encounter.status


def append_encounter_workflow_audit(
    *,
    workflow: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    preview_value: str,
    status_before: str | None,
    status_after: str | None,
    reason: str,
    changes: dict[str, Any],
    db: Session | None = None,
) -> tuple[WorkflowOperation, str]:
    operation = WorkflowOperation(
        workflow=workflow,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        preview_hash=preview_value,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        changes=changes,
    )
    operation, audit_path = append_workflow_operation(operation, db=db)
    return operation, str(audit_path)


def note_changes(note: ClinicalEncounterNote) -> dict[str, Any]:
    return {
        "note_id": note.note_id,
        "encounter_id": note.encounter_id,
        "status": note.status,
        "version": note.version,
        "is_addendum": note.is_addendum,
        "amended_from_note_id": note.amended_from_note_id,
    }


def ordered_encounter_notes(encounter: ClinicalEncounter) -> list[ClinicalEncounterNote]:
    return sorted(encounter.notes, key=lambda note: (note.created_at or datetime.min.replace(tzinfo=UTC), note.note_id or 0))


def ordered_status_history(encounter: ClinicalEncounter) -> list[ClinicalEncounterStatusHistory]:
    return sorted(encounter.status_history, key=lambda row: row.changed_at or datetime.min.replace(tzinfo=UTC), reverse=True)
