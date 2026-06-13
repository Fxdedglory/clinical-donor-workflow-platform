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
    AppointmentType,
    CAPA,
    ClinicalAdverseEvent,
    ClinicalCarePlan,
    ClinicalCharge,
    ClinicalClaim,
    ClinicalComplianceExport,
    ClinicalDenial,
    ClinicalEncounter,
    ClinicalOrder,
    ClinicalOrderCatalogItem,
    ClinicalOrderResult,
    ClinicalPayment,
    ClinicalProvider,
    ClinicalQualityApproval,
    ClinicalQualityEvent,
    ClinicalQualityEventLink,
    ClinicalQualityInvestigation,
    ClinicalQualityStatusHistory,
    ClinicalRoom,
    ClinicalScreeningSession,
    Deviation,
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
    return [row for row in rows if getattr(row, attr, None) == value]


class _ClinicalQualityDb:
    def __init__(
        self,
        *,
        permissions: list[str] | None = None,
        patients: list[Patient] | None = None,
        encounters: list[ClinicalEncounter] | None = None,
        events: list[ClinicalQualityEvent] | None = None,
        capas: list[CAPA] | None = None,
        adverse_events: list[ClinicalAdverseEvent] | None = None,
        exports: list[ClinicalComplianceExport] | None = None,
    ) -> None:
        self.permissions = permissions or ["quality.read", "quality.manage", "quality.close", "quality.export", "patients.read"]
        self.patients = patients or [_patient()]
        self.appointments = [_appointment(self.patients[0])]
        self.sessions = [_session(self.patients[0], self.appointments[0])]
        self.encounters = encounters or [_encounter(self.patients[0])]
        self.orders = [_order(self.patients[0], self.encounters[0])]
        self.care_plans = [_care_plan(self.patients[0])]
        self.charges, self.claims, self.payments, self.denials = _billing_context(self.patients[0])
        self.deviations = [_deviation()]
        self.capas = capas or [_capa()]
        self.events = events or []
        self.adverse_events = adverse_events or []
        self.exports = exports or []
        self.status_history: list[ClinicalQualityStatusHistory] = []
        self.committed = False
        self._next_event_id = max([event.event_id or 0 for event in self.events] + [0]) + 1
        self._next_adverse_event_id = max([event.adverse_event_id or 0 for event in self.adverse_events] + [0]) + 1
        self._next_export_id = max([export.export_id or 0 for export in self.exports] + [0]) + 1
        self._next_link_id = 1
        self._next_investigation_id = 1
        self._next_approval_id = 1
        self._next_history_id = 1
        for event in self.events:
            self._prepare_event(event)
        for adverse_event in self.adverse_events:
            self._prepare_adverse_event(adverse_event)
        for export in self.exports:
            self._prepare_export(export)

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
        if "clinical_quality_status_history" in sql:
            return _Rows(self.status_history)
        if "clinical_compliance_exports" in sql:
            return _Rows(_id_filter(self.exports, "export_id", sql))
        if "clinical_adverse_events" in sql:
            return _Rows(_id_filter(self.adverse_events, "adverse_event_id", sql))
        if "clinical_quality_events" in sql:
            return _Rows(_id_filter(self.events, "event_id", sql))
        if "fact_capa" in sql:
            return _Rows(_id_filter(self.capas, "capa_id", sql))
        if "fact_deviation" in sql:
            return _Rows(_id_filter(self.deviations, "deviation_id", sql))
        if "clinical_denials" in sql:
            return _Rows(_id_filter(self.denials, "denial_id", sql))
        if "clinical_payments" in sql:
            return _Rows(_id_filter(self.payments, "payment_id", sql))
        if "clinical_claims" in sql:
            return _Rows(_id_filter(self.claims, "claim_id", sql))
        if "clinical_charges" in sql:
            return _Rows(_id_filter(self.charges, "charge_id", sql))
        if "clinical_care_plans" in sql:
            return _Rows(_id_filter(self.care_plans, "care_plan_id", sql))
        if "clinical_order_results" in sql and "clinical_orders" not in sql:
            return _Rows(_id_filter(self._results(), "result_id", sql))
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
            return _Rows(_id_filter(self.patients, "patient_pk", sql))
        return _Rows([])

    def add(self, value):
        if isinstance(value, ClinicalQualityEvent) and value not in self.events:
            self.events.append(value)
            self._prepare_event(value)
        if isinstance(value, ClinicalAdverseEvent) and value not in self.adverse_events:
            self.adverse_events.append(value)
            self._prepare_adverse_event(value)
        if isinstance(value, ClinicalComplianceExport) and value not in self.exports:
            self.exports.append(value)
            self._prepare_export(value)

    def flush(self) -> None:
        for event in self.events:
            self._prepare_event(event)
        for adverse_event in self.adverse_events:
            self._prepare_adverse_event(adverse_event)
        for export in self.exports:
            self._prepare_export(export)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        if isinstance(value, ClinicalQualityEvent):
            self._prepare_event(value)
        if isinstance(value, ClinicalAdverseEvent):
            self._prepare_adverse_event(value)
        if isinstance(value, ClinicalComplianceExport):
            self._prepare_export(value)

    def _results(self) -> list[ClinicalOrderResult]:
        return [result for order in self.orders for result in order.results]

    def _prepare_event(self, event: ClinicalQualityEvent) -> None:
        now = datetime.now(UTC)
        if event.event_id is None:
            event.event_id = self._next_event_id
            self._next_event_id += 1
        event.event_number = event.event_number or f"QE-TEST-{event.event_id:03d}"
        event.created_at = event.created_at or now
        event.updated_at = event.updated_at or now
        event.is_deleted = bool(event.is_deleted)
        event.patient = event.patient or next((patient for patient in self.patients if patient.patient_pk == event.patient_pk), None)
        event.patient_pk = event.patient_pk or (event.patient.patient_pk if event.patient else None)
        event.appointment = event.appointment or next((item for item in self.appointments if item.appointment_id == event.appointment_id), None)
        event.screening_session = event.screening_session or next((item for item in self.sessions if item.session_id == event.screening_session_id), None)
        event.encounter = event.encounter or next((item for item in self.encounters if item.encounter_id == event.encounter_id), None)
        event.order = event.order or next((item for item in self.orders if item.order_id == event.order_id), None)
        event.order_result = event.order_result or next((item for item in self._results() if item.result_id == event.order_result_id), None)
        event.care_plan = event.care_plan or next((item for item in self.care_plans if item.care_plan_id == event.care_plan_id), None)
        event.charge = event.charge or next((item for item in self.charges if item.charge_id == event.charge_id), None)
        event.claim = event.claim or next((item for item in self.claims if item.claim_id == event.claim_id), None)
        event.payment = event.payment or next((item for item in self.payments if item.payment_id == event.payment_id), None)
        event.denial = event.denial or next((item for item in self.denials if item.denial_id == event.denial_id), None)
        event.deviation = event.deviation or next((item for item in self.deviations if item.deviation_id == event.deviation_id), None)
        event.capa = event.capa or next((item for item in self.capas if item.capa_id == event.capa_id), None)
        event.links = list(getattr(event, "links", []) or [])
        event.investigations = list(getattr(event, "investigations", []) or [])
        event.approvals = list(getattr(event, "approvals", []) or [])
        event.status_history = list(getattr(event, "status_history", []) or [])
        for link in event.links:
            if link.link_id is None:
                link.link_id = self._next_link_id
                self._next_link_id += 1
            link.event = event
            link.event_id = event.event_id
            link.created_at = link.created_at or now
        for investigation in event.investigations:
            if investigation.investigation_id is None:
                investigation.investigation_id = self._next_investigation_id
                self._next_investigation_id += 1
            investigation.event = event
            investigation.event_id = event.event_id
            investigation.created_at = investigation.created_at or now
        for approval in event.approvals:
            if approval.approval_id is None:
                approval.approval_id = self._next_approval_id
                self._next_approval_id += 1
            approval.event = event
            approval.event_id = event.event_id
            approval.created_at = approval.created_at or now
        for history in event.status_history:
            if history.history_id is None:
                history.history_id = self._next_history_id
                self._next_history_id += 1
            history.event = event
            history.event_id = event.event_id
            history.changed_at = history.changed_at or now
            history.reason = history.reason or ""
            history.notes = history.notes or ""
            if history not in self.status_history:
                self.status_history.append(history)

    def _prepare_adverse_event(self, adverse_event: ClinicalAdverseEvent) -> None:
        now = datetime.now(UTC)
        if adverse_event.adverse_event_id is None:
            adverse_event.adverse_event_id = self._next_adverse_event_id
            self._next_adverse_event_id += 1
        adverse_event.adverse_event_number = adverse_event.adverse_event_number or f"AE-TEST-{adverse_event.adverse_event_id:03d}"
        adverse_event.created_at = adverse_event.created_at or now
        adverse_event.updated_at = adverse_event.updated_at or now
        adverse_event.patient = adverse_event.patient or next((patient for patient in self.patients if patient.patient_pk == adverse_event.patient_pk), None)
        adverse_event.quality_event = adverse_event.quality_event or next((event for event in self.events if event.event_id == adverse_event.quality_event_id), None)
        adverse_event.screening_session = adverse_event.screening_session or next((item for item in self.sessions if item.session_id == adverse_event.screening_session_id), None)
        adverse_event.encounter = adverse_event.encounter or next((item for item in self.encounters if item.encounter_id == adverse_event.encounter_id), None)
        adverse_event.order = adverse_event.order or next((item for item in self.orders if item.order_id == adverse_event.order_id), None)
        adverse_event.order_result = adverse_event.order_result or next((item for item in self._results() if item.result_id == adverse_event.order_result_id), None)
        adverse_event.care_plan = adverse_event.care_plan or next((item for item in self.care_plans if item.care_plan_id == adverse_event.care_plan_id), None)

    def _prepare_export(self, export: ClinicalComplianceExport) -> None:
        now = datetime.now(UTC)
        if export.export_id is None:
            export.export_id = self._next_export_id
            self._next_export_id += 1
        export.export_number = export.export_number or f"CEXP-TEST-{export.export_id:03d}"
        export.modules = list(export.modules or [])
        export.criteria = dict(export.criteria or {})
        export.evidence_summary = dict(export.evidence_summary or {})
        export.generated_at = export.generated_at or now
        export.created_at = export.created_at or now


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="quality",
        email="quality@example.org",
        full_name="Quality User",
        role="Quality Assurance Specialist",
        role_id=4,
        account_type="internal",
        user_type="internal",
        is_external=False,
        external_user_flag=False,
    )


