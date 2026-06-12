from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CARE_PLAN_STATUSES = Literal["draft", "active", "on_hold", "completed", "cancelled", "closed"]


class CarePlanWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class CarePlanBlockingIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None


class CarePlanCreatePreviewRequest(BaseModel):
    patient_id: str
    encounter_id: int | None = None
    screening_session_id: int | None = None
    order_id: int | None = None
    order_result_id: int | None = None
    title: str
    plan_type: str = "case_management"
    priority: str = "routine"
    reason: str = "Create care plan"
    start_date: date | None = None
    target_date: date | None = None
    team_member_name: str | None = None
    team_member_role: str | None = None

    @field_validator("patient_id", "title", "plan_type", "priority", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("team_member_name", "team_member_role")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CarePlanCreateRequest(CarePlanCreatePreviewRequest):
    preview_hash: str | None = None


class CarePlanGoalPreviewRequest(BaseModel):
    goal: str
    target_date: date | None = None
    status: str = "active"
    priority: str | None = None
    notes: str | None = None
    reason: str = "Add care plan goal"

    @field_validator("goal", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class CarePlanGoalCommitRequest(CarePlanGoalPreviewRequest):
    preview_hash: str | None = None


class CarePlanInterventionPreviewRequest(BaseModel):
    intervention: str
    intervention_type: str = "follow_up"
    owner: str | None = None
    due_date: date | None = None
    status: str = "planned"
    notes: str | None = None
    reason: str = "Add care plan intervention"

    @field_validator("intervention", "intervention_type", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class CarePlanInterventionCommitRequest(CarePlanInterventionPreviewRequest):
    preview_hash: str | None = None


class CarePlanTaskPreviewRequest(BaseModel):
    title: str
    description: str | None = None
    owner: str
    due_date: date
    priority: str = "routine"
    status: str = "open"
    notes: str | None = None
    reason: str = "Add care plan task"

    @field_validator("title", "owner", "priority", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class CarePlanTaskCommitRequest(CarePlanTaskPreviewRequest):
    preview_hash: str | None = None


class CarePlanProgressPreviewRequest(BaseModel):
    progress_note: str
    status_update: CARE_PLAN_STATUSES | None = None
    reason: str = "Add care plan progress update"

    @field_validator("progress_note", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class CarePlanProgressCommitRequest(CarePlanProgressPreviewRequest):
    preview_hash: str | None = None


class CarePlanClosePreviewRequest(BaseModel):
    outcome_summary: str
    closure_reason: str
    reason: str = "Close care plan"

    @field_validator("outcome_summary", "closure_reason", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class CarePlanCloseCommitRequest(CarePlanClosePreviewRequest):
    preview_hash: str | None = None


class CarePlanStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int
    care_plan_id: int
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    changed_by: int | None = None
    reason: str
    notes: str


class CarePlanGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    goal_id: int
    care_plan_id: int
    goal: str
    target_date: date | None = None
    status: str
    priority: str | None = None
    notes: str | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class CarePlanInterventionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intervention_id: int
    care_plan_id: int
    intervention: str
    intervention_type: str
    owner: str | None = None
    due_date: date | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class CarePlanTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    care_plan_id: int
    title: str
    description: str | None = None
    owner: str
    due_date: date
    priority: str
    status: str
    completed_at: datetime | None = None
    completed_by: int | None = None
    notes: str | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class CarePlanProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    progress_note_id: int
    care_plan_id: int
    progress_note: str
    status_update: str | None = None
    created_at: datetime
    created_by: int | None = None


class CarePlanTeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_member_id: int
    care_plan_id: int
    member_name: str
    role: str
    is_primary: bool
    created_at: datetime
    created_by: int | None = None


class CarePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    care_plan_id: int
    care_plan_number: str
    patient_pk: int
    patient_id: str
    patient_name: str = ""
    encounter_id: int | None = None
    encounter_number: str | None = None
    screening_session_id: int | None = None
    screening_session_number: str | None = None
    order_id: int | None = None
    order_number: str | None = None
    order_result_id: int | None = None
    order_result_summary: str | None = None
    result_flag: str
    has_critical_unacknowledged: bool
    title: str
    plan_type: str
    priority: str
    status: str
    reason: str
    start_date: date | None = None
    target_date: date | None = None
    closed_at: datetime | None = None
    closed_by: int | None = None
    closure_reason: str | None = None
    outcome_summary: str | None = None
    source: str
    version: int
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    goals: list[CarePlanGoalResponse] = Field(default_factory=list)
    interventions: list[CarePlanInterventionResponse] = Field(default_factory=list)
    tasks: list[CarePlanTaskResponse] = Field(default_factory=list)
    progress_notes: list[CarePlanProgressResponse] = Field(default_factory=list)
    team_members: list[CarePlanTeamMemberResponse] = Field(default_factory=list)
    status_history: list[CarePlanStatusHistoryResponse] = Field(default_factory=list)


class CarePlanListResponse(BaseModel):
    care_plans: list[CarePlanResponse]
    total: int


class CarePlanPreviewResponse(BaseModel):
    workflow: str
    entity_type: str
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    blocking_issues: list[CarePlanBlockingIssue] = Field(default_factory=list)
    warnings: list[CarePlanWarning] = Field(default_factory=list)
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class CarePlanCommitResponse(BaseModel):
    status: Literal["committed"] = "committed"
    operation_id: str
    audit_path: str
    care_plan: CarePlanResponse | None = None
    goal: CarePlanGoalResponse | None = None
    intervention: CarePlanInterventionResponse | None = None
    task: CarePlanTaskResponse | None = None
    progress_note: CarePlanProgressResponse | None = None
