from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import (
    ClinicalAdverseEvent,
    ClinicalComplianceExport,
    ClinicalQualityApproval,
    ClinicalQualityEvent,
    ClinicalQualityEventLink,
    ClinicalQualityInvestigation,
    Patient,
    User,
)
from app.schemas.clinical_quality import (
    AdverseEventCommitRequest,
    AdverseEventListResponse,
    AdverseEventPreviewRequest,
    AdverseEventResponse,
    AuditEvidenceResponse,
    ComplianceExportCommitRequest,
    ComplianceExportListResponse,
    ComplianceExportPreviewRequest,
    QualityCapaLinkCommitRequest,
    QualityCapaLinkPreviewRequest,
    QualityCloseCommitRequest,
    QualityClosePreviewRequest,
    QualityCommitResponse,
    QualityDashboardResponse,
    QualityEventCreatePreviewRequest,
    QualityEventCreateRequest,
    QualityEventListResponse,
    QualityEventResponse,
    QualityInvestigationCommitRequest,
    QualityInvestigationPreviewRequest,
    QualityPreviewResponse,
)
from app.services.clinical_quality import (
    ACTIVE_QUALITY_STATUSES,
    adverse_event_changes,
    adverse_event_context,
    adverse_event_preview,
    append_quality_status_history,
    append_quality_workflow_audit,
    audit_evidence_response,
    capa_by_id,
    capa_link_preview,
    close_preview,
    compliance_export_changes,
    compliance_export_preview,
    dashboard_response,
    new_adverse_event_number,
    new_compliance_export_number,
    new_quality_event_number,
    now_utc,
    quality_actor,
    quality_event_changes,
    quality_event_context,
    quality_event_create_preview,
    quality_event_link_rows,
    quality_event_by_id,
    resolved_patient_for_context,
    investigation_preview,
)
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical/quality", tags=["Clinical Quality"])

READ_PERMISSIONS = {"system.admin", "quality.read", "quality.manage", "quality.close", "quality.export", "qms.manage", "audit.review", "patients.read"}
MUTATION_PERMISSIONS = {"system.admin", "quality.manage", "qms.manage"}
CLOSE_PERMISSIONS = {"system.admin", "quality.close", "qms.manage"}
EXPORT_PERMISSIONS = {"system.admin", "quality.export", "audit.review", "qms.manage"}
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


def require_quality_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access quality operations")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quality read permission required")
    return current_user


def require_quality_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate quality operations")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quality mutation permission required")
    return current_user


def require_quality_close(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot close quality operations")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(CLOSE_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quality close permission required")
    return current_user


def require_quality_export(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot export quality evidence")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(EXPORT_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quality export permission required")
    return current_user


def _reject_blocking(preview: QualityPreviewResponse) -> None:
    if preview.blocking_issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "quality_validation_failed",
                "message": "Blocking quality issues prevent commit.",
                "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues],
            },
        )


@router.get("/events", response_model=QualityEventListResponse)
def list_quality_events(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    source_module: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_quality_read),
    db: Session = Depends(get_db),
) -> QualityEventListResponse:
    query = select(ClinicalQualityEvent).where(ClinicalQualityEvent.is_deleted.is_(False))
    joined_patient = False
    if status_filter:
        query = query.where(ClinicalQualityEvent.status == status_filter)
    if severity:
        query = query.where(ClinicalQualityEvent.severity == severity)
    if category:
        query = query.where(ClinicalQualityEvent.category == category)
    if owner:
        query = query.where(func.lower(ClinicalQualityEvent.owner).like(f"%{owner.strip().lower()}%"))
    if source_module:
        query = query.where(ClinicalQualityEvent.source_module == source_module)
    if patient_id:
        query = query.join(Patient)
        joined_patient = True
        query = query.where(Patient.patient_id == patient_id)
    if date_from:
        query = query.where(ClinicalQualityEvent.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(ClinicalQualityEvent.created_at <= datetime.combine(date_to, time.max))
    if q:
        like = f"%{q.strip().lower()}%"
        if not joined_patient:
            query = query.outerjoin(Patient)
        query = query.where(
            or_(
                func.lower(ClinicalQualityEvent.event_number).like(like),
                func.lower(ClinicalQualityEvent.category).like(like),
                func.lower(ClinicalQualityEvent.description).like(like),
                func.lower(ClinicalQualityEvent.owner).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalQualityEvent.updated_at.desc())).scalars().all())
    return QualityEventListResponse(events=rows[offset : offset + limit], total=len(rows))


@router.get("/events/{event_id}", response_model=QualityEventResponse)
def get_quality_event(
    event_id: int,
    current_user: User = Depends(require_quality_read),
    db: Session = Depends(get_db),
) -> ClinicalQualityEvent:
    event = quality_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality event not found")
    return event


