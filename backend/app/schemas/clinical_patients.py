from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DuplicateRiskWarning(BaseModel):
    patient_id: str
    patient_pk: int
    display_name: str
    date_of_birth: date
    matched_fields: list[str] = Field(default_factory=list)
    message: str


class PatientContactRequest(BaseModel):
    contact_type: str = "emergency"
    full_name: str
    relationship: str | None = None
    phone: str | None = None
    email: str | None = None
    is_primary: bool = False
    status: str = "active"


class PatientContactResponse(PatientContactRequest):
    model_config = ConfigDict(from_attributes=True)

    contact_id: int
    patient_pk: int
    created_at: datetime
    updated_at: datetime


class PatientInsuranceRequest(BaseModel):
    payer_name: str
    member_id: str | None = None
    group_number: str | None = None
    plan_type: str | None = None
    priority: str = "primary"
    eligibility_status: str = "not_verified"
    status: str = "active"


class PatientInsuranceResponse(PatientInsuranceRequest):
    model_config = ConfigDict(from_attributes=True)

    insurance_id: int
    patient_pk: int
    created_at: datetime
    updated_at: datetime


class PatientConsentRequest(BaseModel):
    consent_type: str
    consent_status: str = "captured"
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    captured_by_name: str | None = None
    notes: str = ""


class PatientConsentResponse(PatientConsentRequest):
    model_config = ConfigDict(from_attributes=True)

    consent_id: int
    patient_pk: int
    created_at: datetime
    updated_at: datetime


class PatientDemographicsBase(BaseModel):
    donor_reference: str | None = None
    first_name: str
    middle_name: str | None = None
    last_name: str
    date_of_birth: date
    sex_at_birth: str
    gender_identity: str | None = None
    preferred_language: str | None = None
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    status: str = "active"

    @field_validator("first_name", "last_name", "sex_at_birth")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class PatientCreatePreviewRequest(PatientDemographicsBase):
    contacts: list[PatientContactRequest] = Field(default_factory=list)
    insurance: list[PatientInsuranceRequest] = Field(default_factory=list)
    consents: list[PatientConsentRequest] = Field(default_factory=list)


class PatientCreateRequest(PatientCreatePreviewRequest):
    preview_hash: str | None = None
    reason: str = "Create patient/donor profile"


class PatientUpdatePreviewRequest(BaseModel):
    donor_reference: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex_at_birth: str | None = None
    gender_identity: str | None = None
    preferred_language: str | None = None
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    status: str | None = None


class PatientUpdateRequest(PatientUpdatePreviewRequest):
    preview_hash: str | None = None
    reason: str = "Update demographics"


class PatientResponse(PatientDemographicsBase):
    model_config = ConfigDict(from_attributes=True)

    patient_pk: int
    patient_id: str
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    source: str
    version: int
    contacts: list[PatientContactResponse] = Field(default_factory=list)
    insurance_profiles: list[PatientInsuranceResponse] = Field(default_factory=list)
    consents: list[PatientConsentResponse] = Field(default_factory=list)


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int


class PatientPreviewResponse(BaseModel):
    workflow: str
    entity_type: str = "patient"
    entity_id: str
    preview_hash: str
    validation_status: str
    validation_issues: list[str] = Field(default_factory=list)
    duplicate_warnings: list[DuplicateRiskWarning] = Field(default_factory=list)
    summary: str
    changes: dict[str, object] = Field(default_factory=dict)


class PatientCommitResponse(BaseModel):
    patient: PatientResponse
    operation_id: str
    audit_path: str
