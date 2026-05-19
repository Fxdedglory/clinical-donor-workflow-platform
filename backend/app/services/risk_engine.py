from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAnalysis:
    risk_score: int
    risk_level: str
    recommended_action: str
    flagged_conditions: list[str]
    review_priority: str


INFECTIOUS_KEYWORDS = {"hiv", "hepatitis", "tb", "tuberculosis", "sepsis", "infection"}
CLINICAL_CAUTION_KEYWORDS = {"fever", "unexplained weight loss", "recent hospitalization", "malignancy"}


def analyze_donor_risk(
    *,
    donor_name: str | None,
    age: int | None,
    blood_type: str | None,
    infectious_history: bool = False,
    travel_risk: bool = False,
    missing_required_fields: bool = False,
    clinical_notes: str = "",
) -> RiskAnalysis:
    score = 0
    flags: list[str] = []

    if missing_required_fields or not donor_name or age is None or not blood_type:
        score += 50
        flags.append("Missing required intake data")

    if age is not None and age < 18:
        score += 40
        flags.append("Donor under minimum review age")
    elif age is not None and age > 70:
        score += 25
        flags.append("Age above standard donor threshold")

    normalized_blood_type = (blood_type or "").strip().upper()
    if normalized_blood_type in {"", "UNKNOWN", "N/A"}:
        score += 10
        flags.append("Blood type unavailable")

    if infectious_history:
        score += 45
        flags.append("Infectious disease history disclosed")

    if travel_risk:
        score += 15
        flags.append("Recent travel risk requires clinical review")

    lowered_notes = clinical_notes.lower()
    if any(keyword in lowered_notes for keyword in INFECTIOUS_KEYWORDS):
        score += 35
        flags.append("Clinical notes contain infectious risk terms")
    if any(keyword in lowered_notes for keyword in CLINICAL_CAUTION_KEYWORDS):
        score += 20
        flags.append("Clinical notes contain cautionary history")

    score = min(score, 100)
    auto_flag = infectious_history or any("infectious" in flag.lower() for flag in flags)

    if score >= 75:
        risk_level = "Critical"
        recommended_action = "Reject" if auto_flag else "Escalate to Medical Director"
        review_priority = "STAT"
    elif score >= 50:
        risk_level = "High"
        recommended_action = "Defer Pending Clinical Review"
        review_priority = "High"
    elif score >= 25:
        risk_level = "Moderate"
        recommended_action = "Manual Clinical Review"
        review_priority = "Standard"
    else:
        risk_level = "Low"
        recommended_action = "Approve"
        review_priority = "Routine"

    if not flags:
        flags.append("No abnormal screening flags detected")

    return RiskAnalysis(
        risk_score=score,
        risk_level=risk_level,
        recommended_action=recommended_action,
        flagged_conditions=flags,
        review_priority=review_priority,
    )

