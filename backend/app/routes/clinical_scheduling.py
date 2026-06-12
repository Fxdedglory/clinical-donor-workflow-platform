from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import (
    Appointment,
    AppointmentType,
    ClinicalEquipment,
    ClinicalProvider,
    ClinicalRoom,
    Patient,
    User,
)
from app.schemas.clinical_scheduling import (
    AppointmentCancelPreviewRequest,
    AppointmentCancelRequest,
    AppointmentCheckInPreviewRequest,
    AppointmentCheckInRequest,
    AppointmentCommitResponse,
    AppointmentCreatePreviewRequest,
    AppointmentCreateRequest,
    AppointmentListResponse,
    AppointmentNoShowPreviewRequest,
    AppointmentNoShowRequest,
    AppointmentPreviewResponse,
    AppointmentResponse,
    AppointmentReschedulePreviewRequest,
    AppointmentRescheduleRequest,
    AppointmentTypeResponse,
    SchedulingResourceItem,
    SchedulingResourceResponse,
)
from app.services.clinical_scheduling import (
    append_appointment_workflow_audit,
    append_status_history,
    appointment_by_id,
    appointment_type_by_id,
    equipment_by_ids,
    new_appointment_number,
    now_utc,
    patient_by_identifier,
    preview_appointment_create,
    preview_appointment_reschedule,
    preview_status_transition,
    provider_by_id,
    replace_appointment_resources,
    room_by_id,
    scheduling_actor,
)
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical/scheduling", tags=["Clinical Scheduling"])

READ_PERMISSIONS = {"system.admin", "scheduling.read", "scheduling.manage", "patients.read", "patients.manage"}
MUTATION_PERMISSIONS = {"system.admin", "scheduling.manage"}
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


def require_scheduling_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access scheduling")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Scheduling read permission required")
    return current_user


def require_scheduling_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate scheduling")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Scheduling mutation permission required")
    return current_user


def _appointment_or_404(db: Session, appointment_id: int) -> Appointment:
    appointment = appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


def _reject_failed_preview(preview: AppointmentPreviewResponse) -> None:
    if any(conflict.blocking for conflict in preview.conflicts):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "scheduling_conflict",
                "message": "Blocking scheduling conflicts prevent commit.",
                "conflicts": [conflict.model_dump(mode="json") for conflict in preview.conflicts],
            },
        )


def _appointment_changes(appointment: Appointment) -> dict[str, object]:
    return {
        "appointment_number": appointment.appointment_number,
        "patient_id": appointment.patient_id,
        "provider_id": appointment.provider_id,
        "room_id": appointment.room_id,
        "appointment_type_id": appointment.appointment_type_id,
        "equipment_ids": appointment.equipment_ids,
        "scheduled_start": appointment.scheduled_start.isoformat(),
        "scheduled_end": appointment.scheduled_end.isoformat(),
        "status": appointment.status,
        "reason": appointment.reason,
    }


@router.get("/appointments", response_model=AppointmentListResponse)
def list_appointments(
    q: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    provider_id: int | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_scheduling_read),
    db: Session = Depends(get_db),
) -> AppointmentListResponse:
    query = select(Appointment).where(Appointment.is_deleted.is_(False))
    if date_filter:
        start_of_day = datetime.combine(date_filter, time.min)
        end_of_day = datetime.combine(date_filter, time.max)
        query = query.where(Appointment.scheduled_start >= start_of_day, Appointment.scheduled_start <= end_of_day)
    if status_filter:
        query = query.where(Appointment.status == status_filter)
    if provider_id:
        query = query.where(Appointment.provider_id == provider_id)
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.join(Patient).where(
            or_(
                func.lower(Appointment.appointment_number).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
            )
        )
    rows = list(db.execute(query.order_by(Appointment.scheduled_start.desc()).offset(offset).limit(limit)).scalars().all())
    return AppointmentListResponse(appointments=rows, total=len(rows))


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(require_scheduling_read),
    db: Session = Depends(get_db),
) -> Appointment:
    return _appointment_or_404(db, appointment_id)


