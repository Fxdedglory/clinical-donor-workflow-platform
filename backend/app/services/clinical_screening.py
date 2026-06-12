from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    ClinicalDeferral,
    ClinicalScreeningAnswer,
    ClinicalScreeningOutcome,
    ClinicalScreeningSession,
    ClinicalScreeningStatusHistory,
    ClinicalScreeningVitals,
    Donor,
    Patient,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_screening import (
    EligibilityPreviewRequest,
    EligibilityPreviewResponse,
    EligibilityRuleResult,
    ScreeningBlockingIssue,
    ScreeningQuestion,
    ScreeningQuestionnairePreviewRequest,
    ScreeningSessionCreatePreviewRequest,
    ScreeningSessionPreviewResponse,
    ScreeningTemplateResponse,
    ScreeningVitalsPreviewRequest,
    ScreeningWarning,
)
from app.services.clinical_patients import actor_label, patient_name
from app.services.clinical_workflows import append_workflow_operation, preview_hash
from app.services.eligibility_engine import evaluate_donor_eligibility

TEMPLATE_ID = "minimal_donor_screening_v1"
MINIMAL_SCREENING_TEMPLATE = ScreeningTemplateResponse(
    template_id=TEMPLATE_ID,
    name="Minimal donor screening questionnaire",
    version="1.0",
    questions=[
        ScreeningQuestion(
            question_key="identity_verified",
            label="Identity verified",
            risk_when=False,
            guidance="Confirm donor identity against the registration profile.",
        ),
        ScreeningQuestion(
            question_key="authorization_verified",
            label="Authorization verified",
            risk_when=False,
            guidance="Confirm authorization/consent documentation before eligibility decision.",
        ),
        ScreeningQuestion(
            question_key="infectious_symptoms",
            label="Fever or infectious symptoms in screening window",
            risk_when=True,
        ),
        ScreeningQuestion(question_key="transmissible_disease_history", label="Known transmissible disease history", risk_when=True),
        ScreeningQuestion(question_key="iv_drug_use", label="IV drug use risk disclosed", risk_when=True),
        ScreeningQuestion(question_key="incarceration_history", label="Recent incarceration risk disclosed", risk_when=True),
        ScreeningQuestion(question_key="travel_exposure", label="Travel exposure requiring review", risk_when=True),
        ScreeningQuestion(question_key="high_risk_behavior", label="High risk behavior disclosed", risk_when=True),
    ],
)
QUESTION_KEYS = [question.question_key for question in MINIMAL_SCREENING_TEMPLATE.questions if question.required]
REQUIRED_VITALS = [
    "weight_kg",
    "temperature_c",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "pulse",
]
OUTCOME_TO_STATUS = {
    "eligible": "eligible",
    "eligible_with_conditions": "eligible_with_conditions",
    "temporarily_deferred": "temporarily_deferred",
    "permanently_deferred": "permanently_deferred",
    "requires_supervisor_review": "requires_supervisor_review",
}
FINAL_OUTCOMES = set(OUTCOME_TO_STATUS)


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_screening_session_number() -> str:
    return f"SCR-{uuid4().hex[:10].upper()}"


def new_deferral_number() -> str:
    return f"DEF-{uuid4().hex[:10].upper()}"


def _all_rows(db: Session, statement) -> list[Any]:
    return list(db.execute(statement).scalars().all())


def _one_or_none(db: Session, statement) -> Any | None:
    return db.execute(statement).scalar_one_or_none()


def patient_by_identifier(db: Session, patient_id: str) -> Patient | None:
    return _one_or_none(db, select(Patient).where(Patient.patient_id == patient_id, Patient.is_deleted.is_(False)))


def donor_for_patient(db: Session, patient: Patient | None) -> Donor | None:
    if not patient or not patient.donor_reference:
        return None
    return _one_or_none(
        db,
        select(Donor).where(
            Donor.donor_identifier == patient.donor_reference,
            Donor.is_archived.is_(False),
        ),
    )


