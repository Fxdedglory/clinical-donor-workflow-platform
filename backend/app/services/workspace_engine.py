from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AIDecision,
    AuditLog,
    ChangeControl,
    DonorReview,
    Notification,
    Role,
    RoleDashboardWidget,
    RoleNavigationConfig,
    RolePermission,
    RoleWorkspaceConfig,
    User,
    Vendor,
    VendorIncident,
    WorkflowTask,
    WorkflowTransitionRule,
)
from app.services.ai_governance import governance_analytics, governance_kpis
from app.services.audit import log_audit, serialize_model
from app.services.notifications import notify_role

TERMINAL_STATES = {"Approved", "Rejected", "Closed"}

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


def _active_role(db: Session, current_user: User, preview_role_id: int | None = None) -> tuple[Role, bool]:
    actual_role = db.get(Role, current_user.role_id) if current_user.role_id else None
    if not actual_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current user has no role")

    if not preview_role_id or preview_role_id == actual_role.role_id:
        return actual_role, False

    permissions = _permissions_for_user(db, current_user)
    if "system.admin" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace preview requires system admin")

    preview_role = db.get(Role, preview_role_id)
    if not preview_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview role not found")
    return preview_role, True


def _config_for_role(db: Session, role: Role) -> RoleWorkspaceConfig:
    config = db.execute(
        select(RoleWorkspaceConfig).where(RoleWorkspaceConfig.role_id == role.role_id)
    ).scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace config not found")
    return config


def _role_tasks(db: Session, role: Role, current_user: User, *, include_all: bool = False) -> list[WorkflowTask]:
    query = select(WorkflowTask)
    if role.role_name == "System Administrator":
        return []
    if role.role_name == "Operations Manager" or include_all:
        query = query.where(WorkflowTask.status.not_in(["Completed", "Rejected"]))
    else:
        query = query.where(
            or_(
                WorkflowTask.assigned_role_id == role.role_id,
                WorkflowTask.assigned_to_user_id == current_user.user_id,
            ),
            WorkflowTask.status.not_in(["Completed", "Rejected"]),
        )
    return list(db.execute(query.order_by(WorkflowTask.due_date, desc(WorkflowTask.created_at)).limit(250)).scalars().all())


def _task_counts(db: Session, role: Role, user: User) -> dict[str, int]:
    tasks = _role_tasks(db, role, user)
    return {
        "open": len(tasks),
        "escalated": sum(1 for task in tasks if task.status == "Escalated" or task.escalation_level > 0),
        "urgent": sum(1 for task in tasks if task.priority in {"High", "Critical", "STAT"}),
        "near_sla": sum(1 for task in tasks if task.due_date and task.due_date <= datetime.now(UTC) + timedelta(hours=6)),
    }


def _queue_rows_for_tasks(db: Session, tasks: list[WorkflowTask]) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    rows: list[dict[str, Any]] = []
    for task in tasks[:80]:
        hours_left = None
        if task.due_date:
            hours_left = round((task.due_date - now).total_seconds() / 3600, 1)
        row = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "title": task.title,
            "priority": task.priority,
            "status": task.status,
            "workflow_state": task.workflow_state,
            "workflow_status": task.workflow_state,
            "queue_name": task.queue_name,
            "due_date": task.due_date,
            "assigned_date": task.created_at,
            "sla_timer": f"{hours_left}h" if hours_left is not None else "",
            "escalation_status": "Escalated" if task.escalation_level else "Normal",
            "related_record_type": task.related_record_type,
            "related_record_id": task.related_record_id,
        }
        if task.related_record_type == "DonorReview":
            donor = db.get(DonorReview, int(task.related_record_id))
            if donor:
                row.update(
                    {
                        "donor_id": donor.donor_id,
                        "donor_name": donor.donor_name,
                        "submission_status": donor.intake_status,
                        "missing_documents": "Yes" if donor.missing_required_fields else "No",
                        "risk_score": donor.risk_score,
                        "infectious_flags": "Yes" if donor.infectious_history else "No",
                    }
                )
        elif task.related_record_type == "VendorIncident":
            incident = db.get(VendorIncident, int(task.related_record_id))
            if incident:
                vendor = db.get(Vendor, incident.vendor_id)
                row.update(
                    {
                        "ticket_number": incident.ticket_number,
                        "vendor": vendor.vendor_name if vendor else "",
                        "severity": incident.severity,
                        "sla_breached": incident.sla_breached,
                        "ticket_age_hours": incident.ticket_age_hours,
                    }
                )
        elif task.related_record_type == "ChangeControl":
            change = db.get(ChangeControl, int(task.related_record_id))
            if change:
                row.update(
                    {
                        "request_id": change.request_id,
                        "risk_level": change.risk_level,
                        "approval_status": change.approval_status,
                        "capa_required": change.capa_required,
                        "implementation_due_date": change.implementation_due_date,
                    }
                )
        rows.append(row)
    return rows


