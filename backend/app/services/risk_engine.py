from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


class RuleLike(Protocol):
    rule_id: int
    rule_name: str
    risk_category: str
    condition_type: str
    condition_operator: str
    condition_value: str
    risk_score_delta: int
    severity: str
    auto_escalate: bool


@dataclass(frozen=True)
class TriggeredRule:
    rule_id: int
    rule_name: str
    risk_category: str
    condition: str
    score_delta: int
    severity: str
    auto_escalate: bool
    explanation: str


@dataclass(frozen=True)
class RiskAnalysis:
    risk_score: int
    risk_level: str
    recommended_action: str
    flagged_conditions: list[str]
    review_priority: str
    triggered_rules: list[dict[str, Any]] = field(default_factory=list)
    score_contributions: list[dict[str, Any]] = field(default_factory=list)
    escalation_reasons: list[str] = field(default_factory=list)
    workflow_impact: str = ""
    confidence_level: float = 0.0
    historical_comparison: dict[str, Any] = field(default_factory=dict)


DEFAULT_RULES = [
    {
        "rule_id": 0,
        "rule_name": "Missing Required Intake Data",
        "risk_category": "Data Completeness",
        "condition_type": "missing_required_fields",
        "condition_operator": "equals",
        "condition_value": "true",
        "risk_score_delta": 50,
        "severity": "High",
        "auto_escalate": False,
    },
    {
        "rule_id": 0,
        "rule_name": "Age Above Standard Donor Threshold",
        "risk_category": "Clinical Demographic",
        "condition_type": "age",
        "condition_operator": "gt",
        "condition_value": "70",
        "risk_score_delta": 25,
        "severity": "Moderate",
        "auto_escalate": False,
    },
    {
        "rule_id": 0,
        "rule_name": "Donor Under Minimum Review Age",
        "risk_category": "Clinical Demographic",
        "condition_type": "age",
        "condition_operator": "lt",
        "condition_value": "18",
        "risk_score_delta": 40,
        "severity": "High",
        "auto_escalate": False,
    },
    {
        "rule_id": 0,
        "rule_name": "Blood Type Unavailable",
        "risk_category": "Data Completeness",
        "condition_type": "blood_type",
        "condition_operator": "in",
        "condition_value": "UNKNOWN,N/A,",
        "risk_score_delta": 10,
        "severity": "Low",
        "auto_escalate": False,
    },
    {
        "rule_id": 0,
        "rule_name": "Infectious Disease History Disclosed",
        "risk_category": "Infectious Risk",
        "condition_type": "infectious_history",
        "condition_operator": "equals",
        "condition_value": "true",
        "risk_score_delta": 50,
        "severity": "Critical",
        "auto_escalate": True,
    },
    {
        "rule_id": 0,
        "rule_name": "Recent Travel Risk",
        "risk_category": "Exposure Risk",
        "condition_type": "travel_risk",
        "condition_operator": "equals",
        "condition_value": "true",
        "risk_score_delta": 15,
        "severity": "Moderate",
        "auto_escalate": False,
    },
    {
        "rule_id": 0,
        "rule_name": "Clinical Notes Infectious Terms",
        "risk_category": "Clinical Narrative",
        "condition_type": "clinical_notes",
        "condition_operator": "contains_any",
        "condition_value": "hiv,hepatitis,tb,tuberculosis,sepsis,infection",
        "risk_score_delta": 35,
        "severity": "High",
        "auto_escalate": True,
    },
    {
        "rule_id": 0,
        "rule_name": "Clinical Notes Cautionary History",
        "risk_category": "Clinical Narrative",
        "condition_type": "clinical_notes",
        "condition_operator": "contains_any",
        "condition_value": "fever,unexplained weight loss,recent hospitalization,malignancy",
        "risk_score_delta": 20,
        "severity": "Moderate",
        "auto_escalate": False,
    },
    {
        "rule_id": 0,
        "rule_name": "Missing Chain of Custody",
        "risk_category": "Chain of Custody",
        "condition_type": "clinical_notes",
        "condition_operator": "contains_any",
        "condition_value": "missing chain of custody,chain-of-custody missing,custody gap",
        "risk_score_delta": 45,
        "severity": "Critical",
        "auto_escalate": True,
    },
    {
        "rule_id": 0,
        "rule_name": "Failed Lab Validation",
        "risk_category": "Lab Validation",
        "condition_type": "clinical_notes",
        "condition_operator": "contains_any",
        "condition_value": "failed lab validation,invalid lab result,conflicting lab",
        "risk_score_delta": 45,
        "severity": "Critical",
        "auto_escalate": True,
    },
    {
        "rule_id": 0,
        "rule_name": "Conflicting Documentation",
        "risk_category": "Documentation Conflict",
        "condition_type": "clinical_notes",
        "condition_operator": "contains_any",
        "condition_value": "conflicting documentation,conflicting attestation,document mismatch",
        "risk_score_delta": 35,
        "severity": "High",
        "auto_escalate": True,
    },
]


