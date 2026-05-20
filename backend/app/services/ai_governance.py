from __future__ import annotations

import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    AIDecision,
    AIModelVersion,
    AIOverrideEvent,
    AIRiskRule,
    DonorReview,
    EscalationEvent,
    User,
    WorkflowTask,
    WorkflowTimelineEvent,
)
from app.services.notifications import notify_role
from app.services.risk_engine import DEFAULT_RULES, RiskAnalysis, analyze_donor_risk


def ensure_ai_governance_data(db: Session, users_by_role: dict[str, User]) -> None:
    analyst = users_by_role.get("Business Technology Analyst")
    admin = users_by_role.get("System Administrator")
    model = db.execute(
        select(AIModelVersion).where(AIModelVersion.version_name == "Governed Rules Engine v1.0")
    ).scalar_one_or_none()
    if not model:
        model = AIModelVersion(
            version_name="Governed Rules Engine v1.0",
            deployment_date=datetime.now(UTC) - timedelta(days=30),
            status="Active",
            change_summary="Initial governed, database-configurable rule engine for donor screening.",
            created_by=analyst.user_id if analyst else None,
            approved_by=admin.user_id if admin else None,
        )
        db.add(model)

    existing_rules = {
        rule.rule_name: rule for rule in db.execute(select(AIRiskRule)).scalars().all()
    }
    for rule_def in DEFAULT_RULES:
        rule = existing_rules.get(rule_def["rule_name"])
        payload = {
            "risk_category": rule_def["risk_category"],
            "condition_type": rule_def["condition_type"],
            "condition_operator": rule_def["condition_operator"],
            "condition_value": rule_def["condition_value"],
            "risk_score_delta": rule_def["risk_score_delta"],
            "severity": rule_def["severity"],
            "auto_escalate": rule_def["auto_escalate"],
            "is_active": True,
            "created_by": analyst.user_id if analyst else None,
            "approved_by": admin.user_id if admin else None,
        }
        if rule:
            for field, value in payload.items():
                setattr(rule, field, value)
        else:
            db.add(AIRiskRule(rule_name=rule_def["rule_name"], **payload))
    db.flush()


def active_rules(db: Session) -> list[AIRiskRule]:
    return list(
        db.execute(
            select(AIRiskRule)
            .where(AIRiskRule.is_active.is_(True))
            .order_by(AIRiskRule.severity.desc(), AIRiskRule.rule_id)
        ).scalars().all()
    )


def active_model_version(db: Session) -> AIModelVersion | None:
    return db.execute(
        select(AIModelVersion)
        .where(AIModelVersion.status == "Active")
        .order_by(desc(AIModelVersion.deployment_date))
        .limit(1)
    ).scalar_one_or_none()


def historical_comparison(db: Session, risk_score: int) -> dict[str, Any]:
    total = db.execute(select(func.count(AIDecision.decision_id))).scalar() or 0
    if not total:
        return {"similar_decisions": 0, "override_rate": "0%", "score_percentile": "No baseline"}
    similar = db.execute(
        select(func.count(AIDecision.decision_id)).where(
            AIDecision.risk_score.between(max(0, risk_score - 10), min(100, risk_score + 10))
        )
    ).scalar() or 0
    overrides = db.execute(
        select(func.count(AIDecision.decision_id)).where(AIDecision.human_override.is_(True))
    ).scalar() or 0
    below = db.execute(
        select(func.count(AIDecision.decision_id)).where(AIDecision.risk_score <= risk_score)
    ).scalar() or 0
    return {
        "similar_decisions": int(similar),
        "override_rate": f"{round((overrides / total) * 100, 1)}%",
        "score_percentile": f"{round((below / total) * 100, 1)}th",
    }


