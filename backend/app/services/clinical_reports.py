from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_user_permissions
from app.models import (
    Appointment,
    ClinicalAdverseEvent,
    ClinicalCarePlan,
    ClinicalCarePlanTask,
    ClinicalCharge,
    ClinicalClaim,
    ClinicalComplianceExport,
    ClinicalDeferral,
    ClinicalDenial,
    ClinicalEncounter,
    ClinicalEncounterNote,
    ClinicalOrder,
    ClinicalOrderResult,
    ClinicalPayment,
    ClinicalQualityEvent,
    ClinicalQualityInvestigation,
    ClinicalReportExport,
    ClinicalReportExportItem,
    ClinicalReportStatusHistory,
    ClinicalScreeningOutcome,
    ClinicalScreeningSession,
    Patient,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_reports import (
    AnalyticsExportCommitRequest,
    AnalyticsExportCommitResponse,
    AnalyticsExportItemResponse,
    AnalyticsExportPreviewRequest,
    AnalyticsExportPreviewResponse,
    AnalyticsExportResponse,
    AuditActivityReportResponse,
    BillingWorkQueueReportResponse,
    CarePlanAgingReportResponse,
    ClinicalReportsDashboardResponse,
    DeferralReportResponse,
    EncounterVolumeReportResponse,
    OrdersResultsReportResponse,
    PatientThroughputReportResponse,
    QualityTrendsReportResponse,
    ReportFilterRequest,
    ReportMetricCard,
    ReportSeriesPoint,
    ReportWarning,
    SchedulingUtilizationReportResponse,
    ScreeningOutcomesReportResponse,
)
from app.services.clinical_patients import actor_label
from app.services.clinical_workflows import (
    append_workflow_operation,
    preview_hash,
    read_workflow_operations,
)

REPORT_READ_PERMISSIONS = {
    "system.admin",
    "reports.read",
    "reports.export",
    "dashboard.view",
    "audit.review",
    "quality.export",
    "clinical_admin.read",
}
REPORT_EXPORT_PERMISSIONS = {"system.admin", "reports.export", "quality.export", "audit.review", "clinical_admin.manage"}
EXTERNAL_ROLES = {"Partner External User", "Supplier External User"}
DEFAULT_EXPORT_MODULES = [
    "patient_throughput",
    "scheduling_utilization",
    "screening_outcomes",
    "deferrals",
    "encounter_volume",
    "orders_results",
    "care_plan_aging",
    "billing_work_queue",
    "quality_trends",
    "audit_activity",
]


def now_utc() -> datetime:
    return datetime.now(UTC)


def reports_actor(user: User) -> str:
    return actor_label(user)


def is_external_user(user: User) -> bool:
    return bool(
        user.is_external
        or user.external_user_flag
        or user.account_type in {"partner", "supplier", "external"}
        or user.user_type in {"partner", "supplier", "external"}
        or user.role in EXTERNAL_ROLES
    )


def permission_set(db: Session, user: User) -> set[str]:
    return set(getattr(user, "permissions", []) or []) | set(get_user_permissions(db, user))


def _warning(warning_type: str, message: str, field: str | None = None) -> ReportWarning:
    return ReportWarning(warning_type=warning_type, message=message, field=field)


def _all_rows(db: Session, model: type, include_deleted: bool = False) -> list[Any]:
    statement = select(model)
    if hasattr(model, "is_deleted") and not include_deleted:
        statement = statement.where(model.is_deleted.is_(False))
    return list(db.execute(statement).scalars().all())


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _in_range(value: Any, filters: ReportFilterRequest) -> bool:
    value_date = _as_date(value)
    if filters.date_from and (value_date is None or value_date < filters.date_from):
        return False
    if filters.date_to and (value_date is None or value_date > filters.date_to):
        return False
    return True


def _filter_by_date(rows: list[Any], filters: ReportFilterRequest, *attrs: str) -> list[Any]:
    if not filters.date_from and not filters.date_to:
        return rows
    filtered = []
    for row in rows:
        values = [getattr(row, attr, None) for attr in attrs]
        if any(_in_range(value, filters) for value in values if value is not None):
            filtered.append(row)
    return filtered


def _filter_status(rows: list[Any], filters: ReportFilterRequest) -> list[Any]:
    if not filters.status:
        return rows
    return [row for row in rows if getattr(row, "status", None) == filters.status]


def _counter(rows: list[Any], attr: str, fallback: str = "unknown") -> dict[str, int]:
    return dict(Counter(str(getattr(row, attr, None) or fallback) for row in rows))


def _series_by_date(rows: list[Any], attr: str) -> list[ReportSeriesPoint]:
    counts: dict[date, int] = defaultdict(int)
    for row in rows:
        value = _as_date(getattr(row, attr, None))
        if value:
            counts[value] += 1
    return [ReportSeriesPoint(label=item.isoformat(), date=item, value=count) for item, count in sorted(counts.items())]


def _sum(rows: list[Any], attr: str) -> float:
    return round(sum(float(getattr(row, attr, 0) or 0) for row in rows), 2)


def _patient_id(row: Any) -> str:
    return getattr(row, "patient_id", None) or str(getattr(row, "patient_pk", ""))


def _report_filters(filters: ReportFilterRequest) -> dict[str, Any]:
    return filters.model_dump(mode="json", exclude_none=True)


def patient_throughput_report(db: Session, filters: ReportFilterRequest) -> PatientThroughputReportResponse:
    all_patients = _all_rows(db, Patient)
    patients = _filter_status(_filter_by_date(all_patients, filters, "created_at", "updated_at"), filters)
    status_counts = _counter(all_patients if not filters.status else patients, "status")
    duplicate_warning_count = 0
    metrics = [
        ReportMetricCard(label="Total patients / donors", value=len(all_patients)),
        ReportMetricCard(label="New registrations", value=len(patients)),
        ReportMetricCard(label="Active", value=status_counts.get("active", 0), tone="success"),
        ReportMetricCard(label="Deferred", value=status_counts.get("deferred", 0), tone="warning"),
    ]
    return PatientThroughputReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=metrics,
        status_counts=status_counts,
        registrations_by_date=_series_by_date(patients, "created_at"),
        duplicate_warning_count=duplicate_warning_count,
        warnings=[_warning("not_persisted", "Duplicate warnings are preview-only and are not persisted as reportable rows.")],
    )