def _donor_rows(db: Session, *, high_risk_only: bool = False, limit: int = 80) -> list[dict[str, Any]]:
    query = select(DonorReview)
    if high_risk_only:
        query = query.where(DonorReview.risk_score >= 50)
    query = query.where(DonorReview.intake_status.in_(["Pending", "Under Review", "Deferred"]))
    donors = db.execute(query.order_by(desc(DonorReview.risk_score), DonorReview.created_at).limit(limit)).scalars().all()
    rows = []
    for donor in donors:
        rows.append(
            {
                "donor_id": donor.donor_id,
                "donor_name": donor.donor_name,
                "submission_status": donor.intake_status,
                "missing_documents": "Yes" if donor.missing_required_fields else "No",
                "priority": donor.review_priority,
                "risk_score": donor.risk_score,
                "infectious_flags": "Yes" if donor.infectious_history else "No",
                "workflow_status": donor.intake_status,
                "assigned_date": donor.created_at,
                "sla_timer": "Near breach" if donor.risk_score >= 50 else "On track",
            }
        )
    return rows


def _change_rows(db: Session, *, capa_only: bool = False, limit: int = 80) -> list[dict[str, Any]]:
    query = select(ChangeControl)
    if capa_only:
        query = query.where(ChangeControl.capa_required.is_(True))
    query = query.where(ChangeControl.approval_status.in_(["Draft", "Investigation", "Pending Approval"]))
    changes = db.execute(query.order_by(desc(ChangeControl.created_at)).limit(limit)).scalars().all()
    return [
        {
            "request_id": item.request_id,
            "risk_level": item.risk_level,
            "approval_status": item.approval_status,
            "capa_required": item.capa_required,
            "implementation_due_date": item.implementation_due_date,
            "workflow_state": "CAPA Investigation" if item.capa_required else "Pending QA Review",
            "reason": item.reason,
        }
        for item in changes
    ]


def _vendor_rows(db: Session, limit: int = 80) -> list[dict[str, Any]]:
    rows = db.execute(
        select(VendorIncident, Vendor.vendor_name)
        .join(Vendor, Vendor.vendor_id == VendorIncident.vendor_id)
        .order_by(desc(VendorIncident.sla_breached), desc(VendorIncident.opened_at))
        .limit(limit)
    ).all()
    return [
        {
            "ticket_number": incident.ticket_number,
            "vendor": vendor_name,
            "severity": incident.severity,
            "status": incident.status,
            "sla_breached": incident.sla_breached,
            "uptime_percent": incident.uptime_percent,
            "ticket_age_hours": incident.ticket_age_hours,
            "impact_summary": incident.impact_summary,
        }
        for incident, vendor_name in rows
    ]


def _workspace_matrix(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Role.role_name, RoleWorkspaceConfig)
        .join(RoleWorkspaceConfig, RoleWorkspaceConfig.role_id == Role.role_id)
        .order_by(Role.role_name)
    ).all()
    return [
        {
            "role": role_name,
            "workspace": config.workspace_name,
            "visible_tabs": len(config.visible_tabs),
            "widgets": len(config.enabled_widgets),
            "default_queue": config.default_queue,
        }
        for role_name, config in rows
    ]