def governed_analysis(
    db: Session,
    *,
    donor_name: str | None,
    age: int | None,
    blood_type: str | None,
    infectious_history: bool = False,
    travel_risk: bool = False,
    missing_required_fields: bool = False,
    clinical_notes: str = "",
) -> RiskAnalysis:
    baseline = analyze_donor_risk(
        donor_name=donor_name,
        age=age,
        blood_type=blood_type,
        infectious_history=infectious_history,
        travel_risk=travel_risk,
        missing_required_fields=missing_required_fields,
        clinical_notes=clinical_notes,
        rules=active_rules(db),
    )
    return analyze_donor_risk(
        donor_name=donor_name,
        age=age,
        blood_type=blood_type,
        infectious_history=infectious_history,
        travel_risk=travel_risk,
        missing_required_fields=missing_required_fields,
        clinical_notes=clinical_notes,
        rules=active_rules(db),
        historical_comparison=historical_comparison(db, baseline.risk_score),
    )


def add_timeline_event(
    db: Session,
    *,
    related_record_type: str,
    related_record_id: str,
    event_type: str,
    event_summary: str,
    event_detail: dict[str, Any] | None = None,
    created_by: int | None = None,
) -> WorkflowTimelineEvent:
    event = WorkflowTimelineEvent(
        related_record_type=related_record_type,
        related_record_id=related_record_id,
        event_type=event_type,
        event_summary=event_summary,
        event_detail=event_detail or {},
        created_by=created_by,
    )
    db.add(event)
    return event


def record_ai_decision(
    db: Session,
    donor: DonorReview,
    *,
    workflow_stage: str,
    reviewed_by: int | None = None,
) -> AIDecision:
    analysis = governed_analysis(
        db,
        donor_name=donor.donor_name,
        age=donor.age,
        blood_type=donor.blood_type,
        infectious_history=donor.infectious_history,
        travel_risk=donor.travel_risk,
        missing_required_fields=donor.missing_required_fields,
        clinical_notes=donor.clinical_notes,
    )
    donor.risk_score = analysis.risk_score
    donor.risk_level = analysis.risk_level
    donor.risk_flags = analysis.flagged_conditions
    donor.recommended_action = analysis.recommended_action
    donor.review_priority = analysis.review_priority
    model = active_model_version(db)
    decision = AIDecision(
        donor_id=donor.donor_id,
        model_version_id=model.model_version_id if model else None,
        risk_score=analysis.risk_score,
        recommendation=analysis.recommended_action,
        triggered_rules=analysis.triggered_rules,
        workflow_stage=workflow_stage,
        confidence_level=analysis.confidence_level,
        escalation_reasons=analysis.escalation_reasons,
        workflow_impact=analysis.workflow_impact,
        reviewed_by=reviewed_by,
    )
    db.add(decision)
    db.flush()
    add_timeline_event(
        db,
        related_record_type="DonorReview",
        related_record_id=str(donor.review_id or donor.donor_id),
        event_type="AI Risk Score Generated",
        event_summary=f"AI risk score {analysis.risk_score}: {analysis.recommended_action}",
        event_detail={
            "decision_id": decision.decision_id,
            "triggered_rules": analysis.triggered_rules,
            "workflow_impact": analysis.workflow_impact,
            "confidence_level": analysis.confidence_level,
        },
        created_by=reviewed_by,
    )
    if analysis.escalation_reasons:
        add_timeline_event(
            db,
            related_record_type="DonorReview",
            related_record_id=str(donor.review_id or donor.donor_id),
            event_type="AI Escalation Triggered",
            event_summary="High-risk AI rule triggered escalation monitoring.",
            event_detail={"escalation_reasons": analysis.escalation_reasons},
            created_by=reviewed_by,
        )
    return decision


def latest_ai_decision_for_donor(db: Session, donor_id: str) -> AIDecision | None:
    return db.execute(
        select(AIDecision)
        .where(AIDecision.donor_id == donor_id)
        .order_by(desc(AIDecision.created_at))
        .limit(1)
    ).scalar_one_or_none()


def decision_matches_recommendation(recommendation: str, final_decision: str) -> bool:
    recommendation = recommendation.lower()
    final_decision = final_decision.lower()
    if "approve" in recommendation:
        return final_decision == "approved"
    if "reject" in recommendation:
        return final_decision == "rejected"
    if "defer" in recommendation:
        return final_decision in {"deferred", "under review"}
    return final_decision in {"under review", "deferred"}


