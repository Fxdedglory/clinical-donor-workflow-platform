from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentResource,
    AppointmentStatusHistory,
    AppointmentType,
    ClinicalEquipment,
    ClinicalProvider,
    ClinicalRoom,
    Patient,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_scheduling import (
    AppointmentCancelPreviewRequest,
    AppointmentCheckInPreviewRequest,
    AppointmentCreatePreviewRequest,
    AppointmentNoShowPreviewRequest,
    AppointmentPreviewResponse,
    AppointmentReschedulePreviewRequest,
    SchedulingConflict,
    SchedulingWarning,
)
from app.services.clinical_patients import actor_label, patient_name
from app.services.clinical_workflows import append_workflow_operation, preview_hash

ACTIVE_CONFLICT_STATUSES = {"scheduled", "checked_in", "rescheduled"}
SCHEDULED_ONLY_TRANSITIONS = {"cancelled", "checked_in", "no_show", "rescheduled"}
NORMAL_START_HOUR = 8
NORMAL_END_HOUR = 17


def new_appointment_number() -> str:
    return f"APT-{uuid4().hex[:10].upper()}"


def _all_rows(db: Session, statement) -> list[Any]:
    return list(db.execute(statement).scalars().all())


def _one_or_none(db: Session, statement) -> Any | None:
    return db.execute(statement).scalar_one_or_none()


def patient_by_identifier(db: Session, patient_id: str) -> Patient | None:
    return _one_or_none(db, select(Patient).where(Patient.patient_id == patient_id, Patient.is_deleted.is_(False)))


def provider_by_id(db: Session, provider_id: int) -> ClinicalProvider | None:
    return _one_or_none(
        db,
        select(ClinicalProvider).where(
            ClinicalProvider.provider_id == provider_id,
            ClinicalProvider.is_deleted.is_(False),
        ),
    )


def room_by_id(db: Session, room_id: int | None) -> ClinicalRoom | None:
    if room_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalRoom).where(ClinicalRoom.room_id == room_id, ClinicalRoom.is_deleted.is_(False)),
    )


def appointment_type_by_id(db: Session, appointment_type_id: int) -> AppointmentType | None:
    return _one_or_none(
        db,
        select(AppointmentType).where(
            AppointmentType.appointment_type_id == appointment_type_id,
            AppointmentType.is_deleted.is_(False),
        ),
    )


def equipment_by_ids(db: Session, equipment_ids: list[int]) -> list[ClinicalEquipment]:
    if not equipment_ids:
        return []
    return _all_rows(
        db,
        select(ClinicalEquipment).where(
            ClinicalEquipment.equipment_id.in_(equipment_ids),
            ClinicalEquipment.is_deleted.is_(False),
        ),
    )


def appointment_by_id(db: Session, appointment_id: int) -> Appointment | None:
    return _one_or_none(
        db,
        select(Appointment).where(Appointment.appointment_id == appointment_id, Appointment.is_deleted.is_(False)),
    )


