from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.clinical_reports import (
    AnalyticsExportCommitRequest,
    AnalyticsExportCommitResponse,
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
    SchedulingUtilizationReportResponse,
    ScreeningOutcomesReportResponse,
)
from app.services.clinical_reports import (
    REPORT_EXPORT_PERMISSIONS,
    REPORT_READ_PERMISSIONS,
    apply_small_cell_suppression,
    analytics_export_preview,
    audit_activity_report,
    billing_work_queue_report,
    care_plan_aging_report,
    commit_analytics_export,
    dashboard_response,
    deferral_report,
    encounter_volume_report,
    is_external_user,
    list_analytics_exports,
    orders_results_report,
    patient_throughput_report,
    permission_set,
    quality_trends_report,
    scheduling_utilization_report,
    screening_outcomes_report,
)
from app.services.clinical_phi import export_profile_denial_reason
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical/reports", tags=["Clinical Reports"])


def require_reports_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access clinical reports")
    if permission_set(db, current_user).isdisjoint(REPORT_READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical reports read permission required")
    return current_user


def require_reports_export(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot generate analytics exports")
    if permission_set(db, current_user).isdisjoint(REPORT_EXPORT_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical reports export permission required")
    return current_user


def report_filters(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    module: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    workflow: str | None = Query(default=None),
    export_profile: str = Query(default="aggregate_safe"),
) -> ReportFilterRequest:
    return ReportFilterRequest(
        date_from=date_from,
        date_to=date_to,
        status=status_filter,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        workflow=workflow,
        export_profile=export_profile,
    )


def _enforce_report_export_profile(profile: str, current_user: User, db: Session) -> None:
    try:
        reason = export_profile_denial_reason(profile, current_user, permission_set(db, current_user))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if reason:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)


@router.get("/dashboard", response_model=ClinicalReportsDashboardResponse)
def get_reports_dashboard(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> ClinicalReportsDashboardResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(dashboard_response(db, filters), filters.export_profile)


@router.get("/patient-throughput", response_model=PatientThroughputReportResponse)
def get_patient_throughput_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> PatientThroughputReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(patient_throughput_report(db, filters), filters.export_profile)


@router.get("/scheduling-utilization", response_model=SchedulingUtilizationReportResponse)
def get_scheduling_utilization_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> SchedulingUtilizationReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(scheduling_utilization_report(db, filters), filters.export_profile)


@router.get("/screening-outcomes", response_model=ScreeningOutcomesReportResponse)
def get_screening_outcomes_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> ScreeningOutcomesReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(screening_outcomes_report(db, filters), filters.export_profile)


@router.get("/deferrals", response_model=DeferralReportResponse)
def get_deferral_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> DeferralReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(deferral_report(db, filters), filters.export_profile)


@router.get("/encounter-volume", response_model=EncounterVolumeReportResponse)
def get_encounter_volume_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> EncounterVolumeReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(encounter_volume_report(db, filters), filters.export_profile)


@router.get("/orders-results", response_model=OrdersResultsReportResponse)
def get_orders_results_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> OrdersResultsReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(orders_results_report(db, filters), filters.export_profile)


@router.get("/care-plan-aging", response_model=CarePlanAgingReportResponse)
def get_care_plan_aging_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> CarePlanAgingReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(care_plan_aging_report(db, filters), filters.export_profile)


@router.get("/billing-work-queue", response_model=BillingWorkQueueReportResponse)
def get_billing_work_queue_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> BillingWorkQueueReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(billing_work_queue_report(db, filters), filters.export_profile)


@router.get("/quality-trends", response_model=QualityTrendsReportResponse)
def get_quality_trends_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> QualityTrendsReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(quality_trends_report(db, filters), filters.export_profile)


@router.get("/audit-activity", response_model=AuditActivityReportResponse)
def get_audit_activity_report(
    filters: ReportFilterRequest = Depends(report_filters),
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> AuditActivityReportResponse:
    _enforce_report_export_profile(filters.export_profile, current_user, db)
    return apply_small_cell_suppression(audit_activity_report(db, filters), filters.export_profile)


@router.get("/analytics-exports", response_model=list[AnalyticsExportResponse])
def get_analytics_exports(
    current_user: User = Depends(require_reports_read),
    db: Session = Depends(get_db),
) -> list[AnalyticsExportResponse]:
    return list_analytics_exports(db)


@router.post("/analytics-exports/preview", response_model=AnalyticsExportPreviewResponse)
def preview_analytics_export(
    payload: AnalyticsExportPreviewRequest,
    current_user: User = Depends(require_reports_export),
    db: Session = Depends(get_db),
) -> AnalyticsExportPreviewResponse:
    _enforce_report_export_profile(payload.export_profile, current_user, db)
    return analytics_export_preview(db, payload)


@router.post(
    "/analytics-exports",
    response_model=AnalyticsExportCommitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analytics_export(
    payload: AnalyticsExportCommitRequest,
    request: Request,
    current_user: User = Depends(require_reports_export),
    db: Session = Depends(get_db),
) -> AnalyticsExportCommitResponse:
    require_generation_confirmation(request)
    _enforce_report_export_profile(payload.export_profile, current_user, db)
    return commit_analytics_export(db, payload, current_user)
