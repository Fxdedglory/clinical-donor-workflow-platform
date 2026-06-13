from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    CAPA,
    ClinicalAdverseEvent,
    ClinicalCarePlan,
    ClinicalCharge,
    ClinicalClaim,
    ClinicalComplianceExport,
    ClinicalDenial,
    ClinicalEncounter,
    ClinicalOrder,
    ClinicalOrderResult,
    ClinicalPayment,
    ClinicalQualityEvent,
    ClinicalQualityEventLink,
    ClinicalQualityStatusHistory,
    ClinicalScreeningSession,
    Deviation,
    Patient,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_quality import (
    AdverseEventPreviewRequest,
    AuditEvidenceResponse,
    ComplianceExportPreviewRequest,
    QualityBlockingIssue,
    QualityCapaLinkPreviewRequest,
    QualityClosePreviewRequest,
    QualityDashboardResponse,
    QualityEventCreatePreviewRequest,
    QualityPreviewResponse,
    QualityWarning,
    QualityInvestigationPreviewRequest,
)
from app.services.clinical_patients import actor_label
from app.services.clinical_workflows import append_workflow_operation, preview_hash, read_workflow_operations

ACTIVE_QUALITY_STATUSES = {
    "open",
    "under_review",
    "investigation",
    "capa_required",
    "pending_approval",
    "closed",
    "cancelled",
}
MUTABLE_QUALITY_STATUSES = ACTIVE_QUALITY_STATUSES - {"closed", "cancelled"}
ELEVATED_SEVERITIES = {"high", "severe", "critical"}


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_quality_event_number() -> str:
    return f"QE-{uuid4().hex[:10].upper()}"


def new_adverse_event_number() -> str:
    return f"AE-{uuid4().hex[:10].upper()}"


def new_compliance_export_number() -> str:
    return f"CEXP-{uuid4().hex[:10].upper()}"


def quality_actor(user: User) -> str:
    return actor_label(user)


def _one_or_none(db: Session, statement) -> Any | None:
    return db.execute(statement).scalar_one_or_none()


def patient_by_identifier(db: Session, patient_id: str | None) -> Patient | None:
    if not patient_id:
        return None
    return _one_or_none(db, select(Patient).where(Patient.patient_id == patient_id, Patient.is_deleted.is_(False)))


def patient_by_pk(db: Session, patient_pk: int | None) -> Patient | None:
    if patient_pk is None:
        return None
    return _one_or_none(db, select(Patient).where(Patient.patient_pk == patient_pk, Patient.is_deleted.is_(False)))


def appointment_by_id(db: Session, appointment_id: int | None) -> Appointment | None:
    if appointment_id is None:
        return None
    return _one_or_none(
        db,
        select(Appointment).where(Appointment.appointment_id == appointment_id, Appointment.is_deleted.is_(False)),
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


def order_by_id(db: Session, order_id: int | None) -> ClinicalOrder | None:
    if order_id is None:
        return None
    return _one_or_none(db, select(ClinicalOrder).where(ClinicalOrder.order_id == order_id, ClinicalOrder.is_deleted.is_(False)))


def order_result_by_id(db: Session, result_id: int | None) -> ClinicalOrderResult | None:
    if result_id is None:
        return None
    return _one_or_none(db, select(ClinicalOrderResult).where(ClinicalOrderResult.result_id == result_id))


def care_plan_by_id(db: Session, care_plan_id: int | None) -> ClinicalCarePlan | None:
    if care_plan_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalCarePlan).where(
            ClinicalCarePlan.care_plan_id == care_plan_id,
            ClinicalCarePlan.is_deleted.is_(False),
        ),
    )


def charge_by_id(db: Session, charge_id: int | None) -> ClinicalCharge | None:
    if charge_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalCharge).where(ClinicalCharge.charge_id == charge_id, ClinicalCharge.is_deleted.is_(False)),
    )


def claim_by_id(db: Session, claim_id: int | None) -> ClinicalClaim | None:
    if claim_id is None:
        return None
    return _one_or_none(db, select(ClinicalClaim).where(ClinicalClaim.claim_id == claim_id, ClinicalClaim.is_deleted.is_(False)))