def _duration_minutes(scheduled_start: datetime, scheduled_end: datetime) -> int:
    return int((scheduled_end - scheduled_start).total_seconds() // 60)


def _outside_normal_hours(scheduled_start: datetime, scheduled_end: datetime) -> bool:
    if scheduled_start.weekday() >= 5 or scheduled_end.weekday() >= 5:
        return True
    starts_before_open = scheduled_start.hour < NORMAL_START_HOUR
    ends_after_close = scheduled_end.hour > NORMAL_END_HOUR or (
        scheduled_end.hour == NORMAL_END_HOUR and (scheduled_end.minute > 0 or scheduled_end.second > 0)
    )
    return starts_before_open or ends_after_close


def _equipment_names(equipment: list[ClinicalEquipment], requested_ids: list[int]) -> list[str]:
    by_id = {item.equipment_id: item for item in equipment}
    names = []
    for equipment_id in requested_ids:
        item = by_id.get(equipment_id)
        names.append(item.equipment_name if item else f"Equipment {equipment_id}")
    return names


def _resource_conflicts(
    db: Session,
    *,
    scheduled_start: datetime,
    scheduled_end: datetime,
    patient: Patient | None,
    provider_id: int,
    room_id: int | None,
    equipment_ids: list[int],
    exclude_appointment_id: int | None = None,
) -> list[SchedulingConflict]:
    conflicts: list[SchedulingConflict] = []
    if scheduled_end <= scheduled_start:
        return [
            SchedulingConflict(
                conflict_type="invalid_time",
                entity_type="appointment",
                entity_id="draft",
                message="Scheduled end must be after scheduled start.",
            )
        ]

    query = select(Appointment).where(
        Appointment.is_deleted.is_(False),
        Appointment.status.in_(ACTIVE_CONFLICT_STATUSES),
        Appointment.scheduled_start < scheduled_end,
        Appointment.scheduled_end > scheduled_start,
    )
    appointments = _all_rows(db, query)
    requested_equipment = set(equipment_ids)
    for appointment in appointments:
        if exclude_appointment_id is not None and appointment.appointment_id == exclude_appointment_id:
            continue
        if appointment.status not in ACTIVE_CONFLICT_STATUSES:
            continue
        if not (appointment.scheduled_start < scheduled_end and appointment.scheduled_end > scheduled_start):
            continue
        appointment_ref = appointment.appointment_number or str(appointment.appointment_id)
        if appointment.provider_id == provider_id:
            conflicts.append(
                SchedulingConflict(
                    conflict_type="provider_overlap",
                    entity_type="appointment",
                    entity_id=appointment_ref,
                    message=f"Provider is already scheduled for {appointment_ref}.",
                )
            )
        if room_id is not None and appointment.room_id == room_id:
            conflicts.append(
                SchedulingConflict(
                    conflict_type="room_overlap",
                    entity_type="appointment",
                    entity_id=appointment_ref,
                    message=f"Room is already reserved for {appointment_ref}.",
                )
            )
        if patient is not None and appointment.patient_pk == patient.patient_pk:
            conflicts.append(
                SchedulingConflict(
                    conflict_type="patient_overlap",
                    entity_type="appointment",
                    entity_id=appointment_ref,
                    message=f"Patient/donor is already scheduled for {appointment_ref}.",
                )
            )
        appointment_equipment = {resource.equipment_id for resource in appointment.resources}
        for equipment_id in requested_equipment & appointment_equipment:
            conflicts.append(
                SchedulingConflict(
                    conflict_type="equipment_overlap",
                    entity_type="appointment",
                    entity_id=appointment_ref,
                    message=f"Equipment {equipment_id} is already reserved for {appointment_ref}.",
                )
            )
    return conflicts


def _schedule_warnings(
    *,
    scheduled_start: datetime,
    scheduled_end: datetime,
    appointment_type: AppointmentType | None,
) -> list[SchedulingWarning]:
    warnings: list[SchedulingWarning] = []
    if appointment_type and scheduled_end > scheduled_start:
        requested_duration = _duration_minutes(scheduled_start, scheduled_end)
        if requested_duration != appointment_type.default_duration_minutes:
            warnings.append(
                SchedulingWarning(
                    warning_type="duration_mismatch",
                    field="scheduled_end",
                    message=(
                        f"Requested duration is {requested_duration} minutes; "
                        f"{appointment_type.name} defaults to {appointment_type.default_duration_minutes} minutes."
                    ),
                )
            )
    if scheduled_end > scheduled_start and _outside_normal_hours(scheduled_start, scheduled_end):
        warnings.append(
            SchedulingWarning(
                warning_type="outside_normal_hours",
                field="scheduled_start",
                message="Appointment is outside normal weekday operating hours.",
            )
        )
    return warnings


def _validation_status(conflicts: list[SchedulingConflict], warnings: list[SchedulingWarning]) -> str:
    if any(conflict.blocking for conflict in conflicts):
        return "failed"
    if warnings:
        return "warning"
    return "passed"


def _create_preview_response(
    *,
    workflow: str,
    entity_id: str,
    changes: dict[str, Any],
    conflicts: list[SchedulingConflict],
    warnings: list[SchedulingWarning],
    patient: Patient | None,
    provider: ClinicalProvider | None,
    room: ClinicalRoom | None,
    equipment: list[ClinicalEquipment],
    equipment_ids: list[int],
    scheduled_start: datetime,
    scheduled_end: datetime,
) -> AppointmentPreviewResponse:
    status = _validation_status(conflicts, warnings)
    if status == "failed":
        summary = "Scheduling preview found blocking conflicts."
    elif status == "warning":
        summary = "Scheduling preview passed with warnings."
    else:
        summary = "Scheduling preview passed."
    return AppointmentPreviewResponse(
        workflow=workflow,
        entity_id=entity_id,
        preview_hash=preview_hash({"workflow": workflow, "entity_id": entity_id, "changes": changes}),
        validation_status=status,
        conflicts=conflicts,
        warnings=warnings,
        summary=summary,
        changes=changes,
        selected_patient=patient_name(patient) if patient else None,
        selected_provider=provider.full_name if provider else None,
        selected_room=room.room_name if room else None,
        selected_equipment=_equipment_names(equipment, equipment_ids),
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
    )


def preview_appointment_create(db: Session, payload: AppointmentCreatePreviewRequest) -> AppointmentPreviewResponse:
    patient = patient_by_identifier(db, payload.patient_id)
    provider = provider_by_id(db, payload.provider_id)
    room = room_by_id(db, payload.room_id)
    appointment_type = appointment_type_by_id(db, payload.appointment_type_id)
    equipment = equipment_by_ids(db, payload.equipment_ids)

    conflicts: list[SchedulingConflict] = []
    if patient is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_patient",
                entity_type="patient",
                entity_id=payload.patient_id,
                message="Patient/donor profile was not found.",
            )
        )
    if provider is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_provider",
                entity_type="provider",
                entity_id=str(payload.provider_id),
                message="Provider was not found.",
            )
        )
    if payload.room_id is not None and room is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_room",
                entity_type="room",
                entity_id=str(payload.room_id),
                message="Room was not found.",
            )
        )
    if appointment_type is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_appointment_type",
                entity_type="appointment_type",
                entity_id=str(payload.appointment_type_id),
                message="Appointment type was not found.",
            )
        )
    elif appointment_type.requires_room and payload.room_id is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="room_required",
                entity_type="room",
                entity_id="missing",
                message=f"{appointment_type.name} requires a room.",
            )
        )
    found_equipment_ids = {item.equipment_id for item in equipment}
    for equipment_id in set(payload.equipment_ids) - found_equipment_ids:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_equipment",
                entity_type="equipment",
                entity_id=str(equipment_id),
                message=f"Equipment {equipment_id} was not found.",
            )
        )
    if patient is not None and provider is not None:
        conflicts.extend(
            _resource_conflicts(
                db,
                scheduled_start=payload.scheduled_start,
                scheduled_end=payload.scheduled_end,
                patient=patient,
                provider_id=payload.provider_id,
                room_id=payload.room_id,
                equipment_ids=payload.equipment_ids,
            )
        )
    elif payload.scheduled_end <= payload.scheduled_start:
        conflicts.extend(
            _resource_conflicts(
                db,
                scheduled_start=payload.scheduled_start,
                scheduled_end=payload.scheduled_end,
                patient=patient,
                provider_id=payload.provider_id,
                room_id=payload.room_id,
                equipment_ids=payload.equipment_ids,
            )
        )
    warnings = _schedule_warnings(
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        appointment_type=appointment_type,
    )
    return _create_preview_response(
        workflow="appointment.book",
        entity_id="draft",
        changes=payload.model_dump(mode="json"),
        conflicts=conflicts,
        warnings=warnings,
        patient=patient,
        provider=provider,
        room=room,
        equipment=equipment,
        equipment_ids=payload.equipment_ids,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
    )


