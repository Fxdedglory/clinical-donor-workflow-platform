from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import (
    ClinicalCarePlan,
    ClinicalCarePlanGoal,
    ClinicalCarePlanIntervention,
    ClinicalCarePlanProgressNote,
    ClinicalCarePlanTask,
    ClinicalCarePlanTeamMember,
    Patient,
    User,
)
from app.schemas.clinical_care_plans import (
    CarePlanCloseCommitRequest,
    CarePlanClosePreviewRequest,
    CarePlanCommitResponse,
    CarePlanCreatePreviewRequest,
    CarePlanCreateRequest,
    CarePlanGoalCommitRequest,
    CarePlanGoalPreviewRequest,
    CarePlanInterventionCommitRequest,
    CarePlanInterventionPreviewRequest,
    CarePlanListResponse,
    CarePlanPreviewResponse,
    CarePlanProgressCommitRequest,
    CarePlanProgressPreviewRequest,
    CarePlanResponse,
    CarePlanTaskCommitRequest,
    CarePlanTaskPreviewRequest,
)
from app.services.clinical_care_plans import (
    append_care_plan_workflow_audit,
    append_status_history,
    care_plan_actor,
    care_plan_by_id,
    care_plan_changes,
    care_plan_create_preview,
    close_preview,
    encounter_by_id,
    goal_changes,
    goal_preview,
    intervention_changes,
    intervention_preview,
    new_care_plan_number,
    now_utc,
    order_by_id,
    order_result_by_id,
    patient_by_identifier,
    progress_changes,
    progress_preview,
    screening_session_by_id,
    task_changes,
    task_preview,
    update_care_plan_status,
)
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical/care-plans", tags=["Clinical Care Plans"])

READ_PERMISSIONS = {"system.admin", "care_plans.read", "care_plans.manage", "care_plans.close", "patients.read"}
MUTATION_PERMISSIONS = {"system.admin", "care_plans.manage"}
CLOSE_PERMISSIONS = {"system.admin", "care_plans.close", "care_plans.manage"}
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


def require_care_plan_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access care plans")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Care plan read permission required")
    return current_user


def require_care_plan_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate care plans")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Care plan mutation permission required")
    return current_user


def require_care_plan_closure(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot close care plans")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(CLOSE_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Care plan closure permission required")
    return current_user


def _care_plan_or_404(db: Session, care_plan_id: int) -> ClinicalCarePlan:
    care_plan = care_plan_by_id(db, care_plan_id)
    if not care_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care plan not found")
    return care_plan


def _reject_blocking(preview: CarePlanPreviewResponse) -> None:
    if preview.blocking_issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "care_plan_validation_failed",
                "message": "Blocking care plan issues prevent commit.",
                "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues],
            },
        )


@router.get("", response_model=CarePlanListResponse)
def list_care_plans(
    q: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
    encounter_id: int | None = Query(default=None),
    order_id: int | None = Query(default=None),
    order_context: bool | None = Query(default=None),
    result_flag: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_care_plan_read),
    db: Session = Depends(get_db),
) -> CarePlanListResponse:
    query = select(ClinicalCarePlan).where(ClinicalCarePlan.is_deleted.is_(False))
    joined_patient = False
    if date_filter:
        query = query.where(ClinicalCarePlan.start_date == date_filter)
    if status_filter:
        query = query.where(ClinicalCarePlan.status == status_filter)
    if priority:
        query = query.where(ClinicalCarePlan.priority == priority)
    if patient_id:
        query = query.join(Patient)
        joined_patient = True
        query = query.where(Patient.patient_id == patient_id)
    if encounter_id is not None:
        query = query.where(ClinicalCarePlan.encounter_id == encounter_id)
    if order_id is not None:
        query = query.where(ClinicalCarePlan.order_id == order_id)
    if order_context is True:
        query = query.where(ClinicalCarePlan.order_id.is_not(None))
    if order_context is False:
        query = query.where(ClinicalCarePlan.order_id.is_(None))
    if q:
        like = f"%{q.strip().lower()}%"
        if not joined_patient:
            query = query.join(Patient)
        query = query.where(
            or_(
                func.lower(ClinicalCarePlan.care_plan_number).like(like),
                func.lower(ClinicalCarePlan.title).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
                func.lower(Patient.donor_reference).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalCarePlan.updated_at.desc())).scalars().all())
    if result_flag:
        rows = [row for row in rows if row.result_flag == result_flag]
    return CarePlanListResponse(care_plans=rows[offset : offset + limit], total=len(rows))