def scheduling_utilization_report(db: Session, filters: ReportFilterRequest) -> SchedulingUtilizationReportResponse:
    appointments = _filter_status(_filter_by_date(_all_rows(db, Appointment), filters, "scheduled_start", "created_at"), filters)
    status_counts = _counter(appointments, "status")
    by_provider: dict[str, dict[str, Any]] = {}
    type_counts: Counter[str] = Counter()
    for appt in appointments:
        provider_key = str(getattr(appt, "provider_id", "unknown"))
        duration_minutes = 0
        if getattr(appt, "scheduled_start", None) and getattr(appt, "scheduled_end", None):
            duration_minutes = max(0, int((appt.scheduled_end - appt.scheduled_start).total_seconds() // 60))
        by_provider.setdefault(provider_key, {"provider_id": getattr(appt, "provider_id", None), "appointments": 0, "scheduled_minutes": 0})
        by_provider[provider_key]["appointments"] += 1
        by_provider[provider_key]["scheduled_minutes"] += duration_minutes
        type_name = getattr(appt, "appointment_type_name", None) or str(getattr(appt, "appointment_type_id", "unknown"))
        type_counts[type_name] += 1
    return SchedulingUtilizationReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Scheduled appointments", value=status_counts.get("scheduled", 0)),
            ReportMetricCard(label="Checked in", value=status_counts.get("checked_in", 0), tone="success"),
            ReportMetricCard(label="Cancelled", value=status_counts.get("cancelled", 0), tone="warning"),
            ReportMetricCard(label="No-shows", value=status_counts.get("no_show", 0), tone="warning"),
        ],
        status_counts=status_counts,
        provider_utilization=sorted(by_provider.values(), key=lambda item: str(item["provider_id"])),
        appointment_type_breakdown=dict(type_counts),
    )


