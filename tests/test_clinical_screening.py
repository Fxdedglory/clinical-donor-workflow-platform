import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models import (
    Appointment,
    ClinicalDeferral,
    ClinicalScreeningAnswer,
    ClinicalScreeningOutcome,
    ClinicalScreeningSession,
    ClinicalScreeningStatusHistory,
    ClinicalScreeningVitals,
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


class _ClinicalScreeningSessionDb:
    def __init__(
        self,
        *,
        permissions: list[str] | None = None,
        patients: list[Patient] | None = None,
        appointments: list[Appointment] | None = None,
        sessions: list[ClinicalScreeningSession] | None = None,
    ) -> None:
        self.permissions = permissions or ["screening.read", "screening.manage", "screening.override", "patients.read"]
        self.patients = patients or [_patient()]
        self.appointments = appointments or [_appointment(self.patients[0])]
        self.sessions = sessions or []
        self.deferrals: list[ClinicalDeferral] = []
        self.committed = False
        self._next_session_id = 1
        self._next_answer_id = 1
        self._next_vitals_id = 1
        self._next_outcome_id = 1
        self._next_deferral_id = 1
        self._next_history_id = 1
        for session in self.sessions:
            self._prepare_session(session)

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
        if "clinical_screening_sessions" in sql:
            return _Rows(_id_filter(self.sessions, "session_id", sql))
        if "clinical_deferrals" in sql:
            return _Rows(_id_filter(self.deferrals, "deferral_id", sql))
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
        if isinstance(value, ClinicalScreeningSession):
            if value not in self.sessions:
                self.sessions.append(value)
            self._prepare_session(value)

    def flush(self) -> None:
        for session in self.sessions:
            self._prepare_session(session)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        if isinstance(value, ClinicalScreeningSession):
            self._prepare_session(value)

    def _prepare_session(self, session: ClinicalScreeningSession) -> None:
        now = datetime.now(UTC)
        if session.session_id is None:
            session.session_id = self._next_session_id
            self._next_session_id += 1
        session.created_at = session.created_at or now
        session.updated_at = session.updated_at or now
        session.source = session.source or "clinical_screening"
        session.version = session.version or 1
        session.reason = session.reason or ""
        session.supervisor_review_required = bool(session.supervisor_review_required)
        session.is_deleted = bool(session.is_deleted)
        session.patient = session.patient or self.patients[0]
        session.patient_pk = session.patient_pk or session.patient.patient_pk
        if session.appointment_id:
            session.appointment = session.appointment or self.appointments[0]
        for answer in session.answers:
            if answer.answer_id is None:
                answer.answer_id = self._next_answer_id
                self._next_answer_id += 1
            answer.session_id = session.session_id
            answer.created_at = answer.created_at or now
            answer.updated_at = answer.updated_at or now
        for vitals in session.vitals:
            if vitals.vitals_id is None:
                vitals.vitals_id = self._next_vitals_id
                self._next_vitals_id += 1
            vitals.session_id = session.session_id
            vitals.captured_at = vitals.captured_at or now
        for outcome in session.outcomes:
            if outcome.outcome_id is None:
                outcome.outcome_id = self._next_outcome_id
                self._next_outcome_id += 1
            outcome.session_id = session.session_id
            outcome.created_at = outcome.created_at or now
            outcome.supervisor_review_required = bool(outcome.supervisor_review_required)
            outcome.blocking_issues = outcome.blocking_issues or []
            outcome.warnings = outcome.warnings or []
            outcome.rule_results = outcome.rule_results or []
            outcome.reason = outcome.reason or ""
        for deferral in session.deferrals:
            if deferral.deferral_id is None:
                deferral.deferral_id = self._next_deferral_id
                self._next_deferral_id += 1
            deferral.session_id = session.session_id
            deferral.patient_pk = session.patient_pk
            deferral.patient = session.patient
            deferral.created_at = deferral.created_at or now
            deferral.starts_at = deferral.starts_at or now
            if deferral not in self.deferrals:
                self.deferrals.append(deferral)
        for history in session.status_history:
            if history.history_id is None:
                history.history_id = self._next_history_id
                self._next_history_id += 1
            history.session_id = session.session_id
            history.changed_at = history.changed_at or now


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="screening",
        email="screening@example.org",
        full_name="Screening User",
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


def _patient(patient_id: str = "PT-SCREEN-001") -> Patient:
    return Patient(
        patient_pk=1,
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


def _appointment(patient: Patient) -> Appointment:
    return Appointment(
        appointment_id=1,
        appointment_number="APT-SCREEN-001",
        patient_pk=patient.patient_pk,
        patient=patient,
        provider_id=1,
        room_id=1,
        appointment_type_id=1,
        scheduled_start=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        status="scheduled",
        reason="Donor intake",
        source="clinical_scheduling",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _session(status: str = "in_progress", *, complete: bool = False) -> ClinicalScreeningSession:
    patient = _patient()
    session = ClinicalScreeningSession(
        session_id=1,
        session_number="SCR-EXISTING-1",
        patient_pk=patient.patient_pk,
        patient=patient,
        appointment_id=1,
        appointment=_appointment(patient),
        template_id="minimal_donor_screening_v1",
        status=status,
        reason="Start screening",
        source="clinical_screening",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    session.answers = []
    session.vitals = []
    session.outcomes = []
    session.deferrals = []
    session.status_history = []
    if complete:
        session.answers = [
            ClinicalScreeningAnswer(question_key=key, answer_value={"value": value}, notes="")
            for key, value in _complete_answers().items()
        ]
        session.vitals = [ClinicalScreeningVitals(**_complete_vitals_model())]
    return session


def _session_payload() -> dict[str, object]:
    return {
        "patient_id": "PT-SCREEN-001",
        "appointment_id": 1,
        "reason": "Start donor screening",
    }


def _complete_answers() -> dict[str, object]:
    return {
        "identity_verified": True,
        "authorization_verified": True,
        "infectious_symptoms": False,
        "transmissible_disease_history": False,
        "iv_drug_use": False,
        "incarceration_history": False,
        "travel_exposure": False,
        "high_risk_behavior": False,
    }


def _complete_vitals_payload() -> dict[str, object]:
    return {
        "height_cm": 170,
        "weight_kg": 72,
        "temperature_c": 36.8,
        "blood_pressure_systolic": 118,
        "blood_pressure_diastolic": 76,
        "pulse": 72,
        "respiration_rate": 14,
        "oxygen_saturation": 98,
    }


def _complete_vitals_model() -> dict[str, object]:
    return {
        **_complete_vitals_payload(),
        "captured_at": datetime.now(UTC),
        "notes": "",
    }


def _override_dependencies(session: _ClinicalScreeningSessionDb, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_screening_session_create_preview_validates_patient_linkage() -> None:
    session = _ClinicalScreeningSessionDb()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/preview",
            json={**_session_payload(), "patient_id": "PT-MISSING"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert payload["blocking_issues"][0]["issue_type"] == "unknown_patient"


def test_screening_session_commit_rejects_missing_confirmation_header() -> None:
    session = _ClinicalScreeningSessionDb()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/screening/sessions", json=_session_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"


def test_screening_session_commit_succeeds_with_confirmation(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    session = _ClinicalScreeningSessionDb()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions",
            headers={"X-Confirm-Generation": "true"},
            json={**_session_payload(), "preview_hash": "sha256-session"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    assert response.json()["session"]["session_number"].startswith("SCR-")
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "screening.session_create"
    assert entries[-1]["preview_hash"] == "sha256-session"


def test_questionnaire_preview_reports_missing_required_answers() -> None:
    db = _ClinicalScreeningSessionDb(sessions=[_session()])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/questionnaire/preview",
            json={"answers": {"identity_verified": True}},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert any(issue["issue_type"] == "missing_required_answer" for issue in payload["blocking_issues"])


def test_questionnaire_commit_writes_audit_event(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalScreeningSessionDb(sessions=[_session()])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/questionnaire",
            headers={"X-Confirm-Generation": "true"},
            json={"answers": _complete_answers(), "preview_hash": "sha256-questionnaire"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert len(db.sessions[0].answers) == len(_complete_answers())
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "screening.questionnaire_commit"


def test_vitals_preview_reports_missing_and_out_of_range_vitals() -> None:
    db = _ClinicalScreeningSessionDb(sessions=[_session()])
    _override_dependencies(db, _internal_user())
    try:
        missing_response = TestClient(app).post("/api/clinical/screening/sessions/1/vitals/preview", json={})
        range_response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/vitals/preview",
            json={**_complete_vitals_payload(), "temperature_c": 43},
        )
    finally:
        _clear_overrides()

    assert missing_response.status_code == 200
    assert any(issue["issue_type"] == "missing_required_vital" for issue in missing_response.json()["blocking_issues"])
    assert range_response.status_code == 200
    assert any(issue["issue_type"] == "out_of_range_vital" for issue in range_response.json()["blocking_issues"])


def test_vitals_commit_writes_audit_event(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalScreeningSessionDb(sessions=[_session()])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/vitals",
            headers={"X-Confirm-Generation": "true"},
            json={**_complete_vitals_payload(), "preview_hash": "sha256-vitals"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert db.sessions[0].vitals[-1].weight_kg == 72
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "screening.vitals_commit"


def test_eligibility_preview_returns_explainable_rule_output() -> None:
    screening = _session(complete=True)
    screening.answers[2].answer_value = {"value": True}
    db = _ClinicalScreeningSessionDb(sessions=[screening])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/screening/sessions/1/eligibility/preview", json={})
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposed_outcome"] == "temporarily_deferred"
    assert payload["rules_evaluated"]
    assert payload["recommended_deferral_type"] == "temporary"


def test_result_commit_rejects_missing_required_questionnaire_or_vitals() -> None:
    db = _ClinicalScreeningSessionDb(sessions=[_session()])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/result",
            headers={"X-Confirm-Generation": "true"},
            json={"outcome": "eligible", "reason": "Complete"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "screening_validation_failed"


def test_eligible_result_commit_updates_status_and_writes_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    screening = _session(status="pending_eligibility", complete=True)
    db = _ClinicalScreeningSessionDb(sessions=[screening])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/result",
            headers={"X-Confirm-Generation": "true"},
            json={"outcome": "eligible", "reason": "Meets screening criteria", "preview_hash": "sha256-result"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert screening.status == "eligible"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "screening.result_commit"


def test_temporary_deferral_creates_deferral_and_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    screening = _session(status="pending_eligibility", complete=True)
    screening.answers[2].answer_value = {"value": True}
    db = _ClinicalScreeningSessionDb(sessions=[screening])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/result",
            headers={"X-Confirm-Generation": "true"},
            json={"outcome": "temporarily_deferred", "reason": "Fever symptoms", "deferral_type": "temporary"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["deferral"]["deferral_type"] == "temporary"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert [entry["workflow"] for entry in entries][-2:] == ["screening.result_commit", "screening.deferral_create"]


def test_permanent_deferral_creates_deferral_and_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    screening = _session(status="pending_eligibility", complete=True)
    screening.answers[3].answer_value = {"value": True}
    db = _ClinicalScreeningSessionDb(sessions=[screening])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/result",
            headers={"X-Confirm-Generation": "true"},
            json={"outcome": "permanently_deferred", "reason": "Permanent risk disclosure", "deferral_type": "permanent"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["deferral"]["deferral_type"] == "permanent"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "screening.deferral_create"


def test_supervisor_override_requires_reason_and_writes_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    screening = _session(status="requires_supervisor_review", complete=True)
    screening.current_outcome = "requires_supervisor_review"
    db = _ClinicalScreeningSessionDb(sessions=[screening])
    _override_dependencies(db, _internal_user())
    try:
        missing_reason = TestClient(app).post(
            "/api/clinical/screening/sessions/1/override/preview",
            json={"original_outcome": "requires_supervisor_review", "override_outcome": "eligible"},
        )
        response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/override",
            headers={"X-Confirm-Generation": "true"},
            json={
                "original_outcome": "requires_supervisor_review",
                "override_outcome": "eligible_with_conditions",
                "reason": "Supervisor accepted documented mitigation",
            },
        )
    finally:
        _clear_overrides()

    assert missing_reason.status_code == 422
    assert response.status_code == 200
    assert screening.status == "eligible_with_conditions"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "screening.override_commit"


def test_external_partner_mutation_is_rejected() -> None:
    db = _ClinicalScreeningSessionDb(permissions=["partner.portal"], sessions=[_session()])
    _override_dependencies(db, _external_user())
    try:
        response = TestClient(app).post("/api/clinical/screening/sessions/preview", json=_session_payload())
        override_response = TestClient(app).post(
            "/api/clinical/screening/sessions/1/override/preview",
            json={"original_outcome": "requires_supervisor_review", "override_outcome": "eligible", "reason": "No"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 403
    assert override_response.status_code == 403
