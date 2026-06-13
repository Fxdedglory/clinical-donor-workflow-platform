from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, time
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_user_permissions
from app.models import (
    AppointmentType,
    ClinicalAdminApprovalPath,
    ClinicalAdminApprovalStep,
    ClinicalAdminConfigVersion,
    ClinicalAdminStatusHistory,
    ClinicalBillingCodeCatalog,
    ClinicalDeferralRuleVersion,
    ClinicalEligibilityRuleVersion,
    ClinicalNoteTemplate,
    ClinicalNotificationTemplate,
    ClinicalOrderCatalogItem,
    ClinicalProvider,
    ClinicalProviderScheduleTemplate,
    ClinicalQualityCategory,
    ClinicalScreeningTemplateVersion,
    Role,
    RolePermission,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_admin import (
    AdminConfigVersionResponse,
    ApprovalPathCommitRequest,
    ApprovalPathPreviewRequest,
    AppointmentTypeAdminCommitRequest,
    AppointmentTypeAdminPreviewRequest,
    BillingCodeCatalogCommitRequest,
    BillingCodeCatalogPreviewRequest,
    ClinicalAdminBlockingIssue,
    ClinicalAdminCommitResponse,
    ClinicalAdminDashboardResponse,
    ClinicalAdminPreviewResponse,
    ClinicalAdminWarning,
    ClinicalRbacOverviewResponse,
    ClinicalRbacRoleResponse,
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
from app.services.clinical_patients import actor_label
from app.services.clinical_workflows import append_workflow_operation, preview_hash, read_workflow_operations

ADMIN_READ_PERMISSIONS = {"system.admin", "clinical_admin.read", "clinical_admin.manage", "audit.review"}
ADMIN_MUTATION_PERMISSIONS = {"system.admin", "clinical_admin.manage"}
EXTERNAL_ROLES = {"Partner External User", "Supplier External User"}


ADMIN_WORKFLOWS: dict[str, dict[str, Any]] = {
    "appointment_type": {
        "workflow": "admin.appointment_type_upsert",
        "entity_type": "appointment_type",
        "affected_modules": ["Scheduling", "Clinical Dashboard", "Reports"],
    },
    "provider_schedule": {
        "workflow": "admin.provider_schedule_upsert",
        "entity_type": "clinical_provider_schedule_template",
        "affected_modules": ["Scheduling", "Clinical Dashboard"],
    },
    "screening_template": {
        "workflow": "admin.screening_template_version",
        "entity_type": "clinical_screening_template_version",
        "affected_modules": ["Donor Screening", "Encounters", "Quality"],
    },
    "eligibility_rule": {
        "workflow": "admin.eligibility_rule_version",
        "entity_type": "clinical_eligibility_rule_version",
        "affected_modules": ["Donor Screening", "Quality", "Reports"],
    },
    "deferral_rule": {
        "workflow": "admin.deferral_rule_version",
        "entity_type": "clinical_deferral_rule_version",
        "affected_modules": ["Donor Screening", "Care Plans", "Quality"],
    },
    "note_template": {
        "workflow": "admin.note_template_upsert",
        "entity_type": "clinical_note_template",
        "affected_modules": ["Encounters", "Quality"],
    },
    "order_catalog": {
        "workflow": "admin.order_catalog_upsert",
        "entity_type": "clinical_order_catalog_item",
        "affected_modules": ["Orders / Results", "Care Plans", "Billing"],
    },
    "billing_code": {
        "workflow": "admin.billing_code_upsert",
        "entity_type": "clinical_billing_code_catalog",
        "affected_modules": ["Billing", "Reports"],
    },
    "quality_category": {
        "workflow": "admin.quality_category_upsert",
        "entity_type": "clinical_quality_category",
        "affected_modules": ["Quality", "CAPA", "Reports"],
    },
    "approval_path": {
        "workflow": "admin.approval_path_upsert",
        "entity_type": "clinical_admin_approval_path",
        "affected_modules": ["Quality", "Orders / Results", "Care Plans", "Billing"],
    },
    "notification_template": {
        "workflow": "admin.notification_template_upsert",
        "entity_type": "clinical_notification_template",
        "affected_modules": ["Notifications", "Clinical Dashboard"],
    },
}


def now_utc() -> datetime:
    return datetime.now(UTC)


def admin_actor(user: User) -> str:
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


def _warning(warning_type: str, message: str, field: str | None = None) -> ClinicalAdminWarning:
    return ClinicalAdminWarning(warning_type=warning_type, message=message, field=field)


def _blocking(issue_type: str, message: str, field: str | None = None) -> ClinicalAdminBlockingIssue:
    return ClinicalAdminBlockingIssue(issue_type=issue_type, message=message, field=field)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat(timespec="minutes")
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _row_dict(row: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: _serialize_value(getattr(row, field, None)) for field in fields}


def _all_rows(db: Session, model: type, include_deleted: bool = False) -> list[Any]:
    statement = select(model)
    if hasattr(model, "is_deleted") and not include_deleted:
        statement = statement.where(model.is_deleted.is_(False))
    return list(db.execute(statement).scalars().all())


def _first_by_attr(db: Session, model: type, attr_name: str, value: Any) -> Any | None:
    if value is None:
        return None
    rows = _all_rows(db, model, include_deleted=True)
    return next((row for row in rows if getattr(row, attr_name, None) == value), None)


def _row_by_id(db: Session, model: type, id_field: str, value: int | None) -> Any | None:
    if value is None:
        return None
    getter = getattr(db, "get", None)
    if callable(getter):
        row = getter(model, value)
        if row is not None:
            return row
    return _first_by_attr(db, model, id_field, value)


def _latest_by_key(db: Session, model: type, key_field: str, key_value: str) -> Any | None:
    rows = [row for row in _all_rows(db, model, include_deleted=True) if getattr(row, key_field, None) == key_value]
    if not rows:
        return None
    return max(rows, key=lambda row: getattr(row, "version", 1) or 1)


def _next_version(db: Session, model: type, key_field: str, key_value: str, requested: int | None = None) -> int:
    if requested:
        return requested
    latest = _latest_by_key(db, model, key_field, key_value)
    return int(getattr(latest, "version", 0) or 0) + 1


def _status_from_active(active: bool) -> str:
    return "active" if active else "inactive"


def _changed_fields(current: dict[str, Any], proposed: dict[str, Any]) -> list[str]:
    fields = sorted(set(current) | set(proposed))
    return [field for field in fields if current.get(field) != proposed.get(field)]


def _payload_dict(payload: Any) -> dict[str, Any]:
    return payload.model_dump(mode="json", exclude={"preview_hash"})


def _admin_preview(
    *,
    slug: str,
    entity_id: str,
    current: dict[str, Any],
    proposed: dict[str, Any],
    status_before: str | None,
    status_after: str | None,
    payload: Any,
    warnings: list[ClinicalAdminWarning] | None = None,
    blocking_issues: list[ClinicalAdminBlockingIssue] | None = None,
) -> ClinicalAdminPreviewResponse:
    meta = ADMIN_WORKFLOWS[slug]
    blocking = blocking_issues or []
    changed = _changed_fields(current, proposed)
    action = "Update" if current else "Create"
    return ClinicalAdminPreviewResponse(
        workflow=meta["workflow"],
        entity_type=meta["entity_type"],
        entity_id=entity_id,
        preview_hash=preview_hash({"workflow": meta["workflow"], "entity_id": entity_id, "payload": _payload_dict(payload)}),
        summary=f"{action} preview generated for {meta['entity_type']} {entity_id}.",
        status_before=status_before,
        status_after=status_after,
        current_config=current,
        proposed_config=proposed,
        changed_fields=changed,
        warnings=warnings or [],
        blocking_issues=blocking,
        affected_modules=meta["affected_modules"],
    )


def _reject_blocking(preview: ClinicalAdminPreviewResponse) -> None:
    if preview.blocking_issues:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "admin_validation_failed",
                "message": "Blocking administration issues prevent commit.",
                "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues],
            },
        )