def appointment_by_id(db: Session, appointment_id: int | None) -> Appointment | None:
    if appointment_id is None:
        return None
    return _one_or_none(
        db,
        select(Appointment).where(Appointment.appointment_id == appointment_id, Appointment.is_deleted.is_(False)),
    )


def screening_session_by_id(db: Session, session_id: int) -> ClinicalScreeningSession | None:
    return _one_or_none(
        db,
        select(ClinicalScreeningSession).where(
            ClinicalScreeningSession.session_id == session_id,
            ClinicalScreeningSession.is_deleted.is_(False),
        ),
    )


def answer_map(session: ClinicalScreeningSession) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for answer in session.answers:
        raw = answer.answer_value or {}
        values[answer.question_key] = raw.get("value")
    return values


def latest_vitals(session: ClinicalScreeningSession) -> ClinicalScreeningVitals | None:
    if not session.vitals:
        return None
    return sorted(session.vitals, key=lambda item: item.captured_at or datetime.min.replace(tzinfo=UTC), reverse=True)[0]


def latest_outcome(session: ClinicalScreeningSession) -> ClinicalScreeningOutcome | None:
    if not session.outcomes:
        return None
    return sorted(session.outcomes, key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)[0]


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def missing_required_answers(answers: dict[str, Any]) -> list[str]:
    return [key for key in QUESTION_KEYS if key not in answers or _is_missing(answers.get(key))]


def questionnaire_preview(
    session: ClinicalScreeningSession,
    payload: ScreeningQuestionnairePreviewRequest,
) -> ScreeningSessionPreviewResponse:
    missing = missing_required_answers(payload.answers)
    issues = [
        ScreeningBlockingIssue(
            issue_type="missing_required_answer",
            field=key,
            message=f"Required screening question {key} is missing.",
        )
        for key in missing
    ]
    warnings = []
    for question in MINIMAL_SCREENING_TEMPLATE.questions:
        value = payload.answers.get(question.question_key)
        if value == question.risk_when and question.risk_when is not None:
            warnings.append(
                ScreeningWarning(
                    warning_type="risk_answer",
                    field=question.question_key,
                    message=f"{question.label} requires eligibility review.",
                )
            )
    status = "failed" if issues else "warning" if warnings else "passed"
    changes = payload.model_dump(mode="json")
    return ScreeningSessionPreviewResponse(
        workflow="screening.questionnaire_commit",
        entity_id=session.session_number,
        preview_hash=preview_hash({"workflow": "screening.questionnaire_commit", "entity_id": session.session_number, "changes": changes}),
        validation_status=status,
        blocking_issues=issues,
        warnings=warnings,
        summary="Questionnaire preview found missing answers." if issues else "Questionnaire is ready for commit.",
        changes=changes,
    )


def vitals_payload_from_model(vitals: ClinicalScreeningVitals | None) -> dict[str, Any]:
    if not vitals:
        return {}
    return {
        "height_cm": vitals.height_cm,
        "weight_kg": vitals.weight_kg,
        "temperature_c": vitals.temperature_c,
        "blood_pressure_systolic": vitals.blood_pressure_systolic,
        "blood_pressure_diastolic": vitals.blood_pressure_diastolic,
        "pulse": vitals.pulse,
        "respiration_rate": vitals.respiration_rate,
        "oxygen_saturation": vitals.oxygen_saturation,
    }


def _vitals_payload(payload: ScreeningVitalsPreviewRequest) -> dict[str, Any]:
    return payload.model_dump(mode="json", exclude={"captured_at", "notes"})