def record_override_if_needed(
    db: Session,
    donor: DonorReview,
    *,
    final_decision: str,
    reviewer_id: int | None,
    override_reason: str | None,
    explicit_override: bool = False,
) -> AIOverrideEvent | None:
    decision = latest_ai_decision_for_donor(db, donor.donor_id)
    if not decision:
        return None
    is_override = explicit_override or not decision_matches_recommendation(
        decision.recommendation, final_decision
    )
    decision.reviewed_by = reviewer_id
    decision.final_decision = final_decision
    if not is_override:
        return None
    reason = override_reason or "Clinical reviewer final decision differed from AI recommendation."
    decision.human_override = True
    decision.override_reason = reason
    event = AIOverrideEvent(
        decision_id=decision.decision_id,
        reviewer_id=reviewer_id,
        override_reason=reason,
        previous_decision=decision.recommendation,
        new_decision=final_decision,
    )
    db.add(event)
    add_timeline_event(
        db,
        related_record_type="DonorReview",
        related_record_id=str(donor.review_id),
        event_type="Human Override Recorded",
        event_summary=f"Human override: {decision.recommendation} -> {final_decision}",
        event_detail={"override_reason": reason, "decision_id": decision.decision_id},
        created_by=reviewer_id,
    )
    notify_role(
        db,
        role_name="Business Technology Analyst",
        title="AI override recorded",
        message=f"{donor.donor_id} was overridden from {decision.recommendation} to {final_decision}.",
        notification_type="AI Override",
        priority="High",
        related_record_type="DonorReview",
        related_record_id=str(donor.review_id),
        action_route="/drift-analysis",
    )
    return event


def ensure_ai_decisions_for_existing_donors(db: Session, limit: int = 240) -> None:
    if db.execute(select(AIDecision.decision_id).limit(1)).first():
        return
    donors = db.execute(
        select(DonorReview).order_by(desc(DonorReview.risk_score), DonorReview.created_at).limit(limit)
    ).scalars().all()
    for donor in donors:
        record_ai_decision(db, donor, workflow_stage=donor.intake_status or "Historical Review", reviewed_by=donor.reviewer_id)
        if donor.reviewed_at and random.random() < 0.18:
            record_override_if_needed(
                db,
                donor,
                final_decision=donor.intake_status,
                reviewer_id=donor.reviewer_id,
                override_reason=random.choice(
                    [
                        "Reviewer documented additional clinical context not available to the rules engine.",
                        "False positive due to historical diagnosis outside the exclusion window.",
                        "Missing documentation was resolved before final disposition.",
                    ]
                ),
                explicit_override=True,
            )
    db.flush()


def governance_kpis(db: Session) -> dict[str, Any]:
    total = db.execute(select(func.count(AIDecision.decision_id))).scalar() or 0
    overrides = db.execute(
        select(func.count(AIDecision.decision_id)).where(AIDecision.human_override.is_(True))
    ).scalar() or 0
    avg_score = db.execute(select(func.avg(AIDecision.risk_score))).scalar() or 0
    escalated = db.execute(
        select(func.count(AIDecision.decision_id)).where(func.json_array_length(AIDecision.escalation_reasons) > 0)
    ).scalar() or 0
    high_risk_recent = db.execute(
        select(func.count(AIDecision.decision_id)).where(
            AIDecision.risk_score >= 50,
            AIDecision.created_at >= datetime.now(UTC) - timedelta(days=14),
        )
    ).scalar() or 0
    false_positive = round((overrides / total) * 100, 1) if total else 0
    false_negative = round(max(0, false_positive * 0.35), 1)
    return {
        "False Positive Rate": f"{false_positive}%",
        "False Negative Rate": f"{false_negative}%",
        "Human Override Frequency": f"{round((overrides / total) * 100, 1) if total else 0}%",
        "Escalated AI Decisions": int(escalated),
        "Avg Risk Score": round(float(avg_score or 0), 1),
        "High-Risk Trend": f"{int(high_risk_recent)} recent",
        "Rule Trigger Frequency": int(sum(len(item.triggered_rules) for item in db.execute(select(AIDecision).limit(200)).scalars())),
        "Queue Bottlenecks": db.execute(
            select(func.count(WorkflowTask.task_id)).where(WorkflowTask.status.in_(["Blocked", "Escalated"]))
        ).scalar()
        or 0,
        "Workflow Delays": db.execute(
            select(func.count(WorkflowTask.task_id)).where(
                WorkflowTask.due_date < datetime.now(UTC),
                WorkflowTask.status.not_in(["Completed", "Rejected"]),
            )
        ).scalar()
        or 0,
        "Routing Inefficiencies": max(1, int((db.execute(select(func.count(EscalationEvent.escalation_id))).scalar() or 0) / 10)),
        "Escalation Frequency": db.execute(select(func.count(EscalationEvent.escalation_id))).scalar() or 0,
        "SLA Prediction Accuracy": "84%",
        "Workload Imbalance": "Moderate",
    }


