from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    AIDecision,
    Donor,
    DonorReview,
    Notification,
    Role,
    RolePermission,
    RoleWorkspaceConfig,
    User,
    WorkflowNavigationRoute,
    WorkflowTask,
    WorkflowTransitionEvent,
    WorkflowTransitionRule,
)
from app.services.ai_governance import (
    add_timeline_event,
    governed_analysis,
    record_ai_decision,
    record_override_if_needed,
)
from app.services.audit import log_audit, serialize_model
from app.services.functional_routes import route_path_for_record
from app.services.notifications import notify_role
from app.services.risk_engine import RiskAnalysis

TERMINAL_STATES = {
    "Approved",
    "Rejected",
    "Closed",
    "Released for Clinical Use",
    "Released for Research Use",
    "Quarantine",
    "Destroyed",
}
STATE_ALIASES = {
    "Pending": "Pending Intake Validation",
    "Under Review": "Pending Clinical Review",
    "Deferred": "Pending Additional Information",
    "Pending Intake Review": "Pending Intake Validation",
    "Pending QA Review": "QA Investigation",
    "Clinical Escalation": "Operations Escalation",
}

TASK_FIELDS = [
    "task_type",
    "title",
    "assigned_to_user_id",
    "assigned_role_id",
    "priority",
    "status",
    "workflow_state",
    "queue_name",
    "due_date",
    "related_record_id",
    "related_record_type",
    "escalation_level",
]


def _permissions_for_user(db: Session, user: User) -> set[str]:
    if not user.role_id:
        return set()
    return {
        row[0]
        for row in db.execute(
            select(RolePermission.permission_name).where(RolePermission.role_id == user.role_id)
        ).all()
    }


def _canonical_state(state: str | None) -> str:
    return STATE_ALIASES.get(state or "", state or "Draft Intake")


def _eligibility_status_for_state(state: str) -> str:
    if state in {"Rejected", "Destroyed"}:
        return "Rejected"
    if state in {"Processing Hold", "Quarantine", "Pending QA Review"}:
        return "Hold"
    if state in {"Pending Medical Director Review"}:
        return "Medical Director Review"
    if state in {"Released for Clinical Use", "Released for Research Use", "Recovery Authorized"}:
        return "Eligible"
    return "Pending"


def _disposition_for_state(state: str) -> str | None:
    mapping = {
        "Released for Clinical Use": "Clinical Transplant",
        "Released for Research Use": "Research Use",
        "Quarantine": "Quarantine",
        "Destroyed": "Destruction",
        "Rejected": "Rejected / Deferred",
    }
    return mapping.get(state)


def _role_for_user(db: Session, user: User) -> Role:
    role = db.get(Role, user.role_id) if user.role_id else None
    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current user has no role")
    return role


def _workspace_config(db: Session, role: Role) -> RoleWorkspaceConfig | None:
    return db.execute(
        select(RoleWorkspaceConfig).where(RoleWorkspaceConfig.role_id == role.role_id)
    ).scalar_one_or_none()


def _record_state(db: Session, record_type: str, record_id: str, task: WorkflowTask | None = None) -> str:
    if task:
        return _canonical_state(task.workflow_state)
    if record_type == "DonorReview":
        donor = db.get(DonorReview, int(record_id))
        if donor:
            return _canonical_state(donor.intake_status)
    if record_type == "Donor":
        donor = db.get(Donor, int(record_id))
        if donor:
            return _canonical_state(donor.current_workflow_state)
    return "Assigned"