def _status_history(
    db: Session,
    *,
    config_type: str,
    config_id: str,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    if from_status == to_status:
        return
    db.add(
        ClinicalAdminStatusHistory(
            config_type=config_type,
            config_id=config_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            reason=reason,
            notes=notes,
        )
    )


def _record_config_version(
    db: Session,
    *,
    config_type: str,
    config_key: str,
    entity_type: str,
    entity_id: str,
    snapshot: dict[str, Any],
    change_summary: dict[str, Any],
    status: str,
    version: int,
    user_id: int | None,
    reason: str,
) -> ClinicalAdminConfigVersion:
    timestamp = now_utc()
    version_row = ClinicalAdminConfigVersion(
        config_type=config_type,
        config_key=config_key,
        version=version,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        snapshot=snapshot,
        change_summary=change_summary,
        effective_from=timestamp,
        created_at=timestamp,
        created_by=user_id,
        reason=reason,
    )
    db.add(version_row)
    db.flush()
    return version_row


def append_admin_workflow_audit(
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
    operation, audit_path = append_workflow_operation(operation)
    return operation, str(audit_path)


def _commit_response(
    *,
    operation: WorkflowOperation,
    audit_path: str,
    config_version: ClinicalAdminConfigVersion,
    entity: dict[str, Any],
) -> ClinicalAdminCommitResponse:
    return ClinicalAdminCommitResponse(
        operation_id=operation.operation_id,
        audit_path=audit_path,
        config_version=AdminConfigVersionResponse.model_validate(config_version),
        entity=entity,
    )


APPOINTMENT_TYPE_FIELDS = (
    "appointment_type_id",
    "type_code",
    "name",
    "default_duration_minutes",
    "category",
    "description",
    "requires_room",
    "status",
    "version",
)
PROVIDER_SCHEDULE_FIELDS = (
    "schedule_template_id",
    "provider_id",
    "provider_name",
    "weekday",
    "date_pattern",
    "start_time",
    "end_time",
    "location",
    "room_id",
    "room_name",
    "active",
    "version",
)
SCREENING_TEMPLATE_FIELDS = ("template_version_id", "template_key", "template_name", "version", "required_questions", "active", "reason")
RULE_VERSION_FIELDS = (
    "rule_version_id",
    "rule_key",
    "rule_name",
    "rule_type",
    "severity",
    "expression",
    "criteria",
    "explanation",
    "active",
    "version",
    "reason",
)
NOTE_TEMPLATE_FIELDS = ("template_id", "template_key", "name", "note_type", "body", "sections", "status", "version")
ORDER_CATALOG_FIELDS = (
    "catalog_item_id",
    "code",
    "name",
    "order_type",
    "description",
    "default_priority",
    "specimen_type",
    "active",
    "version",
)
BILLING_CODE_FIELDS = ("code_id", "code", "code_type", "description", "default_amount", "active", "version")
QUALITY_CATEGORY_FIELDS = (
    "category_id",
    "category_key",
    "category",
    "severity_mapping",
    "closure_approval_required",
    "approval_required",
    "active",
    "version",
)
APPROVAL_PATH_FIELDS = ("path_id", "workflow", "path_name", "version", "active")
NOTIFICATION_TEMPLATE_FIELDS = ("notification_template_id", "workflow", "channel", "subject", "body", "active", "version")


def _appointment_type_proposed(payload: AppointmentTypeAdminPreviewRequest, version: int | None = None) -> dict[str, Any]:
    proposed = {
        "appointment_type_id": payload.appointment_type_id,
        "type_code": payload.type_code,
        "name": payload.name,
        "default_duration_minutes": payload.duration_minutes,
        "category": payload.category,
        "description": payload.description,
        "requires_room": payload.requires_room,
        "status": _status_from_active(payload.active),
    }
    if version is not None:
        proposed["version"] = version
    return proposed


def preview_appointment_type(db: Session, payload: AppointmentTypeAdminPreviewRequest) -> ClinicalAdminPreviewResponse:
    current = _row_by_id(db, AppointmentType, "appointment_type_id", payload.appointment_type_id) or _first_by_attr(db, AppointmentType, "type_code", payload.type_code)
    current_config = _row_dict(current, APPOINTMENT_TYPE_FIELDS) if current else {}
    version = int(current_config.get("version") or 0) + 1 if current else 1
    proposed = _appointment_type_proposed(payload, version)
    entity_id = str(current.appointment_type_id if current else payload.type_code)
    return _admin_preview(
        slug="appointment_type",
        entity_id=entity_id,
        current=current_config,
        proposed=proposed,
        status_before=current_config.get("status"),
        status_after=proposed["status"],
        payload=payload,
        warnings=[_warning("downstream_review", "Scheduling templates using this type should be reviewed.", "type_code")],
    )


def commit_appointment_type(db: Session, payload: AppointmentTypeAdminCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    preview = preview_appointment_type(db, payload)
    _reject_blocking(preview)
    row = _row_by_id(db, AppointmentType, "appointment_type_id", payload.appointment_type_id) or _first_by_attr(db, AppointmentType, "type_code", payload.type_code)
    before = getattr(row, "status", None) if row else None
    if row is None:
        row = AppointmentType(type_code=payload.type_code)
        db.add(row)
    row.name = payload.name
    row.default_duration_minutes = payload.duration_minutes
    row.category = payload.category
    row.description = payload.description
    row.requires_room = payload.requires_room
    row.status = _status_from_active(payload.active)
    row.version = int(getattr(row, "version", 0) or 0) + 1 if before is not None else 1
    db.flush()
    entity = _row_dict(row, APPOINTMENT_TYPE_FIELDS)
    version_row = _record_config_version(
        db,
        config_type="appointment_type",
        config_key=row.type_code,
        entity_type=ADMIN_WORKFLOWS["appointment_type"]["entity_type"],
        entity_id=str(row.appointment_type_id),
        snapshot=entity,
        change_summary={"changed_fields": preview.changed_fields},
        status=row.status,
        version=row.version,
        user_id=user.user_id,
        reason=payload.reason,
    )
    _status_history(db, config_type="appointment_type", config_id=str(row.appointment_type_id), from_status=before, to_status=row.status, user_id=user.user_id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    db.refresh(version_row)
    operation, audit_path = append_admin_workflow_audit(
        workflow=ADMIN_WORKFLOWS["appointment_type"]["workflow"],
        entity_type=ADMIN_WORKFLOWS["appointment_type"]["entity_type"],
        entity_id=str(row.appointment_type_id),
        actor=admin_actor(user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=before,
        status_after=row.status,
        reason=payload.reason,
        changes=entity,
    )
    return _commit_response(operation=operation, audit_path=audit_path, config_version=version_row, entity=entity)


def _provider_schedule_proposed(payload: ProviderScheduleTemplatePreviewRequest, version: int | None = None) -> dict[str, Any]:
    proposed = {
        "schedule_template_id": payload.schedule_template_id,
        "provider_id": payload.provider_id,
        "weekday": payload.weekday,
        "date_pattern": payload.date_pattern,
        "start_time": _serialize_value(payload.start_time),
        "end_time": _serialize_value(payload.end_time),
        "location": payload.location,
        "room_id": payload.room_id,
        "active": payload.active,
    }
    if version is not None:
        proposed["version"] = version
    return proposed


def preview_provider_schedule(db: Session, payload: ProviderScheduleTemplatePreviewRequest) -> ClinicalAdminPreviewResponse:
    current = _row_by_id(db, ClinicalProviderScheduleTemplate, "schedule_template_id", payload.schedule_template_id)
    provider = _row_by_id(db, ClinicalProvider, "provider_id", payload.provider_id)
    current_config = _row_dict(current, PROVIDER_SCHEDULE_FIELDS) if current else {}
    version = int(current_config.get("version") or 0) + 1 if current else 1
    proposed = _provider_schedule_proposed(payload, version)
    issues = [] if provider else [_blocking("provider_missing", "Provider is required for schedule template.", "provider_id")]
    return _admin_preview(
        slug="provider_schedule",
        entity_id=str(current.schedule_template_id if current else f"provider-{payload.provider_id}"),
        current=current_config,
        proposed=proposed,
        status_before=_status_from_active(bool(current.active)) if current else None,
        status_after=_status_from_active(payload.active),
        payload=payload,
        blocking_issues=issues,
        warnings=[_warning("foundation_scope", "Recurring conflict logic remains planned for a later sprint.", "date_pattern")],
    )


def commit_provider_schedule(db: Session, payload: ProviderScheduleTemplateCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    preview = preview_provider_schedule(db, payload)
    _reject_blocking(preview)
    row = _row_by_id(db, ClinicalProviderScheduleTemplate, "schedule_template_id", payload.schedule_template_id)
    before = _status_from_active(bool(row.active)) if row else None
    if row is None:
        row = ClinicalProviderScheduleTemplate(provider_id=payload.provider_id, created_by=user.user_id)
        db.add(row)
    row.provider_id = payload.provider_id
    row.weekday = payload.weekday
    row.date_pattern = payload.date_pattern
    row.start_time = payload.start_time
    row.end_time = payload.end_time
    row.location = payload.location
    row.room_id = payload.room_id
    row.active = payload.active
    row.version = int(getattr(row, "version", 0) or 0) + 1 if before is not None else 1
    row.updated_by = user.user_id
    db.flush()
    entity = _row_dict(row, PROVIDER_SCHEDULE_FIELDS)
    version_row = _record_config_version(
        db,
        config_type="provider_schedule",
        config_key=f"provider-{row.provider_id}",
        entity_type=ADMIN_WORKFLOWS["provider_schedule"]["entity_type"],
        entity_id=str(row.schedule_template_id),
        snapshot=entity,
        change_summary={"changed_fields": preview.changed_fields},
        status=_status_from_active(row.active),
        version=row.version,
        user_id=user.user_id,
        reason=payload.reason,
    )
    _status_history(db, config_type="provider_schedule", config_id=str(row.schedule_template_id), from_status=before, to_status=_status_from_active(row.active), user_id=user.user_id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    db.refresh(version_row)
    operation, audit_path = append_admin_workflow_audit(
        workflow=ADMIN_WORKFLOWS["provider_schedule"]["workflow"],
        entity_type=ADMIN_WORKFLOWS["provider_schedule"]["entity_type"],
        entity_id=str(row.schedule_template_id),
        actor=admin_actor(user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=before,
        status_after=_status_from_active(row.active),
        reason=payload.reason,
        changes=entity,
    )
    return _commit_response(operation=operation, audit_path=audit_path, config_version=version_row, entity=entity)


def _versioned_preview(
    db: Session,
    *,
    slug: str,
    model: type,
    key_field: str,
    payload: Any,
    proposed: dict[str, Any],
) -> ClinicalAdminPreviewResponse:
    latest = _latest_by_key(db, model, key_field, proposed[key_field])
    current = _row_dict(latest, tuple(proposed.keys()) + ("reason",)) if latest else {}
    proposed["version"] = _next_version(db, model, key_field, proposed[key_field], proposed.get("version"))
    return _admin_preview(
        slug=slug,
        entity_id=str(getattr(latest, "rule_version_id", None) or getattr(latest, "template_version_id", None) or proposed[key_field]),
        current=current,
        proposed=proposed,
        status_before=_status_from_active(bool(getattr(latest, "active", False))) if latest else None,
        status_after=_status_from_active(bool(proposed["active"])),
        payload=payload,
        warnings=[_warning("versioned_config", "Commit creates a new version and preserves prior versions.", key_field)],
    )


def preview_screening_template(db: Session, payload: ScreeningTemplateVersionPreviewRequest) -> ClinicalAdminPreviewResponse:
    return _versioned_preview(
        db,
        slug="screening_template",
        model=ClinicalScreeningTemplateVersion,
        key_field="template_key",
        payload=payload,
        proposed={
            "template_key": payload.template_key,
            "template_name": payload.template_name,
            "version": payload.version,
            "required_questions": payload.required_questions,
            "active": payload.active,
        },
    )


def preview_eligibility_rule(db: Session, payload: EligibilityRuleVersionPreviewRequest) -> ClinicalAdminPreviewResponse:
    return _versioned_preview(
        db,
        slug="eligibility_rule",
        model=ClinicalEligibilityRuleVersion,
        key_field="rule_key",
        payload=payload,
        proposed={
            "rule_key": payload.rule_key,
            "rule_name": payload.rule_name,
            "rule_type": payload.rule_type,
            "severity": payload.severity,
            "expression": payload.expression,
            "criteria": payload.criteria,
            "explanation": payload.explanation,
            "active": payload.active,
            "version": payload.version,
        },
    )


def preview_deferral_rule(db: Session, payload: DeferralRuleVersionPreviewRequest) -> ClinicalAdminPreviewResponse:
    return _versioned_preview(
        db,
        slug="deferral_rule",
        model=ClinicalDeferralRuleVersion,
        key_field="rule_key",
        payload=payload,
        proposed={
            "rule_key": payload.rule_key,
            "rule_name": payload.rule_name,
            "rule_type": payload.rule_type,
            "severity": payload.severity,
            "expression": payload.expression,
            "criteria": payload.criteria,
            "explanation": payload.explanation,
            "active": payload.active,
            "version": payload.version,
        },
    )


def _retire_prior_active(db: Session, model: type, key_field: str, key_value: str, user_id: int | None) -> None:
    for row in _all_rows(db, model, include_deleted=True):
        if getattr(row, key_field, None) == key_value and getattr(row, "active", False):
            row.active = False
            if hasattr(row, "retired_at"):
                row.retired_at = now_utc()
            if hasattr(row, "retired_by"):
                row.retired_by = user_id


def _commit_versioned(
    db: Session,
    *,
    slug: str,
    model: type,
    key_field: str,
    id_field: str,
    fields: tuple[str, ...],
    payload: Any,
    preview_func: Callable[[Session, Any], ClinicalAdminPreviewResponse],
    user: User,
) -> ClinicalAdminCommitResponse:
    preview = preview_func(db, payload)
    _reject_blocking(preview)
    key_value = getattr(payload, key_field)
    version = int(preview.proposed_config["version"])
    if payload.active:
        _retire_prior_active(db, model, key_field, key_value, user.user_id)
    row = model(**{key: getattr(payload, key) for key in preview.proposed_config if hasattr(payload, key)})
    row.version = version
    row.created_by = user.user_id
    row.reason = payload.reason
    db.add(row)
    db.flush()
    entity = _row_dict(row, fields)
    entity_id = str(getattr(row, id_field))
    status_after = _status_from_active(bool(row.active))
    version_row = _record_config_version(
        db,
        config_type=slug,
        config_key=key_value,
        entity_type=ADMIN_WORKFLOWS[slug]["entity_type"],
        entity_id=entity_id,
        snapshot=entity,
        change_summary={"changed_fields": preview.changed_fields},
        status=status_after,
        version=version,
        user_id=user.user_id,
        reason=payload.reason,
    )
    _status_history(db, config_type=slug, config_id=entity_id, from_status=preview.status_before, to_status=status_after, user_id=user.user_id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    db.refresh(version_row)
    operation, audit_path = append_admin_workflow_audit(
        workflow=ADMIN_WORKFLOWS[slug]["workflow"],
        entity_type=ADMIN_WORKFLOWS[slug]["entity_type"],
        entity_id=entity_id,
        actor=admin_actor(user),
        preview_value=getattr(payload, "preview_hash", None) or preview.preview_hash,
        status_before=preview.status_before,
        status_after=status_after,
        reason=payload.reason,
        changes=entity,
    )
    return _commit_response(operation=operation, audit_path=audit_path, config_version=version_row, entity=entity)


def commit_screening_template(db: Session, payload: ScreeningTemplateVersionCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    return _commit_versioned(
        db,
        slug="screening_template",
        model=ClinicalScreeningTemplateVersion,
        key_field="template_key",
        id_field="template_version_id",
        fields=SCREENING_TEMPLATE_FIELDS,
        payload=payload,
        preview_func=preview_screening_template,
        user=user,
    )


def commit_eligibility_rule(db: Session, payload: EligibilityRuleVersionCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    return _commit_versioned(
        db,
        slug="eligibility_rule",
        model=ClinicalEligibilityRuleVersion,
        key_field="rule_key",
        id_field="rule_version_id",
        fields=RULE_VERSION_FIELDS,
        payload=payload,
        preview_func=preview_eligibility_rule,
        user=user,
    )


def commit_deferral_rule(db: Session, payload: DeferralRuleVersionCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    return _commit_versioned(
        db,
        slug="deferral_rule",
        model=ClinicalDeferralRuleVersion,
        key_field="rule_key",
        id_field="rule_version_id",
        fields=RULE_VERSION_FIELDS,
        payload=payload,
        preview_func=preview_deferral_rule,
        user=user,
    )


def _note_template_proposed(payload: NoteTemplateAdminPreviewRequest, version: int | None = None) -> dict[str, Any]:
    proposed = {
        "template_id": payload.template_id,
        "template_key": payload.template_key,
        "name": payload.name,
        "note_type": payload.note_type,
        "body": payload.body,
        "sections": payload.sections,
        "status": _status_from_active(payload.active),
    }
    if version is not None:
        proposed["version"] = version
    return proposed


def preview_note_template(db: Session, payload: NoteTemplateAdminPreviewRequest) -> ClinicalAdminPreviewResponse:
    current = _row_by_id(db, ClinicalNoteTemplate, "template_id", payload.template_id) or _first_by_attr(db, ClinicalNoteTemplate, "template_key", payload.template_key)
    current_config = _row_dict(current, NOTE_TEMPLATE_FIELDS) if current else {}
    version = int(current_config.get("version") or 0) + 1 if current else 1
    proposed = _note_template_proposed(payload, version)
    return _admin_preview(
        slug="note_template",
        entity_id=str(current.template_id if current else payload.template_key),
        current=current_config,
        proposed=proposed,
        status_before=current_config.get("status"),
        status_after=proposed["status"],
        payload=payload,
        warnings=[_warning("encounter_review", "Signed notes retain their original content; new template versions affect future notes.", "template_key")],
    )


def commit_note_template(db: Session, payload: NoteTemplateAdminCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    preview = preview_note_template(db, payload)
    _reject_blocking(preview)
    row = _row_by_id(db, ClinicalNoteTemplate, "template_id", payload.template_id) or _first_by_attr(db, ClinicalNoteTemplate, "template_key", payload.template_key)
    before = getattr(row, "status", None) if row else None
    if row is None:
        row = ClinicalNoteTemplate(template_key=payload.template_key)
        db.add(row)
    row.name = payload.name
    row.note_type = payload.note_type
    row.body = payload.body
    row.sections = payload.sections
    row.status = _status_from_active(payload.active)
    row.version = int(getattr(row, "version", 0) or 0) + 1 if before is not None else 1
    db.flush()
    entity = _row_dict(row, NOTE_TEMPLATE_FIELDS)
    version_row = _record_config_version(
        db,
        config_type="note_template",
        config_key=row.template_key,
        entity_type=ADMIN_WORKFLOWS["note_template"]["entity_type"],
        entity_id=str(row.template_id),
        snapshot=entity,
        change_summary={"changed_fields": preview.changed_fields},
        status=row.status,
        version=row.version,
        user_id=user.user_id,
        reason=payload.reason,
    )
    _status_history(db, config_type="note_template", config_id=str(row.template_id), from_status=before, to_status=row.status, user_id=user.user_id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    db.refresh(version_row)
    operation, audit_path = append_admin_workflow_audit(
        workflow=ADMIN_WORKFLOWS["note_template"]["workflow"],
        entity_type=ADMIN_WORKFLOWS["note_template"]["entity_type"],
        entity_id=str(row.template_id),
        actor=admin_actor(user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=before,
        status_after=row.status,
        reason=payload.reason,
        changes=entity,
    )
    return _commit_response(operation=operation, audit_path=audit_path, config_version=version_row, entity=entity)


def _catalog_upsert_preview(
    db: Session,
    *,
    slug: str,
    model: type,
    id_field: str,
    key_field: str,
    fields: tuple[str, ...],
    payload: Any,
    proposed: dict[str, Any],
) -> ClinicalAdminPreviewResponse:
    current = _row_by_id(db, model, id_field, getattr(payload, id_field, None)) or _first_by_attr(db, model, key_field, proposed[key_field])
    current_config = _row_dict(current, fields) if current else {}
    proposed["version"] = int(current_config.get("version") or 0) + 1 if current else 1
    return _admin_preview(
        slug=slug,
        entity_id=str(getattr(current, id_field) if current else proposed[key_field]),
        current=current_config,
        proposed=proposed,
        status_before=_status_from_active(bool(getattr(current, "active", False))) if current else None,
        status_after=_status_from_active(bool(proposed["active"])),
        payload=payload,
    )


def preview_order_catalog(db: Session, payload: OrderCatalogAdminPreviewRequest) -> ClinicalAdminPreviewResponse:
    return _catalog_upsert_preview(
        db,
        slug="order_catalog",
        model=ClinicalOrderCatalogItem,
        id_field="catalog_item_id",
        key_field="code",
        fields=ORDER_CATALOG_FIELDS,
        payload=payload,
        proposed={
            "catalog_item_id": payload.catalog_item_id,
            "code": payload.code,
            "name": payload.name,
            "order_type": payload.order_type,
            "description": payload.description,
            "default_priority": payload.default_priority,
            "specimen_type": payload.specimen_type,
            "active": payload.active,
        },
    )


def preview_billing_code(db: Session, payload: BillingCodeCatalogPreviewRequest) -> ClinicalAdminPreviewResponse:
    return _catalog_upsert_preview(
        db,
        slug="billing_code",
        model=ClinicalBillingCodeCatalog,
        id_field="code_id",
        key_field="code",
        fields=BILLING_CODE_FIELDS,
        payload=payload,
        proposed={
            "code_id": payload.code_id,
            "code": payload.code,
            "code_type": payload.code_type,
            "description": payload.description,
            "default_amount": payload.default_amount,
            "active": payload.active,
        },
    )


def preview_quality_category(db: Session, payload: QualityCategoryPreviewRequest) -> ClinicalAdminPreviewResponse:
    return _catalog_upsert_preview(
        db,
        slug="quality_category",
        model=ClinicalQualityCategory,
        id_field="category_id",
        key_field="category_key",
        fields=QUALITY_CATEGORY_FIELDS,
        payload=payload,
        proposed={
            "category_id": payload.category_id,
            "category_key": payload.category_key,
            "category": payload.category,
            "severity_mapping": payload.severity_mapping,
            "closure_approval_required": payload.closure_required,
            "approval_required": payload.approval_required,
            "active": payload.active,
        },
    )


def _commit_catalog_upsert(
    db: Session,
    *,
    slug: str,
    model: type,
    id_field: str,
    key_field: str,
    fields: tuple[str, ...],
    payload: Any,
    preview_func: Callable[[Session, Any], ClinicalAdminPreviewResponse],
    user: User,
) -> ClinicalAdminCommitResponse:
    preview = preview_func(db, payload)
    _reject_blocking(preview)
    row = _row_by_id(db, model, id_field, getattr(payload, id_field, None)) or _first_by_attr(db, model, key_field, getattr(payload, key_field))
    before = _status_from_active(bool(getattr(row, "active", False))) if row else None
    if row is None:
        row = model(**{key_field: getattr(payload, key_field)})
        if hasattr(row, "created_by"):
            row.created_by = user.user_id
        db.add(row)
    for field, value in preview.proposed_config.items():
        if hasattr(row, field) and field != id_field:
            setattr(row, field, value)
    row.version = int(preview.proposed_config["version"])
    if hasattr(row, "updated_by"):
        row.updated_by = user.user_id
    db.flush()
    entity = _row_dict(row, fields)
    status_after = _status_from_active(bool(getattr(row, "active", False)))
    entity_id = str(getattr(row, id_field))
    version_row = _record_config_version(
        db,
        config_type=slug,
        config_key=getattr(row, key_field),
        entity_type=ADMIN_WORKFLOWS[slug]["entity_type"],
        entity_id=entity_id,
        snapshot=entity,
        change_summary={"changed_fields": preview.changed_fields},
        status=status_after,
        version=row.version,
        user_id=user.user_id,
        reason=payload.reason,
    )
    _status_history(db, config_type=slug, config_id=entity_id, from_status=before, to_status=status_after, user_id=user.user_id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    db.refresh(version_row)
    operation, audit_path = append_admin_workflow_audit(
        workflow=ADMIN_WORKFLOWS[slug]["workflow"],
        entity_type=ADMIN_WORKFLOWS[slug]["entity_type"],
        entity_id=entity_id,
        actor=admin_actor(user),
        preview_value=getattr(payload, "preview_hash", None) or preview.preview_hash,
        status_before=before,
        status_after=status_after,
        reason=payload.reason,
        changes=entity,
    )
    return _commit_response(operation=operation, audit_path=audit_path, config_version=version_row, entity=entity)


def commit_order_catalog(db: Session, payload: OrderCatalogAdminCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    return _commit_catalog_upsert(db, slug="order_catalog", model=ClinicalOrderCatalogItem, id_field="catalog_item_id", key_field="code", fields=ORDER_CATALOG_FIELDS, payload=payload, preview_func=preview_order_catalog, user=user)


def commit_billing_code(db: Session, payload: BillingCodeCatalogCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    return _commit_catalog_upsert(db, slug="billing_code", model=ClinicalBillingCodeCatalog, id_field="code_id", key_field="code", fields=BILLING_CODE_FIELDS, payload=payload, preview_func=preview_billing_code, user=user)


def commit_quality_category(db: Session, payload: QualityCategoryCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    return _commit_catalog_upsert(db, slug="quality_category", model=ClinicalQualityCategory, id_field="category_id", key_field="category_key", fields=QUALITY_CATEGORY_FIELDS, payload=payload, preview_func=preview_quality_category, user=user)


def _approval_path_snapshot(row: ClinicalAdminApprovalPath) -> dict[str, Any]:
    data = _row_dict(row, APPROVAL_PATH_FIELDS)
    data["steps"] = [
        {
            "step_id": step.step_id,
            "step_order": step.step_order,
            "role": step.role,
            "permission": step.permission,
            "required": step.required,
            "active": step.active,
        }
        for step in sorted(row.steps, key=lambda item: item.step_order)
    ]
    return data


def preview_approval_path(db: Session, payload: ApprovalPathPreviewRequest) -> ClinicalAdminPreviewResponse:
    latest = _latest_by_key(db, ClinicalAdminApprovalPath, "workflow", payload.workflow)
    current = _approval_path_snapshot(latest) if latest else {}
    version = int(getattr(latest, "version", 0) or 0) + 1
    proposed = {
        "workflow": payload.workflow,
        "path_name": payload.path_name,
        "version": version,
        "active": payload.active,
        "steps": [step.model_dump(mode="json") for step in payload.steps],
    }
    return _admin_preview(
        slug="approval_path",
        entity_id=str(getattr(latest, "path_id", None) or payload.workflow),
        current=current,
        proposed=proposed,
        status_before=_status_from_active(bool(getattr(latest, "active", False))) if latest else None,
        status_after=_status_from_active(payload.active),
        payload=payload,
        warnings=[_warning("versioned_config", "Commit creates a new approval path version and preserves prior paths.", "workflow")],
    )


def commit_approval_path(db: Session, payload: ApprovalPathCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    preview = preview_approval_path(db, payload)
    _reject_blocking(preview)
    if payload.active:
        _retire_prior_active(db, ClinicalAdminApprovalPath, "workflow", payload.workflow, user.user_id)
    row = ClinicalAdminApprovalPath(
        workflow=payload.workflow,
        path_name=payload.path_name,
        version=int(preview.proposed_config["version"]),
        active=payload.active,
        created_by=user.user_id,
        updated_by=user.user_id,
    )
    row.steps = [
        ClinicalAdminApprovalStep(
            step_order=step.step_order,
            role=step.role,
            permission=step.permission,
            required=step.required,
            active=step.active,
        )
        for step in payload.steps
    ]
    db.add(row)
    db.flush()
    entity = _approval_path_snapshot(row)
    status_after = _status_from_active(row.active)
    version_row = _record_config_version(
        db,
        config_type="approval_path",
        config_key=row.workflow,
        entity_type=ADMIN_WORKFLOWS["approval_path"]["entity_type"],
        entity_id=str(row.path_id),
        snapshot=entity,
        change_summary={"changed_fields": preview.changed_fields},
        status=status_after,
        version=row.version,
        user_id=user.user_id,
        reason=payload.reason,
    )
    _status_history(db, config_type="approval_path", config_id=str(row.path_id), from_status=preview.status_before, to_status=status_after, user_id=user.user_id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    db.refresh(version_row)
    operation, audit_path = append_admin_workflow_audit(
        workflow=ADMIN_WORKFLOWS["approval_path"]["workflow"],
        entity_type=ADMIN_WORKFLOWS["approval_path"]["entity_type"],
        entity_id=str(row.path_id),
        actor=admin_actor(user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=preview.status_before,
        status_after=status_after,
        reason=payload.reason,
        changes=entity,
    )
    return _commit_response(operation=operation, audit_path=audit_path, config_version=version_row, entity=entity)


def preview_notification_template(db: Session, payload: NotificationTemplatePreviewRequest) -> ClinicalAdminPreviewResponse:
    current = _row_by_id(db, ClinicalNotificationTemplate, "notification_template_id", payload.notification_template_id)
    if current is None:
        current = next(
            (
                row
                for row in _all_rows(db, ClinicalNotificationTemplate, include_deleted=True)
                if row.workflow == payload.workflow and row.channel == payload.channel
            ),
            None,
        )
    current_config = _row_dict(current, NOTIFICATION_TEMPLATE_FIELDS) if current else {}
    version = int(current_config.get("version") or 0) + 1 if current else 1
    proposed = {
        "notification_template_id": payload.notification_template_id,
        "workflow": payload.workflow,
        "channel": payload.channel,
        "subject": payload.subject,
        "body": payload.body,
        "active": payload.active,
        "version": version,
    }
    return _admin_preview(
        slug="notification_template",
        entity_id=str(current.notification_template_id if current else f"{payload.workflow}:{payload.channel}"),
        current=current_config,
        proposed=proposed,
        status_before=_status_from_active(bool(getattr(current, "active", False))) if current else None,
        status_after=_status_from_active(payload.active),
        payload=payload,
        warnings=[_warning("delivery_pending", "Template is stored only; notification delivery is planned workflow.", "channel")],
    )


def commit_notification_template(db: Session, payload: NotificationTemplateCommitRequest, user: User) -> ClinicalAdminCommitResponse:
    preview = preview_notification_template(db, payload)
    _reject_blocking(preview)
    row = _row_by_id(db, ClinicalNotificationTemplate, "notification_template_id", payload.notification_template_id)
    if row is None:
        row = next(
            (
                existing
                for existing in _all_rows(db, ClinicalNotificationTemplate, include_deleted=True)
                if existing.workflow == payload.workflow and existing.channel == payload.channel
            ),
            None,
        )
    before = _status_from_active(bool(row.active)) if row else None
    if row is None:
        row = ClinicalNotificationTemplate(workflow=payload.workflow, channel=payload.channel, created_by=user.user_id)
        db.add(row)
    row.subject = payload.subject
    row.body = payload.body
    row.active = payload.active
    row.version = int(preview.proposed_config["version"])
    row.updated_by = user.user_id
    db.flush()
    entity = _row_dict(row, NOTIFICATION_TEMPLATE_FIELDS)
    status_after = _status_from_active(row.active)
    version_row = _record_config_version(
        db,
        config_type="notification_template",
        config_key=f"{row.workflow}:{row.channel}",
        entity_type=ADMIN_WORKFLOWS["notification_template"]["entity_type"],
        entity_id=str(row.notification_template_id),
        snapshot=entity,
        change_summary={"changed_fields": preview.changed_fields},
        status=status_after,
        version=row.version,
        user_id=user.user_id,
        reason=payload.reason,
    )
    _status_history(db, config_type="notification_template", config_id=str(row.notification_template_id), from_status=before, to_status=status_after, user_id=user.user_id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    db.refresh(version_row)
    operation, audit_path = append_admin_workflow_audit(
        workflow=ADMIN_WORKFLOWS["notification_template"]["workflow"],
        entity_type=ADMIN_WORKFLOWS["notification_template"]["entity_type"],
        entity_id=str(row.notification_template_id),
        actor=admin_actor(user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=before,
        status_after=status_after,
        reason=payload.reason,
        changes=entity,
    )
    return _commit_response(operation=operation, audit_path=audit_path, config_version=version_row, entity=entity)


def list_config_versions(db: Session) -> list[ClinicalAdminConfigVersion]:
    return list(
        db.execute(select(ClinicalAdminConfigVersion).order_by(ClinicalAdminConfigVersion.created_at.desc()))
        .scalars()
        .all()
    )


def list_appointment_types(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, APPOINTMENT_TYPE_FIELDS) for row in _all_rows(db, AppointmentType)]


def list_provider_schedules(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, PROVIDER_SCHEDULE_FIELDS) for row in _all_rows(db, ClinicalProviderScheduleTemplate)]


def list_screening_templates(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, SCREENING_TEMPLATE_FIELDS) for row in _all_rows(db, ClinicalScreeningTemplateVersion, include_deleted=True)]


def list_eligibility_rules(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, RULE_VERSION_FIELDS) for row in _all_rows(db, ClinicalEligibilityRuleVersion, include_deleted=True)]


def list_deferral_rules(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, RULE_VERSION_FIELDS) for row in _all_rows(db, ClinicalDeferralRuleVersion, include_deleted=True)]


def list_note_templates(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, NOTE_TEMPLATE_FIELDS) for row in _all_rows(db, ClinicalNoteTemplate)]


def list_order_catalog(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, ORDER_CATALOG_FIELDS) for row in _all_rows(db, ClinicalOrderCatalogItem)]


def list_billing_codes(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, BILLING_CODE_FIELDS) for row in _all_rows(db, ClinicalBillingCodeCatalog)]


def list_quality_categories(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, QUALITY_CATEGORY_FIELDS) for row in _all_rows(db, ClinicalQualityCategory)]


def list_approval_paths(db: Session) -> list[dict[str, Any]]:
    return [_approval_path_snapshot(row) for row in _all_rows(db, ClinicalAdminApprovalPath)]


def list_notification_templates(db: Session) -> list[dict[str, Any]]:
    return [_row_dict(row, NOTIFICATION_TEMPLATE_FIELDS) for row in _all_rows(db, ClinicalNotificationTemplate)]


def rbac_overview(db: Session) -> ClinicalRbacOverviewResponse:
    roles = list(db.execute(select(Role).order_by(Role.role_name)).scalars().all())
    permission_rows = list(db.execute(select(RolePermission)).scalars().all())
    permissions_by_role_id: dict[int, list[str]] = {}
    for row in permission_rows:
        permissions_by_role_id.setdefault(row.role_id, []).append(row.permission_name)
    role_payloads = []
    for role in roles:
        permissions = sorted(set(permissions_by_role_id.get(role.role_id, [])))
        role_payloads.append(
            ClinicalRbacRoleResponse(
                role=role.role_name,
                permissions=permissions,
                can_read_admin=bool(set(permissions) & ADMIN_READ_PERMISSIONS),
                can_manage_admin=bool(set(permissions) & ADMIN_MUTATION_PERMISSIONS),
                external=role.role_name in EXTERNAL_ROLES,
            )
        )
    return ClinicalRbacOverviewResponse(
        read_permissions=sorted(ADMIN_READ_PERMISSIONS),
        manage_permissions=sorted(ADMIN_MUTATION_PERMISSIONS),
        roles=role_payloads,
    )


def dashboard_response(db: Session) -> ClinicalAdminDashboardResponse:
    versions = list_config_versions(db)
    counts = Counter(version.config_type for version in versions)
    operations = [operation for operation in read_workflow_operations() if str(operation.get("workflow", "")).startswith("admin.")]
    return ClinicalAdminDashboardResponse(
        total_config_versions=len(versions),
        active_config_versions=sum(1 for version in versions if version.status == "active"),
        configuration_counts=dict(counts),
        recent_versions=versions[:5],
        recent_audit_operations=operations[-8:],
        warnings=[
            _warning("foundation_scope", "Administration stores configuration and audit evidence; delivery engines and advanced conflict logic remain planned."),
        ],
    )