def _value_for_condition(
    *,
    donor_name: str | None,
    age: int | None,
    blood_type: str | None,
    infectious_history: bool,
    travel_risk: bool,
    missing_required_fields: bool,
    clinical_notes: str,
    condition_type: str,
) -> Any:
    values = {
        "donor_name": donor_name,
        "age": age,
        "blood_type": blood_type,
        "infectious_history": infectious_history,
        "travel_risk": travel_risk,
        "missing_required_fields": missing_required_fields
        or not donor_name
        or age is None
        or not blood_type,
        "clinical_notes": clinical_notes,
    }
    return values.get(condition_type)


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "y"}


def _matches(value: Any, operator: str, expected: str) -> bool:
    operator = operator.lower().strip()
    if operator == "equals":
        if isinstance(value, bool):
            return value is _as_bool(expected)
        return str(value or "").strip().lower() == expected.strip().lower()
    if operator in {"gt", "gte", "lt", "lte"}:
        if value is None:
            return False
        numeric_value = float(value)
        numeric_expected = float(expected)
        return {
            "gt": numeric_value > numeric_expected,
            "gte": numeric_value >= numeric_expected,
            "lt": numeric_value < numeric_expected,
            "lte": numeric_value <= numeric_expected,
        }[operator]
    if operator == "in":
        options = {item.strip().upper() for item in expected.split(",")}
        return str(value or "").strip().upper() in options
    if operator == "contains_any":
        text = str(value or "").lower()
        return any(item.strip().lower() in text for item in expected.split(",") if item.strip())
    if operator == "missing":
        return value in {None, ""}
    return False


def _rule_to_dict(rule: RuleLike | dict[str, Any]) -> dict[str, Any]:
    if isinstance(rule, dict):
        return rule
    return {
        "rule_id": rule.rule_id,
        "rule_name": rule.rule_name,
        "risk_category": rule.risk_category,
        "condition_type": rule.condition_type,
        "condition_operator": rule.condition_operator,
        "condition_value": rule.condition_value,
        "risk_score_delta": rule.risk_score_delta,
        "severity": rule.severity,
        "auto_escalate": rule.auto_escalate,
    }


def _recommendation(score: int, auto_escalate: bool) -> tuple[str, str, str]:
    if score >= 75:
        return "Critical", "Escalate to QA Review" if auto_escalate else "Escalate to Medical Director", "STAT"
    if score >= 50:
        return "High", "Defer Pending Clinical Review", "High"
    if score >= 25:
        return "Moderate", "Manual Clinical Review", "Standard"
    return "Low", "Approve", "Routine"


def analyze_donor_risk(
    *,
    donor_name: str | None,
    age: int | None,
    blood_type: str | None,
    infectious_history: bool = False,
    travel_risk: bool = False,
    missing_required_fields: bool = False,
    clinical_notes: str = "",
    rules: Sequence[RuleLike | dict[str, Any]] | None = None,
    historical_comparison: dict[str, Any] | None = None,
) -> RiskAnalysis:
    active_rules = [_rule_to_dict(rule) for rule in (rules or DEFAULT_RULES)]
    triggered: list[TriggeredRule] = []
    for rule in active_rules:
        value = _value_for_condition(
            donor_name=donor_name,
            age=age,
            blood_type=blood_type,
            infectious_history=infectious_history,
            travel_risk=travel_risk,
            missing_required_fields=missing_required_fields,
            clinical_notes=clinical_notes,
            condition_type=rule["condition_type"],
        )
        if _matches(value, rule["condition_operator"], rule["condition_value"]):
            triggered.append(
                TriggeredRule(
                    rule_id=rule["rule_id"],
                    rule_name=rule["rule_name"],
                    risk_category=rule["risk_category"],
                    condition=f"{rule['condition_type']} {rule['condition_operator']} {rule['condition_value']}",
                    score_delta=rule["risk_score_delta"],
                    severity=rule["severity"],
                    auto_escalate=rule["auto_escalate"],
                    explanation=f"{rule['rule_name']} contributed +{rule['risk_score_delta']} risk.",
                )
            )

    score = min(sum(rule.score_delta for rule in triggered), 100)
    auto_escalate = any(rule.auto_escalate for rule in triggered)
    risk_level, recommended_action, review_priority = _recommendation(score, auto_escalate)
    flags = [rule.rule_name for rule in triggered] or ["No abnormal screening flags detected"]
    escalation_reasons = [
        rule.rule_name
        for rule in triggered
        if rule.auto_escalate or rule.severity in {"High", "Critical"}
    ]
    if score >= 75:
        workflow_impact = "High-risk case should route to clinical escalation or QA review before closure."
    elif score >= 50:
        workflow_impact = "Case should remain in clinical review with elevated SLA monitoring."
    elif score >= 25:
        workflow_impact = "Manual clinical review is recommended before final disposition."
    else:
        workflow_impact = "No additional AI-driven workflow routing is recommended."

    confidence_level = round(min(0.94, 0.68 + (score / 300) + (len(triggered) * 0.015)), 2)

    return RiskAnalysis(
        risk_score=score,
        risk_level=risk_level,
        recommended_action=recommended_action,
        flagged_conditions=flags,
        review_priority=review_priority,
        triggered_rules=[rule.__dict__ for rule in triggered],
        score_contributions=[
            {"rule_name": rule.rule_name, "score_delta": rule.score_delta, "severity": rule.severity}
            for rule in triggered
        ],
        escalation_reasons=escalation_reasons,
        workflow_impact=workflow_impact,
        confidence_level=confidence_level,
        historical_comparison=historical_comparison or {},
    )