def screening_outcomes_report(db: Session, filters: ReportFilterRequest) -> ScreeningOutcomesReportResponse:
    sessions = _filter_status(_filter_by_date(_all_rows(db, ClinicalScreeningSession), filters, "started_at", "completed_at", "created_at"), filters)
    outcomes = _filter_by_date(_all_rows(db, ClinicalScreeningOutcome), filters, "created_at")
    outcome_counts = Counter(outcome.committed_outcome or outcome.proposed_outcome or "unknown" for outcome in outcomes)
    deferral_type_counts = Counter(outcome.deferral_type or "none" for outcome in outcomes if outcome.deferral_type)
    supervisor_review_count = sum(1 for session in sessions if session.supervisor_review_required) + sum(1 for outcome in outcomes if outcome.supervisor_review_required)
    override_count = sum(1 for outcome in outcomes if outcome.override_outcome)
    return ScreeningOutcomesReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Screening sessions", value=len(sessions)),
            ReportMetricCard(label="Eligible", value=outcome_counts.get("eligible", 0), tone="success"),
            ReportMetricCard(label="Eligible with conditions", value=outcome_counts.get("eligible_with_conditions", 0), tone="warning"),
            ReportMetricCard(label="Supervisor review", value=supervisor_review_count, tone="warning"),
        ],
        status_counts=_counter(sessions, "status"),
        outcome_counts={**dict(outcome_counts), **{f"deferral_{key}": value for key, value in deferral_type_counts.items()}},
        supervisor_review_count=supervisor_review_count,
        override_count=override_count,
    )


def deferral_report(db: Session, filters: ReportFilterRequest) -> DeferralReportResponse:
    deferrals = _filter_status(_filter_by_date(_all_rows(db, ClinicalDeferral), filters, "starts_at", "created_at"), filters)
    type_counts = _counter(deferrals, "deferral_type")
    reason_counts = dict(Counter((deferral.reason or "unspecified")[:80] for deferral in deferrals))
    context = [
        {
            "deferral_number": deferral.deferral_number,
            "patient_id": _patient_id(deferral),
            "deferral_type": deferral.deferral_type,
            "status": deferral.status,
            "starts_at": deferral.starts_at.isoformat() if deferral.starts_at else None,
            "ends_at": deferral.ends_at.isoformat() if deferral.ends_at else None,
        }
        for deferral in deferrals[:25]
    ]
    return DeferralReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Active deferrals", value=sum(1 for item in deferrals if item.status == "active"), tone="warning"),
            ReportMetricCard(label="Temporary", value=type_counts.get("temporary", 0)),
            ReportMetricCard(label="Permanent", value=type_counts.get("permanent", 0), tone="danger"),
            ReportMetricCard(label="Patient-linked", value=sum(1 for item in deferrals if item.patient_pk)),
        ],
        status_counts=_counter(deferrals, "status"),
        type_counts=type_counts,
        reason_counts=reason_counts,
        patient_context=context,
    )


def encounter_volume_report(db: Session, filters: ReportFilterRequest) -> EncounterVolumeReportResponse:
    encounters = _filter_status(_filter_by_date(_all_rows(db, ClinicalEncounter), filters, "started_at", "created_at"), filters)
    notes = _filter_by_date(_all_rows(db, ClinicalEncounterNote), filters, "signed_at", "created_at")
    signed_count = sum(1 for note in notes if note.status == "signed")
    amended_count = sum(1 for note in notes if note.status == "amended" or note.is_addendum)
    draft_count = sum(1 for encounter in encounters if encounter.status in {"draft", "in_progress"})
    return EncounterVolumeReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Encounters", value=len(encounters)),
            ReportMetricCard(label="Signed notes", value=signed_count, tone="success"),
            ReportMetricCard(label="Amended notes", value=amended_count, tone="warning"),
            ReportMetricCard(label="Draft / in-progress", value=draft_count, tone="warning"),
        ],
        status_counts=_counter(encounters, "status"),
        note_status_counts=_counter(notes, "status"),
        signing_activity=_series_by_date([note for note in notes if note.signed_at], "signed_at"),
    )