def payment_by_id(db: Session, payment_id: int | None) -> ClinicalPayment | None:
    if payment_id is None:
        return None
    return _one_or_none(db, select(ClinicalPayment).where(ClinicalPayment.payment_id == payment_id))


def denial_by_id(db: Session, denial_id: int | None) -> ClinicalDenial | None:
    if denial_id is None:
        return None
    return _one_or_none(db, select(ClinicalDenial).where(ClinicalDenial.denial_id == denial_id))


def deviation_by_id(db: Session, deviation_id: int | None) -> Deviation | None:
    if deviation_id is None:
        return None
    return _one_or_none(
        db,
        select(Deviation).where(Deviation.deviation_id == deviation_id, Deviation.is_archived.is_(False)),
    )


def capa_by_id(db: Session, capa_id: int | None) -> CAPA | None:
    if capa_id is None:
        return None
    return _one_or_none(db, select(CAPA).where(CAPA.capa_id == capa_id, CAPA.is_archived.is_(False)))


def quality_event_by_id(db: Session, event_id: int | None) -> ClinicalQualityEvent | None:
    if event_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalQualityEvent).where(
            ClinicalQualityEvent.event_id == event_id,
            ClinicalQualityEvent.is_deleted.is_(False),
        ),
    )


def _issue(issue_type: str, field: str, message: str) -> QualityBlockingIssue:
    return QualityBlockingIssue(issue_type=issue_type, field=field, message=message)


def _warning(warning_type: str, field: str, message: str) -> QualityWarning:
    return QualityWarning(warning_type=warning_type, field=field, message=message)