@router.post("/preview", response_model=CarePlanPreviewResponse)
def preview_create_care_plan(
    payload: CarePlanCreatePreviewRequest,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanPreviewResponse:
    return care_plan_create_preview(db, payload)


@router.post("", response_model=CarePlanCommitResponse, status_code=status.HTTP_201_CREATED)
def create_care_plan(
    payload: CarePlanCreateRequest,
    request: Request,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanCommitResponse:
    require_generation_confirmation(request)
    preview = care_plan_create_preview(db, payload)
    _reject_blocking(preview)
    patient = patient_by_identifier(db, payload.patient_id)
    encounter = encounter_by_id(db, payload.encounter_id)
    screening = screening_session_by_id(db, payload.screening_session_id)
    order = order_by_id(db, payload.order_id)
    result = order_result_by_id(db, payload.order_result_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Care plan patient context changed after preview")
    care_plan = ClinicalCarePlan(
        care_plan_number=new_care_plan_number(),
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_id=encounter.encounter_id if encounter else None,
        encounter=encounter,
        screening_session_id=screening.session_id if screening else None,
        screening_session=screening,
        order_id=order.order_id if order else None,
        order=order,
        order_result_id=result.result_id if result else None,
        order_result=result,
        title=payload.title,
        plan_type=payload.plan_type,
        priority=payload.priority,
        status="active",
        reason=payload.reason,
        start_date=payload.start_date,
        target_date=payload.target_date,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    append_status_history(
        care_plan,
        from_status=None,
        to_status="active",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Care plan created",
    )
    if payload.team_member_name:
        care_plan.team_members.append(
            ClinicalCarePlanTeamMember(
                member_name=payload.team_member_name,
                role=payload.team_member_role or "care_team",
                is_primary=True,
                created_by=current_user.user_id,
            )
        )
    db.add(care_plan)
    db.flush()
    db.commit()
    db.refresh(care_plan)
    operation, audit_path = append_care_plan_workflow_audit(
        workflow="care_plan.create",
        entity_type="clinical_care_plan",
        entity_id=care_plan.care_plan_number,
        actor=care_plan_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=care_plan.status,
        reason=payload.reason,
        changes=care_plan_changes(care_plan),
    )
    return CarePlanCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, care_plan=care_plan)


@router.get("/{care_plan_id}", response_model=CarePlanResponse)
def get_care_plan(
    care_plan_id: int,
    current_user: User = Depends(require_care_plan_read),
    db: Session = Depends(get_db),
) -> ClinicalCarePlan:
    return _care_plan_or_404(db, care_plan_id)


@router.post("/{care_plan_id}/goals/preview", response_model=CarePlanPreviewResponse)
def preview_add_goal(
    care_plan_id: int,
    payload: CarePlanGoalPreviewRequest,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanPreviewResponse:
    return goal_preview(_care_plan_or_404(db, care_plan_id), payload)


@router.post("/{care_plan_id}/goals", response_model=CarePlanCommitResponse)
def add_goal(
    care_plan_id: int,
    payload: CarePlanGoalCommitRequest,
    request: Request,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanCommitResponse:
    require_generation_confirmation(request)
    care_plan = _care_plan_or_404(db, care_plan_id)
    preview = goal_preview(care_plan, payload)
    _reject_blocking(preview)
    goal = ClinicalCarePlanGoal(
        care_plan_id=care_plan.care_plan_id,
        goal=payload.goal,
        target_date=payload.target_date,
        status=payload.status,
        priority=payload.priority,
        notes=payload.notes,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    care_plan.goals.append(goal)
    care_plan.updated_by = current_user.user_id
    care_plan.version += 1
    db.flush()
    db.commit()
    db.refresh(care_plan)
    operation, audit_path = append_care_plan_workflow_audit(
        workflow="care_plan.goal_add",
        entity_type="clinical_care_plan_goal",
        entity_id=str(goal.goal_id),
        actor=care_plan_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=care_plan.status,
        status_after=care_plan.status,
        reason=payload.reason,
        changes=goal_changes(goal),
    )
    return CarePlanCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, care_plan=care_plan, goal=goal)


@router.post("/{care_plan_id}/interventions/preview", response_model=CarePlanPreviewResponse)
def preview_add_intervention(
    care_plan_id: int,
    payload: CarePlanInterventionPreviewRequest,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanPreviewResponse:
    return intervention_preview(_care_plan_or_404(db, care_plan_id), payload)


@router.post("/{care_plan_id}/interventions", response_model=CarePlanCommitResponse)
def add_intervention(
    care_plan_id: int,
    payload: CarePlanInterventionCommitRequest,
    request: Request,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanCommitResponse:
    require_generation_confirmation(request)
    care_plan = _care_plan_or_404(db, care_plan_id)
    preview = intervention_preview(care_plan, payload)
    _reject_blocking(preview)
    intervention = ClinicalCarePlanIntervention(
        care_plan_id=care_plan.care_plan_id,
        intervention=payload.intervention,
        intervention_type=payload.intervention_type,
        owner=payload.owner,
        due_date=payload.due_date,
        status=payload.status,
        notes=payload.notes,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    care_plan.interventions.append(intervention)
    care_plan.updated_by = current_user.user_id
    care_plan.version += 1
    db.flush()
    db.commit()
    db.refresh(care_plan)
    operation, audit_path = append_care_plan_workflow_audit(
        workflow="care_plan.intervention_add",
        entity_type="clinical_care_plan_intervention",
        entity_id=str(intervention.intervention_id),
        actor=care_plan_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=care_plan.status,
        status_after=care_plan.status,
        reason=payload.reason,
        changes=intervention_changes(intervention),
    )
    return CarePlanCommitResponse(
        operation_id=operation.operation_id,
        audit_path=audit_path,
        care_plan=care_plan,
        intervention=intervention,
    )


@router.post("/{care_plan_id}/tasks/preview", response_model=CarePlanPreviewResponse)
def preview_add_task(
    care_plan_id: int,
    payload: CarePlanTaskPreviewRequest,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanPreviewResponse:
    return task_preview(_care_plan_or_404(db, care_plan_id), payload)


@router.post("/{care_plan_id}/tasks", response_model=CarePlanCommitResponse)
def add_task(
    care_plan_id: int,
    payload: CarePlanTaskCommitRequest,
    request: Request,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanCommitResponse:
    require_generation_confirmation(request)
    care_plan = _care_plan_or_404(db, care_plan_id)
    preview = task_preview(care_plan, payload)
    _reject_blocking(preview)
    completed_at = now_utc() if payload.status == "completed" else None
    task = ClinicalCarePlanTask(
        care_plan_id=care_plan.care_plan_id,
        title=payload.title,
        description=payload.description,
        owner=payload.owner,
        due_date=payload.due_date,
        priority=payload.priority,
        status=payload.status,
        completed_at=completed_at,
        completed_by=current_user.user_id if completed_at else None,
        notes=payload.notes,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    care_plan.tasks.append(task)
    care_plan.updated_by = current_user.user_id
    care_plan.version += 1
    db.flush()
    db.commit()
    db.refresh(care_plan)
    operation, audit_path = append_care_plan_workflow_audit(
        workflow="care_plan.task_add",
        entity_type="clinical_care_plan_task",
        entity_id=str(task.task_id),
        actor=care_plan_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=care_plan.status,
        status_after=care_plan.status,
        reason=payload.reason,
        changes=task_changes(task),
    )
    return CarePlanCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, care_plan=care_plan, task=task)


@router.post("/{care_plan_id}/progress/preview", response_model=CarePlanPreviewResponse)
def preview_add_progress(
    care_plan_id: int,
    payload: CarePlanProgressPreviewRequest,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanPreviewResponse:
    return progress_preview(_care_plan_or_404(db, care_plan_id), payload)


@router.post("/{care_plan_id}/progress", response_model=CarePlanCommitResponse)
def add_progress(
    care_plan_id: int,
    payload: CarePlanProgressCommitRequest,
    request: Request,
    current_user: User = Depends(require_care_plan_mutation),
    db: Session = Depends(get_db),
) -> CarePlanCommitResponse:
    require_generation_confirmation(request)
    care_plan = _care_plan_or_404(db, care_plan_id)
    preview = progress_preview(care_plan, payload)
    _reject_blocking(preview)
    status_before = care_plan.status
    progress_note = ClinicalCarePlanProgressNote(
        care_plan_id=care_plan.care_plan_id,
        progress_note=payload.progress_note,
        status_update=payload.status_update,
        created_by=current_user.user_id,
    )
    care_plan.progress_notes.append(progress_note)
    if payload.status_update:
        update_care_plan_status(
            care_plan,
            next_status=payload.status_update,
            user_id=current_user.user_id,
            reason=payload.reason,
            notes="Progress update changed care plan status",
        )
    else:
        care_plan.updated_by = current_user.user_id
        care_plan.version += 1
    db.flush()
    db.commit()
    db.refresh(care_plan)
    operation, audit_path = append_care_plan_workflow_audit(
        workflow="care_plan.progress_add",
        entity_type="clinical_care_plan_progress_note",
        entity_id=str(progress_note.progress_note_id),
        actor=care_plan_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=care_plan.status,
        reason=payload.reason,
        changes=progress_changes(progress_note),
    )
    return CarePlanCommitResponse(
        operation_id=operation.operation_id,
        audit_path=audit_path,
        care_plan=care_plan,
        progress_note=progress_note,
    )


@router.post("/{care_plan_id}/close/preview", response_model=CarePlanPreviewResponse)
def preview_close_care_plan(
    care_plan_id: int,
    payload: CarePlanClosePreviewRequest,
    current_user: User = Depends(require_care_plan_closure),
    db: Session = Depends(get_db),
) -> CarePlanPreviewResponse:
    return close_preview(_care_plan_or_404(db, care_plan_id), payload)


@router.post("/{care_plan_id}/close", response_model=CarePlanCommitResponse)
def close_care_plan(
    care_plan_id: int,
    payload: CarePlanCloseCommitRequest,
    request: Request,
    current_user: User = Depends(require_care_plan_closure),
    db: Session = Depends(get_db),
) -> CarePlanCommitResponse:
    require_generation_confirmation(request)
    care_plan = _care_plan_or_404(db, care_plan_id)
    preview = close_preview(care_plan, payload)
    _reject_blocking(preview)
    status_before = care_plan.status
    care_plan.closed_at = now_utc()
    care_plan.closed_by = current_user.user_id
    care_plan.closure_reason = payload.closure_reason
    care_plan.outcome_summary = payload.outcome_summary
    update_care_plan_status(
        care_plan,
        next_status="closed",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes=payload.closure_reason,
    )
    db.flush()
    db.commit()
    db.refresh(care_plan)
    operation, audit_path = append_care_plan_workflow_audit(
        workflow="care_plan.close",
        entity_type="clinical_care_plan",
        entity_id=care_plan.care_plan_number,
        actor=care_plan_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=care_plan.status,
        reason=payload.reason,
        changes={
            "care_plan_id": care_plan.care_plan_id,
            "closure_reason": payload.closure_reason,
            "outcome_summary": payload.outcome_summary,
        },
    )
    return CarePlanCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, care_plan=care_plan)