def orders_results_report(db: Session, filters: ReportFilterRequest) -> OrdersResultsReportResponse:
    orders = _filter_status(_filter_by_date(_all_rows(db, ClinicalOrder), filters, "ordered_at", "created_at"), filters)
    results = _filter_by_date(_all_rows(db, ClinicalOrderResult), filters, "resulted_at", "created_at")
    pending_results = sum(1 for order in orders if not getattr(order, "results", []))
    abnormal_results = sum(1 for result in results if result.abnormal_flag)
    unacknowledged = sum(1 for order in orders if getattr(order, "has_critical_unacknowledged", False))
    return OrdersResultsReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Orders", value=len(orders)),
            ReportMetricCard(label="Pending results", value=pending_results, tone="warning"),
            ReportMetricCard(label="Abnormal results", value=abnormal_results, tone="warning"),
            ReportMetricCard(label="Critical unacknowledged", value=unacknowledged, tone="danger"),
        ],
        order_status_counts=_counter(orders, "status"),
        result_status_counts=_counter(results, "result_status"),
    )


def care_plan_aging_report(db: Session, filters: ReportFilterRequest) -> CarePlanAgingReportResponse:
    plans = _filter_status(_filter_by_date(_all_rows(db, ClinicalCarePlan), filters, "start_date", "created_at"), filters)
    tasks = _filter_by_date(_all_rows(db, ClinicalCarePlanTask), filters, "due_date", "created_at")
    today = date.today()
    open_tasks = [task for task in tasks if task.status not in {"completed", "cancelled", "closed"}]
    overdue_tasks = [task for task in open_tasks if task.due_date and task.due_date < today]
    linked_flagged = sum(1 for plan in plans if getattr(plan, "result_flag", "none") in {"abnormal", "critical"})
    return CarePlanAgingReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Active care plans", value=sum(1 for plan in plans if plan.status == "active"), tone="success"),
            ReportMetricCard(label="Closed care plans", value=sum(1 for plan in plans if plan.status == "closed")),
            ReportMetricCard(label="Overdue tasks", value=len(overdue_tasks), tone="danger" if overdue_tasks else "neutral"),
            ReportMetricCard(label="Linked abnormal / critical", value=linked_flagged, tone="warning"),
        ],
        status_counts=_counter(plans, "status"),
        task_status_counts=_counter(tasks, "status"),
        priority_counts=_counter(tasks, "priority"),
    )


def billing_work_queue_report(db: Session, filters: ReportFilterRequest) -> BillingWorkQueueReportResponse:
    charges = _filter_status(_filter_by_date(_all_rows(db, ClinicalCharge), filters, "service_date", "created_at"), filters)
    claims = _filter_status(_filter_by_date(_all_rows(db, ClinicalClaim), filters, "submitted_at", "created_at"), filters)
    payments = _filter_by_date(_all_rows(db, ClinicalPayment), filters, "posted_at", "created_at")
    denials = _filter_status(_filter_by_date(_all_rows(db, ClinicalDenial), filters, "due_date", "created_at"), filters)
    open_denials = [denial for denial in denials if denial.status not in {"resolved", "closed", "cancelled"}]
    return BillingWorkQueueReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Charges", value=len(charges)),
            ReportMetricCard(label="Claim balance", value=_sum(claims, "balance"), tone="warning"),
            ReportMetricCard(label="Denied claims", value=sum(1 for claim in claims if claim.status == "denied"), tone="warning"),
            ReportMetricCard(label="Open denials", value=len(open_denials), tone="danger" if open_denials else "neutral"),
        ],
        claim_status_counts=_counter(claims, "status"),
        charge_status_counts=_counter(charges, "status"),
        denial_status_counts=_counter(denials, "status"),
        balances={
            "charges": _sum(charges, "total_amount"),
            "claim_total": _sum(claims, "total_amount"),
            "claim_balance": _sum(claims, "balance"),
            "payments_posted": _sum(payments, "payment_amount"),
            "adjustments_posted": _sum(payments, "adjustment_amount"),
        },
    )