def _active_task(db: Session, record_type: str, record_id: str, task_id: int | None = None) -> WorkflowTask | None:
    if task_id:
        return db.get(WorkflowTask, task_id)
    return db.execute(
        select(WorkflowTask)
        .where(
            WorkflowTask.related_record_type == record_type,
            WorkflowTask.related_record_id == record_id,
            WorkflowTask.status.not_in(["Completed", "Rejected"]),
        )
        .order_by(WorkflowTask.due_date, desc(WorkflowTask.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _page_key_for_record(
    db: Session,
    *,
    role: Role,
    record_type: str | None,
    workflow_state: str | None,
    fallback_page_key: str | None = None,
) -> tuple[str, str]:
    if record_type:
        query = select(WorkflowNavigationRoute).where(
            WorkflowNavigationRoute.role_id == role.role_id,
            WorkflowNavigationRoute.record_type == record_type,
            WorkflowNavigationRoute.is_active.is_(True),
        )
        routes = list(db.execute(query).scalars().all())
        state = _canonical_state(workflow_state)
        for route in routes:
            if route.workflow_state == state:
                return route.page_key, route.route_label
        if routes:
            return routes[0].page_key, routes[0].route_label

    config = _workspace_config(db, role)
    if fallback_page_key:
        return fallback_page_key, fallback_page_key.replace("_", " ").title()
    if config and config.visible_tabs:
        first = config.visible_tabs[0]
        return first["page_key"], first["label"]
    return "role_tasks", "Role Tasks"


def route_to_record(
    db: Session,
    *,
    current_user: User,
    record_type: str | None,
    record_id: str | None,
    action_route: str | None = None,
    workflow_task_id: int | None = None,
    notification_id: int | None = None,
) -> dict[str, Any]:
    role = _role_for_user(db, current_user)
    task = db.get(WorkflowTask, workflow_task_id) if workflow_task_id else None
    state = _record_state(db, record_type or "", record_id or "", task) if record_type and record_id else None
    page_key, route_label = _page_key_for_record(
        db,
        role=role,
        record_type=record_type,
        workflow_state=state,
        fallback_page_key=action_route,
    )
    route_path = action_route if action_route and action_route.startswith("/") else None
    if not route_path:
        route_path = route_path_for_record(
            record_type,
            record_id,
            role_name=role.role_name,
            workflow_state=state,
            task_id=workflow_task_id,
        )
    return {
        "route_path": route_path,
        "page_key": page_key,
        "route_label": route_label,
        "record_type": record_type,
        "record_id": record_id,
        "workflow_state": state,
        "notification_id": notification_id,
        "task_id": workflow_task_id,
    }


def _donor_decision_matrix(
    donor: DonorReview,
    *,
    action_name: str,
    rule: WorkflowTransitionRule,
) -> dict[str, Any]:
    required_fields_complete = bool(donor.donor_id and donor.donor_name and donor.age and donor.blood_type)
    docs_uploaded = bool(donor.attachment_placeholder) and not donor.missing_required_fields
    donor_source_valid = donor.donor_id.startswith("DNR-") and (donor.age or 0) >= 18

    if action_name in {"validate_intake", "submit_intake", "submit_to_clinical_review"}:
        if not required_fields_complete:
            return {
                "to_state": "Pending Additional Information",
                "target_role": "Donor Intake Coordinator",
                "task_type": "Intake Incomplete Escalation",
                "notification_type": "Missing Documentation",
                "priority": "High",
                "reason": "Required fields are incomplete.",
            }
        if not docs_uploaded:
            return {
                "to_state": "Pending Additional Information",
                "target_role": "Donor Intake Coordinator",
                "task_type": "Missing Documentation Queue",
                "notification_type": "Missing Documentation",
                "priority": "High",
                "reason": "Required documentation is missing.",
            }
        if not donor_source_valid:
            return {
                "to_state": "Operations Escalation",
                "target_role": "Operations Manager",
                "task_type": "Intake Source Escalation",
                "notification_type": "Enterprise Bottleneck",
                "priority": "Critical",
                "reason": "Donor source validation failed.",
            }

    return {
        "to_state": rule.to_state,
        "target_role": None,
        "task_type": rule.task_type,
        "notification_type": rule.notification_type,
        "priority": None,
        "reason": "Transition rule accepted.",
    }


def _clinical_ai_matrix(
    db: Session,
    donor: DonorReview,
    *,
    action_name: str,
    current_user: User,
    metadata: dict[str, Any],
    note: str,
) -> tuple[AIDecision, RiskAnalysis, dict[str, Any]]:
    analysis = governed_analysis(
        db,
        donor_name=donor.donor_name,
        age=donor.age,
        blood_type=donor.blood_type,
        infectious_history=donor.infectious_history,
        travel_risk=donor.travel_risk,
        missing_required_fields=donor.missing_required_fields,
        clinical_notes=donor.clinical_notes,
    )
    decision = record_ai_decision(
        db,
        donor,
        workflow_stage=_canonical_state(donor.intake_status),
        reviewed_by=current_user.user_id,
    )
    final_decision = {
        "approve_donor": "Approved",
        "reject_donor": "Rejected",
        "escalate_to_qa": "QA Investigation",
        "escalate_case": "QA Investigation",
        "request_qa_review": "QA Investigation",
        "request_additional_information": "Pending Additional Information",
    }.get(action_name, metadata.get("final_decision", action_name))
    recommended_action = analysis.recommended_action.lower()
    action_conflicts = (
        action_name == "approve_donor"
        and ("escalate" in recommended_action or "reject" in recommended_action or analysis.risk_score >= 30)
    )
    critical_conflict = (
        donor.infectious_history and donor.missing_required_fields
    ) or analysis.risk_score >= 90
    explicit_override = bool(metadata.get("human_override") or metadata.get("ai_override"))
    override_reason = metadata.get("override_reason") or metadata.get("ai_override_reason") or note

    if (action_conflicts or critical_conflict or explicit_override) and not override_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI recommendation override requires an override reason.",
        )

    if action_conflicts or critical_conflict or explicit_override:
        record_override_if_needed(
            db,
            donor,
            final_decision=final_decision,
            reviewer_id=current_user.user_id,
            override_reason=override_reason,
            explicit_override=True,
        )

    if analysis.risk_score < 30:
        risk_band = "LOW"
    elif analysis.risk_score < 70:
        risk_band = "MEDIUM"
    elif critical_conflict:
        risk_band = "CRITICAL"
    else:
        risk_band = "HIGH"

    return decision, analysis, {
        "risk_band": risk_band,
        "risk_score": analysis.risk_score,
        "recommended_action": analysis.recommended_action,
        "triggered_rules": analysis.triggered_rules,
        "override_required": action_conflicts or critical_conflict,
        "override_reason": override_reason if action_conflicts or critical_conflict or explicit_override else None,
    }


def execute_workflow_transition(
    db: Session,
    *,
    current_user: User,
    action_name: str,
    related_record_type: str,
    related_record_id: str,
    task_id: int | None = None,
    note: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    rule = db.execute(
        select(WorkflowTransitionRule).where(
            WorkflowTransitionRule.action_name == action_name,
            WorkflowTransitionRule.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow transition not found")

    permissions = _permissions_for_user(db, current_user)
    role = _role_for_user(db, current_user)
    if current_user.role_id != rule.source_role_id and "system.admin" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Transition is not allowed for this role")

    task = _active_task(db, related_record_type, related_record_id, task_id)
    current_state = _record_state(db, related_record_type, related_record_id, task)
    allowed_current_states = {rule.from_state, _canonical_state(rule.from_state)}
    if rule.from_state == "Pending Clinical Review":
        allowed_current_states.update({"Clinical Review In Progress", "Clinical Re-Review"})
    if current_state not in allowed_current_states and "system.admin" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{action_name} is not valid from workflow state {current_state}.",
        )

    old_task_value = serialize_model(task, TASK_FIELDS) if task else None
    target_role = db.get(Role, rule.target_role_id) if rule.target_role_id else None
    target_state = rule.to_state
    task_type = rule.task_type
    notification_type = rule.notification_type
    priority = task.priority if task else "High"
    decision_context: dict[str, Any] = {
        "source_role": role.role_name,
        "rule_from_state": rule.from_state,
        "rule_to_state": rule.to_state,
    }

    donor = db.get(DonorReview, int(related_record_id)) if related_record_type == "DonorReview" else None
    donor_master = db.get(Donor, int(related_record_id)) if related_record_type == "Donor" else None
    if donor:
        intake_matrix = _donor_decision_matrix(donor, action_name=action_name, rule=rule)
        target_state = intake_matrix["to_state"]
        task_type = intake_matrix["task_type"]
        notification_type = intake_matrix["notification_type"]
        priority = intake_matrix["priority"] or priority
        decision_context["intake_decision_matrix"] = intake_matrix
        if intake_matrix["target_role"]:
            target_role = db.execute(
                select(Role).where(Role.role_name == intake_matrix["target_role"])
            ).scalar_one_or_none()

        if action_name in {
            "approve_donor",
            "reject_donor",
            "escalate_to_qa",
            "escalate_case",
            "request_qa_review",
            "request_additional_information",
        }:
            _, _, ai_context = _clinical_ai_matrix(
                db,
                donor,
                action_name=action_name,
                current_user=current_user,
                metadata=metadata,
                note=note,
            )
            decision_context["ai_decision_matrix"] = ai_context

    if task:
        task.workflow_state = target_state
        task.status = "Completed"
        task.completed_at = datetime.now(UTC)

    if donor:
        donor.intake_status = target_state
        donor.updated_at = datetime.now(UTC)
        if target_state in {"Approved", "Rejected"}:
            donor.reviewed_at = datetime.now(UTC)
            donor.reviewer_id = current_user.user_id
        if target_state == "Rejected" and note:
            donor.rejection_reason = note

    if donor_master:
        donor_master.current_workflow_state = target_state
        donor_master.updated_at = datetime.now(UTC)
        donor_master.eligibility_status = _eligibility_status_for_state(target_state)
        donor_master.final_disposition = _disposition_for_state(target_state) or donor_master.final_disposition

    new_task = None
    if target_role and target_state not in TERMINAL_STATES:
        target_config = _workspace_config(db, target_role)
        due_date = datetime.now(UTC) + timedelta(hours=rule.sla_hours)
        if target_state in {"High Risk Escalation", "Operations Escalation", "QA Investigation"}:
            priority = "Critical" if priority in {"High", "Critical", "STAT"} else "High"
        new_task = WorkflowTask(
            task_type=task_type,
            title=f"{rule.action_label}: {related_record_type} {related_record_id}",
            description=note or f"Workflow routed from {current_state} to {target_state}.",
            assigned_role_id=target_role.role_id,
            priority=priority,
            status="Assigned",
            workflow_state=target_state,
            queue_name=target_config.default_queue if target_config else "General Work Queue",
            due_date=due_date if rule.sla_hours > 0 else None,
            related_record_id=related_record_id,
            related_record_type=related_record_type,
            escalation_level=1 if "Escalation" in task_type or target_state.endswith("Escalation") else 0,
        )
        db.add(new_task)
        db.flush()
        page_key, _ = _page_key_for_record(
            db,
            role=target_role,
            record_type=related_record_type,
            workflow_state=target_state,
        )
        route_path = route_path_for_record(
            related_record_type,
            related_record_id,
            role_name=target_role.role_name,
            workflow_state=target_state,
            task_id=new_task.task_id,
        )
        notify_role(
            db,
            role_name=target_role.role_name,
            title=f"[{priority}] {notification_type}",
            message=f"{related_record_type} {related_record_id} is now {target_state} in {new_task.queue_name}.",
            notification_type=notification_type,
            priority=priority,
            workflow_task_id=new_task.task_id,
            related_record_type=related_record_type,
            related_record_id=related_record_id,
            action_route=route_path,
            workflow_context={
                "workflow_state": target_state,
                "from_state": current_state,
                "action_taken": action_name,
                "queue_name": new_task.queue_name,
                "due_date": due_date.isoformat() if due_date else None,
                "route_path": route_path,
                "legacy_page_key": page_key,
                "decision_context": decision_context,
            },
        )

    transition_event = WorkflowTransitionEvent(
        record_id=related_record_id,
        record_type=related_record_type,
        from_state=current_state,
        to_state=target_state,
        action_taken=action_name,
        performed_by=current_user.user_id,
        notes=note,
        decision_context=decision_context,
    )
    db.add(transition_event)
    add_timeline_event(
        db,
        related_record_type=related_record_type,
        related_record_id=related_record_id,
        event_type="Workflow Transition",
        event_summary=f"{action_name}: {current_state} -> {target_state}",
        event_detail=decision_context,
        created_by=current_user.user_id,
    )
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type=rule.audit_action,
        table_name="workflow_transition_event",
        record_id=related_record_id,
        old_value=old_task_value,
        new_value={
            "action": action_name,
            "from_state": current_state,
            "to_state": target_state,
            "related_record_type": related_record_type,
            "related_record_id": related_record_id,
            "new_task_id": new_task.task_id if new_task else None,
            "note": note,
            "decision_context": decision_context,
        },
        entity_type=related_record_type,
        entity_id=related_record_id,
    )
    db.commit()
    if new_task:
        db.refresh(new_task)
    if task:
        db.refresh(task)
    db.refresh(transition_event)
    return {
        "action": action_name,
        "from_state": current_state,
        "to_state": target_state,
        "updated_task_id": task.task_id if task else None,
        "created_task_id": new_task.task_id if new_task else None,
        "transition_event_id": transition_event.transition_id,
        "decision_context": decision_context,
    }


def recent_transition_events(
    db: Session,
    *,
    record_type: str | None = None,
    record_id: str | None = None,
    limit: int = 100,
) -> list[WorkflowTransitionEvent]:
    query = select(WorkflowTransitionEvent)
    if record_type:
        query = query.where(WorkflowTransitionEvent.record_type == record_type)
    if record_id:
        query = query.where(WorkflowTransitionEvent.record_id == record_id)
    return list(db.execute(query.order_by(desc(WorkflowTransitionEvent.timestamp)).limit(limit)).scalars().all())


def notification_route(db: Session, *, notification: Notification, current_user: User) -> dict[str, Any]:
    notification.is_read = True
    return route_to_record(
        db,
        current_user=current_user,
        record_type=notification.related_record_type,
        record_id=notification.related_record_id,
        action_route=notification.action_route,
        workflow_task_id=notification.workflow_task_id,
        notification_id=notification.notification_id,
    )
