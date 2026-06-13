from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import (
    ClinicalDeferral,
    ClinicalScreeningOutcome,
    ClinicalScreeningSession,
    ClinicalScreeningVitals,
    Patient,
    User,
)
from app.schemas.clinical_screening import (
    DeferralResponse,
    EligibilityPreviewRequest,
    EligibilityPreviewResponse,
    EligibilityRuleResult,
    ScreeningBlockingIssue,
    ScreeningCommitResponse,
    ScreeningOverrideCommitRequest,
    ScreeningOverridePreviewRequest,
    ScreeningQuestionnaireCommitRequest,
    ScreeningQuestionnairePreviewRequest,
    ScreeningResultCommitRequest,
    ScreeningSessionCreatePreviewRequest,
    ScreeningSessionCreateRequest,
    ScreeningSessionListResponse,
    ScreeningSessionPreviewResponse,
    ScreeningSessionResponse,
    ScreeningTemplateResponse,
    ScreeningVitalsCommitRequest,
    ScreeningVitalsPreviewRequest,
    ScreeningWarning,
)
from app.services.clinical_screening import (
    append_screening_workflow_audit,
    append_status_history,
    appointment_by_id,
    commit_answers,
    create_deferral_for_outcome,
    donor_for_patient,
    eligibility_preview,
    latest_vitals,
    list_screening_rules,
    list_screening_templates,
    new_screening_session_number,
    now_utc,
    patient_by_identifier,
    questionnaire_preview,
    screening_actor,
    screening_session_by_id,
    session_create_preview,
    update_session_status,
    vitals_preview,
)
from app.services.clinical_workflows import preview_hash, require_generation_confirmation

router = APIRouter(prefix="/api/clinical/screening", tags=["Clinical Screening"])

READ_PERMISSIONS = {
    "system.admin",
    "screening.read",
    "screening.manage",
    "screening.override",
    "patients.read",
    "eligibility.read",
}
MUTATION_PERMISSIONS = {
    "system.admin",
    "screening.manage",
    "screening.override",
    "donors.review",
    "eligibility.review",
}
OVERRIDE_PERMISSIONS = {"system.admin", "screening.override", "eligibility.manage"}
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


def require_screening_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access clinical screening")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Screening read permission required")
    return current_user


def require_screening_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate clinical screening")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Screening mutation permission required")
    return current_user


def require_screening_override(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot override screening results")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(OVERRIDE_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Screening override permission required")
    return current_user


def _session_or_404(db: Session, session_id: int) -> ClinicalScreeningSession:
    session = screening_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening session not found")
    return session


def _reject_blocking(preview: ScreeningSessionPreviewResponse | EligibilityPreviewResponse) -> None:
    if preview.blocking_issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "screening_validation_failed",
                "message": "Blocking screening issues prevent commit.",
                "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues],
            },
        )


def _outcome_status(outcome: str) -> str:
    return {
        "eligible": "eligible",
        "eligible_with_conditions": "eligible_with_conditions",
        "temporarily_deferred": "temporarily_deferred",
        "permanently_deferred": "permanently_deferred",
        "requires_supervisor_review": "requires_supervisor_review",
    }[outcome]


