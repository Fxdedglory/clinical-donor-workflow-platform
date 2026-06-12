import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
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
)
from app.services import clinical_workflows


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


class _ClinicalOrderDb:
    def __init__(
        self,
        *,
        permissions: list[str] | None = None,
        patients: list[Patient] | None = None,
        appointments: list[Appointment] | None = None,
        sessions: list[ClinicalScreeningSession] | None = None,
        encounters: list[ClinicalEncounter] | None = None,
        catalog: list[ClinicalOrderCatalogItem] | None = None,
        orders: list[ClinicalOrder] | None = None,
    ) -> None:
        self.permissions = permissions or ["orders.read", "orders.manage", "orders.acknowledge", "patients.read"]
        self.patients = patients or [_patient()]
        self.appointments = appointments or [_appointment(self.patients[0])]
        self.sessions = sessions or [_screening_session(self.patients[0], self.appointments[0])]
        self.encounters = encounters or [_encounter(self.patients[0], self.appointments[0], self.sessions[0])]
        self.catalog = catalog or [_catalog_item()]
        self.orders = orders or []
        self.committed = False
        self._next_order_id = max([order.order_id or 0 for order in self.orders] + [0]) + 1
        self._next_result_id = 1
        self._next_acknowledgement_id = 1
        self._next_history_id = 1
        for patient in self.patients:
            patient.orders = list(getattr(patient, "orders", []) or [])
        for order in self.orders:
            self._prepare_order(order)

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
        if "clinical_order_results" in sql and "clinical_orders" not in sql:
            return _Rows(_id_filter(self._results(), "result_id", sql))
        if "clinical_order_catalog_items" in sql:
            return _Rows(_id_filter(self.catalog, "catalog_item_id", sql))
        if "clinical_orders" in sql:
            return _Rows(_id_filter(self.orders, "order_id", sql))
        if "clinical_encounters" in sql:
            return _Rows(_id_filter(self.encounters, "encounter_id", sql))
        if "clinical_screening_sessions" in sql:
            return _Rows(_id_filter(self.sessions, "session_id", sql))
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
        if isinstance(value, ClinicalOrder) and value not in self.orders:
            self.orders.append(value)
            self._prepare_order(value)

    def flush(self) -> None:
        for order in self.orders:
            self._prepare_order(order)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        if isinstance(value, ClinicalOrder):
            self._prepare_order(value)

    def _results(self) -> list[ClinicalOrderResult]:
        return [result for order in self.orders for result in order.results]

    def _prepare_order(self, order: ClinicalOrder) -> None:
        now = datetime.now(UTC)
        if order.order_id is None:
            order.order_id = self._next_order_id
            self._next_order_id += 1
        order.created_at = order.created_at or now
        order.updated_at = order.updated_at or now
        order.source = order.source or "clinical_orders"
        order.version = order.version or 1
        order.is_deleted = bool(order.is_deleted)
        order.patient = order.patient or self.patients[0]
        order.patient_pk = order.patient_pk or order.patient.patient_pk
        if order not in order.patient.orders:
            order.patient.orders.append(order)
        order.catalog_item = order.catalog_item or self.catalog[0]
        order.catalog_item_id = order.catalog_item_id or order.catalog_item.catalog_item_id
        if order.encounter_id:
            order.encounter = order.encounter or next((item for item in self.encounters if item.encounter_id == order.encounter_id), None)
        if order.screening_session_id:
            order.screening_session = order.screening_session or next((item for item in self.sessions if item.session_id == order.screening_session_id), None)
        if order.appointment_id:
            order.appointment = order.appointment or next((item for item in self.appointments if item.appointment_id == order.appointment_id), None)
        order.results = list(getattr(order, "results", []) or [])
        order.acknowledgements = list(getattr(order, "acknowledgements", []) or [])
        order.status_history = list(getattr(order, "status_history", []) or [])
        for result in order.results:
            if result.result_id is None:
                result.result_id = self._next_result_id
                self._next_result_id += 1
            result.order_id = order.order_id
            result.order = order
            result.created_at = result.created_at or now
            result.updated_at = result.updated_at or now
            result.resulted_at = result.resulted_at or now
            result.notes = result.notes or ""
        for acknowledgement in order.acknowledgements:
            if acknowledgement.acknowledgement_id is None:
                acknowledgement.acknowledgement_id = self._next_acknowledgement_id
                self._next_acknowledgement_id += 1
            acknowledgement.order_id = order.order_id
            acknowledgement.order = order
            acknowledgement.acknowledged_at = acknowledgement.acknowledged_at or now
            acknowledgement.created_at = acknowledgement.created_at or now
            acknowledgement.acknowledgement_note = acknowledgement.acknowledgement_note or ""
        for history in order.status_history:
            if history.history_id is None:
                history.history_id = self._next_history_id
                self._next_history_id += 1
            history.order_id = order.order_id
            history.order = order
            history.changed_at = history.changed_at or now
            history.reason = history.reason or ""
            history.notes = history.notes or ""


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="orders",
        email="orders@example.org",
        full_name="Orders User",
        role="Clinical Reviewer",
        role_id=3,
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