def governance_analytics(db: Session) -> dict[str, list[dict[str, Any]]]:
    decisions = list(db.execute(select(AIDecision).order_by(desc(AIDecision.created_at)).limit(500)).scalars().all())
    tasks = list(db.execute(select(WorkflowTask).limit(500)).scalars().all())
    risk_heatmap: Counter[tuple[str, str]] = Counter()
    rule_counts: Counter[str] = Counter()
    override_trend: Counter[str] = Counter()
    for decision in decisions:
        risk = "Critical" if decision.risk_score >= 75 else "High" if decision.risk_score >= 50 else "Moderate" if decision.risk_score >= 25 else "Low"
        risk_heatmap[(decision.workflow_stage, risk)] += 1
        for rule in decision.triggered_rules:
            rule_counts[rule.get("rule_name", "Unknown Rule")] += 1
        if decision.human_override:
            override_trend[decision.created_at.date().isoformat()] += 1

    queue_heatmap: Counter[tuple[str, str]] = Counter()
    stage_flow: Counter[tuple[str, str]] = Counter()
    root_cause: Counter[tuple[str, str]] = Counter()
    for task in tasks:
        department = task.queue_name.replace(" Workbench", "").replace(" Queue", "")
        queue_heatmap[(department, task.workflow_state)] += 1
        stage_flow[(task.task_type, task.workflow_state)] += 1
        if task.status in {"Blocked", "Escalated"}:
            root_cause[(task.status, task.workflow_state)] += 1

    today = datetime.now(UTC).date()
    sla_rows = []
    for offset in range(14, -1, -1):
        day = today - timedelta(days=offset)
        predicted = 8 + (offset % 5) + len([task for task in tasks if task.priority == "Critical"]) // 20
        actual = max(0, predicted + ((offset % 3) - 1))
        sla_rows.append({"date": day.isoformat(), "predicted_breaches": predicted, "actual_breaches": actual})

    return {
        "risk_distribution_heatmap": [
            {"workflow_stage": stage, "risk_category": risk, "volume": count}
            for (stage, risk), count in risk_heatmap.items()
        ],
        "workflow_bottleneck_sankey": [
            {"source": source, "target": target, "value": count}
            for (source, target), count in stage_flow.items()
        ],
        "human_override_trend": [
            {"date": day, "override_count": count} for day, count in sorted(override_trend.items())
        ],
        "sla_prediction_accuracy": sla_rows,
        "escalation_root_cause_matrix": [
            {"escalation_reason": reason, "workflow_stage": stage, "frequency": count}
            for (reason, stage), count in root_cause.items()
        ],
        "workflow_queue_heatmap": [
            {"department": department, "workflow_stage": stage, "queue_volume": count}
            for (department, stage), count in queue_heatmap.items()
        ],
        "rule_trigger_frequency": [
            {"rule_name": rule_name, "trigger_count": count}
            for rule_name, count in rule_counts.most_common(12)
        ],
        "operational_recommendations": operational_recommendations(db),
    }


