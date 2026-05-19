from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import SOPTrainingAssignment, TrainingCompletion, User
from app.schemas import TrainingAssignmentCreate, TrainingAssignmentRead, TrainingCompletionCreate
from app.services.audit import log_audit

router = APIRouter(prefix="/api/training", tags=["SOP Training"])


@router.get("/assignments", response_model=list[TrainingAssignmentRead])
def list_assignments(
    _: User = Depends(require_permission("training.manage")),
    db: Session = Depends(get_db),
) -> list[SOPTrainingAssignment]:
    return list(
        db.execute(
            select(SOPTrainingAssignment).order_by(desc(SOPTrainingAssignment.assigned_date))
        ).scalars().all()
    )


@router.post("/assignments", response_model=TrainingAssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: TrainingAssignmentCreate,
    current_user: User = Depends(require_permission("training.manage")),
    db: Session = Depends(get_db),
) -> SOPTrainingAssignment:
    assignment = SOPTrainingAssignment(**payload.model_dump())
    db.add(assignment)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="ASSIGN_SOP_TRAINING",
        table_name="fact_sop_training_assignment",
        record_id=str(assignment.assignment_id),
        old_value=None,
        new_value=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/complete")
def complete_training(
    payload: TrainingCompletionCreate,
    current_user: User = Depends(require_permission("training.manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    assignment = db.get(SOPTrainingAssignment, payload.assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training assignment not found")
    completion = TrainingCompletion(
        assignment_id=payload.assignment_id,
        completed_by_user_id=payload.completed_by_user_id,
        completion_date=datetime.now(UTC),
        acknowledgment_status="Acknowledged",
        attestation_text=payload.attestation_text,
    )
    assignment.acknowledgment_status = "Completed"
    db.add(completion)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="COMPLETE_SOP_TRAINING",
        table_name="fact_training_completion",
        record_id=str(completion.completion_id),
        old_value=None,
        new_value={"assignment_id": completion.assignment_id, "status": completion.acknowledgment_status},
    )
    db.commit()
    return {"status": "completed"}