def quality_trends_report(db: Session, filters: ReportFilterRequest) -> QualityTrendsReportResponse:
    events = _filter_status(_filter_by_date(_all_rows(db, ClinicalQualityEvent), filters, "due_date", "created_at"), filters)
    adverse_events = _filter_by_date(_all_rows(db, ClinicalAdverseEvent), filters, "event_at", "created_at")
    investigations = _filter_by_date(_all_rows(db, ClinicalQualityInvestigation), filters, "created_at")
    exports = _filter_by_date(_all_rows(db, ClinicalComplianceExport), filters, "generated_at", "created_at")
    return QualityTrendsReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Quality events", value=len(events)),
            ReportMetricCard(label="Adverse events", value=len(adverse_events), tone="warning"),
            ReportMetricCard(label="Open investigations", value=len(investigations), tone="warning"),
            ReportMetricCard(label="CAPA-linked events", value=sum(1 for event in events if event.capa_id), tone="success"),
            ReportMetricCard(label="Compliance exports", value=len(exports)),
        ],
        severity_counts=_counter(events, "severity"),
        status_counts=_counter(events, "status"),
        category_counts=_counter(events, "category"),
    )


def _parse_operation_timestamp(operation: dict[str, Any]) -> datetime | None:
    value = operation.get("timestamp")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _operation_matches(operation: dict[str, Any], filters: ReportFilterRequest) -> bool:
    timestamp = _parse_operation_timestamp(operation)
    if filters.date_from or filters.date_to:
        if timestamp is None or not _in_range(timestamp, filters):
            return False
    if filters.actor and filters.actor.lower() not in str(operation.get("actor", "")).lower():
        return False
    if filters.workflow and filters.workflow not in str(operation.get("workflow", "")):
        return False
    if filters.entity_type and operation.get("entity_type") != filters.entity_type:
        return False
    if filters.entity_id and operation.get("entity_id") != filters.entity_id:
        return False
    if filters.module and not str(operation.get("workflow", "")).startswith(filters.module):
        return False
    return True


def audit_activity_report(db: Session, filters: ReportFilterRequest) -> AuditActivityReportResponse:
    operations = [operation for operation in read_workflow_operations(db=db) if _operation_matches(operation, filters)]
    return AuditActivityReportResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        filters=_report_filters(filters),
        metrics=[
            ReportMetricCard(label="Workflow audit events", value=len(operations)),
            ReportMetricCard(label="Unique workflows", value=len(set(operation.get("workflow") for operation in operations))),
            ReportMetricCard(label="Unique actors", value=len(set(operation.get("actor") for operation in operations))),
            ReportMetricCard(label="Committed operations", value=sum(1 for operation in operations if operation.get("commit_confirmed") is True), tone="success"),
        ],
        total_operations=len(operations),
        workflow_counts=dict(Counter(str(operation.get("workflow", "unknown")) for operation in operations)),
        actor_counts=dict(Counter(str(operation.get("actor", "unknown")) for operation in operations)),
        entity_type_counts=dict(Counter(str(operation.get("entity_type", "unknown")) for operation in operations)),
        operations=operations[-50:],
    )