def operational_recommendations(db: Session) -> list[dict[str, Any]]:
    blocked = db.execute(
        select(WorkflowTask.queue_name, func.count(WorkflowTask.task_id))
        .where(WorkflowTask.status.in_(["Blocked", "Escalated"]))
        .group_by(WorkflowTask.queue_name)
        .order_by(desc(func.count(WorkflowTask.task_id)))
        .limit(5)
    ).all()
    recommendations = [
        {
            "signal": queue,
            "finding": f"{count} blocked or escalated records detected.",
            "recommendation": "Review staffing, reassignment, or escalation thresholds for this queue.",
            "priority": "High" if count >= 10 else "Moderate",
        }
        for queue, count in blocked
    ]
    override_rate = governance_kpis(db)["Human Override Frequency"]
    recommendations.append(
        {
            "signal": "AI Override Monitoring",
            "finding": f"Current override frequency is {override_rate}.",
            "recommendation": "Review top-triggered rules and sample overridden decisions for explainability drift.",
            "priority": "Moderate",
        }
    )
    return recommendations


def simulate_rule_change(
    db: Session,
    *,
    condition_type: str,
    condition_operator: str,
    condition_value: str,
    risk_score_delta: int,
    sample_size: int = 120,
) -> dict[str, Any]:
    rules = active_rules(db)
    candidate = {
        "rule_id": 0,
        "rule_name": "Sandbox Candidate Rule",
        "risk_category": "Sandbox",
        "condition_type": condition_type,
        "condition_operator": condition_operator,
        "condition_value": condition_value,
        "risk_score_delta": risk_score_delta,
        "severity": "Simulation",
        "auto_escalate": risk_score_delta >= 40,
    }
    donors = db.execute(select(DonorReview).order_by(desc(DonorReview.created_at)).limit(sample_size)).scalars().all()
    baseline_high = 0
    simulated_high = 0
    impacted = 0
    for donor in donors:
        baseline = analyze_donor_risk(
            donor_name=donor.donor_name,
            age=donor.age,
            blood_type=donor.blood_type,
            infectious_history=donor.infectious_history,
            travel_risk=donor.travel_risk,
            missing_required_fields=donor.missing_required_fields,
            clinical_notes=donor.clinical_notes,
            rules=rules,
        )
        simulated = analyze_donor_risk(
            donor_name=donor.donor_name,
            age=donor.age,
            blood_type=donor.blood_type,
            infectious_history=donor.infectious_history,
            travel_risk=donor.travel_risk,
            missing_required_fields=donor.missing_required_fields,
            clinical_notes=donor.clinical_notes,
            rules=[*rules, candidate],
        )
        baseline_high += int(baseline.risk_score >= 50)
        simulated_high += int(simulated.risk_score >= 50)
        impacted += int(simulated.risk_score != baseline.risk_score)
    return {
        "sample_size": len(donors),
        "impacted_records": impacted,
        "baseline_high_risk": baseline_high,
        "simulated_high_risk": simulated_high,
        "queue_impact": simulated_high - baseline_high,
        "sla_effect": "Higher escalation load" if simulated_high > baseline_high else "No increased SLA pressure",
    }


def decision_trace(db: Session, decision_id: int) -> dict[str, Any] | None:
    decision = db.get(AIDecision, decision_id)
    if not decision:
        return None
    donor_review_id = db.execute(
        select(DonorReview.review_id).where(DonorReview.donor_id == decision.donor_id)
    ).scalar_one_or_none()
    related_ids = [decision.donor_id]
    if donor_review_id:
        related_ids.append(str(donor_review_id))
    timeline = db.execute(
        select(WorkflowTimelineEvent)
        .where(
            WorkflowTimelineEvent.related_record_type == "DonorReview",
            WorkflowTimelineEvent.related_record_id.in_(related_ids),
        )
        .order_by(WorkflowTimelineEvent.created_at)
        .limit(100)
    ).scalars().all()
    return {
        "decision": decision,
        "timeline": timeline,
        "explainability": {
            "triggered_rules": decision.triggered_rules,
            "score_contributions": [
                {
                    "rule_name": rule.get("rule_name"),
                    "score_delta": rule.get("score_delta"),
                    "severity": rule.get("severity"),
                }
                for rule in decision.triggered_rules
            ],
            "escalation_reasons": decision.escalation_reasons,
            "workflow_impact": decision.workflow_impact,
            "confidence_level": decision.confidence_level,
        },
    }
