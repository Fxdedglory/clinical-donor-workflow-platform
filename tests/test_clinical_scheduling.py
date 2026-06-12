import json
import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models import (
    Appointment,
    AppointmentResource,
    AppointmentStatusHistory,
    AppointmentType,
    ClinicalEquipment,
    ClinicalProvider,
    ClinicalRoom,
    Patient,
)
from app.services import clinical_workflows
from fastapi.testclient import TestClient


class _PermissionResult:
    def __init__(self, permissions: list[str]) -> None:
        self.permissions = permissions

    def all(self):
        return [(permission,) for permission in self.permissions]


class _Rows:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows


def _compiled(statement) -> str:
    try:
        return str(statement.compile(compile_kwargs={"literal_binds": True}))
    except Exception:
        return str(statement)


def _id_filter(rows: list[object], attr: str, sql: str) -> list[object]:
    match = re.search(rf"{attr}\s*=\s*(\d+)", sql)
    if not match:
        return rows
    value = int(match.group(1))
    return [row for row in rows if getattr(row, attr) == value]


class _ClinicalSchedulingSession:
    def __init__(
        self,
        *,
        permissions: list[str] | None = None,
        patients: list[Patient] | None = None,
        appointments: list[Appointment] | None = None,
    ) -> None:
        self.permissions = permissions or ["scheduling.read", "scheduling.manage", "patients.read"]
        self.patients = patients or [_patient()]
        self.providers = [_provider(1, "Jordan Ellis, RN"), _provider(2, "Morgan Patel, MD")]
        self.rooms = [_room(1, "Intake Room 101"), _room(2, "Screening Room 102")]
        self.equipment = [_equipment(1, "Vitals Cart 1"), _equipment(2, "Phlebotomy Kit 1")]
        self.appointment_types = [_appointment_type(1, "Donor intake appointment", 60)]
        self.appointments = appointments or []
        self.committed = False
        self._next_appointment_id = max([appointment.appointment_id or 0 for appointment in self.appointments] + [0]) + 1
        self._next_resource_id = 1
        self._next_history_id = 1
        for appointment in self.appointments:
            self._prepare_appointment(appointment)

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
        if "clinical_providers" in sql:
            return _Rows(_id_filter(self.providers, "provider_id", sql))
        if "clinical_rooms" in sql:
            return _Rows(_id_filter(self.rooms, "room_id", sql))
        if "clinical_equipment" in sql:
            id_matches = re.findall(r"clinical_equipment\.equipment_id\s+IN\s+\(([^)]+)\)", sql)
            if id_matches:
                requested = {int(value.strip()) for value in id_matches[0].split(",")}
                return _Rows([item for item in self.equipment if item.equipment_id in requested])
            return _Rows(self.equipment)
        if "appointment_types" in sql:
            return _Rows(_id_filter(self.appointment_types, "appointment_type_id", sql))
        if "appointments" in sql:
            return _Rows(_id_filter(self.appointments, "appointment_id", sql))
        if "patients" in sql:
            patient_id_match = re.search(r"patients\.patient_id\s*=\s*'([^']+)'", sql)
            if patient_id_match:
                patient_id = patient_id_match.group(1)
                return _Rows([patient for patient in self.patients if patient.patient_id == patient_id])
            return _Rows(self.patients)
        return _Rows([])

    def add(self, value):
        if isinstance(value, Appointment):
            if value not in self.appointments:
                self.appointments.append(value)
            self._prepare_appointment(value)
        if isinstance(value, AppointmentStatusHistory):
            appointment = self.appointments[0]
            appointment.status_history.append(value)
            self._prepare_appointment(appointment)

    def flush(self) -> None:
        for appointment in self.appointments:
            self._prepare_appointment(appointment)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        if isinstance(value, Appointment):
            self._prepare_appointment(value)

    def _prepare_appointment(self, appointment: Appointment) -> None:
        now = datetime.now(UTC)
        if appointment.appointment_id is None:
            appointment.appointment_id = self._next_appointment_id
            self._next_appointment_id += 1
        appointment.created_at = appointment.created_at or now
        appointment.updated_at = appointment.updated_at or now
        appointment.source = appointment.source or "clinical_scheduling"
        appointment.version = appointment.version or 1
        appointment.is_deleted = bool(appointment.is_deleted)
        appointment.patient = appointment.patient or self.patients[0]
        appointment.patient_pk = appointment.patient_pk or appointment.patient.patient_pk
        appointment.provider = appointment.provider or next(
            provider for provider in self.providers if provider.provider_id == appointment.provider_id
        )
        if appointment.room_id:
            appointment.room = appointment.room or next(room for room in self.rooms if room.room_id == appointment.room_id)
        appointment.appointment_type = appointment.appointment_type or self.appointment_types[0]
        for resource in appointment.resources:
            if resource.appointment_resource_id is None:
                resource.appointment_resource_id = self._next_resource_id
                self._next_resource_id += 1
            resource.appointment_id = appointment.appointment_id
            resource.equipment = resource.equipment or next(
                item for item in self.equipment if item.equipment_id == resource.equipment_id
            )
        for history in appointment.status_history:
            if history.history_id is None:
                history.history_id = self._next_history_id
                self._next_history_id += 1
            history.appointment_id = appointment.appointment_id
            history.changed_at = history.changed_at or now


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="scheduler",
        email="scheduler@example.org",
        full_name="Scheduler User",
        role="Donor Intake Coordinator",
        role_id=2,
        account_type="internal",
        user_type="internal",
        is_external=False,
        external_user_flag=False,
    )