def _workspace_kpis(db: Session, role: Role, user: User) -> dict[str, Any]:
    counts = _task_counts(db, role, user)
    now = datetime.now(UTC)

    if role.role_name == "Donor Intake Coordinator":
        pending = db.execute(select(func.count(DonorReview.review_id)).where(DonorReview.intake_status == "Pending")).scalar() or 0
        incomplete = db.execute(select(func.count(DonorReview.review_id)).where(DonorReview.missing_required_fields.is_(True))).scalar() or 0
        return {
            "Pending Intake Packages": int(pending),
            "Incomplete Submissions": int(incomplete),
            "Avg Intake Completion Time": "18.6h",
            "Intake SLA Status": f"{counts['near_sla']} near breach",
            "Urgent Donor Intakes": counts["urgent"],
        }

    if role.role_name == "Clinical Reviewer":
        pending = db.execute(select(func.count(DonorReview.review_id)).where(DonorReview.intake_status.in_(["Pending", "Under Review"]))).scalar() or 0
        high_risk = db.execute(select(func.count(DonorReview.review_id)).where(DonorReview.risk_score >= 50)).scalar() or 0
        avg_review = db.execute(
            select(func.avg(func.extract("epoch", DonorReview.reviewed_at - DonorReview.created_at) / 3600)).where(
                DonorReview.reviewed_at.is_not(None)
            )
        ).scalar()
        return {
            "Pending Clinical Reviews": int(pending),
            "High Risk Donors": int(high_risk),
            "Avg Review Turnaround": f"{round(float(avg_review or 0), 1)}h",
            "Escalated Cases": counts["escalated"],
            "SLA Risk Cases": counts["near_sla"],
        }

    if role.role_name == "Quality Assurance Specialist":
        open_investigations = db.execute(
            select(func.count(ChangeControl.change_id)).where(ChangeControl.approval_status.in_(["Draft", "Investigation", "Pending Approval"]))
        ).scalar() or 0
        capa = db.execute(select(func.count(ChangeControl.change_id)).where(ChangeControl.capa_required.is_(True))).scalar() or 0
        audit_exceptions = db.execute(select(func.count(AuditLog.audit_id)).where(AuditLog.action_type.like("%REJECT%"))).scalar() or 0
        return {
            "Open Investigations": int(open_investigations),
            "CAPA Aging": f"{counts['near_sla']} overdue",
            "SOP Deviations": int(capa),
            "Audit Exceptions": int(audit_exceptions),
            "Compliance Risk Score": min(100, int(open_investigations) + int(capa) * 2),
        }

    if role.role_name == "Vendor Operations Analyst":
        vendor_count = db.execute(select(func.count(VendorIncident.incident_id))).scalar() or 0
        open_incidents = db.execute(select(func.count(VendorIncident.incident_id)).where(VendorIncident.status == "Open")).scalar() or 0
        breaches = db.execute(select(func.count(VendorIncident.incident_id)).where(VendorIncident.sla_breached.is_(True))).scalar() or 0
        avg_resolution = db.execute(select(func.avg(VendorIncident.resolution_minutes)).where(VendorIncident.resolution_minutes.is_not(None))).scalar()
        uptime = db.execute(select(func.avg(VendorIncident.uptime_percent))).scalar()
        return {
            "Vendor Uptime": f"{round(float(uptime or 0), 2)}%",
            "Open Incidents": int(open_incidents),
            "SLA Breaches": int(breaches),
            "Avg Resolution Time": f"{round(float(avg_resolution or 0) / 60, 1)}h",
            "Critical Outages": int(db.execute(select(func.count(VendorIncident.incident_id)).where(VendorIncident.severity == "Critical")).scalar() or 0),
            "Vendor Records": int(vendor_count),
        }

    if role.role_name == "Operations Manager":
        completed_today = db.execute(
            select(func.count(WorkflowTask.task_id)).where(WorkflowTask.completed_at >= now - timedelta(days=1))
        ).scalar() or 0
        total_open = db.execute(
            select(func.count(WorkflowTask.task_id)).where(WorkflowTask.status.not_in(["Completed", "Rejected"]))
        ).scalar() or 0
        breaches = db.execute(select(func.count(VendorIncident.incident_id)).where(VendorIncident.sla_breached.is_(True))).scalar() or 0
        return {
            "Enterprise Backlog": int(total_open),
            "Escalated Workflows": counts["escalated"],
            "Staffing Load": f"{counts['open']} open",
            "SLA Compliance": f"{max(0, 100 - int(breaches or 0))}%",
            "Workflow Throughput": int(completed_today),
        }

    if role.role_name == "Business Technology Analyst":
        return governance_kpis(db)

    active_users = db.execute(select(func.count(User.user_id)).where(User.is_active.is_(True))).scalar() or 0
    role_count = db.execute(select(func.count(Role.role_id))).scalar() or 0
    workspace_configs = db.execute(select(func.count(RoleWorkspaceConfig.config_id))).scalar() or 0
    workflow_rules = db.execute(select(func.count(WorkflowTransitionRule.transition_id))).scalar() or 0
    audit_events = db.execute(select(func.count(AuditLog.audit_id))).scalar() or 0
    return {
        "Active Users": int(active_users),
        "Configured Roles": int(role_count),
        "Workspace Configurations": int(workspace_configs),
        "Workflow Rules": int(workflow_rules),
        "Audit Events": int(audit_events),
    }


