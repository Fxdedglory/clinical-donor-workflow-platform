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
    ClinicalEncounterDiagnosis,
    ClinicalEncounterNote,
    ClinicalEncounterStatusHistory,
    ClinicalNoteTemplate,
    ClinicalPatientAllergy,
    ClinicalPatientMedication,
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


class _ClinicalEncounterDb:
    def __init__(
        self,
        *,
        permissions: list[str] | None = None,
        patients: list[Patient] | None = None,
        appointments: list[Appointment] | None = None,
        sessions: list[ClinicalScreeningSession] | None = None,
        encounters: list[ClinicalEncounter] | None = None,
    ) -> None:
        self.permissions = permissions or ["encounters.read", "encounters.manage", "encounters.sign", "patients.read"]
        self.patients = patients or [_patient()]
        self.appointments = appointments or [_appointment(self.patients[0], status="checked_in")]
        self.sessions = sessions or [_screening_session(self.patients[0], self.appointments[0])]
        self.encounters = encounters or []
        self.templates = [
            ClinicalNoteTemplate(
                template_id=1,
                template_key="donor_screening_encounter_v1",
                name="Donor screening encounter",
                note_type="clinical_note",
                body="Subjective:\n\nObjective:\n\nAssessment:\n\nPlan:\n",
                status="active",
                version=1,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                is_deleted=False,
            )
        ]
        self.committed = False
        self._next_encounter_id = 1
        self._next_note_id = 1
        self._next_diagnosis_id = 1
        self._next_allergy_id = 1
        self._next_medication_id = 1
        self._next_history_id = 1
        for patient in self.patients:
            self._prepare_patient(patient)
        for encounter in self.encounters:
            self._prepare_encounter(encounter)

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
        if "clinical_note_templates" in sql:
            return _Rows(_id_filter(self.templates, "template_id", sql))
        if "clinical_encounter_notes" in sql:
            return _Rows(_id_filter(self._notes(), "note_id", sql))
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
        if isinstance(value, ClinicalEncounter) and value not in self.encounters:
            self.encounters.append(value)
            self._prepare_encounter(value)

    def flush(self) -> None:
        for patient in self.patients:
            self._prepare_patient(patient)
        for encounter in self.encounters:
            self._prepare_encounter(encounter)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        if isinstance(value, ClinicalEncounter):
            self._prepare_encounter(value)
        if isinstance(value, Patient):
            self._prepare_patient(value)

    def _notes(self) -> list[ClinicalEncounterNote]:
        return [note for encounter in self.encounters for note in encounter.notes]

    def _prepare_patient(self, patient: Patient) -> None:
        now = datetime.now(UTC)
        patient.created_at = patient.created_at or now
        patient.updated_at = patient.updated_at or now
        patient.source = patient.source or "clinical_registration"
        patient.version = patient.version or 1
        patient.is_deleted = bool(patient.is_deleted)
        patient.allergies = list(getattr(patient, "allergies", []) or [])
        patient.medications = list(getattr(patient, "medications", []) or [])
        patient.encounters = list(getattr(patient, "encounters", []) or [])
        for allergy in patient.allergies:
            if allergy.allergy_id is None:
                allergy.allergy_id = self._next_allergy_id
                self._next_allergy_id += 1
            allergy.patient_pk = patient.patient_pk
            allergy.patient = patient
            allergy.created_at = allergy.created_at or now
            allergy.updated_at = allergy.updated_at or now
            allergy.reaction = allergy.reaction or ""
            allergy.notes = allergy.notes or ""
            allergy.is_deleted = bool(allergy.is_deleted)
        for medication in patient.medications:
            if medication.medication_id is None:
                medication.medication_id = self._next_medication_id
                self._next_medication_id += 1
            medication.patient_pk = patient.patient_pk
            medication.patient = patient
            medication.created_at = medication.created_at or now
            medication.updated_at = medication.updated_at or now
            medication.dose = medication.dose or ""
            medication.route = medication.route or ""
            medication.frequency = medication.frequency or ""
            medication.indication = medication.indication or ""
            medication.notes = medication.notes or ""
            medication.is_deleted = bool(medication.is_deleted)

    def _prepare_encounter(self, encounter: ClinicalEncounter) -> None:
        now = datetime.now(UTC)
        if encounter.encounter_id is None:
            encounter.encounter_id = self._next_encounter_id
            self._next_encounter_id += 1
        encounter.created_at = encounter.created_at or now
        encounter.updated_at = encounter.updated_at or now
        encounter.source = encounter.source or "clinical_encounters"
        encounter.version = encounter.version or 1
        encounter.chief_complaint = encounter.chief_complaint or ""
        encounter.reason = encounter.reason or ""
        encounter.is_deleted = bool(encounter.is_deleted)
        encounter.patient = encounter.patient or self.patients[0]
        encounter.patient_pk = encounter.patient_pk or encounter.patient.patient_pk
        if encounter not in encounter.patient.encounters:
            encounter.patient.encounters.append(encounter)
        if encounter.appointment_id:
            encounter.appointment = encounter.appointment or self.appointments[0]
        if encounter.screening_session_id:
            encounter.screening_session = encounter.screening_session or self.sessions[0]
        encounter.notes = list(getattr(encounter, "notes", []) or [])
        encounter.diagnoses = list(getattr(encounter, "diagnoses", []) or [])
        encounter.status_history = list(getattr(encounter, "status_history", []) or [])
        for note in encounter.notes:
            if note.note_id is None:
                note.note_id = self._next_note_id
                self._next_note_id += 1
            note.encounter_id = encounter.encounter_id
            note.encounter = encounter
            if note.template_id:
                note.template = note.template or self.templates[0]
            note.created_at = note.created_at or now
            note.updated_at = note.updated_at or now
            note.title = note.title or "Clinical encounter note"
            note.content = note.content or ""
            note.amendment_reason = note.amendment_reason or ""
            note.version = note.version or 1
            note.is_addendum = bool(note.is_addendum)
        for diagnosis in encounter.diagnoses:
            if diagnosis.diagnosis_id is None:
                diagnosis.diagnosis_id = self._next_diagnosis_id
                self._next_diagnosis_id += 1
            diagnosis.encounter_id = encounter.encounter_id
            diagnosis.encounter = encounter
            diagnosis.created_at = diagnosis.created_at or now
            diagnosis.notes = diagnosis.notes or ""
        for history in encounter.status_history:
            if history.history_id is None:
                history.history_id = self._next_history_id
                self._next_history_id += 1
            history.encounter_id = encounter.encounter_id
            history.changed_at = history.changed_at or now
            history.reason = history.reason or ""
            history.notes = history.notes or ""


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="encounter",
        email="encounter@example.org",
        full_name="Encounter User",
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