@router.get("/sessions", response_model=ScreeningSessionListResponse)
def list_screening_sessions(
    q: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    appointment_context: bool | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_screening_read),
    db: Session = Depends(get_db),
) -> ScreeningSessionListResponse:
    query = select(ClinicalScreeningSession).where(ClinicalScreeningSession.is_deleted.is_(False))
    if date_filter:
        start_of_day = datetime.combine(date_filter, time.min)
        end_of_day = datetime.combine(date_filter, time.max)
        query = query.where(ClinicalScreeningSession.created_at >= start_of_day, ClinicalScreeningSession.created_at <= end_of_day)
    if status_filter:
        query = query.where(ClinicalScreeningSession.status == status_filter)
    if appointment_context is True:
        query = query.where(ClinicalScreeningSession.appointment_id.is_not(None))
    if appointment_context is False:
        query = query.where(ClinicalScreeningSession.appointment_id.is_(None))
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.join(Patient).where(
            or_(
                func.lower(ClinicalScreeningSession.session_number).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
                func.lower(Patient.donor_reference).like(like),
            )
        )
    rows = list(
        db.execute(query.order_by(ClinicalScreeningSession.updated_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return ScreeningSessionListResponse(sessions=rows, total=len(rows))


@router.get("/sessions/{session_id}", response_model=ScreeningSessionResponse)
def get_screening_session(
    session_id: int,
    current_user: User = Depends(require_screening_read),
    db: Session = Depends(get_db),
) -> ClinicalScreeningSession:
    return _session_or_404(db, session_id)


@router.post("/sessions/preview", response_model=ScreeningSessionPreviewResponse)
def preview_create_screening_session(
    payload: ScreeningSessionCreatePreviewRequest,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> ScreeningSessionPreviewResponse:
    return session_create_preview(db, payload)


@router.post("/sessions", response_model=ScreeningCommitResponse, status_code=status.HTTP_201_CREATED)
def create_screening_session(
    payload: ScreeningSessionCreateRequest,
    request: Request,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> ScreeningCommitResponse:
    require_generation_confirmation(request)
    preview = session_create_preview(db, payload)
    _reject_blocking(preview)
    patient = patient_by_identifier(db, payload.patient_id)
    appointment = appointment_by_id(db, payload.appointment_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient/donor reference changed after preview")
    donor = donor_for_patient(db, patient)
    session = ClinicalScreeningSession(
        session_number=new_screening_session_number(),
        patient_pk=patient.patient_pk,
        patient=patient,
        donor_pk=donor.donor_pk if donor else None,
        donor=donor,
        appointment_id=appointment.appointment_id if appointment else None,
        appointment=appointment,
        template_id=payload.template_id,
        status="in_progress",
        supervisor_review_required=False,
        started_at=now_utc(),
        reason=payload.reason,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    append_status_history(
        session,
        from_status=None,
        to_status="in_progress",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Screening session started",
    )
    db.add(session)
    db.flush()
    db.commit()
    db.refresh(session)
    operation, audit_path = append_screening_workflow_audit(
        workflow="screening.session_create",
        session=session,
        actor=screening_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=session.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    return ScreeningCommitResponse(session=session, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/sessions/{session_id}/questionnaire/preview", response_model=ScreeningSessionPreviewResponse)
def preview_questionnaire(
    session_id: int,
    payload: ScreeningQuestionnairePreviewRequest,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> ScreeningSessionPreviewResponse:
    session = _session_or_404(db, session_id)
    return questionnaire_preview(session, payload)


@router.post("/sessions/{session_id}/questionnaire", response_model=ScreeningCommitResponse)
def commit_questionnaire(
    session_id: int,
    payload: ScreeningQuestionnaireCommitRequest,
    request: Request,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> ScreeningCommitResponse:
    require_generation_confirmation(request)
    session = _session_or_404(db, session_id)
    preview = questionnaire_preview(session, payload)
    _reject_blocking(preview)
    status_before = session.status
    commit_answers(session, payload.answers, user_id=current_user.user_id, notes=payload.notes)
    next_status = "pending_eligibility" if latest_vitals(session) else "in_progress"
    update_session_status(
        session,
        next_status=next_status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Questionnaire committed",
    )
    db.flush()
    db.commit()
    db.refresh(session)
    operation, audit_path = append_screening_workflow_audit(
        workflow="screening.questionnaire_commit",
        session=session,
        actor=screening_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=session.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    return ScreeningCommitResponse(session=session, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/sessions/{session_id}/vitals/preview", response_model=ScreeningSessionPreviewResponse)
def preview_vitals(
    session_id: int,
    payload: ScreeningVitalsPreviewRequest,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> ScreeningSessionPreviewResponse:
    session = _session_or_404(db, session_id)
    return vitals_preview(session, payload)


@router.post("/sessions/{session_id}/vitals", response_model=ScreeningCommitResponse)
def commit_vitals(
    session_id: int,
    payload: ScreeningVitalsCommitRequest,
    request: Request,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> ScreeningCommitResponse:
    require_generation_confirmation(request)
    session = _session_or_404(db, session_id)
    preview = vitals_preview(session, payload)
    _reject_blocking(preview)
    status_before = session.status
    vitals = ClinicalScreeningVitals(
        session_id=session.session_id,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        temperature_c=payload.temperature_c,
        blood_pressure_systolic=payload.blood_pressure_systolic,
        blood_pressure_diastolic=payload.blood_pressure_diastolic,
        pulse=payload.pulse,
        respiration_rate=payload.respiration_rate,
        oxygen_saturation=payload.oxygen_saturation,
        captured_at=payload.captured_at or now_utc(),
        captured_by=current_user.user_id,
        notes=payload.notes,
    )
    session.vitals.append(vitals)
    next_status = "pending_eligibility" if session.answers else "in_progress"
    update_session_status(
        session,
        next_status=next_status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Vitals committed",
    )
    db.flush()
    db.commit()
    db.refresh(session)
    operation, audit_path = append_screening_workflow_audit(
        workflow="screening.vitals_commit",
        session=session,
        actor=screening_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=session.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    return ScreeningCommitResponse(session=session, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/sessions/{session_id}/eligibility/preview", response_model=EligibilityPreviewResponse)
def preview_eligibility(
    session_id: int,
    payload: EligibilityPreviewRequest,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> EligibilityPreviewResponse:
    session = _session_or_404(db, session_id)
    return eligibility_preview(db, session, payload)


@router.post("/sessions/{session_id}/result", response_model=ScreeningCommitResponse)
def commit_screening_result(
    session_id: int,
    payload: ScreeningResultCommitRequest,
    request: Request,
    current_user: User = Depends(require_screening_mutation),
    db: Session = Depends(get_db),
) -> ScreeningCommitResponse:
    require_generation_confirmation(request)
    session = _session_or_404(db, session_id)
    preview = eligibility_preview(db, session, EligibilityPreviewRequest(reason=payload.reason))
    _reject_blocking(preview)
    if payload.outcome in {"temporarily_deferred", "permanently_deferred"}:
        expected_type = "temporary" if payload.outcome == "temporarily_deferred" else "permanent"
        if payload.deferral_type and payload.deferral_type != expected_type:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Deferral type does not match outcome")
    status_before = session.status
    next_status = _outcome_status(payload.outcome)
    session.current_outcome = payload.outcome
    session.supervisor_review_required = preview.supervisor_review_required or payload.outcome == "requires_supervisor_review"
    if payload.outcome != "requires_supervisor_review":
        session.completed_at = now_utc()
    session.outcomes.append(
        ClinicalScreeningOutcome(
            session_id=session.session_id,
            proposed_outcome=preview.proposed_outcome,
            committed_outcome=payload.outcome,
            deferral_type=payload.deferral_type,
            supervisor_review_required=session.supervisor_review_required,
            blocking_issues=[issue.model_dump(mode="json") for issue in preview.blocking_issues],
            warnings=[warning.model_dump(mode="json") for warning in preview.warnings],
            rule_results=[rule.model_dump(mode="json") for rule in preview.rules_evaluated],
            reason=payload.reason,
            created_by=current_user.user_id,
        )
    )
    deferral = create_deferral_for_outcome(
        session,
        outcome=payload.outcome,
        reason=payload.reason,
        user_id=current_user.user_id,
        deferral_type=payload.deferral_type,
        ends_at=payload.deferral_ends_at,
    )
    if deferral:
        deferral.patient = session.patient
        deferral.donor = session.donor
    update_session_status(
        session,
        next_status=next_status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Screening result committed",
    )
    db.flush()
    db.commit()
    db.refresh(session)
    operation, audit_path = append_screening_workflow_audit(
        workflow="screening.result_commit",
        session=session,
        actor=screening_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=session.status,
        reason=payload.reason,
        changes={
            "outcome": payload.outcome,
            "proposed_outcome": preview.proposed_outcome,
            "rules_evaluated": [rule.model_dump(mode="json") for rule in preview.rules_evaluated],
        },
        db=db,
    )
    if deferral:
        append_screening_workflow_audit(
            workflow="screening.deferral_create",
            session=session,
            actor=screening_actor(current_user),
            preview_value=payload.preview_hash or preview.preview_hash,
            status_before=status_before,
            status_after=session.status,
            reason=payload.reason,
            changes={
                "deferral_number": deferral.deferral_number,
                "deferral_type": deferral.deferral_type,
                "patient_id": deferral.patient_id,
            },
            db=db,
        )
    return ScreeningCommitResponse(session=session, operation_id=operation.operation_id, audit_path=audit_path, deferral=deferral)


@router.post("/sessions/{session_id}/override/preview", response_model=EligibilityPreviewResponse)
def preview_override(
    session_id: int,
    payload: ScreeningOverridePreviewRequest,
    current_user: User = Depends(require_screening_override),
    db: Session = Depends(get_db),
) -> EligibilityPreviewResponse:
    session = _session_or_404(db, session_id)
    issues: list[ScreeningBlockingIssue] = []
    warnings: list[ScreeningWarning] = []
    if payload.original_outcome == payload.override_outcome:
        warnings.append(
            ScreeningWarning(
                warning_type="same_override_outcome",
                field="override_outcome",
                message="Override outcome matches the original outcome.",
            )
        )
    if session.current_outcome and session.current_outcome != payload.original_outcome:
        warnings.append(
            ScreeningWarning(
                warning_type="current_outcome_mismatch",
                field="original_outcome",
                message=f"Session current outcome is {session.current_outcome}.",
            )
        )
    changes = payload.model_dump(mode="json")
    return EligibilityPreviewResponse(
        workflow="screening.override_preview",
        entity_id=session.session_number,
        preview_hash=preview_hash({"workflow": "screening.override_preview", "entity_id": session.session_number, "changes": changes}),
        validation_status="failed" if issues else "warning" if warnings else "passed",
        proposed_outcome=payload.override_outcome,
        blocking_issues=issues,
        warnings=warnings,
        rules_evaluated=[
            EligibilityRuleResult(
                rule_name="Supervisor override",
                rule_category="Supervisor Review",
                outcome=payload.override_outcome,
                severity="High",
                requires_review=True,
                explanation=payload.reason,
            )
        ],
        supervisor_review_required=True,
        summary="Supervisor override preview is ready for commit.",
        changes=changes,
    )


@router.post("/sessions/{session_id}/override", response_model=ScreeningCommitResponse)
def commit_override(
    session_id: int,
    payload: ScreeningOverrideCommitRequest,
    request: Request,
    current_user: User = Depends(require_screening_override),
    db: Session = Depends(get_db),
) -> ScreeningCommitResponse:
    require_generation_confirmation(request)
    session = _session_or_404(db, session_id)
    preview = preview_override(session_id, payload, current_user, db)
    _reject_blocking(preview)
    status_before = session.status
    next_status = _outcome_status(payload.override_outcome)
    session.current_outcome = payload.override_outcome
    session.supervisor_review_required = False
    if payload.override_outcome != "requires_supervisor_review":
        session.completed_at = now_utc()
    session.outcomes.append(
        ClinicalScreeningOutcome(
            session_id=session.session_id,
            proposed_outcome=payload.original_outcome,
            committed_outcome=payload.override_outcome,
            original_outcome=payload.original_outcome,
            override_outcome=payload.override_outcome,
            supervisor_review_required=True,
            blocking_issues=[],
            warnings=[warning.model_dump(mode="json") for warning in preview.warnings],
            rule_results=[rule.model_dump(mode="json") for rule in preview.rules_evaluated],
            reason=payload.reason,
            created_by=current_user.user_id,
        )
    )
    deferral = create_deferral_for_outcome(
        session,
        outcome=payload.override_outcome,
        reason=payload.reason,
        user_id=current_user.user_id,
    )
    if deferral:
        deferral.patient = session.patient
        deferral.donor = session.donor
    update_session_status(
        session,
        next_status=next_status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Supervisor override committed",
    )
    db.flush()
    db.commit()
    db.refresh(session)
    operation, audit_path = append_screening_workflow_audit(
        workflow="screening.override_commit",
        session=session,
        actor=screening_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=session.status,
        reason=payload.reason,
        changes=preview.changes,
        db=db,
    )
    if deferral:
        append_screening_workflow_audit(
            workflow="screening.deferral_create",
            session=session,
            actor=screening_actor(current_user),
            preview_value=payload.preview_hash or preview.preview_hash,
            status_before=status_before,
            status_after=session.status,
            reason=payload.reason,
            changes={
                "deferral_number": deferral.deferral_number,
                "deferral_type": deferral.deferral_type,
                "patient_id": deferral.patient_id,
            },
            db=db,
        )
    return ScreeningCommitResponse(session=session, operation_id=operation.operation_id, audit_path=audit_path, deferral=deferral)


@router.get("/deferrals", response_model=list[DeferralResponse])
def list_deferrals(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(require_screening_read),
    db: Session = Depends(get_db),
) -> list[ClinicalDeferral]:
    query = select(ClinicalDeferral).order_by(ClinicalDeferral.created_at.desc())
    if status_filter:
        query = query.where(ClinicalDeferral.status == status_filter)
    return list(db.execute(query).scalars().all())


@router.get("/templates", response_model=list[ScreeningTemplateResponse])
def screening_templates(current_user: User = Depends(require_screening_read)) -> list[ScreeningTemplateResponse]:
    return list_screening_templates()


@router.get("/rules", response_model=list[EligibilityRuleResult])
def screening_rules(current_user: User = Depends(require_screening_read)) -> list[EligibilityRuleResult]:
    return list_screening_rules()
