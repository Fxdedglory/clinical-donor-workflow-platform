from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import (
    ClinicalOrder,
    ClinicalOrderResult,
    ClinicalOrderResultAcknowledgement,
    Patient,
    User,
)
from app.schemas.clinical_orders import (
    OrderAcknowledgeCommitRequest,
    OrderAcknowledgePreviewRequest,
    OrderCancelCommitRequest,
    OrderCancelPreviewRequest,
    OrderCatalogItemResponse,
    OrderCommitResponse,
    OrderCreatePreviewRequest,
    OrderCreateRequest,
    OrderListResponse,
    OrderPreviewResponse,
    OrderResponse,
    OrderResultCommitRequest,
    OrderResultPreviewRequest,
)
from app.services.clinical_orders import (
    acknowledgement_preview,
    append_order_workflow_audit,
    append_status_history,
    appointment_by_id,
    catalog_item_by_id,
    list_catalog_items,
    new_order_number,
    now_utc,
    order_actor,
    order_by_id,
    order_changes,
    order_create_preview,
    patient_by_identifier,
    result_changes,
    result_preview,
    screening_session_by_id,
    unacknowledged_critical_results,
    update_order_status,
)
from app.services.clinical_orders import cancellation_preview as cancel_order_preview
from app.services.clinical_orders import encounter_by_id
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical/orders", tags=["Clinical Orders"])

READ_PERMISSIONS = {"system.admin", "orders.read", "orders.manage", "orders.acknowledge", "patients.read"}
MUTATION_PERMISSIONS = {"system.admin", "orders.manage"}
ACK_PERMISSIONS = {"system.admin", "orders.acknowledge", "orders.manage"}
EXTERNAL_ROLES = {"Partner External User", "Supplier External User"}


def _is_external_user(user: User) -> bool:
    return bool(
        user.is_external
        or user.external_user_flag
        or user.account_type in {"partner", "supplier", "external"}
        or user.user_type in {"partner", "supplier", "external"}
        or user.role in EXTERNAL_ROLES
    )


def _permission_set(db: Session, user: User) -> set[str]:
    return set(getattr(user, "permissions", []) or []) | set(get_user_permissions(db, user))


def require_order_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access clinical orders")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order read permission required")
    return current_user


def require_order_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate clinical orders")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order mutation permission required")
    return current_user


def require_order_acknowledgement(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot acknowledge clinical orders")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(ACK_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order acknowledgement permission required")
    return current_user


def _order_or_404(db: Session, order_id: int) -> ClinicalOrder:
    order = order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical order not found")
    return order


def _reject_blocking(preview: OrderPreviewResponse) -> None:
    if preview.blocking_issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "order_validation_failed",
                "message": "Blocking order issues prevent commit.",
                "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues],
            },
        )


@router.get("", response_model=OrderListResponse)
def list_orders(
    q: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    patient_id: str | None = Query(default=None),
    encounter_id: int | None = Query(default=None),
    priority: str | None = Query(default=None),
    result_flag: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_order_read),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    query = select(ClinicalOrder).where(ClinicalOrder.is_deleted.is_(False))
    joined_patient = False
    if date_filter:
        start_of_day = datetime.combine(date_filter, time.min)
        end_of_day = datetime.combine(date_filter, time.max)
        query = query.where(ClinicalOrder.ordered_at >= start_of_day, ClinicalOrder.ordered_at <= end_of_day)
    if status_filter:
        query = query.where(ClinicalOrder.status == status_filter)
    if patient_id:
        query = query.join(Patient)
        joined_patient = True
        query = query.where(Patient.patient_id == patient_id)
    if encounter_id is not None:
        query = query.where(ClinicalOrder.encounter_id == encounter_id)
    if priority:
        query = query.where(ClinicalOrder.priority == priority)
    if q:
        like = f"%{q.strip().lower()}%"
        if not joined_patient:
            query = query.join(Patient)
        query = query.where(
            or_(
                func.lower(ClinicalOrder.order_number).like(like),
                func.lower(ClinicalOrder.clinical_indication).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
                func.lower(Patient.donor_reference).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalOrder.updated_at.desc())).scalars().all())
    if result_flag:
        rows = [row for row in rows if row.result_flag == result_flag]
    return OrderListResponse(orders=rows[offset : offset + limit], total=len(rows))


