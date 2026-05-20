from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    CAPA,
    Deviation,
    Donor,
    DonorScreening,
    EligibilityDecision,
    EligibilityRule,
    InfectiousDiseaseResult,
    InfectiousDiseaseTest,
    MedicalSocialHistory,
    ProcessingRelease,
    RecoverySuitability,
    TissueType,
)

DONOR_ELIGIBILITY_STATES = [
    "Referral Received",
    "Intake In Progress",
    "Pending Administrative Screen",
    "Pending Medical Social History Review",
    "Pending Infectious Disease Review",
    "Pending Tissue Suitability Review",
    "Pending Recovery Suitability Review",
    "Pending Medical Director Review",
    "Pending QA Review",
    "Recovery Authorized",
    "Processing Hold",
    "Pending Processing Release",
    "Released for Clinical Use",
    "Released for Research Use",
    "Quarantine",
    "Rejected",
    "Destroyed",
    "Closed",
]

FINAL_DISPOSITIONS = [
    "Clinical Transplant",
    "Tissue Processing",
    "Research Use",
    "Quarantine",
    "Destruction",
    "Rejected / Deferred",
]

SEVERITY_RANK = {"Low": 1, "Medium": 2, "Moderate": 2, "High": 3, "Critical": 4}
OUTCOME_RANK = {
    "Continue": 1,
    "Eligible": 1,
    "Recovery Approved": 1,
    "Release Approved": 1,
    "Conditional": 2,
    "Research Only": 2,
    "Hold": 3,
    "Recovery Hold": 3,
    "Release Hold": 3,
    "QA Review Required": 4,
    "Medical Director Review": 4,
    "Recovery Escalation": 4,
    "CAPA Required": 4,
    "Reject": 5,
    "Recovery Rejected": 5,
    "Reject / Destroy": 5,
}


@dataclass(frozen=True)
class RuleHit:
    rule_id: int
    rule_name: str
    rule_category: str
    condition: str
    outcome: str
    severity: str
    requires_review: bool
    required_role: str | None
    sop_reference: str