def dashboard_response(db: Session, filters: ReportFilterRequest) -> ClinicalReportsDashboardResponse:
    patient_report = patient_throughput_report(db, filters)
    scheduling_report = scheduling_utilization_report(db, filters)
    screening_report = screening_outcomes_report(db, filters)
    orders_report = orders_results_report(db, filters)
    billing_report = billing_work_queue_report(db, filters)
    quality_report = quality_trends_report(db, filters)
    audit_report = audit_activity_report(db, filters)
    return ClinicalReportsDashboardResponse(
        date_from=filters.date_from,
        date_to=filters.date_to,
        metrics=[
            ReportMetricCard(label="Patients / donors", value=patient_report.metrics[0].value),
            ReportMetricCard(label="Appointments", value=sum(scheduling_report.status_counts.values())),
            ReportMetricCard(label="Screening sessions", value=sum(screening_report.status_counts.values())),
            ReportMetricCard(label="Orders", value=orders_report.metrics[0].value),
            ReportMetricCard(label="Claim balance", value=billing_report.balances.get("claim_balance", 0), tone="warning"),
            ReportMetricCard(label="Quality events", value=quality_report.metrics[0].value),
        ],
        module_counts={
            "patient_throughput": patient_report.metrics[0].value,
            "scheduling_utilization": sum(scheduling_report.status_counts.values()),
            "screening_outcomes": sum(screening_report.status_counts.values()),
            "orders_results": orders_report.metrics[0].value,
            "billing_work_queue": billing_report.balances.get("claim_balance", 0),
            "quality_trends": quality_report.metrics[0].value,
            "audit_activity": audit_report.total_operations,
        },
        recent_audit_operations=audit_report.operations[-8:],
        warnings=[
            _warning("aggregate_scope", "Reports avoid unnecessary PHI and expose aggregate-ready JSON contracts."),
        ],
    )


REPORT_FUNCTIONS = {
    "patient_throughput": patient_throughput_report,
    "scheduling_utilization": scheduling_utilization_report,
    "screening_outcomes": screening_outcomes_report,
    "deferrals": deferral_report,
    "encounter_volume": encounter_volume_report,
    "orders_results": orders_results_report,
    "care_plan_aging": care_plan_aging_report,
    "billing_work_queue": billing_work_queue_report,
    "quality_trends": quality_trends_report,
    "audit_activity": audit_activity_report,
}


def _export_filters(payload: AnalyticsExportPreviewRequest) -> ReportFilterRequest:
    return ReportFilterRequest(
        date_from=payload.date_from,
        date_to=payload.date_to,
        status=payload.status,
        module=payload.module,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        actor=payload.actor,
        workflow=payload.workflow,
    )


def export_row_counts(db: Session, payload: AnalyticsExportPreviewRequest) -> dict[str, int]:
    filters = _export_filters(payload)
    modules = payload.modules or DEFAULT_EXPORT_MODULES
    counts: dict[str, int] = {}
    for module in modules:
        report_func = REPORT_FUNCTIONS.get(module)
        if not report_func:
            counts[module] = 0
            continue
        report = report_func(db, filters)
        metrics_total = sum(int(metric.value) for metric in report.metrics if isinstance(metric.value, int))
        counts[module] = max(metrics_total, sum(getattr(report, "status_counts", {}).values()) if hasattr(report, "status_counts") else 0)
    return counts


def analytics_export_preview(db: Session, payload: AnalyticsExportPreviewRequest) -> AnalyticsExportPreviewResponse:
    modules = payload.modules or DEFAULT_EXPORT_MODULES
    unknown = [module for module in modules if module not in REPORT_FUNCTIONS]
    row_counts = export_row_counts(db, payload)
    warnings = [
        _warning("foundation_scope", "Export stores metadata and row-count contracts only; external warehouse upload is planned.")
    ]
    if payload.include_detail:
        warnings.append(_warning("detail_scope", "Detail export is metadata-only in Sprint 11 and remains RBAC protected.", "include_detail"))
    return AnalyticsExportPreviewResponse(
        preview_hash=preview_hash({"workflow": "reports.analytics_export", "payload": payload.model_dump(mode="json")}),
        summary=f"Analytics export preview includes {len(modules)} report modules.",
        modules=modules,
        date_from=payload.date_from,
        date_to=payload.date_to,
        filters=payload.model_dump(mode="json", exclude_none=True),
        row_counts=row_counts,
        export_format=payload.export_format,
        warnings=warnings,
        blocking_issues=[
            {"issue_type": "unknown_module", "message": f"Unsupported report module: {module}", "field": "modules"}
            for module in unknown
        ],
    )


