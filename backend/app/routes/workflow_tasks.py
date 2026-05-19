from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import User, WorkflowTask
from app.schemas import WorkflowTaskCreate, WorkflowTaskRead, WorkflowTaskUpdate
from app.services.audit import log_audit, serialize_model

router = APIRouter(prefix="/api/workflow-tasks", tags=["Workflow Task Engine"])

TASK_FIELDS = [
    "task_type",
    "title",
    "assigned_to_user_id",
    "assigned_role_id",
    "priority",
    "status",
    "workflow_state",
    "queue_name",
    "due_date",
    "related_record_id",
    "related_record_type",
    "escalation_level",
]


@router.get("", response_model=list[WorkflowTaskRead])
def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    assigned_to_user_id: int | None = None,
    limit: int = Query(default=150, le=500),
    _: User = Depends(require_permission("tasks.read")),
    db: Session = Depends(get_db),
) -> list[WorkflowTask]:
    query = select(WorkflowTask)
    if status_filter:
        query = query.where(WorkflowTask.status == status_filter)
    if assigned_to_user_id:
        query = query.where(WorkflowTask.assigned_to_user_id == assigned_to_user_id)
    return list(db.execute(query.order_by(desc(WorkflowTask.created_at)).limit(limit)).scalars().all())


@router.post("", response_model=WorkflowTaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: WorkflowTaskCreate,
    current_user: User = Depends(require_permission("tasks.manage")),
    db: Session = Depends(get_db),
) -> WorkflowTask:
    task = WorkflowTask(**payload.model_dump())
    db.add(task)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="CREATE_WORKFLOW_TASK",
        table_name="fact_workflow_task",
        record_id=str(task.task_id),
        old_value=None,
        new_value=serialize_model(task, TASK_FIELDS),
    )
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=WorkflowTaskRead)
def update_task(
    task_id: int,
    payload: WorkflowTaskUpdate,
    current_user: User = Depends(require_permission("tasks.update")),
    db: Session = Depends(get_db),
) -> WorkflowTask:
    task = db.get(WorkflowTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    old_value = serialize_model(task, TASK_FIELDS)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(task, field, value)
    if updates.get("status") == "Completed" and not task.completed_at:
        task.completed_at = datetime.now(UTC)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_WORKFLOW_TASK",
        table_name="fact_workflow_task",
        record_id=str(task.task_id),
        old_value=old_value,
        new_value=serialize_model(task, TASK_FIELDS),
    )
    db.commit()
    db.refresh(task)
    return task
