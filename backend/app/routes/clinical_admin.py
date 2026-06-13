from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.clinical_admin import (
    AdminConfigVersionResponse,
    ApprovalPathCommitRequest,
    ApprovalPathPreviewRequest,
    AppointmentTypeAdminCommitRequest,
    AppointmentTypeAdminPreviewRequest,
    BillingCodeCatalogCommitRequest,
    BillingCodeCatalogPreviewRequest,
    ClinicalAdminCommitResponse,
    ClinicalAdminDashboardResponse,
    ClinicalAdminPreviewResponse,
    ClinicalRbacOverviewResponse,
    DeferralRuleVersionCommitRequest,
    DeferralRuleVersionPreviewRequest,
    EligibilityRuleVersionCommitRequest,
    EligibilityRuleVersionPreviewRequest,
    NoteTemplateAdminCommitRequest,
    NoteTemplateAdminPreviewRequest,
    NotificationTemplateCommitRequest,
    NotificationTemplatePreviewRequest,
    OrderCatalogAdminCommitRequest,
    OrderCatalogAdminPreviewRequest,
    ProviderScheduleTemplateCommitRequest,
    ProviderScheduleTemplatePreviewRequest,
    QualityCategoryCommitRequest,
    QualityCategoryPreviewRequest,
    ScreeningTemplateVersionCommitRequest,
    ScreeningTemplateVersionPreviewRequest,
)
from app.services.clinical_admin import (
    ADMIN_MUTATION_PERMISSIONS,
    ADMIN_READ_PERMISSIONS,
    commit_approval_path,
    commit_appointment_type,
    commit_billing_code,
    commit_deferral_rule,
    commit_eligibility_rule,
    commit_note_template,
    commit_notification_template,
    commit_order_catalog,
    commit_provider_schedule,
    commit_quality_category,
    commit_screening_template,
    dashboard_response,
    is_external_user,
    list_approval_paths,
    list_appointment_types,
    list_billing_codes,
    list_config_versions,
    list_deferral_rules,
    list_eligibility_rules,
    list_note_templates,
    list_notification_templates,
    list_order_catalog,
    list_provider_schedules,
    list_quality_categories,
    list_screening_templates,
    permission_set,
    preview_approval_path,
    preview_appointment_type,
    preview_billing_code,
    preview_deferral_rule,
    preview_eligibility_rule,
    preview_note_template,
    preview_notification_template,
    preview_order_catalog,
    preview_provider_schedule,
    preview_quality_category,
    preview_screening_template,
    rbac_overview,
)
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical/admin", tags=["Clinical Administration"])


