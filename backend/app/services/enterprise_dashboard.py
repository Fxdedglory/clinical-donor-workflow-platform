from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    ChangeControl,
    EscalationEvent,
    Notification,
    SOPTrainingAssignment,
    User,
    VendorIncident,
    WorkflowTask,
)


def enterprise_metrics(db: Session) -> dict:
    task_rows = db.execute(
        select(
            WorkflowTask.status,
            WorkflowTask.priority,
            func.count(WorkflowTask.task_id),
            func.avg(func.extract("epoch", func.now() - WorkflowTask.created_at) / 3600),
        )
        .group_by(WorkflowTask.status, WorkflowTask.priority)
        .order_by(WorkflowTask.status, WorkflowTask.priority)
    ).all()

    user_workload = db.execute(
        select(
            User.full_name,
            User.role,
            func.count(WorkflowTask.task_id),
            func.sum(case((WorkflowTask.status == "Completed", 1), else_=0)),
        )
        .join(WorkflowTask, WorkflowTask.assigned_to_user_id == User.user_id, isouter=True)
        .group_by(User.full_name, User.role)
        .order_by(User.role, User.full_name)
    ).all()

    escalations = db.execute(
        select(EscalationEvent.status, func.count(EscalationEvent.escalation_id))
        .group_by(EscalationEvent.status)
        .order_by(EscalationEvent.status)
    ).all()

    now = datetime.now(UTC)
    training = db.execute(
        select(
            SOPTrainingAssignment.acknowledgment_status,
            func.count(SOPTrainingAssignment.assignment_id),
            func.sum(
                case(
                    (
                        (SOPTrainingAssignment.due_date < now)
                        & (SOPTrainingAssignment.acknowledgment_status.not_in(["Completed", "Acknowledged"])),
                        1,
                    ),
                    else_=0,
                )
            ),
        )
        .group_by(SOPTrainingAssignment.acknowledgment_status)
        .order_by(SOPTrainingAssignment.acknowledgment_status)
    ).all()

    compliance_counts = db.execute(
        select(
            func.count(ChangeControl.change_id),
            func.sum(case((ChangeControl.capa_required.is_(True), 1), else_=0)),
            func.sum(case((ChangeControl.approval_status.in_(["Draft", "Investigation", "Pending Approval"]), 1), else_=0)),
        )
    ).one()

    vendor_counts = db.execute(
        select(
            func.count(VendorIncident.incident_id),
            func.sum(case((VendorIncident.status == "Open", 1), else_=0)),
            func.sum(case((VendorIncident.sla_breached.is_(True), 1), else_=0)),
        )
    ).one()

    unread_notifications = db.execute(
        select(func.count(Notification.notification_id)).where(Notification.is_read.is_(False))
    ).scalar() or 0
    recent_audit_count = db.execute(select(func.count(AuditLog.audit_id))).scalar() or 0

    return {
        "kpis": {
            "open_tasks": sum(row[2] for row in task_rows if row[0] != "Completed"),
            "escalated_tasks": sum(row[2] for row in task_rows if row[0] == "Escalated"),
            "unread_notifications": unread_notifications,
            "open_change_controls": int(compliance_counts[2] or 0),
            "open_vendor_incidents": int(vendor_counts[1] or 0),
            "sla_breaches": int(vendor_counts[2] or 0),
            "audit_events": recent_audit_count,
        },
        "tasks_by_status": [
            {
                "status": row[0],
                "priority": row[1],
                "count": row[2],
                "avg_age_hours": round(float(row[3] or 0), 1),
            }
            for row in task_rows
        ],
        "workload_by_user": [
            {
                "user": row[0],
                "role": row[1],
                "task_count": row[2],
                "completed_count": int(row[3] or 0),
            }
            for row in user_workload
        ],
        "escalations": [{"status": row[0], "count": row[1]} for row in escalations],
        "training": [
            {
                "status": row[0],
                "count": row[1],
                "overdue_count": int(row[2] or 0),
            }
            for row in training
        ],
        "compliance": {
            "change_controls": int(compliance_counts[0] or 0),
            "capa_required": int(compliance_counts[1] or 0),
            "open_investigations": int(compliance_counts[2] or 0),
        },
    }