def validate_vitals_values(values: dict[str, Any]) -> tuple[list[ScreeningBlockingIssue], list[ScreeningWarning]]:
    issues = [
        ScreeningBlockingIssue(
            issue_type="missing_required_vital",
            field=field,
            message=f"Required vital {field} is missing.",
        )
        for field in REQUIRED_VITALS
        if _is_missing(values.get(field))
    ]
    warnings: list[ScreeningWarning] = []
    if issues:
        return issues, warnings

    weight = float(values["weight_kg"])
    temperature = float(values["temperature_c"])
    systolic = int(values["blood_pressure_systolic"])
    diastolic = int(values["blood_pressure_diastolic"])
    pulse = int(values["pulse"])
    oxygen = values.get("oxygen_saturation")
    respiration = values.get("respiration_rate")

    if weight <= 0 or weight > 350:
        issues.append(ScreeningBlockingIssue(issue_type="out_of_range_vital", field="weight_kg", message="Weight is outside a plausible screening range."))
    if temperature < 34 or temperature > 41:
        issues.append(ScreeningBlockingIssue(issue_type="out_of_range_vital", field="temperature_c", message="Temperature is outside a plausible screening range."))
    elif temperature >= 37.8:
        warnings.append(ScreeningWarning(warning_type="vital_review", field="temperature_c", message="Elevated temperature may require temporary deferral."))
    if systolic < 70 or systolic > 220:
        issues.append(ScreeningBlockingIssue(issue_type="out_of_range_vital", field="blood_pressure_systolic", message="Systolic blood pressure is outside a plausible range."))
    elif systolic > 160:
        warnings.append(ScreeningWarning(warning_type="vital_review", field="blood_pressure_systolic", message="Elevated systolic blood pressure requires review."))
    if diastolic < 40 or diastolic > 130:
        issues.append(ScreeningBlockingIssue(issue_type="out_of_range_vital", field="blood_pressure_diastolic", message="Diastolic blood pressure is outside a plausible range."))
    elif diastolic > 100:
        warnings.append(ScreeningWarning(warning_type="vital_review", field="blood_pressure_diastolic", message="Elevated diastolic blood pressure requires review."))
    if pulse < 35 or pulse > 180:
        issues.append(ScreeningBlockingIssue(issue_type="out_of_range_vital", field="pulse", message="Pulse is outside a plausible range."))
    elif pulse < 50 or pulse > 120:
        warnings.append(ScreeningWarning(warning_type="vital_review", field="pulse", message="Pulse is outside normal screening range."))
    if oxygen is not None and float(oxygen) < 92:
        warnings.append(ScreeningWarning(warning_type="vital_review", field="oxygen_saturation", message="Low oxygen saturation requires review."))
    if respiration is not None and (int(respiration) < 8 or int(respiration) > 28):
        warnings.append(ScreeningWarning(warning_type="vital_review", field="respiration_rate", message="Respiration rate is outside normal screening range."))
    return issues, warnings


def vitals_preview(
    session: ClinicalScreeningSession,
    payload: ScreeningVitalsPreviewRequest,
) -> ScreeningSessionPreviewResponse:
    changes = payload.model_dump(mode="json")
    issues, warnings = validate_vitals_values(_vitals_payload(payload))
    status = "failed" if issues else "warning" if warnings else "passed"
    return ScreeningSessionPreviewResponse(
        workflow="screening.vitals_commit",
        entity_id=session.session_number,
        preview_hash=preview_hash({"workflow": "screening.vitals_commit", "entity_id": session.session_number, "changes": changes}),
        validation_status=status,
        blocking_issues=issues,
        warnings=warnings,
        summary="Vitals preview found missing or invalid values." if issues else "Vitals are ready for commit.",
        changes=changes,
    )


def session_create_preview(db: Session, payload: ScreeningSessionCreatePreviewRequest) -> ScreeningSessionPreviewResponse:
    patient = patient_by_identifier(db, payload.patient_id)
    appointment = appointment_by_id(db, payload.appointment_id)
    issues: list[ScreeningBlockingIssue] = []
    warnings: list[ScreeningWarning] = []
    if patient is None:
        issues.append(
            ScreeningBlockingIssue(
                issue_type="unknown_patient",
                field="patient_id",
                message="Patient/donor profile was not found.",
            )
        )
    if payload.appointment_id is not None and appointment is None:
        issues.append(
            ScreeningBlockingIssue(
                issue_type="unknown_appointment",
                field="appointment_id",
                message="Scheduling appointment was not found.",
            )
        )
    if patient and appointment and appointment.patient_pk != patient.patient_pk:
        issues.append(
            ScreeningBlockingIssue(
                issue_type="appointment_patient_mismatch",
                field="appointment_id",
                message="Appointment is linked to a different patient/donor.",
            )
        )
    if patient and not donor_for_patient(db, patient):
        warnings.append(
            ScreeningWarning(
                warning_type="donor_engine_unlinked",
                field="patient_id",
                message="No linked dim_donor record was found; clinical screening rules will run without legacy donor engine context.",
            )
        )
    changes = payload.model_dump(mode="json")
    return ScreeningSessionPreviewResponse(
        workflow="screening.session_create",
        entity_id="draft",
        preview_hash=preview_hash({"workflow": "screening.session_create", "changes": changes}),
        validation_status="failed" if issues else "warning" if warnings else "passed",
        blocking_issues=issues,
        warnings=warnings,
        summary="Screening session can be started." if not issues else "Screening session preview found blocking issues.",
        changes=changes,
    )