def _patient(patient_id: str = "PT-ENC-001") -> Patient:
    patient = Patient(
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
    patient.allergies = []
    patient.medications = []
    patient.encounters = []
    return patient


def _appointment(patient: Patient, *, status: str = "checked_in") -> Appointment:
    return Appointment(
        appointment_id=1,
        appointment_number="APT-ENC-001",
        patient_pk=patient.patient_pk,
        patient=patient,
        provider_id=1,
        room_id=1,
        appointment_type_id=1,
        scheduled_start=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        check_in_time=datetime(2026, 6, 15, 8, 55, tzinfo=UTC) if status == "checked_in" else None,
        status=status,
        reason="Donor intake",
        source="clinical_scheduling",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _screening_session(patient: Patient, appointment: Appointment) -> ClinicalScreeningSession:
    return ClinicalScreeningSession(
        session_id=1,
        session_number="SCR-ENC-001",
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


def _encounter(status: str = "ready_for_signature", *, signed: bool = False) -> ClinicalEncounter:
    patient = _patient()
    appointment = _appointment(patient)
    session = _screening_session(patient, appointment)
    encounter = ClinicalEncounter(
        encounter_id=1,
        encounter_number="ENC-EXISTING-1",
        patient_pk=patient.patient_pk,
        patient=patient,
        appointment_id=appointment.appointment_id,
        appointment=appointment,
        screening_session_id=session.session_id,
        screening_session=session,
        encounter_type="donor_screening",
        status=status,
        chief_complaint="Donor screening review",
        reason="Create encounter",
        started_at=datetime.now(UTC),
        source="clinical_encounters",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    note_status = "signed" if signed else "ready_for_signature"
    encounter.notes = [
        ClinicalEncounterNote(
            note_id=1,
            encounter_id=1,
            note_type="clinical_note",
            title="Clinical encounter note",
            content="Subjective: stable\nObjective: reviewed\nAssessment: eligible\nPlan: proceed",
            status=note_status,
            version=1,
            is_addendum=False,
            amendment_reason="",
            signed_at=datetime.now(UTC) if signed else None,
            signed_by=7 if signed else None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    ]
    encounter.diagnoses = []
    encounter.status_history = []
    patient.encounters = [encounter]
    return encounter


def _create_payload() -> dict[str, object]:
    return {
        "patient_id": "PT-ENC-001",
        "appointment_id": 1,
        "screening_session_id": 1,
        "chief_complaint": "Donor screening review",
        "reason": "Create encounter",
    }


def _override_dependencies(session: _ClinicalEncounterDb, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_encounter_create_preview_requires_checked_in_appointment() -> None:
    patient = _patient()
    db = _ClinicalEncounterDb(patients=[patient], appointments=[_appointment(patient, status="scheduled")])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/encounters/preview", json=_create_payload())
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert payload["blocking_issues"][0]["issue_type"] == "appointment_not_checked_in"


def test_encounter_create_rejects_missing_and_invalid_confirmation_headers() -> None:
    db = _ClinicalEncounterDb()
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post("/api/clinical/encounters", json=_create_payload())
        invalid = TestClient(app).post(
            "/api/clinical/encounters",
            headers={"X-Confirm-Generation": "false"},
            json=_create_payload(),
        )
    finally:
        _clear_overrides()

    assert missing.status_code == 409
    assert invalid.status_code == 409
    assert missing.json()["detail"]["status"] == "confirmation_required"
    assert invalid.json()["detail"]["status"] == "confirmation_required"


def test_encounter_create_accepts_valid_confirmation_and_writes_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalEncounterDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/encounters",
            headers={"X-Confirm-Generation": "true"},
            json={**_create_payload(), "preview_hash": "sha256-encounter"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    assert response.json()["encounter"]["encounter_number"].startswith("ENC-")
    assert db.encounters[0].status == "in_progress"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "encounter.create"
    assert entries[-1]["preview_hash"] == "sha256-encounter"


def test_encounter_note_save_sign_and_direct_edit_lock(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    encounter = _encounter(status="in_progress")
    encounter.notes = []
    db = _ClinicalEncounterDb(encounters=[encounter])
    _override_dependencies(db, _internal_user())
    note_payload = {
        "template_id": 1,
        "title": "Clinical encounter note",
        "content": "Subjective: stable\nObjective: reviewed\nAssessment: eligible\nPlan: proceed",
        "reason": "Save note",
    }
    try:
        note_response = TestClient(app).post(
            "/api/clinical/encounters/1/notes",
            headers={"X-Confirm-Generation": "true"},
            json={**note_payload, "preview_hash": "sha256-note"},
        )
        sign_response = TestClient(app).post(
            "/api/clinical/encounters/1/sign",
            headers={"X-Confirm-Generation": "true"},
            json={"note_id": 1, "reason": "Sign note", "preview_hash": "sha256-sign"},
        )
        locked_response = TestClient(app).post(
            "/api/clinical/encounters/1/notes/preview",
            json={**note_payload, "note_id": 1, "content": "Attempt to edit signed note"},
        )
    finally:
        _clear_overrides()

    assert note_response.status_code == 200
    assert sign_response.status_code == 200
    assert db.encounters[0].notes[0].status == "signed"
    assert db.encounters[0].status == "signed"
    assert locked_response.status_code == 200
    assert locked_response.json()["validation_status"] == "failed"
    assert any(issue["issue_type"] == "signed_note_locked" for issue in locked_response.json()["blocking_issues"])
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert [entry["workflow"] for entry in entries][-2:] == ["encounter.note_save", "encounter.sign"]


def test_encounter_amendment_creates_signed_addendum(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalEncounterDb(encounters=[_encounter(status="signed", signed=True)])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/encounters/1/amend",
            headers={"X-Confirm-Generation": "true"},
            json={
                "note_id": 1,
                "amendment_text": "Addendum: patient reported no new symptoms after signature.",
                "reason": "Late clinical clarification",
                "preview_hash": "sha256-amend",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert db.encounters[0].status == "amended"
    assert db.encounters[0].notes[0].status == "amended"
    assert db.encounters[0].notes[-1].is_addendum is True
    assert db.encounters[0].notes[-1].status == "signed"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "encounter.amend"


def test_diagnosis_allergy_and_medication_commits_append_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(json.dumps([{"workflow": "existing.operation"}]), encoding="utf-8")
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalEncounterDb(encounters=[_encounter(status="in_progress")])
    _override_dependencies(db, _internal_user())
    try:
        diagnosis = TestClient(app).post(
            "/api/clinical/encounters/1/diagnoses",
            headers={"X-Confirm-Generation": "true"},
            json={"code": "Z00.00", "display": "General examination", "reason": "Add problem"},
        )
        allergy = TestClient(app).post(
            "/api/clinical/patients/PT-ENC-001/allergies",
            headers={"X-Confirm-Generation": "true"},
            json={"allergen": "Penicillin", "reaction": "Rash", "severity": "moderate", "reason": "Reported allergy"},
        )
        medication = TestClient(app).post(
            "/api/clinical/patients/PT-ENC-001/medications",
            headers={"X-Confirm-Generation": "true"},
            json={"medication_name": "Acetaminophen", "dose": "500 mg", "reason": "Reported medication"},
        )
    finally:
        _clear_overrides()

    assert diagnosis.status_code == 200
    assert allergy.status_code == 200
    assert medication.status_code == 200
    assert len(db.encounters[0].diagnoses) == 1
    assert len(db.patients[0].allergies) == 1
    assert len(db.patients[0].medications) == 1
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[0]["workflow"] == "existing.operation"
    assert [entry["workflow"] for entry in entries[-3:]] == [
        "encounter.diagnosis_add",
        "patient.allergy_add",
        "patient.medication_add",
    ]


def test_external_partner_encounter_mutation_is_rejected() -> None:
    db = _ClinicalEncounterDb(permissions=["partner.portal"], encounters=[_encounter(status="in_progress")])
    _override_dependencies(db, _external_user())
    try:
        response = TestClient(app).post("/api/clinical/encounters/preview", json=_create_payload())
        note_response = TestClient(app).post(
            "/api/clinical/encounters/1/notes/preview",
            json={
                "title": "Clinical encounter note",
                "content": "Subjective: stable\nObjective: reviewed\nAssessment: eligible\nPlan: proceed",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 403
    assert note_response.status_code == 403