def _widget_data(db: Session, role: Role, user: User) -> dict[str, Any]:
    tasks = _role_tasks(db, role, user, include_all=role.role_name == "Operations Manager")
    task_rows = _queue_rows_for_tasks(db, tasks)
    if role.role_name == "Donor Intake Coordinator":
        donor_rows = _donor_rows(db)
        return {
            "intake_queue": donor_rows,
            "missing_documentation": [row for row in donor_rows if row["missing_documents"] == "Yes"],
            "sla_countdown": task_rows,
            "role_tasks": task_rows,
            "role_escalations": [row for row in task_rows if row["escalation_status"] == "Escalated"],
        }
    if role.role_name == "Clinical Reviewer":
        high_risk = _donor_rows(db, high_risk_only=True)
        return {
            "high_risk_queue": high_risk,
            "review_sla_timer": task_rows,
            "escalation_feed": [row for row in task_rows if row["escalation_status"] == "Escalated"],
            "clinical_review_queue": _donor_rows(db),
            "high_risk_cases": high_risk,
            "role_tasks": task_rows,
            "role_escalations": [row for row in task_rows if row["escalation_status"] == "Escalated"],
        }
    if role.role_name == "Quality Assurance Specialist":
        changes = _change_rows(db)
        return {
            "investigation_queue": changes,
            "sop_compliance": _change_rows(db, capa_only=False, limit=40),
            "capa_aging_widget": _change_rows(db, capa_only=True),
            "deviation_heatmap": changes,
            "qa_investigations": changes,
            "capa_queue": _change_rows(db, capa_only=True),
            "deviations": changes,
            "role_tasks": task_rows,
        }
    if role.role_name == "Vendor Operations Analyst":
        vendors = _vendor_rows(db)
        return {
            "live_sla_monitor": vendors,
            "incident_heatmap": vendors,
            "vendor_status_feed": vendors,
            "escalation_timeline": task_rows,
            "sla_monitor": vendors,
            "incident_queue": vendors,
            "role_tasks": task_rows,
            "role_escalations": [row for row in task_rows if row["escalation_status"] == "Escalated"],
        }
    if role.role_name == "Operations Manager":
        workload = db.execute(
            select(Role.role_name, WorkflowTask.status, func.count(WorkflowTask.task_id))
            .join(Role, Role.role_id == WorkflowTask.assigned_role_id, isouter=True)
            .group_by(Role.role_name, WorkflowTask.status)
            .order_by(Role.role_name, WorkflowTask.status)
        ).all()
        workload_rows = [
            {"owner_role": role_name or "Unassigned", "status": task_status, "task_count": count}
            for role_name, task_status, count in workload
        ]
        return {
            "enterprise_queue_health": task_rows,
            "workforce_utilization": workload_rows,
            "escalation_feed": [row for row in task_rows if row["escalation_status"] == "Escalated"],
            "bottleneck_analysis": workload_rows,
            "workforce_analytics": workload_rows,
            "queue_management": task_rows,
            "enterprise_sla": _vendor_rows(db, limit=60),
            "role_escalations": [row for row in task_rows if row["escalation_status"] == "Escalated"],
        }
    if role.role_name == "Business Technology Analyst":
        analytics = governance_analytics(db)
        decisions = db.execute(
            select(AIDecision).order_by(desc(AIDecision.created_at)).limit(120)
        ).scalars().all()
        analytics.update(
            {
                "ai_risk_dashboard": [
                    {
                        "decision_id": item.decision_id,
                        "donor_id": item.donor_id,
                        "risk_score": item.risk_score,
                        "recommendation": item.recommendation,
                        "workflow_stage": item.workflow_stage,
                        "human_override": item.human_override,
                        "final_decision": item.final_decision,
                        "created_at": item.created_at,
                    }
                    for item in decisions
                ],
                "ai_audit_review": [
                    {
                        "decision_id": item.decision_id,
                        "donor_id": item.donor_id,
                        "triggered_rules": len(item.triggered_rules),
                        "confidence_level": item.confidence_level,
                        "human_override": item.human_override,
                        "override_reason": item.override_reason,
                    }
                    for item in decisions
                ],
            }
        )
        return analytics
    return {
        "workspace_matrix": _workspace_matrix(db),
        "role_governance": _workspace_matrix(db),
        "system_health": [
            {"component": "FastAPI", "status": "Online", "owner": "System Administrator"},
            {"component": "PostgreSQL 16", "status": "Online", "owner": "System Administrator"},
            {"component": "Workspace Engine", "status": "Configured", "owner": "System Administrator"},
        ],
    }


