from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    ClinicalEncounter,
    ClinicalOrder,
    ClinicalOrderCatalogItem,
    ClinicalOrderResult,
    ClinicalOrderResultAcknowledgement,
    ClinicalOrderStatusHistory,
    ClinicalScreeningSession,
    Patient,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_orders import (
    OrderAcknowledgePreviewRequest,
    OrderBlockingIssue,
    OrderCancelPreviewRequest,
    OrderCatalogItemResponse,
    OrderCreatePreviewRequest,
    OrderPreviewResponse,
    OrderResultPreviewRequest,
    OrderWarning,
)
from app.services.clinical_patients import actor_label
from app.services.clinical_workflows import append_workflow_operation, preview_hash

CANCELLED_ORDER_STATUS = "cancelled"
RESULTED_ORDER_STATUS = "resulted"
ACTIVE_RESULT_STATUSES = {"normal", "abnormal", "critical", "corrected"}

DEFAULT_CATALOG_ITEMS = [
    OrderCatalogItemResponse(
        catalog_item_id=1,
        code="ID-NAT-PANEL",
        name="Infectious disease NAT panel",
        order_type="infectious_disease",
        description="Clinical order wrapper for the existing donor infectious disease testing assets.",
        default_priority="urgent",
        specimen_type="blood",
        active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ),
    OrderCatalogItemResponse(
        catalog_item_id=2,
        code="ID-SEROLOGY-PANEL",
        name="Infectious disease serology panel",
        order_type="infectious_disease",
        description="Serology testing catalog entry; does not replace legacy donor eligibility result facts.",
        default_priority="routine",
        specimen_type="blood",
        active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ),
    OrderCatalogItemResponse(
        catalog_item_id=3,
        code="CBC",
        name="Complete blood count",
        order_type="laboratory",
        description="General hematology screening order.",
        default_priority="routine",
        specimen_type="whole blood",
        active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ),
]


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_order_number() -> str:
    return f"ORD-{uuid4().hex[:10].upper()}"


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


def appointment_by_id(db: Session, appointment_id: int | None) -> Appointment | None:
    if appointment_id is None:
        return None
    return _one_or_none(db, select(Appointment).where(Appointment.appointment_id == appointment_id, Appointment.is_deleted.is_(False)))


def catalog_item_by_id(db: Session, catalog_item_id: int | None) -> ClinicalOrderCatalogItem | OrderCatalogItemResponse | None:
    if catalog_item_id is None:
        return None
    item = _one_or_none(
        db,
        select(ClinicalOrderCatalogItem).where(
            ClinicalOrderCatalogItem.catalog_item_id == catalog_item_id,
            ClinicalOrderCatalogItem.active.is_(True),
        ),
    )
    if item:
        return item
    return next((fallback for fallback in DEFAULT_CATALOG_ITEMS if fallback.catalog_item_id == catalog_item_id), None)


def order_by_id(db: Session, order_id: int) -> ClinicalOrder | None:
    return _one_or_none(
        db,
        select(ClinicalOrder).where(ClinicalOrder.order_id == order_id, ClinicalOrder.is_deleted.is_(False)),
    )


def result_by_id(db: Session, result_id: int | None) -> ClinicalOrderResult | None:
    if result_id is None:
        return None
    return _one_or_none(db, select(ClinicalOrderResult).where(ClinicalOrderResult.result_id == result_id))


def list_catalog_items(db: Session) -> list[ClinicalOrderCatalogItem | OrderCatalogItemResponse]:
    rows = list(
        db.execute(select(ClinicalOrderCatalogItem).where(ClinicalOrderCatalogItem.active.is_(True)))
        .scalars()
        .all()
    )
    return rows or DEFAULT_CATALOG_ITEMS


def order_actor(user: User) -> str:
    return actor_label(user)


def _issue(issue_type: str, field: str, message: str) -> OrderBlockingIssue:
    return OrderBlockingIssue(issue_type=issue_type, field=field, message=message)


def _warning(warning_type: str, field: str, message: str) -> OrderWarning:
    return OrderWarning(warning_type=warning_type, field=field, message=message)