@router.get("/catalog", response_model=list[OrderCatalogItemResponse])
def order_catalog(
    current_user: User = Depends(require_order_read),
    db: Session = Depends(get_db),
) -> list[object]:
    return list_catalog_items(db)


@router.post("/preview", response_model=OrderPreviewResponse)
def preview_create_order(
    payload: OrderCreatePreviewRequest,
    current_user: User = Depends(require_order_mutation),
    db: Session = Depends(get_db),
) -> OrderPreviewResponse:
    return order_create_preview(db, payload)


@router.post("", response_model=OrderCommitResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    request: Request,
    current_user: User = Depends(require_order_mutation),
    db: Session = Depends(get_db),
) -> OrderCommitResponse:
    require_generation_confirmation(request)
    preview = order_create_preview(db, payload)
    _reject_blocking(preview)
    patient = patient_by_identifier(db, payload.patient_id)
    catalog_item = catalog_item_by_id(db, payload.catalog_item_id)
    encounter = encounter_by_id(db, payload.encounter_id)
    screening = screening_session_by_id(db, payload.screening_session_id)
    appointment = appointment_by_id(db, payload.appointment_id)
    if not patient or not catalog_item:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order context changed after preview")
    order = ClinicalOrder(
        order_number=new_order_number(),
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_id=encounter.encounter_id if encounter else None,
        encounter=encounter,
        screening_session_id=screening.session_id if screening else None,
        screening_session=screening,
        appointment_id=appointment.appointment_id if appointment else None,
        appointment=appointment,
        catalog_item_id=catalog_item.catalog_item_id,
        catalog_item=catalog_item,
        order_type=payload.order_type or catalog_item.order_type,
        priority=payload.priority or catalog_item.default_priority,
        status="ordered",
        clinical_indication=payload.clinical_indication,
        ordering_provider=payload.ordering_provider,
        ordered_at=payload.ordered_at or now_utc(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    append_status_history(
        order,
        from_status=None,
        to_status="ordered",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Clinical order created",
    )
    db.add(order)
    db.flush()
    db.commit()
    db.refresh(order)
    operation, audit_path = append_order_workflow_audit(
        workflow="order.create",
        entity_type="clinical_order",
        entity_id=order.order_number,
        actor=order_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=order.status,
        reason=payload.reason,
        changes=order_changes(order),
    )
    return OrderCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, order=order)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    current_user: User = Depends(require_order_read),
    db: Session = Depends(get_db),
) -> ClinicalOrder:
    return _order_or_404(db, order_id)


@router.post("/{order_id}/results/preview", response_model=OrderPreviewResponse)
def preview_add_result(
    order_id: int,
    payload: OrderResultPreviewRequest,
    current_user: User = Depends(require_order_mutation),
    db: Session = Depends(get_db),
) -> OrderPreviewResponse:
    order = _order_or_404(db, order_id)
    return result_preview(db, order, payload)


@router.post("/{order_id}/results", response_model=OrderCommitResponse)
def add_result(
    order_id: int,
    payload: OrderResultCommitRequest,
    request: Request,
    current_user: User = Depends(require_order_mutation),
    db: Session = Depends(get_db),
) -> OrderCommitResponse:
    require_generation_confirmation(request)
    order = _order_or_404(db, order_id)
    preview = result_preview(db, order, payload)
    _reject_blocking(preview)
    status_before = order.status
    result_status = "corrected" if payload.corrected_from_result_id else payload.result_status
    result = ClinicalOrderResult(
        order_id=order.order_id,
        result_name=payload.result_name,
        result_value=payload.result_value,
        result_unit=payload.result_unit,
        reference_range=payload.reference_range,
        result_status=result_status,
        abnormal_flag=payload.abnormal_flag or payload.result_status in {"abnormal", "critical"},
        critical_flag=payload.critical_flag or payload.result_status == "critical",
        resulted_at=payload.resulted_at or now_utc(),
        resulted_by=current_user.user_id,
        notes=payload.notes,
        corrected_from_result_id=payload.corrected_from_result_id,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    order.results.append(result)
    update_order_status(
        order,
        next_status="resulted",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Order result entered",
    )
    db.flush()
    db.commit()
    db.refresh(order)
    operation, audit_path = append_order_workflow_audit(
        workflow=preview.workflow,
        entity_type="clinical_order_result",
        entity_id=str(result.result_id),
        actor=order_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=order.status,
        reason=payload.reason,
        changes=result_changes(result),
    )
    return OrderCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, order=order, result=result)