@router.post("/appointments/preview", response_model=AppointmentPreviewResponse)
def preview_create_appointment(
    payload: AppointmentCreatePreviewRequest,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentPreviewResponse:
    return preview_appointment_create(db, payload)


@router.post("/appointments", response_model=AppointmentCommitResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreateRequest,
    request: Request,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentCommitResponse:
    require_generation_confirmation(request)
    preview = preview_appointment_create(db, payload)
    _reject_failed_preview(preview)

    patient = patient_by_identifier(db, payload.patient_id)
    provider = provider_by_id(db, payload.provider_id)
    room = room_by_id(db, payload.room_id)
    appointment_type = appointment_type_by_id(db, payload.appointment_type_id)
    equipment = equipment_by_ids(db, payload.equipment_ids)
    if not patient or not provider or not appointment_type or len(equipment) != len(set(payload.equipment_ids)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scheduling references changed after preview")
    appointment = Appointment(
        appointment_number=new_appointment_number(),
        patient_pk=patient.patient_pk,
        patient=patient,
        provider_id=payload.provider_id,
        provider=provider,
        room_id=payload.room_id,
        room=room,
        appointment_type_id=payload.appointment_type_id,
        appointment_type=appointment_type,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        status="scheduled",
        reason=payload.reason,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    replace_appointment_resources(appointment, payload.equipment_ids, current_user.user_id)
    append_status_history(
        appointment,
        from_status=None,
        to_status="scheduled",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Appointment booked",
    )
    db.add(appointment)
    db.flush()
    db.commit()
    db.refresh(appointment)
    preview_value = payload.preview_hash or preview.preview_hash
    operation, audit_path = append_appointment_workflow_audit(
        workflow="appointment.book",
        appointment=appointment,
        actor=scheduling_actor(current_user),
        preview_value=preview_value,
        status_before=None,
        status_after=appointment.status,
        reason=payload.reason,
        changes=_appointment_changes(appointment),
    )
    return AppointmentCommitResponse(appointment=appointment, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/{appointment_id}/reschedule/preview", response_model=AppointmentPreviewResponse)
def preview_reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedulePreviewRequest,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentPreviewResponse:
    appointment = _appointment_or_404(db, appointment_id)
    return preview_appointment_reschedule(db, appointment, payload)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentCommitResponse)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentRescheduleRequest,
    request: Request,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentCommitResponse:
    require_generation_confirmation(request)
    appointment = _appointment_or_404(db, appointment_id)
    status_before = appointment.status
    preview = preview_appointment_reschedule(db, appointment, payload)
    _reject_failed_preview(preview)
    provider_id = payload.provider_id or appointment.provider_id
    room_id = appointment.room_id if payload.room_id is None else payload.room_id
    appointment_type_id = payload.appointment_type_id or appointment.appointment_type_id
    equipment_ids = appointment.equipment_ids if payload.equipment_ids is None else payload.equipment_ids
    provider = provider_by_id(db, provider_id)
    room = room_by_id(db, room_id)
    appointment_type = appointment_type_by_id(db, appointment_type_id)
    if not provider or not appointment_type:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scheduling references changed after preview")

    changes = preview.changes
    appointment.provider_id = provider_id
    appointment.provider = provider
    appointment.room_id = room_id
    appointment.room = room
    appointment.appointment_type_id = appointment_type_id
    appointment.appointment_type = appointment_type
    appointment.scheduled_start = payload.scheduled_start
    appointment.scheduled_end = payload.scheduled_end
    appointment.status = "rescheduled"
    appointment.reason = payload.reason
    appointment.updated_by = current_user.user_id
    appointment.version += 1
    replace_appointment_resources(appointment, equipment_ids, current_user.user_id)
    append_status_history(
        appointment,
        from_status=status_before,
        to_status="rescheduled",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Appointment rescheduled",
    )
    db.flush()
    db.commit()
    db.refresh(appointment)
    operation, audit_path = append_appointment_workflow_audit(
        workflow="appointment.reschedule",
        appointment=appointment,
        actor=scheduling_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=appointment.status,
        reason=payload.reason,
        changes=changes,
    )
    return AppointmentCommitResponse(appointment=appointment, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/{appointment_id}/cancel/preview", response_model=AppointmentPreviewResponse)
def preview_cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancelPreviewRequest,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentPreviewResponse:
    appointment = _appointment_or_404(db, appointment_id)
    return preview_status_transition(appointment, payload, workflow="appointment.cancel", target_status="cancelled")


@router.post("/{appointment_id}/cancel", response_model=AppointmentCommitResponse)
def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancelRequest,
    request: Request,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentCommitResponse:
    require_generation_confirmation(request)
    appointment = _appointment_or_404(db, appointment_id)
    status_before = appointment.status
    preview = preview_status_transition(appointment, payload, workflow="appointment.cancel", target_status="cancelled")
    _reject_failed_preview(preview)
    appointment.status = "cancelled"
    appointment.cancellation_reason = payload.cancellation_reason
    appointment.updated_by = current_user.user_id
    appointment.version += 1
    append_status_history(
        appointment,
        from_status=status_before,
        to_status="cancelled",
        user_id=current_user.user_id,
        reason=payload.cancellation_reason,
        notes="Appointment cancelled",
    )
    db.flush()
    db.commit()
    db.refresh(appointment)
    operation, audit_path = append_appointment_workflow_audit(
        workflow="appointment.cancel",
        appointment=appointment,
        actor=scheduling_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=appointment.status,
        reason=payload.cancellation_reason,
        changes=preview.changes,
    )
    return AppointmentCommitResponse(appointment=appointment, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/{appointment_id}/check-in/preview", response_model=AppointmentPreviewResponse)
def preview_check_in_appointment(
    appointment_id: int,
    payload: AppointmentCheckInPreviewRequest,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentPreviewResponse:
    appointment = _appointment_or_404(db, appointment_id)
    return preview_status_transition(appointment, payload, workflow="appointment.check_in", target_status="checked_in")


@router.post("/{appointment_id}/check-in", response_model=AppointmentCommitResponse)
def check_in_appointment(
    appointment_id: int,
    payload: AppointmentCheckInRequest,
    request: Request,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentCommitResponse:
    require_generation_confirmation(request)
    appointment = _appointment_or_404(db, appointment_id)
    status_before = appointment.status
    preview = preview_status_transition(appointment, payload, workflow="appointment.check_in", target_status="checked_in")
    _reject_failed_preview(preview)
    appointment.status = "checked_in"
    appointment.check_in_time = payload.check_in_time or now_utc()
    appointment.updated_by = current_user.user_id
    appointment.version += 1
    append_status_history(
        appointment,
        from_status=status_before,
        to_status="checked_in",
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Appointment checked in",
    )
    db.flush()
    db.commit()
    db.refresh(appointment)
    operation, audit_path = append_appointment_workflow_audit(
        workflow="appointment.check_in",
        appointment=appointment,
        actor=scheduling_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=appointment.status,
        reason=payload.reason,
        changes=preview.changes,
    )
    return AppointmentCommitResponse(appointment=appointment, operation_id=operation.operation_id, audit_path=audit_path)


@router.post("/{appointment_id}/no-show/preview", response_model=AppointmentPreviewResponse)
def preview_no_show_appointment(
    appointment_id: int,
    payload: AppointmentNoShowPreviewRequest,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentPreviewResponse:
    appointment = _appointment_or_404(db, appointment_id)
    return preview_status_transition(appointment, payload, workflow="appointment.no_show", target_status="no_show")


@router.post("/{appointment_id}/no-show", response_model=AppointmentCommitResponse)
def no_show_appointment(
    appointment_id: int,
    payload: AppointmentNoShowRequest,
    request: Request,
    current_user: User = Depends(require_scheduling_mutation),
    db: Session = Depends(get_db),
) -> AppointmentCommitResponse:
    require_generation_confirmation(request)
    appointment = _appointment_or_404(db, appointment_id)
    status_before = appointment.status
    preview = preview_status_transition(appointment, payload, workflow="appointment.no_show", target_status="no_show")
    _reject_failed_preview(preview)
    appointment.status = "no_show"
    appointment.no_show_reason = payload.no_show_reason
    appointment.updated_by = current_user.user_id
    appointment.version += 1
    append_status_history(
        appointment,
        from_status=status_before,
        to_status="no_show",
        user_id=current_user.user_id,
        reason=payload.no_show_reason,
        notes="Appointment marked no-show",
    )
    db.flush()
    db.commit()
    db.refresh(appointment)
    operation, audit_path = append_appointment_workflow_audit(
        workflow="appointment.no_show",
        appointment=appointment,
        actor=scheduling_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=appointment.status,
        reason=payload.no_show_reason,
        changes=preview.changes,
    )
    return AppointmentCommitResponse(appointment=appointment, operation_id=operation.operation_id, audit_path=audit_path)


@router.get("/resources", response_model=SchedulingResourceResponse)
def scheduling_resources(
    current_user: User = Depends(require_scheduling_read),
    db: Session = Depends(get_db),
) -> SchedulingResourceResponse:
    providers = list(
        db.execute(
            select(ClinicalProvider)
            .where(ClinicalProvider.is_deleted.is_(False))
            .order_by(ClinicalProvider.full_name)
        )
        .scalars()
        .all()
    )
    rooms = list(
        db.execute(select(ClinicalRoom).where(ClinicalRoom.is_deleted.is_(False)).order_by(ClinicalRoom.room_name))
        .scalars()
        .all()
    )
    equipment = list(
        db.execute(
            select(ClinicalEquipment)
            .where(ClinicalEquipment.is_deleted.is_(False))
            .order_by(ClinicalEquipment.equipment_name)
        )
        .scalars()
        .all()
    )
    return SchedulingResourceResponse(
        providers=[
            SchedulingResourceItem(
                id=provider.provider_id,
                code=provider.provider_code,
                name=provider.full_name,
                category=provider.role,
                status=provider.status,
            )
            for provider in providers
        ],
        rooms=[
            SchedulingResourceItem(
                id=room.room_id,
                code=room.room_code,
                name=room.room_name,
                category=room.location or "room",
                status=room.status,
            )
            for room in rooms
        ],
        equipment=[
            SchedulingResourceItem(
                id=item.equipment_id,
                code=item.equipment_code,
                name=item.equipment_name,
                category=item.equipment_type,
                status=item.status,
            )
            for item in equipment
        ],
    )


@router.get("/appointment-types", response_model=list[AppointmentTypeResponse])
def appointment_types(
    current_user: User = Depends(require_scheduling_read),
    db: Session = Depends(get_db),
) -> list[AppointmentType]:
    return list(
        db.execute(
            select(AppointmentType)
            .where(AppointmentType.is_deleted.is_(False))
            .order_by(AppointmentType.name)
        )
        .scalars()
        .all()
    )
