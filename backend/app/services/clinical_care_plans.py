from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ClinicalCarePlan,
    ClinicalCarePlanGoal,
    ClinicalCarePlanIntervention,
    ClinicalCarePlanProgressNote,
    ClinicalCarePlanStatusHistory,
    ClinicalCarePlanTask,
    ClinicalEncounter,
    ClinicalOrder,
    ClinicalOrderResult,
    ClinicalScreeningSession,
    Patient,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_care_plans import (
    CarePlanBlockingIssue,
    CarePlanClosePreviewRequest,
    CarePlanCreatePreviewRequest,
    CarePlanGoalPreviewRequest,
    CarePlanInterventionPreviewRequest,
    CarePlanPreviewResponse,
    CarePlanProgressPreviewRequest,
    CarePlanTaskPreviewRequest,
    CarePlanWarning,
)
from app.services.clinical_patients import actor_label
from app.services.clinical_workflows import append_workflow_operation, preview_hash

TERMINAL_CARE_PLAN_STATUSES = {"completed", "cancelled", "closed"}
PROGRESS_STATUS_UPDATES = {"draft", "active", "on_hold"}


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_care_plan_number() -> str:
    return f"CP-{uuid4().hex[:10].upper()}"


def _one_or_none(db: Session, statement) -> Any | None:
    return db.execute(statement).scalar_one_or_none()


def patient_by_identifier(db: Session, patient_id: str) -> Patient | None:
    return _one_or_none(db, select(Patient).where(Patient.patient_id == patient_id, Patient.is_deleted.is_(False)))


def encounter_by_id(db: Session, encounter_id: int | None) -> ClinicalEncounter | None:
    if encounter_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalEncounter).where(
            ClinicalEncounter.encounter_id == encounter_id,
            ClinicalEncounter.is_deleted.is_(False),
        ),
    )


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


def order_by_id(db: Session, order_id: int | None) -> ClinicalOrder | None:
    if order_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalOrder).where(ClinicalOrder.order_id == order_id, ClinicalOrder.is_deleted.is_(False)),
    )


def order_result_by_id(db: Session, result_id: int | None) -> ClinicalOrderResult | None:
    if result_id is None:
        return None
    return _one_or_none(db, select(ClinicalOrderResult).where(ClinicalOrderResult.result_id == result_id))


def care_plan_by_id(db: Session, care_plan_id: int) -> ClinicalCarePlan | None:
    return _one_or_none(
        db,
        select(ClinicalCarePlan).where(
            ClinicalCarePlan.care_plan_id == care_plan_id,
            ClinicalCarePlan.is_deleted.is_(False),
        ),
    )


def care_plan_actor(user: User) -> str:
    return actor_label(user)


def _issue(issue_type: str, field: str, message: str) -> CarePlanBlockingIssue:
    return CarePlanBlockingIssue(issue_type=issue_type, field=field, message=message)


def _warning(warning_type: str, field: str, message: str) -> CarePlanWarning:
    return CarePlanWarning(warning_type=warning_type, field=field, message=message)


