from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ENCOUNTER_STATUSES = Literal["draft", "in_progress", "ready_for_signature", "signed", "amended", "cancelled"]
NOTE_STATUSES = Literal["draft", "ready_for_signature", "signed", "amended"]


class EncounterValidationIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None
    severity: Literal["info", "warning", "error"] = "error"


class EncounterCreatePreviewRequest(BaseModel):
    patient_id: str
    appointment_id: int | None = None
    screening_session_id: int | None = None
    encounter_type: str = "donor_screening"
    chief_complaint: str = ""
    started_at: datetime | None = None
    reason: str = "Create clinical encounter"

    @field_validator("patient_id", "encounter_type", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class EncounterCreateRequest(EncounterCreatePreviewRequest):
    preview_hash: str | None = None


class EncounterStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int
    encounter_id: int
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    changed_by: int | None = None
    reason: str
    notes: str


class NoteTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: int
    template_key: str
    name: str
    note_type: str
    body: str
    status: str
    version: int


class EncounterNotePreviewRequest(BaseModel):
    note_id: int | None = None
    template_id: int | None = None
    note_type: str = "clinical_note"
    title: str = "Clinical encounter note"
    content: str
    reason: str = "Save draft encounter note"

    @field_validator("note_type", "title", "content", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class EncounterNoteCommitRequest(EncounterNotePreviewRequest):
    preview_hash: str | None = None


class EncounterNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    note_id: int
    encounter_id: int
    template_id: int | None = None
    template_name: str | None = None
    note_type: str
    title: str
    content: str
    status: str
    version: int
    is_addendum: bool
    amended_from_note_id: int | None = None
    amendment_reason: str
    signed_at: datetime | None = None
    signed_by: int | None = None
    locked: bool
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class EncounterSignPreviewRequest(BaseModel):
    note_id: int | None = None
    attestation: str = "I attest this encounter note is accurate and complete."
    reason: str = "Sign encounter note"

    @field_validator("attestation", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class EncounterSignCommitRequest(EncounterSignPreviewRequest):
    preview_hash: str | None = None


class EncounterAmendPreviewRequest(BaseModel):
    note_id: int | None = None
    amendment_text: str
    title: str = "Encounter note addendum"
    reason: str

    @field_validator("amendment_text", "title", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class EncounterAmendCommitRequest(EncounterAmendPreviewRequest):
    preview_hash: str | None = None


class EncounterDiagnosisRequest(BaseModel):
    code: str
    display: str
    diagnosis_type: str = "problem"
    status: str = "active"
    onset_date: date | None = None
    notes: str = ""
    reason: str = "Add encounter diagnosis/problem"
    preview_hash: str | None = None

    @field_validator("code", "display", "diagnosis_type", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class EncounterDiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    diagnosis_id: int
    encounter_id: int
    code: str
    display: str
    diagnosis_type: str
    status: str
    onset_date: date | None = None
    notes: str
    created_at: datetime
    created_by: int | None = None


class PatientAllergyRequest(BaseModel):
    allergen: str
    reaction: str = ""
    severity: str = "unknown"
    status: str = "active"
    onset_date: date | None = None
    notes: str = ""
    reason: str = "Add patient allergy"
    preview_hash: str | None = None

    @field_validator("allergen", "severity", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class PatientAllergyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    allergy_id: int
    patient_pk: int
    patient_id: str
    allergen: str
    reaction: str
    severity: str
    status: str
    onset_date: date | None = None
    notes: str
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class PatientMedicationRequest(BaseModel):
    medication_name: str
    dose: str = ""
    route: str = ""
    frequency: str = ""
    status: str = "active"
    start_date: date | None = None
    end_date: date | None = None
    indication: str = ""
    notes: str = ""
    reason: str = "Add patient medication"
    preview_hash: str | None = None

    @field_validator("medication_name", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class PatientMedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medication_id: int
    patient_pk: int
    patient_id: str
    medication_name: str
    dose: str
    route: str
    frequency: str
    status: str
    start_date: date | None = None
    end_date: date | None = None
    indication: str
    notes: str
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class EncounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    encounter_id: int
    encounter_number: str
    patient_pk: int
    patient_id: str
    patient_name: str = ""
    appointment_id: int | None = None
    appointment_number: str | None = None
    screening_session_id: int | None = None
    screening_session_number: str | None = None
    encounter_type: str
    status: str
    chief_complaint: str
    reason: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    signed_at: datetime | None = None
    signed_by: int | None = None
    source: str
    version: int
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    notes: list[EncounterNoteResponse] = Field(default_factory=list)
    diagnoses: list[EncounterDiagnosisResponse] = Field(default_factory=list)
    allergies: list[PatientAllergyResponse] = Field(default_factory=list)
    medications: list[PatientMedicationResponse] = Field(default_factory=list)
    status_history: list[EncounterStatusHistoryResponse] = Field(default_factory=list)


class EncounterListResponse(BaseModel):
    encounters: list[EncounterResponse]
    total: int


class EncounterPreviewResponse(BaseModel):
    workflow: str
    entity_type: str
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    blocking_issues: list[EncounterValidationIssue] = Field(default_factory=list)
    warnings: list[EncounterValidationIssue] = Field(default_factory=list)
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class EncounterCommitResponse(BaseModel):
    status: Literal["committed"] = "committed"
    operation_id: str
    audit_path: str
    encounter: EncounterResponse | None = None
    note: EncounterNoteResponse | None = None
    diagnosis: EncounterDiagnosisResponse | None = None
    allergy: PatientAllergyResponse | None = None
    medication: PatientMedicationResponse | None = None
