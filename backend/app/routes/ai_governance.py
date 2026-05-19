from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_permission
from app.database import get_db
from app.models import (
    AIDecision,
    AIModelVersion,
    AIOverrideEvent,
    AIRiskRule,
    User,
    WorkflowTimelineEvent,
)
from app.schemas import (
    AIDecisionRead,
    AIModelVersionRead,
    AIOverrideEventRead,
    AIRiskRuleCreate,
    AIRiskRuleRead,
    AIRiskRuleUpdate,
    RuleSimulationRequest,
    WorkflowTimelineEventRead,
)
from app.services.ai_governance import (
    decision_trace,
    governance_analytics,
    governance_kpis,
    simulate_rule_change,
)
from app.services.audit import log_audit, serialize_model

router = APIRouter(prefix="/api/ai-governance", tags=["AI Governance"])

RULE_FIELDS = [
    "rule_name",
    "risk_category",
    "condition_type",
    "condition_operator",
    "condition_value",
    "risk_score_delta",
    "severity",
    "auto_escalate",
    "is_active",
]


@router.get("/dashboard")
def dashboard(
    _: User = Depends(require_permission("ai_governance.review")),
    db: Session = Depends(get_db),
) -> dict:
    return {"kpis": governance_kpis(db), "analytics": governance_analytics(db)}


@router.get("/rules", response_model=list[AIRiskRuleRead])
def list_rules(
    _: User = Depends(require_permission("ai_governance.review")),
    db: Session = Depends(get_db),
) -> list[AIRiskRule]:
    return list(db.execute(select(AIRiskRule).order_by(AIRiskRule.rule_id)).scalars().all())


@router.post("/rules", response_model=AIRiskRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: AIRiskRuleCreate,
    current_user: User = Depends(require_permission("risk_rules.manage")),
    db: Session = Depends(get_db),
) -> AIRiskRule:
    rule = AIRiskRule(
        **payload.model_dump(),
        created_by=current_user.user_id,
        approved_by=current_user.user_id,
    )
    db.add(rule)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="CREATE_AI_RISK_RULE",
        table_name="dim_ai_risk_rule",
        record_id=str(rule.rule_id),
        old_value=None,
        new_value=serialize_model(rule, RULE_FIELDS),
        entity_type="AIRiskRule",
        entity_id=str(rule.rule_id),
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=AIRiskRuleRead)
def update_rule(
    rule_id: int,
    payload: AIRiskRuleUpdate,
    current_user: User = Depends(require_permission("risk_rules.manage")),
    db: Session = Depends(get_db),
) -> AIRiskRule:
    rule = db.get(AIRiskRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI risk rule not found")
    old_value = serialize_model(rule, RULE_FIELDS)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.approved_by = current_user.user_id
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_AI_RISK_RULE",
        table_name="dim_ai_risk_rule",
        record_id=str(rule.rule_id),
        old_value=old_value,
        new_value=serialize_model(rule, RULE_FIELDS),
        entity_type="AIRiskRule",
        entity_id=str(rule.rule_id),
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/model-versions", response_model=list[AIModelVersionRead])
def list_model_versions(
    _: User = Depends(require_permission("ai_governance.review")),
    db: Session = Depends(get_db),
) -> list[AIModelVersion]:
    return list(
        db.execute(select(AIModelVersion).order_by(desc(AIModelVersion.deployment_date))).scalars().all()
    )


@router.get("/decisions", response_model=list[AIDecisionRead])
def list_decisions(
    limit: int = Query(default=100, le=500),
    _: User = Depends(require_permission("ai_governance.review")),
    db: Session = Depends(get_db),
) -> list[AIDecision]:
    return list(db.execute(select(AIDecision).order_by(desc(AIDecision.created_at)).limit(limit)).scalars().all())


@router.get("/decisions/{decision_id}/explainability")
def explainability(
    decision_id: int,
    _: User = Depends(require_permission("ai_governance.review")),
    db: Session = Depends(get_db),
) -> dict:
    trace = decision_trace(db, decision_id)
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI decision not found")
    return {
        "decision": AIDecisionRead.model_validate(trace["decision"]).model_dump(mode="json"),
        "timeline": [
            WorkflowTimelineEventRead.model_validate(item).model_dump(mode="json")
            for item in trace["timeline"]
        ],
        "explainability": trace["explainability"],
    }


@router.get("/overrides", response_model=list[AIOverrideEventRead])
def list_overrides(
    limit: int = Query(default=100, le=500),
    _: User = Depends(require_permission("ai_governance.review")),
    db: Session = Depends(get_db),
) -> list[AIOverrideEvent]:
    return list(
        db.execute(select(AIOverrideEvent).order_by(desc(AIOverrideEvent.timestamp)).limit(limit)).scalars().all()
    )


@router.post("/simulate-rule")
def simulate_rule(
    payload: RuleSimulationRequest,
    _: User = Depends(require_permission("risk_rules.manage")),
    db: Session = Depends(get_db),
) -> dict:
    return simulate_rule_change(db, **payload.model_dump())


@router.get("/timeline/{related_record_type}/{related_record_id}", response_model=list[WorkflowTimelineEventRead])
def timeline(
    related_record_type: str,
    related_record_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkflowTimelineEvent]:
    return list(
        db.execute(
            select(WorkflowTimelineEvent)
            .where(
                WorkflowTimelineEvent.related_record_type == related_record_type,
                WorkflowTimelineEvent.related_record_id == related_record_id,
            )
            .order_by(WorkflowTimelineEvent.created_at)
        ).scalars().all()
    )