def _preview(
    *,
    workflow: str,
    entity_type: str,
    entity_id: str,
    changes: dict[str, Any],
    blocking_issues: list[CarePlanBlockingIssue] | None = None,
    warnings: list[CarePlanWarning] | None = None,
    summary: str,
) -> CarePlanPreviewResponse:
    issues = blocking_issues or []
    warning_rows = warnings or []
    return CarePlanPreviewResponse(
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


def _context_payload(
    *,
    patient: Patient | None,
    encounter: ClinicalEncounter | None,
    screening: ClinicalScreeningSession | None,
    order: ClinicalOrder | None,
    result: ClinicalOrderResult | None,
) -> dict[str, Any]:
    return {
        "patient_pk": patient.patient_pk if patient else None,
        "encounter_number": encounter.encounter_number if encounter else None,
        "screening_session_number": screening.session_number if screening else None,
        "order_number": order.order_number if order else None,
        "order_result": f"{result.result_name}: {result.result_value}" if result else None,
        "result_flag": "critical" if result and result.critical_flag else "abnormal" if result and result.abnormal_flag else None,
    }


def _closed_issue(care_plan: ClinicalCarePlan) -> CarePlanBlockingIssue | None:
    if care_plan.status in TERMINAL_CARE_PLAN_STATUSES:
        return _issue("care_plan_closed", "care_plan_id", "Closed, completed, or cancelled care plans cannot receive new activity.")
    return None


def care_plan_create_preview(db: Session, payload: CarePlanCreatePreviewRequest) -> CarePlanPreviewResponse:
    patient = patient_by_identifier(db, payload.patient_id)
    encounter = encounter_by_id(db, payload.encounter_id)
    screening = screening_session_by_id(db, payload.screening_session_id)
    order = order_by_id(db, payload.order_id)
    result = order_result_by_id(db, payload.order_result_id)
    issues: list[CarePlanBlockingIssue] = []
    warnings: list[CarePlanWarning] = []

    if patient is None:
        issues.append(_issue("unknown_patient", "patient_id", "Patient/donor profile was not found."))
    if payload.encounter_id is not None and encounter is None:
        issues.append(_issue("unknown_encounter", "encounter_id", "Encounter was not found."))
    if payload.screening_session_id is not None and screening is None:
        issues.append(_issue("unknown_screening_session", "screening_session_id", "Screening session was not found."))
    if payload.order_id is not None and order is None:
        issues.append(_issue("unknown_order", "order_id", "Clinical order was not found."))
    if payload.order_result_id is not None and result is None:
        issues.append(_issue("unknown_order_result", "order_result_id", "Order result was not found."))
    if patient and encounter and encounter.patient_pk != patient.patient_pk:
        issues.append(_issue("encounter_patient_mismatch", "encounter_id", "Encounter belongs to a different patient/donor."))
    if patient and screening and screening.patient_pk != patient.patient_pk:
        issues.append(_issue("screening_patient_mismatch", "screening_session_id", "Screening session belongs to a different patient/donor."))
    if patient and order and order.patient_pk != patient.patient_pk:
        issues.append(_issue("order_patient_mismatch", "order_id", "Order belongs to a different patient/donor."))
    if result and order is None:
        issues.append(_issue("order_required_for_result", "order_id", "Link an order when linking an order result."))
    if result and order and result.order_id != order.order_id:
        issues.append(_issue("order_result_mismatch", "order_result_id", "Order result does not belong to the linked order."))
    if result and order and patient and order.patient_pk != patient.patient_pk:
        issues.append(_issue("order_result_patient_mismatch", "order_result_id", "Linked order result belongs to a different patient/donor."))
    if result and result.critical_flag:
        warnings.append(_warning("critical_result_context", "order_result_id", "Care plan is linked to a critical result context."))
    elif result and result.abnormal_flag:
        warnings.append(_warning("abnormal_result_context", "order_result_id", "Care plan is linked to an abnormal result context."))
    if order and order.has_critical_unacknowledged:
        warnings.append(_warning("critical_unacknowledged", "order_id", "Linked order has an unacknowledged critical result."))

    changes = payload.model_dump(mode="json")
    changes["context"] = _context_payload(patient=patient, encounter=encounter, screening=screening, order=order, result=result)
    return _preview(
        workflow="care_plan.create",
        entity_type="clinical_care_plan",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Care plan is ready to create." if not issues else "Care plan preview found blocking issues.",
    )


def goal_preview(care_plan: ClinicalCarePlan, payload: CarePlanGoalPreviewRequest) -> CarePlanPreviewResponse:
    issues = []
    closed_issue = _closed_issue(care_plan)
    if closed_issue:
        issues.append(closed_issue)
    return _preview(
        workflow="care_plan.goal_add",
        entity_type="clinical_care_plan_goal",
        entity_id=care_plan.care_plan_number,
        changes=payload.model_dump(mode="json"),
        blocking_issues=issues,
        summary="Care plan goal is ready to add." if not issues else "Goal preview found blocking issues.",
    )


def intervention_preview(care_plan: ClinicalCarePlan, payload: CarePlanInterventionPreviewRequest) -> CarePlanPreviewResponse:
    issues = []
    closed_issue = _closed_issue(care_plan)
    if closed_issue:
        issues.append(closed_issue)
    return _preview(
        workflow="care_plan.intervention_add",
        entity_type="clinical_care_plan_intervention",
        entity_id=care_plan.care_plan_number,
        changes=payload.model_dump(mode="json"),
        blocking_issues=issues,
        summary="Care plan intervention is ready to add." if not issues else "Intervention preview found blocking issues.",
    )


def task_preview(care_plan: ClinicalCarePlan, payload: CarePlanTaskPreviewRequest) -> CarePlanPreviewResponse:
    issues = []
    closed_issue = _closed_issue(care_plan)
    if closed_issue:
        issues.append(closed_issue)
    return _preview(
        workflow="care_plan.task_add",
        entity_type="clinical_care_plan_task",
        entity_id=care_plan.care_plan_number,
        changes=payload.model_dump(mode="json"),
        blocking_issues=issues,
        summary="Care plan task is ready to add." if not issues else "Task preview found blocking issues.",
    )


def progress_preview(care_plan: ClinicalCarePlan, payload: CarePlanProgressPreviewRequest) -> CarePlanPreviewResponse:
    issues = []
    warnings: list[CarePlanWarning] = []
    closed_issue = _closed_issue(care_plan)
    if closed_issue:
        issues.append(closed_issue)
    if payload.status_update and payload.status_update not in PROGRESS_STATUS_UPDATES:
        issues.append(_issue("closure_workflow_required", "status_update", "Use the close workflow for completed, cancelled, or closed status."))
    if payload.status_update and payload.status_update == care_plan.status:
        warnings.append(_warning("status_unchanged", "status_update", "Progress note status update matches current care plan status."))
    return _preview(
        workflow="care_plan.progress_add",
        entity_type="clinical_care_plan_progress_note",
        entity_id=care_plan.care_plan_number,
        changes=payload.model_dump(mode="json"),
        blocking_issues=issues,
        warnings=warnings,
        summary="Care plan progress update is ready to add." if not issues else "Progress preview found blocking issues.",
    )


def close_preview(care_plan: ClinicalCarePlan, payload: CarePlanClosePreviewRequest) -> CarePlanPreviewResponse:
    issues = []
    if care_plan.status in TERMINAL_CARE_PLAN_STATUSES:
        issues.append(_issue("already_closed", "care_plan_id", "Care plan is already closed, completed, or cancelled."))
    return _preview(
        workflow="care_plan.close",
        entity_type="clinical_care_plan",
        entity_id=care_plan.care_plan_number,
        changes=payload.model_dump(mode="json"),
        blocking_issues=issues,
        summary="Care plan closure is ready to commit." if not issues else "Care plan closure preview found blocking issues.",
    )


def append_status_history(
    care_plan: ClinicalCarePlan,
    *,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    care_plan.status_history.append(
        ClinicalCarePlanStatusHistory(
            care_plan_id=care_plan.care_plan_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            reason=reason,
            notes=notes,
        )
    )


def update_care_plan_status(
    care_plan: ClinicalCarePlan,
    *,
    next_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> tuple[str, str]:
    status_before = care_plan.status
    if status_before != next_status:
        care_plan.status = next_status
        append_status_history(
            care_plan,
            from_status=status_before,
            to_status=next_status,
            user_id=user_id,
            reason=reason,
            notes=notes,
        )
    care_plan.updated_by = user_id
    care_plan.version += 1
    return status_before, care_plan.status


def append_care_plan_workflow_audit(
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


def care_plan_changes(care_plan: ClinicalCarePlan) -> dict[str, Any]:
    return {
        "care_plan_id": care_plan.care_plan_id,
        "care_plan_number": care_plan.care_plan_number,
        "patient_id": care_plan.patient_id,
        "encounter_id": care_plan.encounter_id,
        "screening_session_id": care_plan.screening_session_id,
        "order_id": care_plan.order_id,
        "order_result_id": care_plan.order_result_id,
        "title": care_plan.title,
        "plan_type": care_plan.plan_type,
        "priority": care_plan.priority,
        "status": care_plan.status,
        "reason": care_plan.reason,
        "start_date": care_plan.start_date.isoformat() if care_plan.start_date else None,
        "target_date": care_plan.target_date.isoformat() if care_plan.target_date else None,
    }


def goal_changes(goal: ClinicalCarePlanGoal) -> dict[str, Any]:
    return {
        "goal_id": goal.goal_id,
        "care_plan_id": goal.care_plan_id,
        "goal": goal.goal,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "status": goal.status,
        "priority": goal.priority,
    }


def intervention_changes(intervention: ClinicalCarePlanIntervention) -> dict[str, Any]:
    return {
        "intervention_id": intervention.intervention_id,
        "care_plan_id": intervention.care_plan_id,
        "intervention": intervention.intervention,
        "intervention_type": intervention.intervention_type,
        "owner": intervention.owner,
        "due_date": intervention.due_date.isoformat() if intervention.due_date else None,
        "status": intervention.status,
    }


def task_changes(task: ClinicalCarePlanTask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "care_plan_id": task.care_plan_id,
        "title": task.title,
        "owner": task.owner,
        "due_date": task.due_date.isoformat(),
        "priority": task.priority,
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def progress_changes(progress_note: ClinicalCarePlanProgressNote) -> dict[str, Any]:
    return {
        "progress_note_id": progress_note.progress_note_id,
        "care_plan_id": progress_note.care_plan_id,
        "progress_note": progress_note.progress_note,
        "status_update": progress_note.status_update,
    }