def _clinical_rule_results(
    answers: dict[str, Any],
    vitals_values: dict[str, Any],
    vital_warnings: list[ScreeningWarning],
) -> list[EligibilityRuleResult]:
    results: list[EligibilityRuleResult] = []
    if answers.get("identity_verified") is False:
        results.append(
            EligibilityRuleResult(
                rule_name="Identity verification required",
                rule_category="Administrative",
                outcome="requires_supervisor_review",
                severity="High",
                requires_review=True,
                explanation="Identity verification is required before eligibility can be finalized.",
            )
        )
    if answers.get("authorization_verified") is False:
        results.append(
            EligibilityRuleResult(
                rule_name="Authorization verification required",
                rule_category="Administrative",
                outcome="requires_supervisor_review",
                severity="High",
                requires_review=True,
                explanation="Authorization documentation is required before eligibility can be finalized.",
            )
        )
    for key in ["transmissible_disease_history", "iv_drug_use", "incarceration_history", "high_risk_behavior"]:
        if answers.get(key) is True:
            results.append(
                EligibilityRuleResult(
                    rule_name=f"{key.replace('_', ' ').title()} exclusion",
                    rule_category="Medical Social History",
                    outcome="permanently_deferred",
                    severity="Critical",
                    requires_review=True,
                    explanation=f"{key.replace('_', ' ')} requires permanent deferral review.",
                )
            )
    if answers.get("infectious_symptoms") is True or answers.get("travel_exposure") is True:
        results.append(
            EligibilityRuleResult(
                rule_name="Temporary infectious exposure deferral",
                rule_category="Medical Social History",
                outcome="temporarily_deferred",
                severity="High",
                requires_review=True,
                explanation="Current symptoms or travel exposure require temporary deferral review.",
            )
        )
    for warning in vital_warnings:
        outcome = "temporarily_deferred" if warning.field == "temperature_c" else "eligible_with_conditions"
        results.append(
            EligibilityRuleResult(
                rule_name=f"Vital review: {warning.field}",
                rule_category="Vitals",
                outcome=outcome,
                severity="Medium",
                requires_review=outcome != "eligible_with_conditions",
                explanation=warning.message,
            )
        )
    return results


def _map_existing_engine_outcome(outcome: str | None, requires_review: bool) -> str | None:
    if not outcome:
        return None
    if outcome in {"Reject", "Recovery Rejected", "Reject / Destroy"}:
        return "permanently_deferred"
    if outcome in {"Hold", "Recovery Hold", "Release Hold"}:
        return "temporarily_deferred"
    if outcome in {"Medical Director Review", "QA Review Required", "CAPA Required"} or requires_review:
        return "requires_supervisor_review"
    if outcome in {"Conditional", "Research Only"}:
        return "eligible_with_conditions"
    if outcome in {"Continue", "Eligible", "Recovery Approved", "Release Approved"}:
        return "eligible"
    return None


def _proposed_outcome(rule_results: list[EligibilityRuleResult]) -> str:
    outcomes = {result.outcome for result in rule_results}
    if "permanently_deferred" in outcomes:
        return "permanently_deferred"
    if "temporarily_deferred" in outcomes:
        return "temporarily_deferred"
    if "requires_supervisor_review" in outcomes:
        return "requires_supervisor_review"
    if "eligible_with_conditions" in outcomes:
        return "eligible_with_conditions"
    return "eligible"