def preview_appointment_reschedule(
    db: Session,
    appointment: Appointment,
    payload: AppointmentReschedulePreviewRequest,
) -> AppointmentPreviewResponse:
    provider_id = payload.provider_id or appointment.provider_id
    room_id = appointment.room_id if payload.room_id is None else payload.room_id
    appointment_type_id = payload.appointment_type_id or appointment.appointment_type_id
    equipment_ids = appointment.equipment_ids if payload.equipment_ids is None else payload.equipment_ids
    provider = provider_by_id(db, provider_id)
    room = room_by_id(db, room_id)
    appointment_type = appointment_type_by_id(db, appointment_type_id)
    equipment = equipment_by_ids(db, equipment_ids)
    patient = appointment.patient

    conflicts: list[SchedulingConflict] = []
    if appointment.status != "scheduled":
        conflicts.append(
            SchedulingConflict(
                conflict_type="invalid_transition",
                entity_type="appointment",
                entity_id=appointment.appointment_number,
                message=f"Cannot reschedule appointment from status {appointment.status}.",
            )
        )
    if provider is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_provider",
                entity_type="provider",
                entity_id=str(provider_id),
                message="Provider was not found.",
            )
        )
    if room_id is not None and room is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_room",
                entity_type="room",
                entity_id=str(room_id),
                message="Room was not found.",
            )
        )
    if appointment_type is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_appointment_type",
                entity_type="appointment_type",
                entity_id=str(appointment_type_id),
                message="Appointment type was not found.",
            )
        )
    elif appointment_type.requires_room and room_id is None:
        conflicts.append(
            SchedulingConflict(
                conflict_type="room_required",
                entity_type="room",
                entity_id="missing",
                message=f"{appointment_type.name} requires a room.",
            )
        )
    found_equipment_ids = {item.equipment_id for item in equipment}
    for equipment_id in set(equipment_ids) - found_equipment_ids:
        conflicts.append(
            SchedulingConflict(
                conflict_type="unknown_equipment",
                entity_type="equipment",
                entity_id=str(equipment_id),
                message=f"Equipment {equipment_id} was not found.",
            )
        )
    if provider is not None:
        conflicts.extend(
            _resource_conflicts(
                db,
                scheduled_start=payload.scheduled_start,
                scheduled_end=payload.scheduled_end,
                patient=patient,
                provider_id=provider_id,
                room_id=room_id,
                equipment_ids=equipment_ids,
                exclude_appointment_id=appointment.appointment_id,
            )
        )
    elif payload.scheduled_end <= payload.scheduled_start:
        conflicts.extend(
            _resource_conflicts(
                db,
                scheduled_start=payload.scheduled_start,
                scheduled_end=payload.scheduled_end,
                patient=patient,
                provider_id=provider_id,
                room_id=room_id,
                equipment_ids=equipment_ids,
                exclude_appointment_id=appointment.appointment_id,
            )
        )
    warnings = _schedule_warnings(
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        appointment_type=appointment_type,
    )
    changes = {
        "scheduled_start": {"before": appointment.scheduled_start.isoformat(), "after": payload.scheduled_start.isoformat()},
        "scheduled_end": {"before": appointment.scheduled_end.isoformat(), "after": payload.scheduled_end.isoformat()},
        "provider_id": {"before": appointment.provider_id, "after": provider_id},
        "room_id": {"before": appointment.room_id, "after": room_id},
        "appointment_type_id": {"before": appointment.appointment_type_id, "after": appointment_type_id},
        "equipment_ids": {"before": appointment.equipment_ids, "after": equipment_ids},
        "reason": payload.reason,
    }
    return _create_preview_response(
        workflow="appointment.reschedule",
        entity_id=appointment.appointment_number,
        changes=changes,
        conflicts=conflicts,
        warnings=warnings,
        patient=patient,
        provider=provider,
        room=room,
        equipment=equipment,
        equipment_ids=equipment_ids,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
    )