def _coerce(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _matches(actual: Any, operator: str, expected: str) -> bool:
    actual_value = _coerce(actual)
    expected_value = _coerce(expected)
    operator = operator.lower()
    if operator in {"=", "eq", "equals"}:
        return actual_value == expected_value
    if operator in {"!=", "ne", "not_equals"}:
        return actual_value != expected_value
    if operator in {"contains", "includes"}:
        return str(expected_value).lower() in str(actual_value).lower()
    if operator == "in":
        values = [item.strip().lower() for item in str(expected).split("|")]
        return str(actual_value).lower() in values
    if operator == "is_true":
        return bool(actual_value) is True
    if operator == "is_false":
        return bool(actual_value) is False

    actual_number = _to_float(actual_value)
    expected_number = _to_float(expected_value)
    if actual_number is None or expected_number is None:
        return False
    if operator in {">", "gt"}:
        return actual_number > expected_number
    if operator in {">=", "gte"}:
        return actual_number >= expected_number
    if operator in {"<", "lt"}:
        return actual_number < expected_number
    if operator in {"<=", "lte"}:
        return actual_number <= expected_number
    return False


def _latest_or_none(rows: list[Any]) -> Any | None:
    return rows[0] if rows else None


def donor_screening_context(db: Session, donor: Donor) -> dict[str, Any]:
    screening = db.execute(
        select(DonorScreening)
        .where(DonorScreening.donor_pk == donor.donor_pk)
        .order_by(desc(DonorScreening.created_at))
        .limit(1)
    ).scalar_one_or_none()
    history = db.execute(
        select(MedicalSocialHistory)
        .where(MedicalSocialHistory.donor_pk == donor.donor_pk)
        .order_by(desc(MedicalSocialHistory.created_at))
        .limit(1)
    ).scalar_one_or_none()
    infectious_rows = db.execute(
        select(InfectiousDiseaseResult, InfectiousDiseaseTest)
        .join(InfectiousDiseaseTest, InfectiousDiseaseResult.test_id == InfectiousDiseaseTest.test_id)
        .where(InfectiousDiseaseResult.donor_pk == donor.donor_pk)
    ).all()
    recoveries = list(
        db.execute(
            select(RecoverySuitability)
            .where(RecoverySuitability.donor_pk == donor.donor_pk)
            .order_by(desc(RecoverySuitability.reviewed_at))
        ).scalars().all()
    )
    releases = list(
        db.execute(
            select(ProcessingRelease)
            .where(ProcessingRelease.donor_pk == donor.donor_pk)
            .order_by(desc(ProcessingRelease.created_at))
        ).scalars().all()
    )
    deviations = list(
        db.execute(
            select(Deviation)
            .where(Deviation.donor_pk == donor.donor_pk)
            .order_by(desc(Deviation.opened_at))
        ).scalars().all()
    )
    capas = list(
        db.execute(
            select(CAPA)
            .where(CAPA.donor_pk == donor.donor_pk)
            .order_by(desc(CAPA.created_at))
        ).scalars().all()
    )

    infectious_by_pathogen: dict[str, str] = {}
    any_positive = False
    specimen_window_invalid = False
    for result, test in infectious_rows:
        key = f"{test.pathogen}_{test.test_method}".lower().replace(" ", "_").replace("/", "_")
        infectious_by_pathogen[key] = result.result_value
        any_positive = any_positive or result.result_value.lower() == "positive"
        specimen_window_invalid = specimen_window_invalid or not result.specimen_window_valid

    latest_recovery = _latest_or_none(recoveries)
    latest_release = _latest_or_none(releases)
    donor_history = donor.donor_history or {}

    context: dict[str, Any] = {
        "donor_pk": donor.donor_pk,
        "donor_identifier": donor.donor_identifier,
        "age": donor.age,
        "blood_type": donor.blood_type,
        "identity_verified": donor_history.get("identity_verified", False),
        "authorization_verified": donor_history.get("authorization_verified", False),
        "time_of_death_captured": donor.time_of_death is not None,
        "chain_of_custody_initiated": donor_history.get("chain_of_custody_initiated", False),
        "specimen_available": donor_history.get("specimen_available", False),
        "recovery_window_valid": donor_history.get("recovery_window_valid", False),
        "jurisdiction_cleared": donor_history.get("jurisdiction_cleared", False),
        "any_positive_infectious_disease": any_positive,
        "specimen_window_invalid": specimen_window_invalid,
        "open_deviation_count": sum(1 for item in deviations if item.status != "Closed"),
        "open_capa_count": sum(1 for item in capas if item.status != "Closed"),
    }
    context.update(infectious_by_pathogen)

    if screening:
        context.update(
            {
                "administrative_outcome": screening.administrative_outcome,
                "medical_social_outcome": screening.medical_social_outcome,
                "infectious_disease_outcome": screening.infectious_disease_outcome,
                "tissue_suitability_outcome": screening.tissue_suitability_outcome,
                "recovery_suitability_outcome": screening.recovery_suitability_outcome,
                "qa_outcome": screening.qa_outcome,
                "automated_rule_outcome": screening.automated_rule_outcome,
            }
        )
    if history:
        context.update(
            {
                "cancer_history": history.cancer_history,
                "neurological_disease": history.neurological_disease,
                "autoimmune_disease": history.autoimmune_disease,
                "transmissible_disease_history": history.transmissible_disease_history,
                "iv_drug_use": history.iv_drug_use,
                "incarceration_history": history.incarceration_history,
                "travel_exposure": history.travel_exposure,
                "high_risk_behavior": history.high_risk_behavior,
                "unknown_history": history.unknown_history,
            }
        )
    if latest_recovery:
        context.update(
            {
                "refrigeration_timing_hours": latest_recovery.refrigeration_timing_hours,
                "body_cooling_status": latest_recovery.body_cooling_status,
                "trauma_contamination": latest_recovery.trauma_contamination,
                "blood_draw_timing_hours": latest_recovery.blood_draw_timing_hours,
                "hospital_release_status": latest_recovery.hospital_release_status,
                "recovery_window_hours": latest_recovery.recovery_window_hours,
                "recovery_outcome": latest_recovery.outcome,
            }
        )
    if latest_release:
        context.update(
            {
                "sterility_testing": latest_release.sterility_testing,
                "bioburden_status": latest_release.bioburden_status,
                "environmental_monitoring": latest_release.environmental_monitoring,
                "packaging_qc": latest_release.packaging_qc,
                "labeling_verification": latest_release.labeling_verification,
                "traceability_verification": latest_release.traceability_verification,
                "chain_of_custody_verified": latest_release.chain_of_custody_verified,
                "release_status": latest_release.release_status,
            }
        )
    return context


def evaluate_donor_eligibility(
    db: Session,
    donor: Donor,
    *,
    category: str | None = None,
    user_id: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    context = donor_screening_context(db, donor)
    query = select(EligibilityRule).where(EligibilityRule.is_active.is_(True))
    if category:
        query = query.where(EligibilityRule.rule_category == category)
    rules = db.execute(query.order_by(EligibilityRule.rule_category, EligibilityRule.rule_name)).scalars().all()

    hits: list[RuleHit] = []
    for rule in rules:
        if _matches(context.get(rule.condition_field), rule.condition_operator, rule.condition_value):
            hits.append(
                RuleHit(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    rule_category=rule.rule_category,
                    condition=f"{rule.condition_field} {rule.condition_operator} {rule.condition_value}",
                    outcome=rule.outcome,
                    severity=rule.severity,
                    requires_review=rule.requires_review,
                    required_role=rule.required_role,
                    sop_reference=rule.sop_reference,
                )
            )

    if hits:
        highest = max(
            hits,
            key=lambda hit: (OUTCOME_RANK.get(hit.outcome, 1), SEVERITY_RANK.get(hit.severity, 1)),
        )
        outcome = highest.outcome
        severity = highest.severity
    else:
        outcome = "Continue"
        severity = "Low"

    requires_review = any(hit.requires_review for hit in hits)
    required_roles = sorted({hit.required_role for hit in hits if hit.required_role})
    final_disposition = _disposition_for_outcome(outcome, donor)

    hit_payload = [hit.__dict__ for hit in hits]
    if persist:
        decision = EligibilityDecision(
            donor_pk=donor.donor_pk,
            rule_id=highest.rule_id if hits else None,
            decision_stage=category or donor.current_workflow_state,
            outcome=outcome,
            severity=severity,
            reason=_decision_reason(hits, outcome),
            requires_review=requires_review,
            required_role=", ".join(required_roles) if required_roles else None,
            triggered_rules=hit_payload,
            final_disposition=final_disposition,
            created_by=user_id,
        )
        db.add(decision)
        donor.eligibility_status = outcome
        donor.final_disposition = final_disposition
        donor.current_workflow_state = _state_for_outcome(outcome, donor.current_workflow_state)
        screening = db.execute(
            select(DonorScreening).where(DonorScreening.donor_pk == donor.donor_pk).limit(1)
        ).scalar_one_or_none()
        if screening:
            _apply_screening_outcome(screening, category, outcome)
        db.flush()

    return {
        "donor_pk": donor.donor_pk,
        "donor_identifier": donor.donor_identifier,
        "workflow_state": donor.current_workflow_state,
        "outcome": outcome,
        "severity": severity,
        "requires_review": requires_review,
        "required_roles": required_roles,
        "final_disposition": final_disposition,
        "triggered_rules": hit_payload,
        "context": context,
    }


def _apply_screening_outcome(screening: DonorScreening, category: str | None, outcome: str) -> None:
    field_by_category = {
        "Administrative": "administrative_outcome",
        "Medical Social History": "medical_social_outcome",
        "Infectious Disease": "infectious_disease_outcome",
        "Tissue Specific": "tissue_suitability_outcome",
        "Recovery Suitability": "recovery_suitability_outcome",
        "Processing Release": "qa_outcome",
        "QMS Compliance": "qa_outcome",
    }
    if category and category in field_by_category:
        setattr(screening, field_by_category[category], outcome)
    screening.automated_rule_outcome = outcome
    screening.current_decision = outcome


def _decision_reason(hits: list[RuleHit], outcome: str) -> str:
    if not hits:
        return "No active eligibility rule produced an exclusion, hold, or escalation."
    names = ", ".join(hit.rule_name for hit in hits[:5])
    return f"{outcome} based on triggered eligibility rules: {names}."


def _state_for_outcome(outcome: str, current_state: str) -> str:
    if outcome in {"Reject", "Recovery Rejected"}:
        return "Rejected"
    if outcome == "Reject / Destroy":
        return "Destroyed"
    if outcome == "Medical Director Review":
        return "Pending Medical Director Review"
    if outcome in {"QA Review Required", "CAPA Required", "Release Hold"}:
        return "Pending QA Review"
    if outcome in {"Hold", "Recovery Hold"}:
        return "Processing Hold"
    if outcome == "Research Only":
        return "Released for Research Use"
    if outcome == "Release Approved":
        return "Released for Clinical Use"
    if outcome == "Recovery Approved":
        return "Recovery Authorized"
    return current_state


def _disposition_for_outcome(outcome: str, donor: Donor) -> str | None:
    if outcome in {"Reject", "Recovery Rejected"}:
        return "Rejected / Deferred"
    if outcome == "Reject / Destroy":
        return "Destruction"
    if outcome in {"Hold", "Release Hold", "Recovery Hold", "CAPA Required"}:
        return "Quarantine"
    if outcome == "Research Only":
        return "Research Use"
    if outcome in {"Release Approved", "Recovery Approved"}:
        return donor.final_disposition or "Clinical Transplant"
    return donor.final_disposition


def eligibility_record_bundle(db: Session, donor: Donor) -> dict[str, Any]:
    screening = db.execute(select(DonorScreening).where(DonorScreening.donor_pk == donor.donor_pk).limit(1)).scalar_one_or_none()
    history = db.execute(select(MedicalSocialHistory).where(MedicalSocialHistory.donor_pk == donor.donor_pk).limit(1)).scalar_one_or_none()
    infectious = db.execute(
        select(InfectiousDiseaseResult, InfectiousDiseaseTest)
        .join(InfectiousDiseaseTest, InfectiousDiseaseResult.test_id == InfectiousDiseaseTest.test_id)
        .where(InfectiousDiseaseResult.donor_pk == donor.donor_pk)
    ).all()
    recoveries = db.execute(
        select(RecoverySuitability, TissueType)
        .join(TissueType, RecoverySuitability.tissue_type_id == TissueType.tissue_type_id)
        .where(RecoverySuitability.donor_pk == donor.donor_pk)
    ).all()
    releases = db.execute(
        select(ProcessingRelease, TissueType)
        .join(TissueType, ProcessingRelease.tissue_type_id == TissueType.tissue_type_id)
        .where(ProcessingRelease.donor_pk == donor.donor_pk)
    ).all()
    decisions = db.execute(
        select(EligibilityDecision)
        .where(EligibilityDecision.donor_pk == donor.donor_pk)
        .order_by(desc(EligibilityDecision.created_at))
        .limit(20)
    ).scalars().all()
    deviations = db.execute(select(Deviation).where(Deviation.donor_pk == donor.donor_pk).limit(20)).scalars().all()
    capas = db.execute(select(CAPA).where(CAPA.donor_pk == donor.donor_pk).limit(20)).scalars().all()
    return {
        "screening": _screening_payload(screening) if screening else None,
        "medical_social_history": _history_payload(history) if history else None,
        "infectious_disease_results": [
            {
                "result_id": result.result_id,
                "test_name": test.test_name,
                "pathogen": test.pathogen,
                "method": test.test_method,
                "result_value": result.result_value,
                "specimen_window_valid": result.specimen_window_valid,
                "review_status": result.review_status,
            }
            for result, test in infectious
        ],
        "recovery_suitability": [
            {
                "recovery_id": recovery.recovery_id,
                "tissue": tissue.tissue_name,
                "recovery_window_hours": recovery.recovery_window_hours,
                "trauma_contamination": recovery.trauma_contamination,
                "hospital_release_status": recovery.hospital_release_status,
                "outcome": recovery.outcome,
            }
            for recovery, tissue in recoveries
        ],
        "processing_releases": [
            {
                "release_id": release.release_id,
                "release_identifier": release.release_identifier,
                "tissue": tissue.tissue_name,
                "release_status": release.release_status,
                "final_disposition": release.final_disposition,
                "chain_of_custody_verified": release.chain_of_custody_verified,
                "route_path": f"/release/{release.release_id}",
            }
            for release, tissue in releases
        ],
        "eligibility_decisions": [
            {
                "decision_id": decision.decision_id,
                "decision_stage": decision.decision_stage,
                "outcome": decision.outcome,
                "severity": decision.severity,
                "requires_review": decision.requires_review,
                "required_role": decision.required_role,
                "final_disposition": decision.final_disposition,
                "created_at": decision.created_at.isoformat(),
            }
            for decision in decisions
        ],
        "deviations": [
            {
                "deviation_id": deviation.deviation_id,
                "deviation_code": deviation.deviation_code,
                "category": deviation.deviation_category,
                "severity": deviation.severity,
                "status": deviation.status,
                "route_path": f"/deviation/{deviation.deviation_id}",
            }
            for deviation in deviations
        ],
        "capas": [
            {
                "capa_id": capa.capa_id,
                "capa_code": capa.capa_code,
                "status": capa.status,
                "due_date": capa.due_date.isoformat() if capa.due_date else None,
                "route_path": f"/capa/{capa.capa_id}",
            }
            for capa in capas
        ],
    }


def _screening_payload(screening: DonorScreening) -> dict[str, Any]:
    return {
        "screening_id": screening.screening_id,
        "referral_id": screening.referral_id,
        "administrative_outcome": screening.administrative_outcome,
        "medical_social_outcome": screening.medical_social_outcome,
        "infectious_disease_outcome": screening.infectious_disease_outcome,
        "tissue_suitability_outcome": screening.tissue_suitability_outcome,
        "recovery_suitability_outcome": screening.recovery_suitability_outcome,
        "qa_outcome": screening.qa_outcome,
        "automated_rule_outcome": screening.automated_rule_outcome,
        "current_decision": screening.current_decision,
    }


def _history_payload(history: MedicalSocialHistory) -> dict[str, Any]:
    return {
        "history_id": history.history_id,
        "cancer_history": history.cancer_history,
        "neurological_disease": history.neurological_disease,
        "autoimmune_disease": history.autoimmune_disease,
        "transmissible_disease_history": history.transmissible_disease_history,
        "iv_drug_use": history.iv_drug_use,
        "incarceration_history": history.incarceration_history,
        "travel_exposure": history.travel_exposure,
        "high_risk_behavior": history.high_risk_behavior,
        "unknown_history": history.unknown_history,
        "outcome": history.outcome,
        "review_notes": history.review_notes,
    }


def eligibility_analytics(db: Session) -> dict[str, Any]:
    donor_states = db.execute(
        select(Donor.current_workflow_state, func.count(Donor.donor_pk))
        .group_by(Donor.current_workflow_state)
        .order_by(Donor.current_workflow_state)
    ).all()
    outcomes = db.execute(
        select(Donor.eligibility_status, func.count(Donor.donor_pk))
        .group_by(Donor.eligibility_status)
        .order_by(Donor.eligibility_status)
    ).all()
    dispositions = db.execute(
        select(Donor.final_disposition, func.count(Donor.donor_pk))
        .where(Donor.final_disposition.is_not(None))
        .group_by(Donor.final_disposition)
    ).all()
    rule_outcomes = db.execute(
        select(EligibilityDecision.outcome, func.count(EligibilityDecision.decision_id))
        .group_by(EligibilityDecision.outcome)
    ).all()
    release_status = db.execute(
        select(ProcessingRelease.release_status, func.count(ProcessingRelease.release_id))
        .group_by(ProcessingRelease.release_status)
    ).all()
    deviation_counts = db.execute(
        select(Deviation.deviation_category, Deviation.severity, func.count(Deviation.deviation_id))
        .group_by(Deviation.deviation_category, Deviation.severity)
    ).all()
    return {
        "donor_state_distribution": [{"state": row[0], "count": row[1]} for row in donor_states],
        "eligibility_outcomes": [{"outcome": row[0], "count": row[1]} for row in outcomes],
        "final_dispositions": [{"disposition": row[0], "count": row[1]} for row in dispositions],
        "rule_outcomes": [{"outcome": row[0], "count": row[1]} for row in rule_outcomes],
        "release_status": [{"release_status": row[0], "count": row[1]} for row in release_status],
        "deviation_matrix": [
            {"category": row[0], "severity": row[1], "count": row[2]}
            for row in deviation_counts
        ],
    }