@router.post("/events/preview", response_model=QualityPreviewResponse)
def preview_create_quality_event(
    payload: QualityEventCreatePreviewRequest,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityPreviewResponse:
    return quality_event_create_preview(db, payload)


@router.post("/events", response_model=QualityCommitResponse, status_code=status.HTTP_201_CREATED)
def create_quality_event(
    payload: QualityEventCreateRequest,
    request: Request,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityCommitResponse:
    require_generation_confirmation(request)
    preview = quality_event_create_preview(db, payload)
    _reject_blocking(preview)
    context = quality_event_context(db, payload)
    patient = resolved_patient_for_context(db, context)
    event = ClinicalQualityEvent(
        event_number=new_quality_event_number(),
        patient_pk=patient.patient_pk if patient else None,
        patient=patient,
        appointment_id=payload.appointment_id,
        appointment=context["appointment"],
        screening_session_id=payload.screening_session_id,
        screening_session=context["screening_session"],
        encounter_id=payload.encounter_id,
        encounter=context["encounter"],
        order_id=payload.order_id,
        order=context["order"],
        order_result_id=payload.order_result_id,
        order_result=context["order_result"],
        care_plan_id=payload.care_plan_id,
        care_plan=context["care_plan"],
        charge_id=payload.charge_id,
        charge=context["charge"],
        claim_id=payload.claim_id,
        claim=context["claim"],
        payment_id=payload.payment_id,
        payment=context["payment"],
        denial_id=payload.denial_id,
        denial=context["denial"],
        deviation_id=payload.deviation_id,
        deviation=context["deviation"],
        capa_id=payload.capa_id,
        capa=context["capa"],
        category=payload.category,
        severity=payload.severity,
        status=payload.status,
        owner=payload.owner,
        due_date=payload.due_date,
        source_module=payload.source_module,
        description=payload.description,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    event.links.extend(quality_event_link_rows(event=event, payload=payload, context=context, user_id=current_user.user_id))
    append_quality_status_history(
        event=event,
        from_status=None,
        to_status=payload.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Quality event created",
    )
    db.add(event)
    db.flush()
    db.commit()
    db.refresh(event)
    operation, audit_path = append_quality_workflow_audit(
        workflow="quality.event_create",
        entity_type="clinical_quality_event",
        entity_id=event.event_number,
        actor=quality_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=event.status,
        reason=payload.reason,
        changes=quality_event_changes(event),
        db=db,
    )
    return QualityCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, event=event)


@router.post("/events/{event_id}/investigation/preview", response_model=QualityPreviewResponse)
def preview_add_investigation(
    event_id: int,
    payload: QualityInvestigationPreviewRequest,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityPreviewResponse:
    return investigation_preview(db, event_id, payload)


@router.post("/events/{event_id}/investigation", response_model=QualityCommitResponse, status_code=status.HTTP_201_CREATED)
def add_investigation(
    event_id: int,
    payload: QualityInvestigationCommitRequest,
    request: Request,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityCommitResponse:
    require_generation_confirmation(request)
    preview = investigation_preview(db, event_id, payload)
    _reject_blocking(preview)
    event = quality_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quality event changed after preview")
    before = event.status
    investigation = ClinicalQualityInvestigation(
        event_id=event.event_id,
        note=payload.note,
        evidence_summary=payload.evidence_summary,
        owner=payload.owner,
        finding=payload.finding,
        root_cause_category=payload.root_cause_category,
        corrective_action_recommendation=payload.corrective_action_recommendation,
        follow_up_due_date=payload.follow_up_due_date,
        created_by=current_user.user_id,
    )
    event.investigations.append(investigation)
    event.status = payload.status_after
    event.owner = payload.owner or event.owner
    event.updated_by = current_user.user_id
    append_quality_status_history(
        event=event,
        from_status=before,
        to_status=event.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes=payload.note,
    )
    db.flush()
    db.commit()
    db.refresh(event)
    operation, audit_path = append_quality_workflow_audit(
        workflow="quality.investigation_add",
        entity_type="clinical_quality_event",
        entity_id=event.event_number,
        actor=quality_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=before,
        status_after=event.status,
        reason=payload.reason,
        changes={"investigation": payload.model_dump(mode="json"), "event": quality_event_changes(event)},
        db=db,
    )
    return QualityCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, event=event)


@router.post("/events/{event_id}/capa/preview", response_model=QualityPreviewResponse)
def preview_link_capa(
    event_id: int,
    payload: QualityCapaLinkPreviewRequest,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityPreviewResponse:
    return capa_link_preview(db, event_id, payload)


@router.post("/events/{event_id}/capa", response_model=QualityCommitResponse, status_code=status.HTTP_201_CREATED)
def link_capa(
    event_id: int,
    payload: QualityCapaLinkCommitRequest,
    request: Request,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityCommitResponse:
    require_generation_confirmation(request)
    preview = capa_link_preview(db, event_id, payload)
    _reject_blocking(preview)
    event = quality_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quality event changed after preview")
    capa = capa_by_id(db, payload.existing_capa_id)
    before = event.status
    if capa:
        event.capa_id = capa.capa_id
        event.capa = capa
        event.links.append(
            ClinicalQualityEventLink(
                entity_type="capa",
                entity_id=str(capa.capa_id),
                label=capa.capa_code,
                created_by=current_user.user_id,
            )
        )
    elif payload.create_planned_capa:
        event.links.append(
            ClinicalQualityEventLink(
                entity_type="planned_capa",
                entity_id=f"planned:{event.event_number}",
                label=payload.corrective_action_owner or "Planned CAPA",
                created_by=current_user.user_id,
            )
        )
    event.status = "capa_required"
    event.updated_by = current_user.user_id
    append_quality_status_history(
        event=event,
        from_status=before,
        to_status=event.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes=f"CAPA linked: {capa.capa_code if capa else 'planned'}",
    )
    db.flush()
    db.commit()
    db.refresh(event)
    operation, audit_path = append_quality_workflow_audit(
        workflow="quality.capa_link",
        entity_type="clinical_quality_event",
        entity_id=event.event_number,
        actor=quality_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=before,
        status_after=event.status,
        reason=payload.reason,
        changes={"capa": payload.model_dump(mode="json"), "event": quality_event_changes(event)},
        db=db,
    )
    return QualityCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, event=event)


@router.post("/events/{event_id}/close/preview", response_model=QualityPreviewResponse)
def preview_close_event(
    event_id: int,
    payload: QualityClosePreviewRequest,
    current_user: User = Depends(require_quality_close),
    db: Session = Depends(get_db),
) -> QualityPreviewResponse:
    return close_preview(db, event_id, payload)


@router.post("/events/{event_id}/close", response_model=QualityCommitResponse, status_code=status.HTTP_201_CREATED)
def close_event(
    event_id: int,
    payload: QualityCloseCommitRequest,
    request: Request,
    current_user: User = Depends(require_quality_close),
    db: Session = Depends(get_db),
) -> QualityCommitResponse:
    require_generation_confirmation(request)
    preview = close_preview(db, event_id, payload)
    _reject_blocking(preview)
    event = quality_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quality event changed after preview")
    before = event.status
    closed_at = now_utc()
    event.status = "closed"
    event.resolution_summary = payload.resolution_summary
    event.closure_reason = payload.closure_reason
    event.closed_at = closed_at
    event.closed_by = current_user.user_id
    event.updated_by = current_user.user_id
    event.approvals.append(
        ClinicalQualityApproval(
            approval_type="closure",
            status="approved",
            approved_at=closed_at,
            approved_by=current_user.user_id,
            comments=payload.closure_reason,
            created_by=current_user.user_id,
        )
    )
    append_quality_status_history(
        event=event,
        from_status=before,
        to_status=event.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes=payload.resolution_summary,
    )
    db.flush()
    db.commit()
    db.refresh(event)
    operation, audit_path = append_quality_workflow_audit(
        workflow="quality.event_close",
        entity_type="clinical_quality_event",
        entity_id=event.event_number,
        actor=quality_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=before,
        status_after=event.status,
        reason=payload.reason,
        changes=quality_event_changes(event),
        db=db,
    )
    return QualityCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, event=event)


@router.get("/adverse-events", response_model=AdverseEventListResponse)
def list_adverse_events(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_quality_read),
    db: Session = Depends(get_db),
) -> AdverseEventListResponse:
    query = select(ClinicalAdverseEvent)
    joined_patient = False
    if status_filter:
        query = query.where(ClinicalAdverseEvent.status == status_filter)
    if severity:
        query = query.where(ClinicalAdverseEvent.severity == severity)
    if patient_id:
        query = query.join(Patient)
        joined_patient = True
        query = query.where(Patient.patient_id == patient_id)
    if q:
        like = f"%{q.strip().lower()}%"
        if not joined_patient:
            query = query.outerjoin(Patient)
        query = query.where(
            or_(
                func.lower(ClinicalAdverseEvent.adverse_event_number).like(like),
                func.lower(ClinicalAdverseEvent.event_type).like(like),
                func.lower(ClinicalAdverseEvent.description).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalAdverseEvent.event_at.desc())).scalars().all())
    return AdverseEventListResponse(adverse_events=rows[offset : offset + limit], total=len(rows))


@router.post("/adverse-events/preview", response_model=QualityPreviewResponse)
def preview_create_adverse_event(
    payload: AdverseEventPreviewRequest,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityPreviewResponse:
    return adverse_event_preview(db, payload)


@router.post("/adverse-events", response_model=QualityCommitResponse, status_code=status.HTTP_201_CREATED)
def create_adverse_event(
    payload: AdverseEventCommitRequest,
    request: Request,
    current_user: User = Depends(require_quality_mutation),
    db: Session = Depends(get_db),
) -> QualityCommitResponse:
    require_generation_confirmation(request)
    preview = adverse_event_preview(db, payload)
    _reject_blocking(preview)
    context = adverse_event_context(db, payload)
    patient = context["patient"]
    if not patient:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Adverse event patient changed after preview")
    adverse_event = ClinicalAdverseEvent(
        adverse_event_number=new_adverse_event_number(),
        quality_event_id=payload.quality_event_id,
        quality_event=context["quality_event"],
        patient_pk=patient.patient_pk,
        patient=patient,
        screening_session_id=payload.screening_session_id,
        screening_session=context["screening_session"],
        encounter_id=payload.encounter_id,
        encounter=context["encounter"],
        order_id=payload.order_id,
        order=context["order"],
        order_result_id=payload.order_result_id,
        order_result=context["order_result"],
        care_plan_id=payload.care_plan_id,
        care_plan=context["care_plan"],
        event_type=payload.event_type,
        severity=payload.severity,
        event_at=payload.event_at,
        description=payload.description,
        immediate_action_taken=payload.immediate_action_taken,
        reporter=payload.reporter,
        follow_up_required=payload.follow_up_required,
        status=payload.status,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(adverse_event)
    db.flush()
    db.commit()
    db.refresh(adverse_event)
    operation, audit_path = append_quality_workflow_audit(
        workflow="quality.adverse_event_create",
        entity_type="clinical_adverse_event",
        entity_id=adverse_event.adverse_event_number,
        actor=quality_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=adverse_event.status,
        reason=payload.reason,
        changes=adverse_event_changes(adverse_event),
        db=db,
    )
    return QualityCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, adverse_event=adverse_event)


@router.get("/audit-evidence", response_model=AuditEvidenceResponse)
def get_audit_evidence(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    actor: str | None = Query(default=None),
    workflow: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    module: str | None = Query(default=None),
    current_user: User = Depends(require_quality_export),
    db: Session = Depends(get_db),
) -> AuditEvidenceResponse:
    return audit_evidence_response(
        db,
        date_from=date_from,
        date_to=date_to,
        actor=actor,
        workflow=workflow,
        entity_type=entity_type,
        entity_id=entity_id,
        module=module,
    )


@router.get("/compliance-exports", response_model=ComplianceExportListResponse)
def list_compliance_exports(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_quality_export),
    db: Session = Depends(get_db),
) -> ComplianceExportListResponse:
    rows = list(
        db.execute(select(ClinicalComplianceExport).order_by(ClinicalComplianceExport.generated_at.desc()))
        .scalars()
        .all()
    )
    return ComplianceExportListResponse(exports=rows[offset : offset + limit], total=len(rows))


@router.post("/compliance-exports/preview", response_model=QualityPreviewResponse)
def preview_compliance_export(
    payload: ComplianceExportPreviewRequest,
    current_user: User = Depends(require_quality_export),
    db: Session = Depends(get_db),
) -> QualityPreviewResponse:
    return compliance_export_preview(db, payload)


@router.post("/compliance-exports", response_model=QualityCommitResponse, status_code=status.HTTP_201_CREATED)
def create_compliance_export(
    payload: ComplianceExportCommitRequest,
    request: Request,
    current_user: User = Depends(require_quality_export),
    db: Session = Depends(get_db),
) -> QualityCommitResponse:
    require_generation_confirmation(request)
    preview = compliance_export_preview(db, payload)
    _reject_blocking(preview)
    generated_at = now_utc()
    export = ClinicalComplianceExport(
        export_number=new_compliance_export_number(),
        date_from=payload.date_from,
        date_to=payload.date_to,
        modules=payload.modules,
        criteria=payload.model_dump(mode="json"),
        evidence_summary=preview.changes.get("evidence_summary", {}),
        status="generated",
        generated_at=generated_at,
        generated_by=current_user.user_id,
        created_by=current_user.user_id,
    )
    db.add(export)
    db.flush()
    db.commit()
    db.refresh(export)
    operation, audit_path = append_quality_workflow_audit(
        workflow="quality.compliance_export",
        entity_type="clinical_compliance_export",
        entity_id=export.export_number,
        actor=quality_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=export.status,
        reason=payload.reason,
        changes=compliance_export_changes(export),
        db=db,
    )
    return QualityCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, compliance_export=export)


@router.get("/dashboard", response_model=QualityDashboardResponse)
def quality_dashboard(
    current_user: User = Depends(require_quality_read),
    db: Session = Depends(get_db),
) -> QualityDashboardResponse:
    return dashboard_response(db)