def preview_status_transition(
    appointment: Appointment,
    payload: AppointmentCancelPreviewRequest
    | AppointmentCheckInPreviewRequest
    | AppointmentNoShowPreviewRequest,
    *,
    workflow: str,
    target_status: str,
) -> AppointmentPreviewResponse:
    conflicts: list[SchedulingConflict] = []
    if target_status in SCHEDULED_ONLY_TRANSITIONS and appointment.status != "scheduled":
        conflicts.append(
            SchedulingConflict(
                conflict_type="invalid_transition",
                entity_type="appointment",
                entity_id=appointment.appointment_number,
                message=f"Cannot move appointment from {appointment.status} to {target_status}.",
            )
        )
    changes = payload.model_dump(mode="json")
    changes["status"] = {"before": appointment.status, "after": target_status}
    return _create_preview_response(
        workflow=workflow,
        entity_id=appointment.appointment_number,
        changes=changes,
        conflicts=conflicts,
        warnings=[],
        patient=appointment.patient,
        provider=appointment.provider,
        room=appointment.room,
        equipment=[resource.equipment for resource in appointment.resources if resource.equipment],
        equipment_ids=appointment.equipment_ids,
        scheduled_start=appointment.scheduled_start,
        scheduled_end=appointment.scheduled_end,
    )


def replace_appointment_resources(appointment: Appointment, equipment_ids: list[int], user_id: int | None) -> None:
    appointment.resources = [
        AppointmentResource(equipment_id=equipment_id, created_by=user_id) for equipment_id in equipment_ids
    ]


def append_status_history(
    appointment: Appointment,
    *,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    appointment.status_history.append(
        AppointmentStatusHistory(
            appointment_id=appointment.appointment_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            reason=reason,
            notes=notes,
        )
    )


def append_appointment_workflow_audit(
    *,
    workflow: str,
    appointment: Appointment,
    actor: str,
    preview_value: str,
    status_before: str | None,
    status_after: str | None,
    reason: str,
    changes: dict[str, Any],
) -> tuple[WorkflowOperation, str]:
    operation = WorkflowOperation(
        workflow=workflow,
        entity_type="appointment",
        entity_id=appointment.appointment_number,
        actor=actor,
        preview_hash=preview_value,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        changes=changes,
    )
    operation, audit_path = append_workflow_operation(operation)
    return operation, str(audit_path)


def now_utc() -> datetime:
    return datetime.now(UTC)


def scheduling_actor(user: User) -> str:
    return actor_label(user)