def _external_user():
    return SimpleNamespace(
        user_id=8,
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


def _patient(patient_pk: int = 1, patient_id: str = "PT-QUAL-001") -> Patient:
    patient = Patient(
        patient_pk=patient_pk,
        patient_id=patient_id,
        first_name="Quality",
        last_name="Patient",
        date_of_birth=date(1986, 5, 6),
        sex_at_birth="Female",
        status="active",
        source="clinical_registration",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    return patient


def _appointment(patient: Patient) -> Appointment:
    provider = ClinicalProvider(
        provider_id=1,
        provider_code="PROV-QUAL",
        full_name="Quality Provider",
        role="Clinician",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    room = ClinicalRoom(
        room_id=1,
        room_code="ROOM-QUAL",
        room_name="Room 1",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    appointment_type = AppointmentType(appointment_type_id=1, type_code="QUAL", name="Quality visit", status="active")
    return Appointment(
        appointment_id=1,
        appointment_number="APT-QUAL-001",
        patient_pk=patient.patient_pk,
        patient=patient,
        provider_id=1,
        provider=provider,
        room_id=1,
        room=room,
        appointment_type_id=1,
        appointment_type=appointment_type,
        scheduled_start=datetime.now(UTC),
        scheduled_end=datetime.now(UTC),
        status="scheduled",
        reason="Quality context",
        source="clinical_scheduling",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _session(patient: Patient, appointment: Appointment) -> ClinicalScreeningSession:
    return ClinicalScreeningSession(
        session_id=1,
        session_number="SCR-QUAL-001",
        patient_pk=patient.patient_pk,
        patient=patient,
        appointment_id=appointment.appointment_id,
        appointment=appointment,
        status="completed",
        source="clinical_screening",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _encounter(patient: Patient, encounter_id: int = 1) -> ClinicalEncounter:
    return ClinicalEncounter(
        encounter_id=encounter_id,
        encounter_number=f"ENC-QUAL-{encounter_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_type="quality",
        status="signed",
        chief_complaint="Quality context",
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


def _order(patient: Patient, encounter: ClinicalEncounter) -> ClinicalOrder:
    catalog = ClinicalOrderCatalogItem(catalog_item_id=1, code="LAB", name="Lab", order_type="lab", active=True)
    order = ClinicalOrder(
        order_id=1,
        order_number="ORD-QUAL-001",
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_id=encounter.encounter_id,
        encounter=encounter,
        catalog_item_id=1,
        catalog_item=catalog,
        order_type="lab",
        priority="routine",
        status="resulted",
        clinical_indication="Quality order",
        ordering_provider="Quality Provider",
        ordered_at=datetime.now(UTC),
        source="clinical_orders",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    result = ClinicalOrderResult(
        result_id=1,
        order_id=order.order_id,
        order=order,
        result_name="Potassium",
        result_value="6.2",
        result_status="critical",
        abnormal_flag=True,
        critical_flag=True,
        resulted_at=datetime.now(UTC),
        notes="Critical result",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    order.results = [result]
    order.acknowledgements = []
    return order


def _care_plan(patient: Patient) -> ClinicalCarePlan:
    return ClinicalCarePlan(
        care_plan_id=1,
        care_plan_number="CP-QUAL-001",
        patient_pk=patient.patient_pk,
        patient=patient,
        title="Quality follow-up",
        plan_type="case_management",
        priority="urgent",
        status="active",
        reason="Quality follow-up",
        source="clinical_care_plans",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _billing_context(patient: Patient):
    charge = ClinicalCharge(
        charge_id=1,
        charge_number="CHG-QUAL-001",
        billing_account_id=1,
        patient_pk=patient.patient_pk,
        patient=patient,
        service_date=date(2026, 6, 12),
        code="LAB100",
        code_type="internal",
        description="Quality charge",
        quantity=1,
        unit_amount=25,
        total_amount=25,
        status="captured",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    claim = ClinicalClaim(
        claim_id=1,
        claim_number="CLM-QUAL-001",
        billing_account_id=1,
        patient_pk=patient.patient_pk,
        patient=patient,
        status="denied",
        total_amount=25,
        paid_amount=0,
        adjustment_amount=0,
        balance=25,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    payment = ClinicalPayment(
        payment_id=1,
        claim_id=claim.claim_id,
        claim=claim,
        billing_account_id=1,
        patient_pk=patient.patient_pk,
        patient=patient,
        payment_amount=0,
        adjustment_amount=0,
        payment_method="eft",
        payer_type="insurance",
        reference_number="PAY-QUAL-001",
        posted_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    denial = ClinicalDenial(
        denial_id=1,
        claim_id=claim.claim_id,
        claim=claim,
        denial_code="CO-16",
        denial_reason="Missing information",
        status="open",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    claim.payments = [payment]
    claim.denials = [denial]
    return [charge], [claim], [payment], [denial]


def _deviation() -> Deviation:
    return Deviation(
        deviation_id=1,
        deviation_code="DEV-QUAL-001",
        deviation_category="Documentation",
        severity="High",
        description="Existing deviation",
        status="Open",
        opened_at=datetime.now(UTC),
        is_archived=False,
    )


def _capa() -> CAPA:
    return CAPA(
        capa_id=1,
        capa_code="CAPA-QUAL-001",
        deviation_id=1,
        root_cause="Documentation gap",
        corrective_action_owner="QA",
        status="Open",
        due_date=datetime.now(UTC),
        created_at=datetime.now(UTC),
        is_archived=False,
    )


def _quality_event(patient: Patient, status: str = "open") -> ClinicalQualityEvent:
    event = ClinicalQualityEvent(
        event_id=1,
        event_number="QE-QUAL-001",
        patient_pk=patient.patient_pk,
        patient=patient,
        category="process_deviation",
        severity="high",
        status=status,
        owner="QA",
        due_date=date(2026, 6, 20),
        source_module="clinical_quality",
        description="Existing quality event",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    event.links = []
    event.investigations = []
    event.approvals = []
    event.status_history = []
    return event


def _override_dependencies(session: _ClinicalQualityDb, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _event_payload() -> dict[str, object]:
    return {
        "patient_id": "PT-QUAL-001",
        "category": "process_deviation",
        "severity": "high",
        "status": "open",
        "owner": "QA",
        "due_date": "2026-06-20",
        "source_module": "clinical_quality",
        "description": "Documented quality event",
        "encounter_id": 1,
        "order_id": 1,
        "order_result_id": 1,
        "deviation_id": 1,
    }


def test_quality_event_preview_validates_patient_linkage() -> None:
    patient = _patient()
    other = _patient(2, "PT-QUAL-002")
    db = _ClinicalQualityDb(patients=[patient, other], encounters=[_encounter(other, 2)])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/quality/events/preview", json={**_event_payload(), "encounter_id": 2})
    finally:
        _clear_overrides()
    assert response.status_code == 200
    assert response.json()["validation_status"] == "failed"
    assert any(issue["issue_type"] == "patient_context_mismatch" for issue in response.json()["blocking_issues"])


def test_quality_event_commit_rejects_missing_invalid_and_accepts_valid_confirmation(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalQualityDb()
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post("/api/clinical/quality/events", json=_event_payload())
        invalid = TestClient(app).post("/api/clinical/quality/events", headers={"X-Confirm-Generation": "false"}, json=_event_payload())
        valid = TestClient(app).post("/api/clinical/quality/events", headers={"X-Confirm-Generation": "true"}, json={**_event_payload(), "preview_hash": "event-hash"})
    finally:
        _clear_overrides()
    assert missing.status_code == 409
    assert invalid.status_code == 409
    assert valid.status_code == 201
    assert audit_path.exists()
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "quality.event_create"
    assert len(db.events) == 1


def test_quality_audit_append_preserves_existing_entries(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(json.dumps([{"operation_id": "existing", "workflow": "seed"}]), encoding="utf-8")
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalQualityDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/quality/events", headers={"X-Confirm-Generation": "true"}, json=_event_payload())
    finally:
        _clear_overrides()
    assert response.status_code == 201
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[0]["operation_id"] == "existing"
    assert entries[-1]["workflow"] == "quality.event_create"


def test_adverse_event_warns_for_critical_and_commits(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    patient = _patient()
    event = _quality_event(patient)
    db = _ClinicalQualityDb(patients=[patient], events=[event])
    payload = {
        "patient_id": "PT-QUAL-001",
        "quality_event_id": 1,
        "event_type": "patient_safety",
        "severity": "critical",
        "event_at": datetime.now(UTC).isoformat(),
        "description": "Critical adverse event",
        "immediate_action_taken": "Stabilized patient",
        "reporter": "Nurse",
        "follow_up_required": False,
    }
    _override_dependencies(db, _internal_user())
    try:
        preview = TestClient(app).post("/api/clinical/quality/adverse-events/preview", json=payload)
        commit = TestClient(app).post("/api/clinical/quality/adverse-events", headers={"X-Confirm-Generation": "true"}, json=payload)
    finally:
        _clear_overrides()
    assert preview.status_code == 200
    assert any(warning["warning_type"] == "supervisor_review_recommended" for warning in preview.json()["warnings"])
    assert commit.status_code == 201
    assert db.adverse_events[0].quality_event_id == 1


def test_investigation_appends_note_and_closed_event_blocks_mutation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    patient = _patient()
    event = _quality_event(patient)
    db = _ClinicalQualityDb(patients=[patient], events=[event])
    _override_dependencies(db, _internal_user())
    try:
        commit = TestClient(app).post(
            "/api/clinical/quality/events/1/investigation",
            headers={"X-Confirm-Generation": "true"},
            json={"note": "Reviewed source documentation", "owner": "QA", "status_after": "investigation"},
        )
        event.status = "closed"
        blocked = TestClient(app).post(
            "/api/clinical/quality/events/1/investigation/preview",
            json={"note": "Attempt after closure", "status_after": "investigation"},
        )
    finally:
        _clear_overrides()
    assert commit.status_code == 201
    assert len(db.events[0].investigations) == 1
    assert db.events[0].investigations[0].note == "Reviewed source documentation"
    assert blocked.status_code == 200
    assert blocked.json()["validation_status"] == "failed"
    assert any(issue["issue_type"] == "event_closed" for issue in blocked.json()["blocking_issues"])


def test_capa_link_reuses_existing_capa(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    patient = _patient()
    event = _quality_event(patient)
    db = _ClinicalQualityDb(patients=[patient], events=[event], capas=[_capa()])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/quality/events/1/capa",
            headers={"X-Confirm-Generation": "true"},
            json={"existing_capa_id": 1, "reason": "Link existing CAPA"},
        )
    finally:
        _clear_overrides()
    assert response.status_code == 201
    assert db.events[0].capa_id == 1
    assert db.events[0].status == "capa_required"
    assert any(link.entity_type == "capa" and link.entity_id == "1" for link in db.events[0].links)


def test_closure_requires_summary_and_records_approval(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    patient = _patient()
    event = _quality_event(patient)
    db = _ClinicalQualityDb(patients=[patient], events=[event])
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post("/api/clinical/quality/events/1/close", headers={"X-Confirm-Generation": "true"}, json={"resolution_summary": "", "closure_reason": ""})
        closed = TestClient(app).post(
            "/api/clinical/quality/events/1/close",
            headers={"X-Confirm-Generation": "true"},
            json={"resolution_summary": "Resolved and verified", "closure_reason": "QA approval complete"},
        )
    finally:
        _clear_overrides()
    assert missing.status_code == 422
    assert closed.status_code == 201
    assert db.events[0].status == "closed"
    assert len(db.events[0].approvals) == 1
    assert db.events[0].approvals[0].approval_type == "closure"


def test_compliance_export_preview_commit_and_audit_evidence_filter(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(
        json.dumps(
            [
                {"operation_id": "quality-op", "workflow": "quality.event_create", "entity_type": "clinical_quality_event", "entity_id": "QE-1", "actor": "QA", "timestamp": datetime.now(UTC).isoformat(), "changes": {"source_module": "clinical_quality"}},
                {"operation_id": "billing-op", "workflow": "billing.charge_capture", "entity_type": "clinical_charge", "entity_id": "CHG-1", "actor": "Billing", "timestamp": datetime.now(UTC).isoformat(), "changes": {"source_module": "clinical_billing"}},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    patient = _patient()
    event = _quality_event(patient)
    history = ClinicalQualityStatusHistory(event=event, event_id=event.event_id, from_status=None, to_status="open", changed_at=datetime.now(UTC), reason="Created", notes="")
    event.status_history = [history]
    db = _ClinicalQualityDb(patients=[patient], events=[event])
    _override_dependencies(db, _internal_user())
    try:
        preview = TestClient(app).post("/api/clinical/quality/compliance-exports/preview", json={"modules": ["quality"], "include_quality_history": True})
        commit = TestClient(app).post("/api/clinical/quality/compliance-exports", headers={"X-Confirm-Generation": "true"}, json={"modules": ["quality"], "preview_hash": "export-hash"})
        evidence = TestClient(app).get("/api/clinical/quality/audit-evidence?workflow=quality.event_create")
    finally:
        _clear_overrides()
    assert preview.status_code == 200
    assert preview.json()["changes"]["evidence_summary"]["workflow_operation_count"] == 1
    assert commit.status_code == 201
    assert db.exports[0].evidence_summary["workflow_operation_count"] == 1
    assert evidence.status_code == 200
    assert evidence.json()["total_operations"] == 1


def test_compliance_export_commit_audit_redacts_phi_payload(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalQualityDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/quality/compliance-exports",
            headers={"X-Confirm-Generation": "true"},
            json={
                "modules": ["quality"],
                "entity_id": "PT-SECRET",
                "export_profile": "compliance_evidence",
                "preview_hash": "export-hash",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    assert db.exports[0].criteria["entity_id"] == "PT-SECRET"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "quality.compliance_export"
    assert entries[-1]["changes"]["export_profile"] == "compliance_evidence"
    assert "PT-SECRET" not in json.dumps(entries[-1]["changes"])


def test_audit_evidence_external_safe_profile_redacts_sensitive_operations(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(
        json.dumps(
            [
                {
                    "operation_id": "quality-op-sensitive",
                    "workflow": "quality.event_create",
                    "entity_type": "clinical_quality_event",
                    "entity_id": "QE-SECRET",
                    "actor": "QA User",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "preview_hash": "sha256-sensitive",
                    "commit_confirmed": True,
                    "status_before": None,
                    "status_after": "open",
                    "reason": "Created",
                    "changes": {
                        "patient_id": "PT-SECRET",
                        "note": "Sensitive clinical narrative",
                        "source_module": "clinical_quality",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalQualityDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).get("/api/clinical/quality/audit-evidence?export_profile=external_safe")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["export_profile"] == "external_safe"
    operation = payload["operations"][0]
    assert operation["entity_id"] == "[redacted]"
    assert operation["changes"]["patient_id"] == "[redacted]"
    assert operation["changes"]["note"] == "[redacted]"
    assert operation["changes"]["source_module"] == "clinical_quality"


def test_external_partner_quality_mutation_is_rejected() -> None:
    db = _ClinicalQualityDb(permissions=["partner.portal"])
    _override_dependencies(db, _external_user())
    try:
        response = TestClient(app).post("/api/clinical/quality/events/preview", json=_event_payload())
    finally:
        _clear_overrides()
    assert response.status_code == 403