def workspace_payload(db: Session, current_user: User, preview_role_id: int | None = None) -> dict[str, Any]:
    active_role, is_preview = _active_role(db, current_user, preview_role_id)
    actual_role = db.get(Role, current_user.role_id)
    config = _config_for_role(db, active_role)
    navigation = list(
        db.execute(
            select(RoleNavigationConfig)
            .where(RoleNavigationConfig.role_id == active_role.role_id, RoleNavigationConfig.is_visible.is_(True))
            .order_by(RoleNavigationConfig.sort_order)
        ).scalars().all()
    )
    widgets = list(
        db.execute(
            select(RoleDashboardWidget)
            .where(RoleDashboardWidget.role_id == active_role.role_id, RoleDashboardWidget.is_enabled.is_(True))
            .order_by(RoleDashboardWidget.sort_order)
        ).scalars().all()
    )
    actions = list(
        db.execute(
            select(WorkflowTransitionRule)
            .where(
                WorkflowTransitionRule.source_role_id == active_role.role_id,
                WorkflowTransitionRule.is_active.is_(True),
            )
            .order_by(WorkflowTransitionRule.action_label)
        ).scalars().all()
    )
    notification_query = select(Notification).where(Notification.user_id == current_user.user_id)
    if config.notification_types:
        notification_query = notification_query.where(Notification.notification_type.in_(config.notification_types + ["System", "Escalation"]))
    notifications = list(
        db.execute(notification_query.order_by(desc(Notification.created_at)).limit(12)).scalars().all()
    )
    return {
        "active_role": active_role.role_name,
        "active_role_id": active_role.role_id,
        "actual_role": actual_role.role_name if actual_role else active_role.role_name,
        "is_preview": is_preview,
        "workspace": config,
        "navigation": navigation,
        "widgets": widgets,
        "kpis": _workspace_kpis(db, active_role, current_user),
        "widget_data": _widget_data(db, active_role, current_user),
        "allowed_actions": actions,
        "queue": _role_tasks(db, active_role, current_user, include_all=active_role.role_name == "Operations Manager"),
        "notifications": notifications,
    }


