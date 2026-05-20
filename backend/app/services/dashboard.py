from datetime import UTC, datetime, timedelta

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, ChangeControl, DonorReview, Vendor, VendorIncident

ACTIVE_DONOR_STATES = [
    "Draft Intake",
    "Pending Intake Validation",
    "Pending Clinical Review",
    "Clinical Review In Progress",
    "Pending Additional Information",
    "High Risk Escalation",
    "QA Investigation",
    "CAPA Investigation",
    "Clinical Re-Review",
    "Operations Escalation",
]


def get_dashboard_metrics(db: Session) -> dict:
    donor_counts = db.execute(
        select(
            func.count(DonorReview.review_id),
            func.sum(case((DonorReview.intake_status.in_(ACTIVE_DONOR_STATES), 1), else_=0)),
            func.sum(case((DonorReview.intake_status == "Approved", 1), else_=0)),
            func.sum(case((DonorReview.intake_status == "Rejected", 1), else_=0)),
            func.avg(DonorReview.risk_score),
        )
    ).one()

    total, pending, approved, rejected, avg_risk = donor_counts
    total = total or 0
    approved = approved or 0
    rejected = rejected or 0
    pending = pending or 0

    reviewed_count = approved + rejected
    approval_rate = round((approved / reviewed_count) * 100, 1) if reviewed_count else 0

    avg_review_hours = db.execute(
        select(
            func.avg(
                func.extract("epoch", DonorReview.reviewed_at - DonorReview.created_at) / 3600
            )
        ).where(DonorReview.reviewed_at.is_not(None))
    ).scalar()

    sla_rows = db.execute(
        select(
            func.count(VendorIncident.incident_id),
            func.sum(case((VendorIncident.sla_breached.is_(True), 1), else_=0)),
        )
    ).one()
    incident_count, breach_count = sla_rows
    incident_count = incident_count or 0
    breach_count = breach_count or 0
    sla_compliance = round(((incident_count - breach_count) / incident_count) * 100, 1) if incident_count else 100

    open_investigations = db.execute(
        select(func.count(ChangeControl.change_id)).where(
            ChangeControl.approval_status.in_(["Investigation", "Pending Approval", "Draft"])
        )
    ).scalar() or 0

    risk_distribution = db.execute(
        select(DonorReview.risk_level, func.count(DonorReview.review_id))
        .group_by(DonorReview.risk_level)
        .order_by(DonorReview.risk_level)
    ).all()

    status_distribution = db.execute(
        select(DonorReview.intake_status, func.count(DonorReview.review_id))
        .group_by(DonorReview.intake_status)
        .order_by(DonorReview.intake_status)
    ).all()

    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    daily_reviews = db.execute(
        select(
            func.date(DonorReview.created_at).label("review_date"),
            func.count(DonorReview.review_id),
        )
        .where(DonorReview.created_at >= seven_days_ago)
        .group_by(func.date(DonorReview.created_at))
        .order_by(func.date(DonorReview.created_at))
    ).all()

    queue_aging = db.execute(
        select(
            DonorReview.review_priority,
            func.avg(func.extract("epoch", func.now() - DonorReview.created_at) / 3600),
            func.count(DonorReview.review_id),
        )
        .where(DonorReview.intake_status.in_(ACTIVE_DONOR_STATES))
        .group_by(DonorReview.review_priority)
        .order_by(DonorReview.review_priority)
    ).all()

    top_queue = db.execute(
        select(DonorReview)
        .where(DonorReview.intake_status.in_(ACTIVE_DONOR_STATES))
        .order_by(desc(DonorReview.risk_score), DonorReview.created_at)
        .limit(10)
    ).scalars().all()

    vendor_health = db.execute(
        select(
            Vendor.vendor_name,
            Vendor.system_name,
            func.avg(VendorIncident.uptime_percent),
            func.sum(case((VendorIncident.sla_breached.is_(True), 1), else_=0)),
            func.count(VendorIncident.incident_id),
        )
        .join(VendorIncident, VendorIncident.vendor_id == Vendor.vendor_id)
        .group_by(Vendor.vendor_name, Vendor.system_name)
        .order_by(Vendor.vendor_name)
    ).all()

    recent_audit = db.execute(
        select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(8)
    ).scalars().all()

    return {
        "kpis": {
            "pending_donor_reviews": pending,
            "avg_review_time_hours": round(float(avg_review_hours or 0), 1),
            "avg_risk_score": round(float(avg_risk or 0), 1),
            "approval_rate": approval_rate,
            "sla_compliance": sla_compliance,
            "open_investigations": open_investigations,
        },
        "risk_distribution": [
            {"risk_level": row[0], "count": row[1]} for row in risk_distribution
        ],
        "status_distribution": [
            {"status": row[0], "count": row[1]} for row in status_distribution
        ],
        "daily_review_trend": [
            {"date": str(row[0]), "count": row[1]} for row in daily_reviews
        ],
        "queue_aging": [
            {
                "priority": row[0],
                "avg_age_hours": round(float(row[1] or 0), 1),
                "count": row[2],
            }
            for row in queue_aging
        ],
        "priority_queue": [
            {
                "review_id": donor.review_id,
                "donor_id": donor.donor_id,
                "donor_name": donor.donor_name,
                "risk_score": donor.risk_score,
                "risk_level": donor.risk_level,
                "review_priority": donor.review_priority,
                "intake_status": donor.intake_status,
            }
            for donor in top_queue
        ],
        "vendor_health": [
            {
                "vendor_name": row[0],
                "system_name": row[1],
                "uptime_percent": round(float(row[2] or 0), 2),
                "sla_breaches": int(row[3] or 0),
                "incident_count": row[4],
            }
            for row in vendor_health
        ],
        "recent_audit": [
            {
                "audit_id": item.audit_id,
                "action_type": item.action_type,
                "table_name": item.table_name,
                "record_id": item.record_id,
                "timestamp": item.timestamp.isoformat(),
            }
            for item in recent_audit
        ],
    }