def new_report_export_number() -> str:
    return f"REXP-{uuid4().hex[:10].upper()}"


def _append_report_status_history(
    export: ClinicalReportExport,
    *,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    export.status_history.append(
        ClinicalReportStatusHistory(
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            reason=reason,
            notes=notes,
        )
    )


def _export_response(export: ClinicalReportExport) -> AnalyticsExportResponse:
    return AnalyticsExportResponse(
        export_id=export.export_id,
        export_number=export.export_number,
        modules=export.modules,
        filters=export.filters,
        date_from=export.date_from,
        date_to=export.date_to,
        export_format=export.export_format,
        row_counts=export.row_counts,
        payload_metadata=export.payload_metadata,
        status=export.status,
        generated_at=export.generated_at,
        generated_by=export.generated_by,
        items=[AnalyticsExportItemResponse.model_validate(item) for item in export.items],
    )


def list_analytics_exports(db: Session) -> list[AnalyticsExportResponse]:
    rows = list(
        db.execute(select(ClinicalReportExport).where(ClinicalReportExport.is_deleted.is_(False))).scalars().all()
    )
    rows.sort(key=lambda row: row.generated_at or row.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)
    return [_export_response(row) for row in rows]


def commit_analytics_export(
    db: Session,
    payload: AnalyticsExportCommitRequest,
    user: User,
) -> AnalyticsExportCommitResponse:
    preview = analytics_export_preview(db, payload)
    if preview.blocking_issues:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"status": "report_validation_failed", "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues]})
    generated_at = now_utc()
    modules = payload.modules or DEFAULT_EXPORT_MODULES
    export = ClinicalReportExport(
        export_number=new_report_export_number(),
        modules=modules,
        filters=payload.model_dump(mode="json", exclude_none=True),
        date_from=payload.date_from,
        date_to=payload.date_to,
        export_format=payload.export_format,
        row_counts=preview.row_counts,
        payload_metadata={
            "format": payload.export_format,
            "include_detail": payload.include_detail,
            "csv_ready": payload.export_format == "csv",
            "external_delivery": "planned",
        },
        status="generated",
        generated_at=generated_at,
        generated_by=user.user_id,
        created_at=generated_at,
        created_by=user.user_id,
    )
    export.items = [
        ClinicalReportExportItem(
            module=module,
            report_name=module.replace("_", " ").title(),
            row_count=preview.row_counts.get(module, 0),
            payload_metadata={"contract": "aggregate_json", "detail_included": payload.include_detail},
        )
        for module in modules
    ]
    _append_report_status_history(export, from_status=None, to_status="generated", user_id=user.user_id, reason=payload.reason, notes="Analytics export metadata generated")
    db.add(export)
    db.flush()
    db.commit()
    db.refresh(export)
    operation = WorkflowOperation(
        workflow="reports.analytics_export",
        entity_type="clinical_report_export",
        entity_id=export.export_number,
        actor=reports_actor(user),
        preview_hash=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=export.status,
        reason=payload.reason,
        changes={
            "modules": modules,
            "date_from": payload.date_from.isoformat() if payload.date_from else None,
            "date_to": payload.date_to.isoformat() if payload.date_to else None,
            "row_counts": preview.row_counts,
            "export_format": payload.export_format,
        },
    )
    operation, audit_path = append_workflow_operation(operation, db=db)
    return AnalyticsExportCommitResponse(operation_id=operation.operation_id, audit_path=str(audit_path), export=_export_response(export))
