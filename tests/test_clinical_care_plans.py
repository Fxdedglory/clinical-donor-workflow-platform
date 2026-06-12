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
    ClinicalCarePlan,
    ClinicalCarePlanGoal,
    ClinicalCarePlanIntervention,
    ClinicalCarePlanProgressNote,
    ClinicalCarePlanStatusHistory,
    ClinicalCarePlanTask,
    ClinicalCarePlanTeamMember,
    ClinicalEncounter,
    ClinicalOrder,
    ClinicalOrderCatalogItem,
    ClinicalOrderResult,
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


class _ClinicalCarePlanDb:
    def __init__(
        self,
        *,
        permissions: list[str] | None = None,
        patients: list[Patient] | None = None,
        appointments: list[Appointment] | None = None,
        sessions: list[ClinicalScreeningSession] | None = None,
        encounters: list[ClinicalEncounter] | None = None,
        orders: list[ClinicalOrder] | None = None,
        care_plans: list[ClinicalCarePlan] | None = None,
    ) -> None:
        self.permissions = permissions or ["care_plans.read", "care_plans.manage", "care_plans.close", "patients.read"]
        if patients is None and care_plans:
            patients = [care_plans[0].patient]
        self.patients = patients or [_patient()]
        self.appointments = appointments or [_appointment(self.patients[0])]
        self.sessions = sessions or [_screening_session(self.patients[0], self.appointments[0])]
        self.encounters = encounters or [_encounter(self.patients[0], self.appointments[0], self.sessions[0])]
        self.orders = orders or [_order(self.patients[0], self.encounters[0], self.sessions[0], self.appointments[0])]
        self.care_plans = care_plans or []
        self.committed = False
        self._next_care_plan_id = max([care_plan.care_plan_id or 0 for care_plan in self.care_plans] + [0]) + 1
        self._next_goal_id = 1
        self._next_intervention_id = 1
        self._next_task_id = 1
        self._next_progress_note_id = 1
        self._next_team_member_id = 1
        self._next_history_id = 1
        for patient in self.patients:
            patient.care_plans = list(getattr(patient, "care_plans", []) or [])
        for care_plan in self.care_plans:
            self._prepare_care_plan(care_plan)

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
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
            return _Rows(self.patients)
        return _Rows([])

    def add(self, value):
        if isinstance(value, ClinicalCarePlan) and value not in self.care_plans:
            self.care_plans.append(value)
            self._prepare_care_plan(value)

    def flush(self) -> None:
        for care_plan in self.care_plans:
            self._prepare_care_plan(care_plan)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        if isinstance(value, ClinicalCarePlan):
            self._prepare_care_plan(value)

    def _results(self) -> list[ClinicalOrderResult]:
        return [result for order in self.orders for result in order.results]

    def _prepare_care_plan(self, care_plan: ClinicalCarePlan) -> None:
        now = datetime.now(UTC)
        if care_plan.care_plan_id is None:
            care_plan.care_plan_id = self._next_care_plan_id
            self._next_care_plan_id += 1
        care_plan.created_at = care_plan.created_at or now
        care_plan.updated_at = care_plan.updated_at or now
        care_plan.source = care_plan.source or "clinical_care_plans"
        care_plan.version = care_plan.version or 1
        care_plan.is_deleted = bool(care_plan.is_deleted)
        care_plan.patient = care_plan.patient or self.patients[0]
        care_plan.patient_pk = care_plan.patient_pk or care_plan.patient.patient_pk
        if care_plan not in care_plan.patient.care_plans:
            care_plan.patient.care_plans.append(care_plan)
        if care_plan.encounter_id:
            care_plan.encounter = care_plan.encounter or next((item for item in self.encounters if item.encounter_id == care_plan.encounter_id), None)
        if care_plan.screening_session_id:
            care_plan.screening_session = care_plan.screening_session or next((item for item in self.sessions if item.session_id == care_plan.screening_session_id), None)
        if care_plan.order_id:
            care_plan.order = care_plan.order or next((item for item in self.orders if item.order_id == care_plan.order_id), None)
        if care_plan.order_result_id:
            care_plan.order_result = care_plan.order_result or next((item for item in self._results() if item.result_id == care_plan.order_result_id), None)
        care_plan.goals = list(getattr(care_plan, "goals", []) or [])
        care_plan.interventions = list(getattr(care_plan, "interventions", []) or [])
        care_plan.tasks = list(getattr(care_plan, "tasks", []) or [])
        care_plan.progress_notes = list(getattr(care_plan, "progress_notes", []) or [])
        care_plan.team_members = list(getattr(care_plan, "team_members", []) or [])
        care_plan.status_history = list(getattr(care_plan, "status_history", []) or [])
        for goal in care_plan.goals:
            if goal.goal_id is None:
                goal.goal_id = self._next_goal_id
                self._next_goal_id += 1
            goal.care_plan_id = care_plan.care_plan_id
            goal.care_plan = care_plan
            goal.created_at = goal.created_at or now
            goal.updated_at = goal.updated_at or now
        for intervention in care_plan.interventions:
            if intervention.intervention_id is None:
                intervention.intervention_id = self._next_intervention_id
                self._next_intervention_id += 1
            intervention.care_plan_id = care_plan.care_plan_id
            intervention.care_plan = care_plan
            intervention.created_at = intervention.created_at or now
            intervention.updated_at = intervention.updated_at or now
        for task in care_plan.tasks:
            if task.task_id is None:
                task.task_id = self._next_task_id
                self._next_task_id += 1
            task.care_plan_id = care_plan.care_plan_id
            task.care_plan = care_plan
            task.created_at = task.created_at or now
            task.updated_at = task.updated_at or now
        for progress_note in care_plan.progress_notes:
            if progress_note.progress_note_id is None:
                progress_note.progress_note_id = self._next_progress_note_id
                self._next_progress_note_id += 1
            progress_note.care_plan_id = care_plan.care_plan_id
            progress_note.care_plan = care_plan
            progress_note.created_at = progress_note.created_at or now
        for member in care_plan.team_members:
            if member.team_member_id is None:
                member.team_member_id = self._next_team_member_id
                self._next_team_member_id += 1
            member.care_plan_id = care_plan.care_plan_id
            member.care_plan = care_plan
            member.created_at = member.created_at or now
            member.role = member.role or "care_team"
            member.is_primary = bool(member.is_primary)
        for history in care_plan.status_history:
            if history.history_id is None:
                history.history_id = self._next_history_id
                self._next_history_id += 1
            history.care_plan_id = care_plan.care_plan_id
            history.care_plan = care_plan
            history.changed_at = history.changed_at or now
            history.reason = history.reason or ""
            history.notes = history.notes or ""


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="careplans",
        email="careplans@example.org",
        full_name="Care Plan User",
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


