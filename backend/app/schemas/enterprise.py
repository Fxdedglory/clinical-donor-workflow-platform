from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: int
    role_name: str
    description: str


class UserCreate(BaseModel):
    username: str
    full_name: str
    email: str
    password: str
    role_id: int
    department: str = "Clinical Operations"
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    password: str | None = None
    role_id: int | None = None
    department: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str | None
    full_name: str
    email: str
    role_id: int | None
    role: str
    department: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime


class WorkflowTaskCreate(BaseModel):
    task_type: str
    title: str
    description: str = ""
    assigned_to_user_id: int | None = None
    assigned_role_id: int | None = None
    priority: str = "Routine"
    status: str = "Assigned"
    due_date: datetime | None = None
    related_record_id: str
    related_record_type: str
    escalation_level: int = 0


class WorkflowTaskUpdate(BaseModel):
    assigned_to_user_id: int | None = None
    assigned_role_id: int | None = None
    priority: str | None = None
    status: str | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    escalation_level: int | None = None


class WorkflowTaskRead(WorkflowTaskCreate):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    created_at: datetime
    completed_at: datetime | None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    priority: str
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    notification_type: str
    priority: str = "Normal"


class EscalationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    escalation_id: int
    related_task_id: int
    escalation_type: str
    trigger_reason: str
    created_at: datetime
    resolved_at: datetime | None
    status: str


class TrainingAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    sop_id: int
    assigned_to_user_id: int | None
    assigned_role_id: int | None
    assigned_date: datetime
    due_date: datetime
    acknowledgment_status: str


class TrainingAssignmentCreate(BaseModel):
    sop_id: int
    assigned_to_user_id: int | None = None
    assigned_role_id: int | None = None
    due_date: datetime
    acknowledgment_status: str = "Assigned"


class TrainingCompletionCreate(BaseModel):
    assignment_id: int
    completed_by_user_id: int
    attestation_text: str = "I acknowledge this SOP revision and related workflow responsibilities."


class RoleResponsibilityRead(BaseModel):
    role_name: str
    job_description: str
    responsibilities: list[str]
    assigned_workflows: list[str]
    operational_kpis: list[str]