def execute_transition(
    db: Session,
    *,
    current_user: User,
    action_name: str,
    related_record_type: str,
    related_record_id: str,
    task_id: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    rule = db.execute(
        select(WorkflowTransitionRule).where(
            WorkflowTransitionRule.action_name == action_name,
            WorkflowTransitionRule.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow transition not found")

    permissions = _permissions_for_user(db, current_user)
    if current_user.role_id != rule.source_role_id and "system.admin" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Transition is not allowed for this role")

    task = db.get(WorkflowTask, task_id) if task_id else None
    old_task_value = serialize_model(task, TASK_FIELDS) if task else None
    if task:
        task.workflow_state = rule.to_state
        task.status = "Completed" if rule.to_state in TERMINAL_STATES else "In Progress"
        if rule.to_state in TERMINAL_STATES:
            task.completed_at = datetime.now(UTC)

    if related_record_type == "DonorReview":
        donor = db.get(DonorReview, int(related_record_id))
        if donor:
            donor.intake_status = rule.to_state if rule.to_state not in TERMINAL_STATES else rule.to_state
            donor.updated_at = datetime.now(UTC)
            if rule.to_state in {"Approved", "Rejected"}:
                donor.reviewed_at = datetime.now(UTC)
                donor.reviewer_id = current_user.user_id
                if rule.to_state == "Rejected" and note:
                    donor.rejection_reason = note

    new_task = None
    target_role = db.get(Role, rule.target_role_id) if rule.target_role_id else None
    if target_role and rule.to_state not in TERMINAL_STATES:
        target_config = _config_for_role(db, target_role)
        due_date = datetime.now(UTC) + timedelta(hours=rule.sla_hours)
        priority = task.priority if task else "High"
        if action_name.startswith("escalate") or "Escalation" in rule.task_type:
            priority = "Critical"
        new_task = WorkflowTask(
            task_type=rule.task_type,
            title=f"{rule.action_label}: {related_record_type} {related_record_id}",
            description=note or f"Workflow routed from {rule.from_state} to {rule.to_state}.",
            assigned_role_id=target_role.role_id,
            priority=priority,
            status="Assigned",
            workflow_state=rule.to_state,
            queue_name=target_config.default_queue,
            due_date=due_date if rule.sla_hours > 0 else None,
            related_record_id=related_record_id,
            related_record_type=related_record_type,
            escalation_level=1 if "Escalation" in rule.task_type else 0,
        )
        db.add(new_task)
        db.flush()
        notify_role(
            db,
            role_name=target_role.role_name,
            title=rule.notification_type,
            message=f"{rule.action_label} routed {related_record_type} {related_record_id} to {target_config.default_queue}.",
            notification_type=rule.notification_type,
            priority=priority,
            related_record_type=related_record_type,
            related_record_id=related_record_id,
            action_route=target_config.visible_tabs[0]["page_key"] if target_config.visible_tabs else "role_tasks",
        )

    log_audit(
        db,
        user_id=current_user.user_id,
        action_type=rule.audit_action,
        table_name="workflow_transition_rule",
        record_id=action_name,
        old_value=old_task_value,
        new_value={
            "action": action_name,
            "from_state": rule.from_state,
            "to_state": rule.to_state,
            "related_record_type": related_record_type,
            "related_record_id": related_record_id,
            "new_task_id": new_task.task_id if new_task else None,
            "note": note,
        },
        entity_type=related_record_type,
        entity_id=related_record_id,
    )
    db.commit()
    if new_task:
        db.refresh(new_task)
    if task:
        db.refresh(task)
    return {
        "action": action_name,
        "from_state": rule.from_state,
        "to_state": rule.to_state,
        "updated_task_id": task.task_id if task else None,
        "created_task_id": new_task.task_id if new_task else None,
    }