def _patient(patient_pk: int = 1, patient_id: str = "PT-CARE-001") -> Patient:
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
    patient.care_plans = []
    return patient


def _appointment(patient: Patient, appointment_id: int = 1) -> Appointment:
    return Appointment(
        appointment_id=appointment_id,
        appointment_number=f"APT-CARE-{appointment_id:03d}",
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
        session_number=f"SCR-CARE-{session_id:03d}",
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


def _encounter(patient: Patient, appointment: Appointment, session: ClinicalScreeningSession, encounter_id: int = 1) -> ClinicalEncounter:
    return ClinicalEncounter(
        encounter_id=encounter_id,
        encounter_number=f"ENC-CARE-{encounter_id:03d}",
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


def _order(
    patient: Patient,
    encounter: ClinicalEncounter,
    session: ClinicalScreeningSession,
    appointment: Appointment,
    order_id: int = 1,
) -> ClinicalOrder:
    catalog = ClinicalOrderCatalogItem(
        catalog_item_id=1,
        code="ID-NAT-PANEL",
        name="Infectious disease NAT panel",
        order_type="infectious_disease",
        description="Existing donor infectious disease testing assets",
        default_priority="urgent",
        specimen_type="blood",
        active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    order = ClinicalOrder(
        order_id=order_id,
        order_number=f"ORD-CARE-{order_id:03d}",
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
        status="resulted",
        clinical_indication="Donor infectious disease screen",
        ordering_provider="Jordan Ellis",
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
        result_name="HIV NAT",
        result_value="reactive",
        result_status="critical",
        abnormal_flag=True,
        critical_flag=True,
        resulted_at=datetime.now(UTC),
        notes="Critical test result",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    order.results = [result]
    order.acknowledgements = []
    return order


def _care_plan(status: str = "active") -> ClinicalCarePlan:
    patient = _patient()
    appointment = _appointment(patient)
    session = _screening_session(patient, appointment)
    encounter = _encounter(patient, appointment, session)
    order = _order(patient, encounter, session, appointment)
    care_plan = ClinicalCarePlan(
        care_plan_id=1,
        care_plan_number="CP-EXISTING-1",
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_id=encounter.encounter_id,
        encounter=encounter,
        screening_session_id=session.session_id,
        screening_session=session,
        order_id=order.order_id,
        order=order,
        order_result_id=order.results[0].result_id,
        order_result=order.results[0],
        title="Critical result follow-up plan",
        plan_type="case_management",
        priority="urgent",
        status=status,
        reason="Create care plan",
        start_date=date(2026, 6, 12),
        target_date=date(2026, 6, 30),
        source="clinical_care_plans",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    care_plan.goals = []
    care_plan.interventions = []
    care_plan.tasks = []
    care_plan.progress_notes = []
    care_plan.team_members = [
        ClinicalCarePlanTeamMember(
            team_member_id=1,
            care_plan_id=1,
            member_name="Avery Coordinator",
            role="Care Coordinator",
            is_primary=True,
            created_at=datetime.now(UTC),
        )
    ]
    care_plan.status_history = [
        ClinicalCarePlanStatusHistory(
            history_id=1,
            care_plan_id=1,
            from_status=None,
            to_status=status,
            changed_at=datetime.now(UTC),
            changed_by=7,
            reason="Existing care plan",
            notes="Seeded for test",
        )
    ]
    patient.care_plans = [care_plan]
    return care_plan


def _create_payload() -> dict[str, object]:
    return {
        "patient_id": "PT-CARE-001",
        "encounter_id": 1,
        "screening_session_id": 1,
        "order_id": 1,
        "order_result_id": 1,
        "title": "Critical result follow-up plan",
        "plan_type": "case_management",
        "priority": "urgent",
        "reason": "Create care plan",
        "start_date": "2026-06-12",
        "target_date": "2026-06-30",
    }


def _override_dependencies(session: _ClinicalCarePlanDb, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_care_plan_create_preview_validates_patient_linkage() -> None:
    db = _ClinicalCarePlanDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/care-plans/preview", json={**_create_payload(), "patient_id": "PT-MISSING"})
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert any(issue["issue_type"] == "unknown_patient" for issue in payload["blocking_issues"])


def test_care_plan_create_preview_validates_encounter_patient_linkage() -> None:
    patient = _patient()
    other_patient = _patient(2, "PT-CARE-002")
    other_appointment = _appointment(other_patient, 2)
    other_session = _screening_session(other_patient, other_appointment, 2)
    db = _ClinicalCarePlanDb(
        patients=[patient, other_patient],
        encounters=[_encounter(other_patient, other_appointment, other_session, 2)],
    )
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/care-plans/preview", json={**_create_payload(), "encounter_id": 2})
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert any(issue["issue_type"] == "encounter_patient_mismatch" for issue in payload["blocking_issues"])


def test_care_plan_create_preview_validates_order_and_result_patient_linkage() -> None:
    patient = _patient()
    other_patient = _patient(2, "PT-CARE-002")
    other_appointment = _appointment(other_patient, 2)
    other_session = _screening_session(other_patient, other_appointment, 2)
    other_encounter = _encounter(other_patient, other_appointment, other_session, 2)
    db = _ClinicalCarePlanDb(
        patients=[patient, other_patient],
        orders=[_order(other_patient, other_encounter, other_session, other_appointment, 2)],
    )
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/care-plans/preview",
            json={**_create_payload(), "order_id": 2, "order_result_id": 1},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert any(issue["issue_type"] == "order_patient_mismatch" for issue in payload["blocking_issues"])


def test_care_plan_create_rejects_missing_and_invalid_confirmation_headers() -> None:
    db = _ClinicalCarePlanDb()
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post("/api/clinical/care-plans", json=_create_payload())
        invalid = TestClient(app).post(
            "/api/clinical/care-plans",
            headers={"X-Confirm-Generation": "false"},
            json=_create_payload(),
        )
    finally:
        _clear_overrides()

    assert missing.status_code == 409
    assert invalid.status_code == 409
    assert missing.json()["detail"]["status"] == "confirmation_required"
    assert invalid.json()["detail"]["status"] == "confirmation_required"


def test_care_plan_create_accepts_confirmation_and_writes_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalCarePlanDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/care-plans",
            headers={"X-Confirm-Generation": "true"},
            json={**_create_payload(), "preview_hash": "sha256-care-plan"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    assert response.json()["care_plan"]["care_plan_number"].startswith("CP-")
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "care_plan.create"
    assert entries[-1]["preview_hash"] == "sha256-care-plan"


def test_goal_intervention_and_task_commits_append_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalCarePlanDb(care_plans=[_care_plan()])
    _override_dependencies(db, _internal_user())
    try:
        goal = TestClient(app).post(
            "/api/clinical/care-plans/1/goals",
            headers={"X-Confirm-Generation": "true"},
            json={"goal": "Complete follow-up review", "reason": "Add goal", "preview_hash": "sha256-goal"},
        )
        intervention = TestClient(app).post(
            "/api/clinical/care-plans/1/interventions",
            headers={"X-Confirm-Generation": "true"},
            json={"intervention": "Call patient", "intervention_type": "follow_up", "owner": "Care coordinator", "reason": "Add intervention", "preview_hash": "sha256-intervention"},
        )
        missing_owner = TestClient(app).post(
            "/api/clinical/care-plans/1/tasks",
            headers={"X-Confirm-Generation": "true"},
            json={"title": "Schedule review", "owner": "", "due_date": "2026-06-20"},
        )
        task = TestClient(app).post(
            "/api/clinical/care-plans/1/tasks",
            headers={"X-Confirm-Generation": "true"},
            json={"title": "Schedule review", "owner": "Care coordinator", "due_date": "2026-06-20", "reason": "Add task", "preview_hash": "sha256-task"},
        )
    finally:
        _clear_overrides()

    assert goal.status_code == 200
    assert intervention.status_code == 200
    assert missing_owner.status_code == 422
    assert task.status_code == 200
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert [entry["workflow"] for entry in entries[-3:]] == [
        "care_plan.goal_add",
        "care_plan.intervention_add",
        "care_plan.task_add",
    ]


def test_progress_update_appends_timeline_and_writes_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalCarePlanDb(care_plans=[_care_plan()])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/care-plans/1/progress",
            headers={"X-Confirm-Generation": "true"},
            json={
                "progress_note": "Patient contacted and follow-up visit scheduled.",
                "status_update": "on_hold",
                "reason": "Add progress",
                "preview_hash": "sha256-progress",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert len(db.care_plans[0].progress_notes) == 1
    assert db.care_plans[0].status == "on_hold"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "care_plan.progress_add"


def test_closure_requires_summary_reason_and_blocks_later_activity(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalCarePlanDb(care_plans=[_care_plan()])
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post(
            "/api/clinical/care-plans/1/close",
            headers={"X-Confirm-Generation": "true"},
            json={"outcome_summary": "", "closure_reason": "Resolved"},
        )
        close = TestClient(app).post(
            "/api/clinical/care-plans/1/close",
            headers={"X-Confirm-Generation": "true"},
            json={
                "outcome_summary": "Follow-up completed and patient notified.",
                "closure_reason": "Care coordination complete",
                "reason": "Close care plan",
                "preview_hash": "sha256-close",
            },
        )
        task_after_close = TestClient(app).post(
            "/api/clinical/care-plans/1/tasks",
            headers={"X-Confirm-Generation": "true"},
            json={"title": "Late task", "owner": "Care coordinator", "due_date": "2026-06-20"},
        )
        progress_after_close = TestClient(app).post(
            "/api/clinical/care-plans/1/progress",
            headers={"X-Confirm-Generation": "true"},
            json={"progress_note": "Late progress"},
        )
    finally:
        _clear_overrides()

    assert missing.status_code == 422
    assert close.status_code == 200
    assert db.care_plans[0].status == "closed"
    assert task_after_close.status_code == 409
    assert progress_after_close.status_code == 409
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "care_plan.close"


def test_external_partner_care_plan_mutation_is_rejected() -> None:
    db = _ClinicalCarePlanDb(permissions=["partner.portal"], care_plans=[_care_plan()])
    _override_dependencies(db, _external_user())
    try:
        create_preview = TestClient(app).post("/api/clinical/care-plans/preview", json=_create_payload())
        goal_preview = TestClient(app).post(
            "/api/clinical/care-plans/1/goals/preview",
            json={"goal": "External mutation attempt"},
        )
    finally:
        _clear_overrides()

    assert create_preview.status_code == 403
    assert goal_preview.status_code == 403