def _preview(
    *,
    workflow: str,
    entity_type: str,
    entity_id: str,
    changes: dict[str, Any],
    blocking_issues: list[QualityBlockingIssue] | None = None,
    warnings: list[QualityWarning] | None = None,
    summary: str,
) -> QualityPreviewResponse:
    issues = blocking_issues or []
    warning_rows = warnings or []
    return QualityPreviewResponse(
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


def patient_context(patient: Patient | None) -> dict[str, Any]:
    if not patient:
        return {"patient_pk": None, "patient_id": None, "patient_name": None}
    return {
        "patient_pk": patient.patient_pk,
        "patient_id": patient.patient_id,
        "patient_name": " ".join(part for part in [patient.first_name, patient.middle_name, patient.last_name] if part),
    }


def quality_event_context(db: Session, payload: QualityEventCreatePreviewRequest) -> dict[str, Any]:
    return {
        "patient": patient_by_identifier(db, payload.patient_id),
        "appointment": appointment_by_id(db, payload.appointment_id),
        "screening_session": screening_session_by_id(db, payload.screening_session_id),
        "encounter": encounter_by_id(db, payload.encounter_id),
        "order": order_by_id(db, payload.order_id),
        "order_result": order_result_by_id(db, payload.order_result_id),
        "care_plan": care_plan_by_id(db, payload.care_plan_id),
        "charge": charge_by_id(db, payload.charge_id),
        "claim": claim_by_id(db, payload.claim_id),
        "payment": payment_by_id(db, payload.payment_id),
        "denial": denial_by_id(db, payload.denial_id),
        "deviation": deviation_by_id(db, payload.deviation_id),
        "capa": capa_by_id(db, payload.capa_id),
    }


def adverse_event_context(db: Session, payload: AdverseEventPreviewRequest) -> dict[str, Any]:
    return {
        "patient": patient_by_identifier(db, payload.patient_id),
        "quality_event": quality_event_by_id(db, payload.quality_event_id),
        "screening_session": screening_session_by_id(db, payload.screening_session_id),
        "encounter": encounter_by_id(db, payload.encounter_id),
        "order": order_by_id(db, payload.order_id),
        "order_result": order_result_by_id(db, payload.order_result_id),
        "care_plan": care_plan_by_id(db, payload.care_plan_id),
    }


def _patient_pk_for_context(value: Any | None) -> int | None:
    if value is None:
        return None
    if hasattr(value, "patient_pk"):
        return value.patient_pk
    if hasattr(value, "order") and value.order is not None:
        return getattr(value.order, "patient_pk", None)
    if hasattr(value, "claim") and value.claim is not None:
        return getattr(value.claim, "patient_pk", None)
    return None


def _context_label(name: str, value: Any | None) -> str | None:
    if value is None:
        return None
    for attr in [
        "appointment_number",
        "session_number",
        "encounter_number",
        "order_number",
        "care_plan_number",
        "charge_number",
        "claim_number",
        "reference_number",
        "denial_code",
        "deviation_code",
        "capa_code",
    ]:
        if hasattr(value, attr):
            label = getattr(value, attr)
            if label:
                return str(label)
    if name == "order_result":
        return f"{value.result_name}: {value.result_value}"
    return str(getattr(value, f"{name}_id", "") or getattr(value, "event_id", "") or getattr(value, "adverse_event_id", ""))


def _context_summary(context: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {
            "id": getattr(value, f"{name}_id", None) or getattr(value, "session_id", None) or getattr(value, "result_id", None) or getattr(value, "deviation_id", None) or getattr(value, "capa_id", None),
            "label": _context_label(name, value),
            "patient_pk": _patient_pk_for_context(value),
        }
        for name, value in context.items()
        if name != "patient" and value is not None
    }


def _resolve_patient(db: Session, context: dict[str, Any]) -> Patient | None:
    patient = context.get("patient")
    if patient:
        return patient
    patient_pks = [patient_pk for value in context.values() if (patient_pk := _patient_pk_for_context(value)) is not None]
    return patient_by_pk(db, patient_pks[0]) if patient_pks else None


def resolved_patient_for_context(db: Session, context: dict[str, Any]) -> Patient | None:
    return _resolve_patient(db, context)


def _context_validation_issues(
    *,
    payload: QualityEventCreatePreviewRequest | AdverseEventPreviewRequest,
    context: dict[str, Any],
    fields: list[tuple[str, Any | None]],
    patient: Patient | None,
) -> list[QualityBlockingIssue]:
    issues: list[QualityBlockingIssue] = []
    for field, value in fields:
        if getattr(payload, field) is not None and value is None:
            issues.append(_issue(f"unknown_{field}", field, f"Linked {field.replace('_', ' ')} was not found."))
    if getattr(payload, "patient_id", None) and not context.get("patient"):
        issues.append(_issue("unknown_patient", "patient_id", "Patient/donor profile was not found."))
    context_patient_pks = {
        patient_pk
        for _name, value in fields
        if value is not None and (patient_pk := _patient_pk_for_context(value)) is not None
    }
    if len(context_patient_pks) > 1:
        issues.append(_issue("mixed_patient_context", "patient_id", "Linked clinical context spans multiple patients/donors."))
    if patient and any(patient_pk != patient.patient_pk for patient_pk in context_patient_pks):
        issues.append(_issue("patient_context_mismatch", "patient_id", "Linked clinical context belongs to a different patient/donor."))
    order = context.get("order")
    result = context.get("order_result")
    if result and order and result.order_id != order.order_id:
        issues.append(_issue("order_result_mismatch", "order_result_id", "Order result does not belong to the linked order."))
    return issues


def quality_event_create_preview(db: Session, payload: QualityEventCreatePreviewRequest) -> QualityPreviewResponse:
    context = quality_event_context(db, payload)
    patient = _resolve_patient(db, context)
    fields = [
        ("appointment_id", context["appointment"]),
        ("screening_session_id", context["screening_session"]),
        ("encounter_id", context["encounter"]),
        ("order_id", context["order"]),
        ("order_result_id", context["order_result"]),
        ("care_plan_id", context["care_plan"]),
        ("charge_id", context["charge"]),
        ("claim_id", context["claim"]),
        ("payment_id", context["payment"]),
        ("denial_id", context["denial"]),
        ("deviation_id", context["deviation"]),
        ("capa_id", context["capa"]),
    ]
    issues = _context_validation_issues(payload=payload, context=context, fields=fields, patient=patient)
    warnings: list[QualityWarning] = []
    if payload.status not in ACTIVE_QUALITY_STATUSES:
        issues.append(_issue("invalid_status", "status", f"Status must be one of {', '.join(sorted(ACTIVE_QUALITY_STATUSES))}."))
    if payload.severity.lower() in ELEVATED_SEVERITIES:
        warnings.append(_warning("supervisor_review_recommended", "severity", "High, severe, and critical quality events should receive supervisor review."))
    if payload.due_date and payload.due_date < date.today():
        warnings.append(_warning("past_due_date", "due_date", "Due date is already in the past."))
    if not patient and not any(value for _field, value in fields):
        warnings.append(_warning("standalone_event", "patient_id", "Quality event has no linked patient or workflow context."))
    changes = payload.model_dump(mode="json")
    changes["patient"] = patient_context(patient)
    changes["context"] = _context_summary(context)
    return _preview(
        workflow="quality.event_create",
        entity_type="clinical_quality_event",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Quality event is ready to create." if not issues else "Quality event preview found blocking issues.",
    )


def adverse_event_preview(db: Session, payload: AdverseEventPreviewRequest) -> QualityPreviewResponse:
    context = adverse_event_context(db, payload)
    patient = context["patient"]
    fields = [
        ("quality_event_id", context["quality_event"]),
        ("screening_session_id", context["screening_session"]),
        ("encounter_id", context["encounter"]),
        ("order_id", context["order"]),
        ("order_result_id", context["order_result"]),
        ("care_plan_id", context["care_plan"]),
    ]
    issues = _context_validation_issues(payload=payload, context=context, fields=fields, patient=patient)
    warnings: list[QualityWarning] = []
    quality_event = context["quality_event"]
    if quality_event and quality_event.status not in MUTABLE_QUALITY_STATUSES:
        issues.append(_issue("quality_event_closed", "quality_event_id", "Linked quality event is closed or cancelled."))
    if quality_event and patient and quality_event.patient_pk and quality_event.patient_pk != patient.patient_pk:
        issues.append(_issue("quality_event_patient_mismatch", "quality_event_id", "Linked quality event belongs to a different patient/donor."))
    if payload.severity.lower() in ELEVATED_SEVERITIES:
        warnings.append(_warning("supervisor_review_recommended", "severity", "Severe or critical adverse events should receive investigation and supervisor review."))
        if not payload.follow_up_required:
            warnings.append(_warning("follow_up_recommended", "follow_up_required", "Follow-up is recommended for severe or critical adverse events."))
    result = context["order_result"]
    if result and getattr(result, "critical_flag", False):
        warnings.append(_warning("critical_result_context", "order_result_id", "Linked order result is marked critical."))
    changes = payload.model_dump(mode="json")
    changes["patient"] = patient_context(patient)
    changes["context"] = _context_summary(context)
    return _preview(
        workflow="quality.adverse_event_create",
        entity_type="clinical_adverse_event",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Adverse event is ready to create." if not issues else "Adverse event preview found blocking issues.",
    )


def investigation_preview(
    db: Session,
    event_id: int,
    payload: QualityInvestigationPreviewRequest,
) -> QualityPreviewResponse:
    event = quality_event_by_id(db, event_id)
    issues: list[QualityBlockingIssue] = []
    warnings: list[QualityWarning] = []
    if not event:
        issues.append(_issue("unknown_quality_event", "event_id", "Quality event was not found."))
    elif event.status not in MUTABLE_QUALITY_STATUSES:
        issues.append(_issue("event_closed", "event_id", "Closed or cancelled quality events cannot be mutated."))
    if payload.status_after not in ACTIVE_QUALITY_STATUSES - {"closed", "cancelled"}:
        issues.append(_issue("invalid_status", "status_after", "Investigation status must keep the event open."))
    if not payload.evidence_summary:
        warnings.append(_warning("evidence_recommended", "evidence_summary", "Evidence summary can be appended later, but is recommended."))
    if event and event.severity.lower() in ELEVATED_SEVERITIES and not payload.owner and not event.owner:
        warnings.append(_warning("owner_recommended", "owner", "Elevated severity investigations should identify an owner."))
    changes = payload.model_dump(mode="json")
    changes["status_before"] = event.status if event else None
    changes["event_number"] = event.event_number if event else None
    return _preview(
        workflow="quality.investigation_add",
        entity_type="clinical_quality_investigation",
        entity_id=event.event_number if event else str(event_id),
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Investigation entry is ready to append." if not issues else "Investigation preview found blocking issues.",
    )


def capa_link_preview(db: Session, event_id: int, payload: QualityCapaLinkPreviewRequest) -> QualityPreviewResponse:
    event = quality_event_by_id(db, event_id)
    capa = capa_by_id(db, payload.existing_capa_id)
    issues: list[QualityBlockingIssue] = []
    warnings: list[QualityWarning] = []
    if not event:
        issues.append(_issue("unknown_quality_event", "event_id", "Quality event was not found."))
    elif event.status not in MUTABLE_QUALITY_STATUSES:
        issues.append(_issue("event_closed", "event_id", "Closed or cancelled quality events cannot be mutated."))
    if payload.existing_capa_id is not None and not capa:
        issues.append(_issue("unknown_capa", "existing_capa_id", "CAPA record was not found."))
    if event and event.capa_id and payload.existing_capa_id and event.capa_id != payload.existing_capa_id:
        warnings.append(_warning("capa_relink", "existing_capa_id", "This will relink the event to a different CAPA."))
    if payload.create_planned_capa and payload.existing_capa_id is None:
        warnings.append(_warning("planned_capa", "create_planned_capa", "A planned CAPA link will be recorded without creating a new QMS CAPA record."))
    changes = payload.model_dump(mode="json")
    changes["status_before"] = event.status if event else None
    changes["status_after"] = "capa_required"
    changes["event_number"] = event.event_number if event else None
    changes["capa_code"] = capa.capa_code if capa else None
    return _preview(
        workflow="quality.capa_link",
        entity_type="clinical_quality_event",
        entity_id=event.event_number if event else str(event_id),
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="CAPA linkage is ready to commit." if not issues else "CAPA linkage preview found blocking issues.",
    )


def close_preview(db: Session, event_id: int, payload: QualityClosePreviewRequest) -> QualityPreviewResponse:
    event = quality_event_by_id(db, event_id)
    issues: list[QualityBlockingIssue] = []
    warnings: list[QualityWarning] = []
    if not event:
        issues.append(_issue("unknown_quality_event", "event_id", "Quality event was not found."))
    elif event.status not in MUTABLE_QUALITY_STATUSES:
        issues.append(_issue("event_closed", "event_id", "Quality event is already closed or cancelled."))
    if event and event.severity.lower() in ELEVATED_SEVERITIES and not event.investigations:
        warnings.append(_warning("investigation_recommended", "event_id", "Elevated severity events should include investigation evidence before closure."))
    changes = payload.model_dump(mode="json")
    changes["status_before"] = event.status if event else None
    changes["status_after"] = "closed"
    changes["event_number"] = event.event_number if event else None
    return _preview(
        workflow="quality.event_close",
        entity_type="clinical_quality_event",
        entity_id=event.event_number if event else str(event_id),
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Quality event is ready for closure approval." if not issues else "Closure preview found blocking issues.",
    )


def _operation_timestamp(operation: dict[str, Any]) -> datetime | None:
    value = operation.get("timestamp")
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _operation_matches(operation: dict[str, Any], payload: ComplianceExportPreviewRequest) -> bool:
    timestamp = _operation_timestamp(operation)
    if payload.date_from and timestamp and timestamp.date() < payload.date_from:
        return False
    if payload.date_to and timestamp and timestamp.date() > payload.date_to:
        return False
    if payload.actor and payload.actor.lower() not in str(operation.get("actor", "")).lower():
        return False
    if payload.workflow and payload.workflow != operation.get("workflow"):
        return False
    if payload.entity_type and payload.entity_type != operation.get("entity_type"):
        return False
    if payload.entity_id and payload.entity_id != operation.get("entity_id"):
        return False
    if payload.modules:
        workflow = str(operation.get("workflow", "")).lower()
        entity_type = str(operation.get("entity_type", "")).lower()
        changes = operation.get("changes") or {}
        source_module = str(changes.get("source_module", "")).lower() if isinstance(changes, dict) else ""
        modules = [module.lower() for module in payload.modules]
        return any(module in workflow or module in entity_type or module in source_module for module in modules)
    return True


def filtered_workflow_operations(payload: ComplianceExportPreviewRequest) -> list[dict[str, Any]]:
    return [operation for operation in read_workflow_operations() if _operation_matches(operation, payload)]


def quality_status_history_evidence(db: Session, payload: ComplianceExportPreviewRequest) -> list[dict[str, Any]]:
    rows = list(db.execute(select(ClinicalQualityStatusHistory)).scalars().all())
    evidence: list[dict[str, Any]] = []
    for row in rows:
        changed_at = row.changed_at
        if payload.date_from and changed_at.date() < payload.date_from:
            continue
        if payload.date_to and changed_at.date() > payload.date_to:
            continue
        event = getattr(row, "event", None)
        if payload.entity_type == "clinical_quality_event" and event and payload.entity_id not in {str(event.event_id), event.event_number}:
            continue
        evidence.append(
            {
                "history_id": row.history_id,
                "event_id": row.event_id,
                "event_number": event.event_number if event else None,
                "from_status": row.from_status,
                "to_status": row.to_status,
                "changed_at": row.changed_at.isoformat(),
                "changed_by": row.changed_by,
                "reason": row.reason,
                "notes": row.notes,
            }
        )
    return evidence


def compliance_export_preview(db: Session, payload: ComplianceExportPreviewRequest) -> QualityPreviewResponse:
    operations = filtered_workflow_operations(payload)
    history = quality_status_history_evidence(db, payload) if payload.include_quality_history else []
    workflow_counts = dict(Counter(operation.get("workflow") for operation in operations))
    status_counts = dict(Counter(row.get("to_status") for row in history))
    criteria = payload.model_dump(mode="json")
    evidence_summary = {
        "workflow_operation_count": len(operations),
        "quality_status_history_count": len(history),
        "workflow_counts": workflow_counts,
        "quality_status_counts": status_counts,
    }
    warnings: list[QualityWarning] = []
    if not operations and not history:
        warnings.append(_warning("empty_export", "modules", "No evidence matched the current export filters."))
    changes = {"criteria": criteria, "evidence_summary": evidence_summary}
    return _preview(
        workflow="quality.compliance_export",
        entity_type="clinical_compliance_export",
        entity_id="draft",
        changes=changes,
        warnings=warnings,
        summary="Compliance export evidence is ready to generate.",
    )


def audit_evidence_response(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    actor: str | None = None,
    workflow: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    module: str | None = None,
) -> AuditEvidenceResponse:
    payload = ComplianceExportPreviewRequest(
        date_from=date_from,
        date_to=date_to,
        actor=actor,
        workflow=workflow,
        entity_type=entity_type,
        entity_id=entity_id,
        modules=[module] if module else [],
    )
    operations = filtered_workflow_operations(payload)
    history = quality_status_history_evidence(db, payload)
    exports = list(db.execute(select(ClinicalComplianceExport).order_by(ClinicalComplianceExport.generated_at.desc())).scalars().all())
    return AuditEvidenceResponse(
        operations=operations,
        quality_status_history=history,
        compliance_exports=exports,
        total_operations=len(operations),
        total_quality_history=len(history),
        total_exports=len(exports),
    )


def append_quality_status_history(
    *,
    event: ClinicalQualityEvent,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    history = ClinicalQualityStatusHistory(
        event_id=event.event_id,
        from_status=from_status,
        to_status=to_status,
        changed_by=user_id,
        reason=reason,
        notes=notes,
    )
    event.status_history.append(history)


def append_quality_workflow_audit(
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


def quality_event_link_rows(
    *,
    event: ClinicalQualityEvent,
    payload: QualityEventCreatePreviewRequest,
    context: dict[str, Any],
    user_id: int | None,
) -> list[ClinicalQualityEventLink]:
    rows: list[ClinicalQualityEventLink] = []
    for field, entity_type, value in [
        ("appointment_id", "appointment", context["appointment"]),
        ("screening_session_id", "screening_session", context["screening_session"]),
        ("encounter_id", "encounter", context["encounter"]),
        ("order_id", "order", context["order"]),
        ("order_result_id", "order_result", context["order_result"]),
        ("care_plan_id", "care_plan", context["care_plan"]),
        ("charge_id", "charge", context["charge"]),
        ("claim_id", "claim", context["claim"]),
        ("payment_id", "payment", context["payment"]),
        ("denial_id", "denial", context["denial"]),
        ("deviation_id", "deviation", context["deviation"]),
        ("capa_id", "capa", context["capa"]),
    ]:
        entity_id = getattr(payload, field)
        if entity_id is not None:
            rows.append(
                ClinicalQualityEventLink(
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    label=_context_label(entity_type, value),
                    created_by=user_id,
                )
            )
    for link in payload.links:
        rows.append(
            ClinicalQualityEventLink(
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                label=link.label,
                created_by=user_id,
            )
        )
    return rows


def quality_event_changes(event: ClinicalQualityEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_number": event.event_number,
        "patient_id": event.patient_id,
        "category": event.category,
        "severity": event.severity,
        "status": event.status,
        "owner": event.owner,
        "due_date": event.due_date.isoformat() if event.due_date else None,
        "source_module": event.source_module,
        "description": event.description,
        "appointment_id": event.appointment_id,
        "screening_session_id": event.screening_session_id,
        "encounter_id": event.encounter_id,
        "order_id": event.order_id,
        "order_result_id": event.order_result_id,
        "care_plan_id": event.care_plan_id,
        "charge_id": event.charge_id,
        "claim_id": event.claim_id,
        "payment_id": event.payment_id,
        "denial_id": event.denial_id,
        "deviation_id": event.deviation_id,
        "capa_id": event.capa_id,
    }


def adverse_event_changes(event: ClinicalAdverseEvent) -> dict[str, Any]:
    return {
        "adverse_event_id": event.adverse_event_id,
        "adverse_event_number": event.adverse_event_number,
        "patient_id": event.patient_id,
        "quality_event_id": event.quality_event_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "event_at": event.event_at.isoformat(),
        "description": event.description,
        "immediate_action_taken": event.immediate_action_taken,
        "reporter": event.reporter,
        "follow_up_required": event.follow_up_required,
        "status": event.status,
    }


def compliance_export_changes(export: ClinicalComplianceExport) -> dict[str, Any]:
    return {
        "export_id": export.export_id,
        "export_number": export.export_number,
        "date_from": export.date_from.isoformat() if export.date_from else None,
        "date_to": export.date_to.isoformat() if export.date_to else None,
        "modules": export.modules,
        "criteria": export.criteria,
        "evidence_summary": export.evidence_summary,
        "status": export.status,
        "generated_at": export.generated_at.isoformat() if export.generated_at else None,
    }


def dashboard_response(db: Session) -> QualityDashboardResponse:
    events = list(
        db.execute(
            select(ClinicalQualityEvent)
            .where(ClinicalQualityEvent.is_deleted.is_(False))
            .order_by(ClinicalQualityEvent.updated_at.desc())
        )
        .scalars()
        .all()
    )
    adverse_events = list(db.execute(select(ClinicalAdverseEvent)).scalars().all())
    exports = list(db.execute(select(ClinicalComplianceExport)).scalars().all())
    operations = [operation for operation in read_workflow_operations() if str(operation.get("workflow", "")).startswith("quality.")]
    today = date.today()
    return QualityDashboardResponse(
        total_events=len(events),
        open_events=sum(1 for event in events if event.status in MUTABLE_QUALITY_STATUSES),
        overdue_events=sum(1 for event in events if event.due_date and event.due_date < today and event.status in MUTABLE_QUALITY_STATUSES),
        adverse_events_open=sum(1 for event in adverse_events if event.status in MUTABLE_QUALITY_STATUSES),
        pending_approval_events=sum(1 for event in events if event.status == "pending_approval"),
        compliance_exports=len(exports),
        status_counts=dict(Counter(event.status for event in events)),
        severity_counts=dict(Counter(event.severity for event in events)),
        recent_events=events[:5],
        recent_audit_operations=operations[-5:],
        warnings=[
            _warning("foundation_scope", "clinical_admin", "Quality categories and approval templates remain planned for Clinical Administration.")
        ],
    )