def _preview(
    *,
    workflow: str,
    entity_type: str,
    entity_id: str,
    changes: dict[str, Any],
    blocking_issues: list[OrderBlockingIssue] | None = None,
    warnings: list[OrderWarning] | None = None,
    summary: str,
) -> OrderPreviewResponse:
    issues = blocking_issues or []
    warning_rows = warnings or []
    return OrderPreviewResponse(
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


def catalog_payload(item: ClinicalOrderCatalogItem | OrderCatalogItemResponse | None) -> dict[str, Any]:
    if item is None:
        return {}
    return {
        "catalog_item_id": item.catalog_item_id,
        "code": item.code,
        "name": item.name,
        "order_type": item.order_type,
        "default_priority": item.default_priority,
        "specimen_type": item.specimen_type,
    }


def order_create_preview(db: Session, payload: OrderCreatePreviewRequest) -> OrderPreviewResponse:
    patient = patient_by_identifier(db, payload.patient_id)
    encounter = encounter_by_id(db, payload.encounter_id)
    screening = screening_session_by_id(db, payload.screening_session_id)
    appointment = appointment_by_id(db, payload.appointment_id)
    catalog_item = catalog_item_by_id(db, payload.catalog_item_id)
    issues: list[OrderBlockingIssue] = []
    warnings: list[OrderWarning] = []

    if patient is None:
        issues.append(_issue("unknown_patient", "patient_id", "Patient/donor profile was not found."))
    if catalog_item is None:
        issues.append(_issue("unknown_catalog_item", "catalog_item_id", "Active order catalog item was not found."))
    if payload.encounter_id is not None and encounter is None:
        issues.append(_issue("unknown_encounter", "encounter_id", "Encounter was not found."))
    if payload.screening_session_id is not None and screening is None:
        issues.append(_issue("unknown_screening_session", "screening_session_id", "Screening session was not found."))
    if payload.appointment_id is not None and appointment is None:
        issues.append(_issue("unknown_appointment", "appointment_id", "Appointment was not found."))
    if patient and encounter and encounter.patient_pk != patient.patient_pk:
        issues.append(_issue("encounter_patient_mismatch", "encounter_id", "Encounter belongs to a different patient/donor."))
    if patient and screening and screening.patient_pk != patient.patient_pk:
        issues.append(_issue("screening_patient_mismatch", "screening_session_id", "Screening session belongs to a different patient/donor."))
    if patient and appointment and appointment.patient_pk != patient.patient_pk:
        issues.append(_issue("appointment_patient_mismatch", "appointment_id", "Appointment belongs to a different patient/donor."))
    if not encounter:
        warnings.append(_warning("no_encounter_context", "encounter_id", "Order will be created without encounter context."))
    if catalog_item and getattr(catalog_item, "order_type", "") == "infectious_disease":
        warnings.append(
            _warning(
                "legacy_infectious_result_context",
                "catalog_item_id",
                "This order references infectious disease testing while preserving the existing donor eligibility result facts.",
            )
        )

    changes = payload.model_dump(mode="json")
    changes["catalog_item"] = catalog_payload(catalog_item)
    return _preview(
        workflow="order.create",
        entity_type="clinical_order",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Clinical order is ready to place." if not issues else "Order preview found blocking issues.",
    )


def _result_workflow(payload: OrderResultPreviewRequest) -> str:
    return "order.result_correct" if payload.corrected_from_result_id else "order.result_add"


def result_preview(db: Session, order: ClinicalOrder, payload: OrderResultPreviewRequest) -> OrderPreviewResponse:
    issues: list[OrderBlockingIssue] = []
    warnings: list[OrderWarning] = []
    corrected_from = result_by_id(db, payload.corrected_from_result_id)
    if order.status == CANCELLED_ORDER_STATUS:
        issues.append(_issue("order_cancelled", "order_id", "Cancelled orders cannot receive new results."))
    if payload.corrected_from_result_id is not None and (corrected_from is None or corrected_from.order_id != order.order_id):
        issues.append(_issue("unknown_corrected_result", "corrected_from_result_id", "Corrected-from result was not found for this order."))
    if payload.result_status == "critical" and not payload.critical_flag:
        warnings.append(_warning("critical_status_without_flag", "critical_flag", "Critical result status will be treated as critical."))
    if payload.critical_flag:
        warnings.append(_warning("critical_ack_required", "critical_flag", "Critical results require acknowledgement."))
    elif payload.abnormal_flag or payload.result_status == "abnormal":
        warnings.append(_warning("abnormal_result", "abnormal_flag", "Abnormal result will be highlighted."))
    changes = payload.model_dump(mode="json")
    return _preview(
        workflow=_result_workflow(payload),
        entity_type="clinical_order_result",
        entity_id=order.order_number,
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Order result is ready to commit." if not issues else "Result preview found blocking issues.",
    )


def unacknowledged_critical_results(order: ClinicalOrder) -> list[ClinicalOrderResult]:
    acknowledged_result_ids = {
        acknowledgement.result_id
        for acknowledgement in order.acknowledgements
        if acknowledgement.result_id is not None
    }
    acknowledged_order = any(acknowledgement.result_id is None for acknowledgement in order.acknowledgements)
    if acknowledged_order:
        return []
    return [
        result
        for result in order.results
        if result.critical_flag and result.result_status != "cancelled" and result.result_id not in acknowledged_result_ids
    ]


def acknowledgement_preview(db: Session, order: ClinicalOrder, payload: OrderAcknowledgePreviewRequest) -> OrderPreviewResponse:
    issues: list[OrderBlockingIssue] = []
    warnings: list[OrderWarning] = []
    result = result_by_id(db, payload.result_id)
    critical_results = unacknowledged_critical_results(order)
    if order.status == CANCELLED_ORDER_STATUS:
        issues.append(_issue("order_cancelled", "order_id", "Cancelled orders cannot be acknowledged."))
    if payload.result_id is not None and (result is None or result.order_id != order.order_id):
        issues.append(_issue("unknown_result", "result_id", "Result was not found for this order."))
    if result and not result.critical_flag:
        warnings.append(_warning("non_critical_acknowledgement", "result_id", "Selected result is not critical."))
    if result and result.critical_flag and result.result_id not in {row.result_id for row in critical_results}:
        issues.append(_issue("critical_result_already_acknowledged", "result_id", "Selected critical result is already acknowledged."))
    if not critical_results and (result is None or not result.critical_flag):
        issues.append(_issue("no_unacknowledged_critical_result", "result_id", "No unacknowledged critical result was found."))
    changes = payload.model_dump(mode="json")
    changes["unacknowledged_critical_result_ids"] = [row.result_id for row in critical_results]
    return _preview(
        workflow="order.acknowledge",
        entity_type="clinical_order",
        entity_id=order.order_number,
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Critical result acknowledgement is ready to commit." if not issues else "Acknowledgement preview found blocking issues.",
    )


def cancellation_preview(order: ClinicalOrder, payload: OrderCancelPreviewRequest) -> OrderPreviewResponse:
    issues: list[OrderBlockingIssue] = []
    if order.status == CANCELLED_ORDER_STATUS:
        issues.append(_issue("already_cancelled", "order_id", "Order is already cancelled."))
    return _preview(
        workflow="order.cancel",
        entity_type="clinical_order",
        entity_id=order.order_number,
        changes=payload.model_dump(mode="json"),
        blocking_issues=issues,
        summary="Order cancellation is ready to commit." if not issues else "Cancellation preview found blocking issues.",
    )


def append_status_history(
    order: ClinicalOrder,
    *,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    order.status_history.append(
        ClinicalOrderStatusHistory(
            order_id=order.order_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            reason=reason,
            notes=notes,
        )
    )


def update_order_status(
    order: ClinicalOrder,
    *,
    next_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> tuple[str, str]:
    status_before = order.status
    if status_before != next_status:
        order.status = next_status
        append_status_history(
            order,
            from_status=status_before,
            to_status=next_status,
            user_id=user_id,
            reason=reason,
            notes=notes,
        )
    order.updated_by = user_id
    order.version += 1
    return status_before, order.status


def append_order_workflow_audit(
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


def order_changes(order: ClinicalOrder) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "order_number": order.order_number,
        "patient_id": order.patient_id,
        "encounter_id": order.encounter_id,
        "screening_session_id": order.screening_session_id,
        "appointment_id": order.appointment_id,
        "catalog_item_id": order.catalog_item_id,
        "order_type": order.order_type,
        "priority": order.priority,
        "status": order.status,
        "clinical_indication": order.clinical_indication,
        "ordering_provider": order.ordering_provider,
    }


def result_changes(result: ClinicalOrderResult) -> dict[str, Any]:
    return {
        "result_id": result.result_id,
        "order_id": result.order_id,
        "result_name": result.result_name,
        "result_value": result.result_value,
        "result_status": result.result_status,
        "abnormal_flag": result.abnormal_flag,
        "critical_flag": result.critical_flag,
        "corrected_from_result_id": result.corrected_from_result_id,
    }
