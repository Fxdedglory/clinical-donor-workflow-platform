import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models import Patient, PatientConsent, PatientContact, PatientInsurance
from app.services import clinical_workflows
from fastapi.testclient import TestClient


class _PermissionResult:
    def __init__(self, permissions: list[str]) -> None:
        self.permissions = permissions

    def all(self):
        return [(permission,) for permission in self.permissions]


class _PatientResult:
    def __init__(self, patients: list[Patient]) -> None:
        self.patients = patients

    def scalar_one_or_none(self):
        return self.patients[0] if self.patients else None

    def scalars(self):
        return self

    def all(self):
        return self.patients


class _ClinicalPatientSession:
    def __init__(self, *, permissions: list[str] | None = None, patients: list[Patient] | None = None) -> None:
        self.permissions = permissions or ["patients.read", "patients.create", "patients.manage"]
        self.patients = patients or []
        self.committed = False
        self._next_patient_pk = len(self.patients) + 1
        self._next_contact_id = 1
        self._next_insurance_id = 1
        self._next_consent_id = 1

    def execute(self, statement, *_args, **_kwargs):
        if "bridge_role_permission" in str(statement):
            return _PermissionResult(self.permissions)
        return _PatientResult(self.patients)

    def add(self, value):
        now = datetime.now(UTC)
        if isinstance(value, Patient):
            if value.patient_pk is None:
                value.patient_pk = self._next_patient_pk
                self._next_patient_pk += 1
            value.created_at = value.created_at or now
            value.updated_at = value.updated_at or now
            value.source = value.source or "clinical_registration"
            value.version = value.version or 1
            value.is_deleted = bool(value.is_deleted)
            for contact in value.contacts:
                self._prepare_contact(contact, value.patient_pk, now)
            for insurance in value.insurance_profiles:
                self._prepare_insurance(insurance, value.patient_pk, now)
            for consent in value.consents:
                self._prepare_consent(consent, value.patient_pk, now)
            self.patients.append(value)
            return
        if isinstance(value, PatientContact):
            patient = self.patients[0]
            self._prepare_contact(value, patient.patient_pk, now)
            patient.contacts.append(value)
            return
        if isinstance(value, PatientInsurance):
            patient = self.patients[0]
            self._prepare_insurance(value, patient.patient_pk, now)
            patient.insurance_profiles.append(value)
            return
        if isinstance(value, PatientConsent):
            patient = self.patients[0]
            self._prepare_consent(value, patient.patient_pk, now)
            patient.consents.append(value)

    def _prepare_contact(self, value: PatientContact, patient_pk: int, now: datetime) -> None:
        value.contact_id = value.contact_id or self._next_contact_id
        self._next_contact_id += 1
        value.patient_pk = patient_pk
        value.created_at = value.created_at or now
        value.updated_at = value.updated_at or now

    def _prepare_insurance(self, value: PatientInsurance, patient_pk: int, now: datetime) -> None:
        value.insurance_id = value.insurance_id or self._next_insurance_id
        self._next_insurance_id += 1
        value.patient_pk = patient_pk
        value.created_at = value.created_at or now
        value.updated_at = value.updated_at or now

    def _prepare_consent(self, value: PatientConsent, patient_pk: int, now: datetime) -> None:
        value.consent_id = value.consent_id or self._next_consent_id
        self._next_consent_id += 1
        value.patient_pk = patient_pk
        value.created_at = value.created_at or now
        value.updated_at = value.updated_at or now

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def refresh(self, _value) -> None:
        return None


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="intake",
        email="intake@example.org",
        full_name="Intake User",
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


def _patient(patient_id: str = "PT-EXISTING") -> Patient:
    now = datetime.now(UTC)
    return Patient(
        patient_pk=1,
        patient_id=patient_id,
        first_name="Avery",
        last_name="Stone",
        date_of_birth=date(1985, 2, 3),
        sex_at_birth="Female",
        phone="555-0100",
        email="avery.stone@example.org",
        status="active",
        source="clinical_registration",
        version=1,
        created_at=now,
        updated_at=now,
        is_deleted=False,
    )


def _create_payload() -> dict[str, object]:
    return {
        "first_name": "Avery",
        "last_name": "Stone",
        "date_of_birth": "1985-02-03",
        "sex_at_birth": "Female",
        "phone": "555-0100",
        "email": "avery.stone@example.org",
        "status": "active",
    }


def _override_dependencies(session: _ClinicalPatientSession, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_patient_create_preview_validates_payload() -> None:
    session = _ClinicalPatientSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/patients/preview", json=_create_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == "patient.create"
    assert payload["validation_status"] == "passed"
    assert payload["preview_hash"]


def test_patient_create_commit_rejects_missing_confirmation_header() -> None:
    session = _ClinicalPatientSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/patients", json=_create_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"


def test_patient_create_commit_rejects_invalid_confirmation_header() -> None:
    session = _ClinicalPatientSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/patients",
            headers={"X-Confirm-Generation": "false"},
            json=_create_payload(),
        )
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"


def test_patient_create_commit_succeeds_and_writes_workflow_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    session = _ClinicalPatientSession()
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/patients",
            headers={"X-Confirm-Generation": "true"},
            json={**_create_payload(), "preview_hash": "sha256-create-preview"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    payload = response.json()
    assert payload["patient"]["patient_id"].startswith("PT-")
    assert payload["operation_id"]
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "patient.create"
    assert entries[-1]["preview_hash"] == "sha256-create-preview"


def test_duplicate_risk_preview_returns_warning() -> None:
    session = _ClinicalPatientSession(patients=[_patient()])
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/patients/preview", json=_create_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "warning"
    assert payload["duplicate_warnings"][0]["patient_id"] == "PT-EXISTING"
    assert "date_of_birth" in payload["duplicate_warnings"][0]["matched_fields"]


def test_patient_update_commit_writes_workflow_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    session = _ClinicalPatientSession(patients=[_patient()])
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).patch(
            "/api/clinical/patients/PT-EXISTING",
            headers={"X-Confirm-Generation": "true"},
            json={"preferred_language": "Spanish", "preview_hash": "sha256-update-preview"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "patient.update_demographics"
    assert entries[-1]["changes"]["preferred_language"]["after"] == "Spanish"


def test_consent_capture_commit_writes_workflow_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    session = _ClinicalPatientSession(patients=[_patient()])
    _override_dependencies(session, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/patients/PT-EXISTING/consents",
            headers={"X-Confirm-Generation": "true"},
            json={"consent_type": "Treatment", "consent_status": "captured", "notes": "Verbal consent captured."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "patient.capture_consent"
    assert entries[-1]["changes"]["consent_type"] == "Treatment"


def test_external_partner_mutation_is_rejected() -> None:
    session = _ClinicalPatientSession(permissions=["partner.portal"])
    _override_dependencies(session, _external_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/patients/preview",
            json=_create_payload(),
        )
    finally:
        _clear_overrides()

    assert response.status_code == 403
    assert "External users" in response.json()["detail"]