def _external_user():
    return SimpleNamespace(
        user_id=9,
        username="partner",
        email="partner@example.org",
        full_name="Partner User",
        role="Partner External User",
        role_id=8,
        account_type="partner",
        user_type="partner",
        is_external=True,
        external_user_flag=True,
    )


def _patient(patient_id: str = "PT-SCHED-001") -> Patient:
    return Patient(
        patient_pk=1,
        patient_id=patient_id,
        first_name="Avery",
        last_name="Stone",
        date_of_birth=datetime(1985, 2, 3, tzinfo=UTC).date(),
        sex_at_birth="Female",
        status="active",
        source="clinical_registration",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _provider(provider_id: int, name: str) -> ClinicalProvider:
    return ClinicalProvider(
        provider_id=provider_id,
        provider_code=f"PROV-{provider_id}",
        full_name=name,
        role="Nurse",
        specialty="Donor intake",
        status="active",
        is_deleted=False,
    )


def _room(room_id: int, name: str) -> ClinicalRoom:
    return ClinicalRoom(
        room_id=room_id,
        room_code=f"ROOM-{room_id}",
        room_name=name,
        location="Clinical wing",
        status="active",
        is_deleted=False,
    )


def _equipment(equipment_id: int, name: str) -> ClinicalEquipment:
    return ClinicalEquipment(
        equipment_id=equipment_id,
        equipment_code=f"EQ-{equipment_id}",
        equipment_name=name,
        equipment_type="vitals",
        status="active",
        is_deleted=False,
    )


def _appointment_type(type_id: int, name: str, duration: int) -> AppointmentType:
    return AppointmentType(
        appointment_type_id=type_id,
        type_code=f"TYPE-{type_id}",
        name=name,
        default_duration_minutes=duration,
        requires_room=True,
        status="active",
        is_deleted=False,
    )


def _start() -> str:
    return "2026-06-15T09:00:00Z"


def _end() -> str:
    return "2026-06-15T10:00:00Z"


def _payload() -> dict[str, object]:
    return {
        "patient_id": "PT-SCHED-001",
        "provider_id": 1,
        "room_id": 1,
        "appointment_type_id": 1,
        "scheduled_start": _start(),
        "scheduled_end": _end(),
        "reason": "Donor intake visit",
        "equipment_ids": [1],
    }


def _appointment(status: str = "scheduled", appointment_id: int = 1) -> Appointment:
    patient = _patient()
    provider = _provider(1, "Jordan Ellis, RN")
    room = _room(1, "Intake Room 101")
    appointment_type = _appointment_type(1, "Donor intake appointment", 60)
    appointment = Appointment(
        appointment_id=appointment_id,
        appointment_number=f"APT-EXISTING-{appointment_id}",
        patient_pk=patient.patient_pk,
        patient=patient,
        provider_id=provider.provider_id,
        provider=provider,
        room_id=room.room_id,
        room=room,
        appointment_type_id=appointment_type.appointment_type_id,
        appointment_type=appointment_type,
        scheduled_start=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        status=status,
        reason="Existing visit",
        source="clinical_scheduling",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    appointment.resources = [AppointmentResource(equipment_id=1, equipment=_equipment(1, "Vitals Cart 1"))]
    appointment.status_history = []
    return appointment


def _override_dependencies(session: _ClinicalSchedulingSession, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_appointment_create_preview_validates() -> None:
    session = _ClinicalSchedulingSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/scheduling/appointments/preview", json=_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == "appointment.book"
    assert payload["validation_status"] == "passed"
    assert payload["preview_hash"]


def test_appointment_create_commit_rejects_missing_confirmation_header() -> None:
    session = _ClinicalSchedulingSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/scheduling/appointments", json=_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"


def test_appointment_create_commit_rejects_invalid_confirmation_header() -> None:
    session = _ClinicalSchedulingSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/scheduling/appointments",
            headers={"X-Confirm-Generation": "false"},
            json=_payload(),
        )
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"


def test_appointment_create_commit_succeeds_and_creates_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    session = _ClinicalSchedulingSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/scheduling/appointments",
            headers={"X-Confirm-Generation": "true"},
            json={**_payload(), "preview_hash": "sha256-scheduling-create"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    assert audit_path.exists()
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "appointment.book"
    assert entries[-1]["preview_hash"] == "sha256-scheduling-create"


def test_appointment_audit_appends_without_destroying_existing_entries(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(json.dumps([{"operation_id": "existing", "workflow": "patient.create"}]), encoding="utf-8")
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    session = _ClinicalSchedulingSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/scheduling/appointments",
            headers={"X-Confirm-Generation": "true"},
            json=_payload(),
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[0]["operation_id"] == "existing"
    assert entries[-1]["workflow"] == "appointment.book"


def test_provider_room_patient_overlap_detected_and_blocks_commit() -> None:
    session = _ClinicalSchedulingSession(appointments=[_appointment()])
    _override_dependencies(session, _internal_user())
    try:
        preview_response = TestClient(app).post("/api/clinical/scheduling/appointments/preview", json=_payload())
        commit_response = TestClient(app).post(
            "/api/clinical/scheduling/appointments",
            headers={"X-Confirm-Generation": "true"},
            json=_payload(),
        )
    finally:
        _clear_overrides()

    assert preview_response.status_code == 200
    conflict_types = {conflict["conflict_type"] for conflict in preview_response.json()["conflicts"]}
    assert {"provider_overlap", "room_overlap", "patient_overlap"}.issubset(conflict_types)
    assert commit_response.status_code == 409
    assert commit_response.json()["detail"]["status"] == "scheduling_conflict"


def test_reschedule_writes_status_history_and_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    appointment = _appointment()
    session = _ClinicalSchedulingSession(appointments=[appointment])
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/scheduling/1/reschedule",
            headers={"X-Confirm-Generation": "true"},
            json={
                "scheduled_start": "2026-06-15T11:00:00Z",
                "scheduled_end": "2026-06-15T12:00:00Z",
                "reason": "Patient requested later visit",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert appointment.status == "rescheduled"
    assert appointment.status_history[-1].to_status == "rescheduled"
    assert json.loads(audit_path.read_text(encoding="utf-8"))[-1]["workflow"] == "appointment.reschedule"


def test_cancellation_requires_reason_and_writes_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    appointment = _appointment()
    session = _ClinicalSchedulingSession(appointments=[appointment])
    _override_dependencies(session, _internal_user())
    try:
        missing_reason = TestClient(app).post(
            "/api/clinical/scheduling/1/cancel/preview",
            json={},
        )
        response = TestClient(app).post(
            "/api/clinical/scheduling/1/cancel",
            headers={"X-Confirm-Generation": "true"},
            json={"cancellation_reason": "Patient unavailable"},
        )
    finally:
        _clear_overrides()

    assert missing_reason.status_code == 422
    assert response.status_code == 200
    assert appointment.status == "cancelled"
    assert appointment.cancellation_reason == "Patient unavailable"
    assert json.loads(audit_path.read_text(encoding="utf-8"))[-1]["workflow"] == "appointment.cancel"


def test_check_in_updates_status_and_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    appointment = _appointment()
    session = _ClinicalSchedulingSession(appointments=[appointment])
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/scheduling/1/check-in",
            headers={"X-Confirm-Generation": "true"},
            json={"check_in_time": "2026-06-15T08:55:00Z"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert appointment.status == "checked_in"
    assert appointment.check_in_time.isoformat().startswith("2026-06-15T08:55:00")
    assert json.loads(audit_path.read_text(encoding="utf-8"))[-1]["workflow"] == "appointment.check_in"


def test_no_show_updates_status_and_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    appointment = _appointment()
    session = _ClinicalSchedulingSession(appointments=[appointment])
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/scheduling/1/no-show",
            headers={"X-Confirm-Generation": "true"},
            json={"no_show_reason": "Patient did not arrive"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert appointment.status == "no_show"
    assert appointment.no_show_reason == "Patient did not arrive"
    assert json.loads(audit_path.read_text(encoding="utf-8"))[-1]["workflow"] == "appointment.no_show"


def test_invalid_transition_rejected() -> None:
    appointment = _appointment(status="checked_in")
    session = _ClinicalSchedulingSession(appointments=[appointment])
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/scheduling/1/cancel",
            headers={"X-Confirm-Generation": "true"},
            json={"cancellation_reason": "Too late to cancel"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "scheduling_conflict"


def test_external_partner_mutation_is_rejected() -> None:
    session = _ClinicalSchedulingSession(permissions=["partner.portal"])
    _override_dependencies(session, _external_user())
    try:
        response = TestClient(app).post("/api/clinical/scheduling/appointments/preview", json=_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 403
    assert "External users" in response.json()["detail"]