def require_admin_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access clinical administration")
    if permission_set(db, current_user).isdisjoint(ADMIN_READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical administration read permission required")
    return current_user


def require_admin_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate clinical administration")
    if permission_set(db, current_user).isdisjoint(ADMIN_MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical administration mutation permission required")
    return current_user


def _confirm(request: Request) -> None:
    require_generation_confirmation(request)


@router.get("/dashboard", response_model=ClinicalAdminDashboardResponse)
def get_admin_dashboard(
    current_user: User = Depends(require_admin_read),
    db: Session = Depends(get_db),
) -> ClinicalAdminDashboardResponse:
    return dashboard_response(db)


@router.get("/config-versions", response_model=list[AdminConfigVersionResponse])
def get_config_versions(
    current_user: User = Depends(require_admin_read),
    db: Session = Depends(get_db),
) -> list[Any]:
    return list_config_versions(db)


@router.get("/appointment-types", response_model=list[dict[str, Any]])
def get_appointment_types(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_appointment_types(db)


@router.post("/appointment-types/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_appointment_type(
    payload: AppointmentTypeAdminPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_appointment_type(db, payload)


@router.post("/appointment-types", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_appointment_type(
    payload: AppointmentTypeAdminCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_appointment_type(db, payload, current_user)


@router.get("/provider-schedules", response_model=list[dict[str, Any]])
def get_provider_schedules(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_provider_schedules(db)


@router.post("/provider-schedules/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_provider_schedule(
    payload: ProviderScheduleTemplatePreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_provider_schedule(db, payload)


@router.post("/provider-schedules", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_provider_schedule(
    payload: ProviderScheduleTemplateCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_provider_schedule(db, payload, current_user)


@router.get("/screening-templates", response_model=list[dict[str, Any]])
def get_screening_templates(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_screening_templates(db)


@router.post("/screening-templates/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_screening_template(
    payload: ScreeningTemplateVersionPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_screening_template(db, payload)


@router.post("/screening-templates", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_screening_template(
    payload: ScreeningTemplateVersionCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_screening_template(db, payload, current_user)


@router.get("/eligibility-rules", response_model=list[dict[str, Any]])
def get_eligibility_rules(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_eligibility_rules(db)


@router.post("/eligibility-rules/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_eligibility_rule(
    payload: EligibilityRuleVersionPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_eligibility_rule(db, payload)


@router.post("/eligibility-rules", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_eligibility_rule(
    payload: EligibilityRuleVersionCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_eligibility_rule(db, payload, current_user)


@router.get("/deferral-rules", response_model=list[dict[str, Any]])
def get_deferral_rules(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_deferral_rules(db)


@router.post("/deferral-rules/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_deferral_rule(
    payload: DeferralRuleVersionPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_deferral_rule(db, payload)


@router.post("/deferral-rules", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_deferral_rule(
    payload: DeferralRuleVersionCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_deferral_rule(db, payload, current_user)


@router.get("/note-templates", response_model=list[dict[str, Any]])
def get_note_templates(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_note_templates(db)


@router.post("/note-templates/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_note_template(
    payload: NoteTemplateAdminPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_note_template(db, payload)


@router.post("/note-templates", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_note_template(
    payload: NoteTemplateAdminCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_note_template(db, payload, current_user)


@router.get("/order-catalog", response_model=list[dict[str, Any]])
def get_order_catalog(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_order_catalog(db)


@router.post("/order-catalog/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_order_catalog(
    payload: OrderCatalogAdminPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_order_catalog(db, payload)


@router.post("/order-catalog", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_order_catalog(
    payload: OrderCatalogAdminCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_order_catalog(db, payload, current_user)


@router.get("/billing-codes", response_model=list[dict[str, Any]])
def get_billing_codes(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_billing_codes(db)


@router.post("/billing-codes/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_billing_code(
    payload: BillingCodeCatalogPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_billing_code(db, payload)


@router.post("/billing-codes", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_billing_code(
    payload: BillingCodeCatalogCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_billing_code(db, payload, current_user)


@router.get("/quality-categories", response_model=list[dict[str, Any]])
def get_quality_categories(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_quality_categories(db)


@router.post("/quality-categories/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_quality_category(
    payload: QualityCategoryPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_quality_category(db, payload)


@router.post("/quality-categories", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_quality_category(
    payload: QualityCategoryCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_quality_category(db, payload, current_user)


@router.get("/approval-paths", response_model=list[dict[str, Any]])
def get_approval_paths(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_approval_paths(db)


@router.post("/approval-paths/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_approval_path(
    payload: ApprovalPathPreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_approval_path(db, payload)


@router.post("/approval-paths", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_approval_path(
    payload: ApprovalPathCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_approval_path(db, payload, current_user)


@router.get("/notification-templates", response_model=list[dict[str, Any]])
def get_notification_templates(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_notification_templates(db)


@router.post("/notification-templates/preview", response_model=ClinicalAdminPreviewResponse)
def preview_admin_notification_template(
    payload: NotificationTemplatePreviewRequest,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminPreviewResponse:
    return preview_notification_template(db, payload)


@router.post("/notification-templates", response_model=ClinicalAdminCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_admin_notification_template(
    payload: NotificationTemplateCommitRequest,
    request: Request,
    current_user: User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> ClinicalAdminCommitResponse:
    _confirm(request)
    return commit_notification_template(db, payload, current_user)


@router.get("/rbac", response_model=ClinicalRbacOverviewResponse)
def get_admin_rbac(current_user: User = Depends(require_admin_read), db: Session = Depends(get_db)) -> ClinicalRbacOverviewResponse:
    return rbac_overview(db)