@router.post("/{order_id}/acknowledge/preview", response_model=OrderPreviewResponse)
def preview_acknowledge_result(
    order_id: int,
    payload: OrderAcknowledgePreviewRequest,
    current_user: User = Depends(require_order_acknowledgement),
    db: Session = Depends(get_db),
) -> OrderPreviewResponse:
    order = _order_or_404(db, order_id)
    return acknowledgement_preview(db, order, payload)


@router.post("/{order_id}/acknowledge", response_model=OrderCommitResponse)
def acknowledge_result(
    order_id: int,
    payload: OrderAcknowledgeCommitRequest,
    request: Request,
    current_user: User = Depends(require_order_acknowledgement),
    db: Session = Depends(get_db),
) -> OrderCommitResponse:
    require_generation_confirmation(request)
    order = _order_or_404(db, order_id)
    preview = acknowledgement_preview(db, order, payload)
    _reject_blocking(preview)
    status_before = order.status
    result_id = payload.result_id
    if result_id is None:
        result_id = next((result.result_id for result in unacknowledged_critical_results(order)), None)
    acknowledgement = ClinicalOrderResultAcknowledgement(
        order_id=order.order_id,
        result_id=result_id,
        acknowledged_at=now_utc(),
        acknowledged_by=current_user.user_id,
        acknowledgement_note=payload.acknowledgement_note,
        created_by=current_user.user_id,
    )
    order.acknowledgements.append(acknowledgement)
    append_status_history(
        order,
        from_status=order.status,
        to_status=order.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Critical order result acknowledged",
    )
    order.updated_by = current_user.user_id
    order.version += 1
    db.flush()
    db.commit()
    db.refresh(order)
    operation, audit_path = append_order_workflow_audit(
        workflow="order.acknowledge",
        entity_type="clinical_order",
        entity_id=order.order_number,
        actor=order_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=order.status,
        reason=payload.reason,
        changes={
            "order_id": order.order_id,
            "result_id": result_id,
            "acknowledgement_id": acknowledgement.acknowledgement_id,
            "acknowledgement_note": payload.acknowledgement_note,
        },
    )
    return OrderCommitResponse(
        operation_id=operation.operation_id,
        audit_path=audit_path,
        order=order,
        acknowledgement=acknowledgement,
    )


@router.post("/{order_id}/cancel/preview", response_model=OrderPreviewResponse)
def preview_cancel_order(
    order_id: int,
    payload: OrderCancelPreviewRequest,
    current_user: User = Depends(require_order_mutation),
    db: Session = Depends(get_db),
) -> OrderPreviewResponse:
    order = _order_or_404(db, order_id)
    return cancel_order_preview(order, payload)


@router.post("/{order_id}/cancel", response_model=OrderCommitResponse)
def cancel_order(
    order_id: int,
    payload: OrderCancelCommitRequest,
    request: Request,
    current_user: User = Depends(require_order_mutation),
    db: Session = Depends(get_db),
) -> OrderCommitResponse:
    require_generation_confirmation(request)
    order = _order_or_404(db, order_id)
    preview = cancel_order_preview(order, payload)
    _reject_blocking(preview)
    status_before = order.status
    order.cancelled_at = now_utc()
    order.cancelled_by = current_user.user_id
    order.cancellation_reason = payload.cancellation_reason
    update_order_status(
        order,
        next_status="cancelled",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes=payload.cancellation_reason,
    )
    db.flush()
    db.commit()
    db.refresh(order)
    operation, audit_path = append_order_workflow_audit(
        workflow="order.cancel",
        entity_type="clinical_order",
        entity_id=order.order_number,
        actor=order_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=order.status,
        reason=payload.reason,
        changes={"order_id": order.order_id, "cancellation_reason": payload.cancellation_reason},
    )
    return OrderCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, order=order)