def eligibility_preview(
    db: Session,
    session: ClinicalScreeningSession,
    payload: EligibilityPreviewRequest | None = None,
) -> EligibilityPreviewResponse:
    answers = answer_map(session)
    vitals = latest_vitals(session)
    vitals_values = vitals_payload_from_model(vitals)
    missing_answers = missing_required_answers(answers)
    vital_issues, vital_warnings = validate_vitals_values(vitals_values)
    missing_vitals = [issue.field or "" for issue in vital_issues if issue.issue_type == "missing_required_vital"]
    blocking_issues = [
        ScreeningBlockingIssue(
            issue_type="missing_required_answer",
            field=key,
            message=f"Required screening question {key} is missing.",
        )
        for key in missing_answers
    ] + vital_issues
    warnings = list(vital_warnings)
    rule_results = _clinical_rule_results(answers, vitals_values, vital_warnings)
    existing_engine_outcome = None
    if session.donor:
        engine_result = evaluate_donor_eligibility(
            db,
            session.donor,
            category=payload.category if payload else None,
            persist=False,
        )
        existing_engine_outcome = engine_result.get("outcome")
        for rule in engine_result.get("triggered_rules", []):
            rule_results.append(
                EligibilityRuleResult(
                    rule_id=rule.get("rule_id"),
                    rule_name=rule.get("rule_name") or "Existing donor eligibility rule",
                    rule_category=rule.get("rule_category") or "Existing Eligibility",
                    outcome=_map_existing_engine_outcome(rule.get("outcome"), bool(rule.get("requires_review"))) or "eligible_with_conditions",
                    severity=rule.get("severity") or "Medium",
                    requires_review=bool(rule.get("requires_review")),
                    explanation=rule.get("condition") or rule.get("outcome") or "Existing donor eligibility rule matched.",
                    source="existing_eligibility_engine",
                )
            )
        mapped = _map_existing_engine_outcome(existing_engine_outcome, bool(engine_result.get("requires_review")))
        if mapped and not engine_result.get("triggered_rules"):
            rule_results.append(
                EligibilityRuleResult(
                    rule_name="Existing donor eligibility engine",
                    rule_category="Existing Eligibility",
                    outcome=mapped,
                    severity=engine_result.get("severity") or "Low",
                    requires_review=bool(engine_result.get("requires_review")),
                    explanation=f"Existing engine proposed {existing_engine_outcome}.",
                    source="existing_eligibility_engine",
                )
            )
    proposed = _proposed_outcome(rule_results)
    recommended_deferral_type = None
    if proposed == "temporarily_deferred":
        recommended_deferral_type = "temporary"
    if proposed == "permanently_deferred":
        recommended_deferral_type = "permanent"
    supervisor_review_required = proposed == "requires_supervisor_review" or any(result.requires_review for result in rule_results)
    changes = {
        "category": payload.category if payload else None,
        "answers_complete": not missing_answers,
        "vitals_complete": not missing_vitals,
        "proposed_outcome": proposed,
        "existing_engine_outcome": existing_engine_outcome,
    }
    validation_status = "failed" if blocking_issues else "warning" if warnings or supervisor_review_required else "passed"
    return EligibilityPreviewResponse(
        entity_id=session.session_number,
        preview_hash=preview_hash({"workflow": "screening.eligibility_preview", "entity_id": session.session_number, "changes": changes}),
        validation_status=validation_status,
        proposed_outcome=proposed,
        blocking_issues=blocking_issues,
        warnings=warnings,
        rules_evaluated=rule_results,
        missing_required_answers=missing_answers,
        missing_required_vitals=missing_vitals,
        recommended_deferral_type=recommended_deferral_type,
        supervisor_review_required=supervisor_review_required,
        summary="Eligibility preview is explainable and ready for result review." if not blocking_issues else "Eligibility preview found missing required screening data.",
        existing_engine_outcome=existing_engine_outcome,
        changes=changes,
    )