def _patient(patient_pk: int = 1, patient_id: str = "PT-ORD-001") -> Patient:
    patient = Patient(
        patient_pk=patient_pk,
        patient_id=patient_id,
        first_name="Avery",
        last_name="Stone",
        date_of_birth=date(1985, 2, 3),
        sex_at_birth="Female",
        status="active",
        source="clinical_registration",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    patient.orders = []
    return patient


def _appointment(patient: Patient, appointment_id: int = 1) -> Appointment:
    return Appointment(
        appointment_id=appointment_id,
        appointment_number=f"APT-ORD-{appointment_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        provider_id=1,
        room_id=1,
        appointment_type_id=1,
        scheduled_start=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        status="checked_in",
        reason="Donor intake",
        source="clinical_scheduling",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _screening_session(patient: Patient, appointment: Appointment, session_id: int = 1) -> ClinicalScreeningSession:
    return ClinicalScreeningSession(
        session_id=session_id,
        session_number=f"SCR-ORD-{session_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        appointment_id=appointment.appointment_id,
        appointment=appointment,
        template_id="minimal_donor_screening_v1",
        status="eligible",
        current_outcome="eligible",
        supervisor_review_required=False,
        reason="Screening complete",
        source="clinical_screening",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _encounter(
    patient: Patient,
    appointment: Appointment,
    session: ClinicalScreeningSession,
    encounter_id: int = 1,
) -> ClinicalEncounter:
    return ClinicalEncounter(
        encounter_id=encounter_id,
        encounter_number=f"ENC-ORD-{encounter_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        appointment_id=appointment.appointment_id,
        appointment=appointment,
        screening_session_id=session.session_id,
        screening_session=session,
        encounter_type="donor_screening",
        status="signed",
        chief_complaint="Donor screening review",
        reason="Signed encounter",
        started_at=datetime.now(UTC),
        signed_at=datetime.now(UTC),
        signed_by=7,
        source="clinical_encounters",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _catalog_item(catalog_item_id: int = 1, code: str = "ID-NAT-PANEL") -> ClinicalOrderCatalogItem:
    return ClinicalOrderCatalogItem(
        catalog_item_id=catalog_item_id,
        code=code,
        name="Infectious disease NAT panel",
        order_type="infectious_disease",
        description="Existing donor infectious disease testing assets",
        default_priority="urgent",
        specimen_type="blood",
        active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _order(status: str = "ordered") -> ClinicalOrder:
    patient = _patient()
    appointment = _appointment(patient)
    session = _screening_session(patient, appointment)
    encounter = _encounter(patient, appointment, session)
    catalog = _catalog_item()
    order = ClinicalOrder(
        order_id=1,
        order_number="ORD-EXISTING-1",
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_id=encounter.encounter_id,
        encounter=encounter,
        screening_session_id=session.session_id,
        screening_session=session,
        appointment_id=appointment.appointment_id,
        appointment=appointment,
        catalog_item_id=catalog.catalog_item_id,
        catalog_item=catalog,
        order_type=catalog.order_type,
        priority="urgent",
        status=status,
        clinical_indication="Donor infectious disease screen",
        ordering_provider="Jordan Ellis",
        ordered_at=datetime.now(UTC),
        source="clinical_orders",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    order.results = []
    order.acknowledgements = []
    order.status_history = [
        ClinicalOrderStatusHistory(
            history_id=1,
            order_id=1,
            from_status=None,
            to_status=status,
            changed_at=datetime.now(UTC),
            changed_by=7,
            reason="Existing order",
            notes="Seeded for test",
        )
    ]
    patient.orders = [order]
    return order


def _create_payload() -> dict[str, object]:
    return {
        "patient_id": "PT-ORD-001",
        "encounter_id": 1,
        "screening_session_id": 1,
        "appointment_id": 1,
        "catalog_item_id": 1,
        "priority": "urgent",
        "clinical_indication": "Donor infectious disease screen",
        "reason": "Create order",
    }


def _override_dependencies(session: _ClinicalOrderDb, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_order_catalog_and_linkage_preview_validation() -> None:
    patient = _patient()
    other_patient = _patient(2, "PT-ORD-002")
    other_appointment = _appointment(other_patient, 2)
    other_session = _screening_session(other_patient, other_appointment, 2)
    db = _ClinicalOrderDb(
        patients=[patient, other_patient],
        encounters=[_encounter(other_patient, other_appointment, other_session, 2)],
    )
    _override_dependencies(db, _internal_user())
    try:
        catalog_response = TestClient(app).get("/api/clinical/orders/catalog")
        preview_response = TestClient(app).post(
            "/api/clinical/orders/preview",
            json={**_create_payload(), "encounter_id": 2},
        )
    finally:
        _clear_overrides()

    assert catalog_response.status_code == 200
    assert catalog_response.json()[0]["code"] == "ID-NAT-PANEL"
    assert preview_response.status_code == 200
    payload = preview_response.json()
    assert payload["validation_status"] == "failed"
    assert any(issue["issue_type"] == "encounter_patient_mismatch" for issue in payload["blocking_issues"])


def test_order_create_rejects_missing_and_invalid_confirmation_headers() -> None:
    db = _ClinicalOrderDb()
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post("/api/clinical/orders", json=_create_payload())
        invalid = TestClient(app).post(
            "/api/clinical/orders",
            headers={"X-Confirm-Generation": "false"},
            json=_create_payload(),
        )
    finally:
        _clear_overrides()

    assert missing.status_code == 409
    assert invalid.status_code == 409
    assert missing.json()["detail"]["status"] == "confirmation_required"
    assert invalid.json()["detail"]["status"] == "confirmation_required"


def test_order_create_accepts_confirmation_and_creates_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalOrderDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/orders",
            headers={"X-Confirm-Generation": "true"},
            json={**_create_payload(), "preview_hash": "sha256-order"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    assert response.json()["order"]["order_number"].startswith("ORD-")
    assert audit_path.exists()
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "order.create"
    assert entries[-1]["preview_hash"] == "sha256-order"


def test_order_result_rejected_after_cancellation() -> None:
    db = _ClinicalOrderDb(orders=[_order(status="cancelled")])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/orders/1/results/preview",
            json={"result_name": "NAT panel", "result_value": "negative"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert any(issue["issue_type"] == "order_cancelled" for issue in payload["blocking_issues"])


def test_critical_result_requires_acknowledgement_and_ack_clears_flag(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalOrderDb(orders=[_order()])
    _override_dependencies(db, _internal_user())
    result_payload = {
        "result_name": "HIV NAT",
        "result_value": "reactive",
        "result_status": "critical",
        "critical_flag": True,
        "reason": "Enter critical result",
    }
    try:
        result_response = TestClient(app).post(
            "/api/clinical/orders/1/results",
            headers={"X-Confirm-Generation": "true"},
            json={**result_payload, "preview_hash": "sha256-result"},
        )
        assert result_response.status_code == 200
        assert db.orders[0].has_critical_unacknowledged is True
        ack_preview = TestClient(app).post(
            "/api/clinical/orders/1/acknowledge/preview",
            json={"result_id": 1, "reason": "Clinical reviewer acknowledged"},
        )
        ack_response = TestClient(app).post(
            "/api/clinical/orders/1/acknowledge",
            headers={"X-Confirm-Generation": "true"},
            json={"result_id": 1, "reason": "Clinical reviewer acknowledged", "preview_hash": "sha256-ack"},
        )
    finally:
        _clear_overrides()

    assert ack_preview.status_code == 200
    assert ack_preview.json()["validation_status"] in {"passed", "warning"}
    assert ack_response.status_code == 200
    assert db.orders[0].has_critical_unacknowledged is False
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert [entry["workflow"] for entry in entries[-2:]] == ["order.result_add", "order.acknowledge"]


def test_order_cancel_requires_reason_and_appends_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(json.dumps([{"workflow": "existing.operation"}]), encoding="utf-8")
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalOrderDb(orders=[_order()])
    _override_dependencies(db, _internal_user())
    try:
        missing_reason = TestClient(app).post(
            "/api/clinical/orders/1/cancel",
            headers={"X-Confirm-Generation": "true"},
            json={"cancellation_reason": ""},
        )
        response = TestClient(app).post(
            "/api/clinical/orders/1/cancel",
            headers={"X-Confirm-Generation": "true"},
            json={
                "cancellation_reason": "Specimen collection cancelled by clinician",
                "reason": "Cancel order",
                "preview_hash": "sha256-cancel",
            },
        )
    finally:
        _clear_overrides()

    assert missing_reason.status_code == 422
    assert response.status_code == 200
    assert db.orders[0].status == "cancelled"
    assert db.orders[0].cancellation_reason == "Specimen collection cancelled by clinician"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[0]["workflow"] == "existing.operation"
    assert entries[-1]["workflow"] == "order.cancel"


def test_external_partner_order_mutation_is_rejected() -> None:
    db = _ClinicalOrderDb(permissions=["partner.portal"], orders=[_order()])
    _override_dependencies(db, _external_user())
    try:
        create_preview = TestClient(app).post("/api/clinical/orders/preview", json=_create_payload())
        result_preview = TestClient(app).post(
            "/api/clinical/orders/1/results/preview",
            json={"result_name": "NAT panel", "result_value": "negative"},
        )
    finally:
        _clear_overrides()

    assert create_preview.status_code == 403
    assert result_preview.status_code == 403