def append_status_history(
    session: ClinicalScreeningSession,
    *,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    session.status_history.append(
        ClinicalScreeningStatusHistory(
            session_id=session.session_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=user_id,
            reason=reason,
            notes=notes,
        )
    )


def append_screening_workflow_audit(
    *,
    workflow: str,
    session: ClinicalScreeningSession,
    actor: str,
    preview_value: str,
    status_before: str | None,
    status_after: str | None,
    reason: str,
    changes: dict[str, Any],
) -> tuple[WorkflowOperation, str]:
    operation = WorkflowOperation(
        workflow=workflow,
        entity_type="screening_session",
        entity_id=session.session_number,
        actor=actor,
        preview_hash=preview_value,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        changes=changes,
    )
    operation, audit_path = append_workflow_operation(operation)
    return operation, str(audit_path)


def commit_answers(
    session: ClinicalScreeningSession,
    answers: dict[str, Any],
    *,
    user_id: int | None,
    notes: str = "",
) -> None:
    existing = {answer.question_key: answer for answer in session.answers}
    timestamp = now_utc()
    for key, value in answers.items():
        payload = {"value": value}
        if key in existing:
            existing[key].answer_value = payload
            existing[key].notes = notes
            existing[key].updated_by = user_id
            existing[key].updated_at = timestamp
        else:
            session.answers.append(
                ClinicalScreeningAnswer(
                    session_id=session.session_id,
                    question_key=key,
                    answer_value=payload,
                    notes=notes,
                    created_by=user_id,
                    updated_by=user_id,
                )
            )


def update_session_status(
    session: ClinicalScreeningSession,
    *,
    next_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> tuple[str, str]:
    status_before = session.status
    if status_before != next_status:
        session.status = next_status
        append_status_history(
            session,
            from_status=status_before,
            to_status=next_status,
            user_id=user_id,
            reason=reason,
            notes=notes,
        )
    session.updated_by = user_id
    session.version += 1
    return status_before, session.status


def create_deferral_for_outcome(
    session: ClinicalScreeningSession,
    *,
    outcome: str,
    reason: str,
    user_id: int | None,
    deferral_type: str | None = None,
    ends_at: datetime | None = None,
) -> ClinicalDeferral | None:
    if outcome not in {"temporarily_deferred", "permanently_deferred"}:
        return None
    resolved_type = deferral_type or ("temporary" if outcome == "temporarily_deferred" else "permanent")
    deferral = ClinicalDeferral(
        deferral_number=new_deferral_number(),
        session_id=session.session_id,
        patient_pk=session.patient_pk,
        donor_pk=session.donor_pk,
        deferral_type=resolved_type,
        reason=reason,
        ends_at=ends_at if resolved_type == "temporary" else None,
        status="active",
        created_by=user_id,
    )
    session.deferrals.append(deferral)
    return deferral


def screening_actor(user: User) -> str:
    return actor_label(user)


def list_screening_templates() -> list[ScreeningTemplateResponse]:
    return [MINIMAL_SCREENING_TEMPLATE]


def list_screening_rules() -> list[EligibilityRuleResult]:
    return [
        EligibilityRuleResult(
            rule_name="Required questionnaire answers",
            rule_category="Completeness",
            outcome="requires_supervisor_review",
            severity="High",
            requires_review=True,
            explanation="All required screening questions must be answered before result commit.",
        ),
        EligibilityRuleResult(
            rule_name="Required vitals",
            rule_category="Completeness",
            outcome="requires_supervisor_review",
            severity="High",
            requires_review=True,
            explanation="Weight, temperature, blood pressure, and pulse are required before result commit.",
        ),
        EligibilityRuleResult(
            rule_name="Deferral risk answers",
            rule_category="Medical Social History",
            outcome="temporarily_deferred",
            severity="High",
            requires_review=True,
            explanation="Current infectious symptoms or travel exposure recommend temporary deferral; permanent risk disclosures recommend permanent deferral.",
        ),
    ]
