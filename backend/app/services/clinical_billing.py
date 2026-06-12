from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ClinicalBillingAccount,
    ClinicalBillingStatusHistory,
    ClinicalCarePlan,
    ClinicalCarePlanTask,
    ClinicalCharge,
    ClinicalClaim,
    ClinicalClaimLine,
    ClinicalDenial,
    ClinicalEncounter,
    ClinicalInsuranceVerification,
    ClinicalOrder,
    ClinicalOrderResult,
    ClinicalPayment,
    Patient,
    PatientInsurance,
    User,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_billing import (
    BillingBlockingIssue,
    BillingPreviewResponse,
    BillingWarning,
    ChargeCapturePreviewRequest,
    ClaimDraftPreviewRequest,
    DenialCapturePreviewRequest,
    InsuranceVerificationPreviewRequest,
    PaymentPostPreviewRequest,
)
from app.services.clinical_patients import actor_label
from app.services.clinical_workflows import append_workflow_operation, preview_hash

VOID_CHARGE_STATUSES = {"voided", "cancelled"}
PAID_CLAIM_STATUSES = {"paid", "closed"}


def now_utc() -> datetime:
    return datetime.now(UTC)


def round_money(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def new_account_number() -> str:
    return f"BA-{uuid4().hex[:10].upper()}"


def new_charge_number() -> str:
    return f"CHG-{uuid4().hex[:10].upper()}"


def new_claim_number() -> str:
    return f"CLM-{uuid4().hex[:10].upper()}"


def billing_actor(user: User) -> str:
    return actor_label(user)


def _one_or_none(db: Session, statement) -> Any | None:
    return db.execute(statement).scalar_one_or_none()


def patient_by_identifier(db: Session, patient_id: str) -> Patient | None:
    return _one_or_none(db, select(Patient).where(Patient.patient_id == patient_id, Patient.is_deleted.is_(False)))


def patient_insurance_by_id(db: Session, insurance_id: int | None) -> PatientInsurance | None:
    if insurance_id is None:
        return None
    return _one_or_none(
        db,
        select(PatientInsurance).where(
            PatientInsurance.insurance_id == insurance_id,
            PatientInsurance.is_deleted.is_(False),
        ),
    )


def encounter_by_id(db: Session, encounter_id: int | None) -> ClinicalEncounter | None:
    if encounter_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalEncounter).where(
            ClinicalEncounter.encounter_id == encounter_id,
            ClinicalEncounter.is_deleted.is_(False),
        ),
    )


def order_by_id(db: Session, order_id: int | None) -> ClinicalOrder | None:
    if order_id is None:
        return None
    return _one_or_none(db, select(ClinicalOrder).where(ClinicalOrder.order_id == order_id, ClinicalOrder.is_deleted.is_(False)))


def order_result_by_id(db: Session, result_id: int | None) -> ClinicalOrderResult | None:
    if result_id is None:
        return None
    return _one_or_none(db, select(ClinicalOrderResult).where(ClinicalOrderResult.result_id == result_id))


def care_plan_by_id(db: Session, care_plan_id: int | None) -> ClinicalCarePlan | None:
    if care_plan_id is None:
        return None
    return _one_or_none(
        db,
        select(ClinicalCarePlan).where(
            ClinicalCarePlan.care_plan_id == care_plan_id,
            ClinicalCarePlan.is_deleted.is_(False),
        ),
    )


def care_plan_task_by_id(db: Session, task_id: int | None) -> ClinicalCarePlanTask | None:
    if task_id is None:
        return None
    return _one_or_none(db, select(ClinicalCarePlanTask).where(ClinicalCarePlanTask.task_id == task_id))


def billing_account_by_id(db: Session, account_id: int) -> ClinicalBillingAccount | None:
    return _one_or_none(
        db,
        select(ClinicalBillingAccount).where(
            ClinicalBillingAccount.account_id == account_id,
            ClinicalBillingAccount.is_deleted.is_(False),
        ),
    )


def first_billing_account_for_patient(db: Session, patient: Patient) -> ClinicalBillingAccount | None:
    return _one_or_none(
        db,
        select(ClinicalBillingAccount)
        .where(
            ClinicalBillingAccount.patient_pk == patient.patient_pk,
            ClinicalBillingAccount.is_deleted.is_(False),
        )
        .order_by(ClinicalBillingAccount.updated_at.desc()),
    )


def charge_by_id(db: Session, charge_id: int) -> ClinicalCharge | None:
    return _one_or_none(
        db,
        select(ClinicalCharge).where(ClinicalCharge.charge_id == charge_id, ClinicalCharge.is_deleted.is_(False)),
    )


def claim_by_id(db: Session, claim_id: int) -> ClinicalClaim | None:
    return _one_or_none(
        db,
        select(ClinicalClaim).where(ClinicalClaim.claim_id == claim_id, ClinicalClaim.is_deleted.is_(False)),
    )


def claim_line_by_id(db: Session, line_id: int | None) -> ClinicalClaimLine | None:
    if line_id is None:
        return None
    return _one_or_none(db, select(ClinicalClaimLine).where(ClinicalClaimLine.line_id == line_id))


def _issue(issue_type: str, field: str, message: str) -> BillingBlockingIssue:
    return BillingBlockingIssue(issue_type=issue_type, field=field, message=message)


def _warning(warning_type: str, field: str, message: str) -> BillingWarning:
    return BillingWarning(warning_type=warning_type, field=field, message=message)


def _preview(
    *,
    workflow: str,
    entity_type: str,
    entity_id: str,
    changes: dict[str, Any],
    blocking_issues: list[BillingBlockingIssue] | None = None,
    warnings: list[BillingWarning] | None = None,
    summary: str,
) -> BillingPreviewResponse:
    issues = blocking_issues or []
    warning_rows = warnings or []
    return BillingPreviewResponse(
        workflow=workflow,
        entity_type=entity_type,
        entity_id=entity_id,
        preview_hash=preview_hash({"workflow": workflow, "entity_type": entity_type, "entity_id": entity_id, "changes": changes}),
        validation_status="failed" if issues else "warning" if warning_rows else "passed",
        blocking_issues=issues,
        warnings=warning_rows,
        summary=summary,
        changes=changes,
    )


def patient_context(patient: Patient | None) -> dict[str, Any]:
    if not patient:
        return {"patient_pk": None, "patient_id": None, "patient_name": None}
    return {
        "patient_pk": patient.patient_pk,
        "patient_id": patient.patient_id,
        "patient_name": " ".join(part for part in [patient.first_name, patient.middle_name, patient.last_name] if part),
    }


def insurance_context(insurance: PatientInsurance | None) -> dict[str, Any]:
    if not insurance:
        return {
            "patient_insurance_id": None,
            "payer_name": None,
            "plan_name": None,
            "member_id": None,
            "group_number": None,
            "eligibility_status": None,
        }
    return {
        "patient_insurance_id": insurance.insurance_id,
        "payer_name": insurance.payer_name,
        "plan_name": insurance.plan_type,
        "member_id": insurance.member_id,
        "group_number": insurance.group_number,
        "eligibility_status": insurance.eligibility_status,
    }


def append_billing_status_history(
    *,
    billing_account: ClinicalBillingAccount | None = None,
    claim: ClinicalClaim | None = None,
    charge: ClinicalCharge | None = None,
    from_status: str | None,
    to_status: str,
    user_id: int | None,
    reason: str,
    notes: str = "",
) -> None:
    history = ClinicalBillingStatusHistory(
        billing_account_id=billing_account.account_id if billing_account else None,
        claim_id=claim.claim_id if claim else None,
        charge_id=charge.charge_id if charge else None,
        from_status=from_status,
        to_status=to_status,
        changed_by=user_id,
        reason=reason,
        notes=notes,
    )
    if claim is not None:
        claim.status_history.append(history)
    elif charge is not None:
        charge.status_history.append(history)
    elif billing_account is not None:
        billing_account.status_history.append(history)


def ensure_billing_account(
    db: Session,
    patient: Patient,
    *,
    insurance: PatientInsurance | None = None,
    user_id: int | None,
) -> ClinicalBillingAccount:
    account = first_billing_account_for_patient(db, patient)
    if account:
        if insurance and account.primary_insurance_id is None:
            account.primary_insurance_id = insurance.insurance_id
            account.primary_insurance = insurance
            account.updated_by = user_id
        return account
    account = ClinicalBillingAccount(
        account_number=new_account_number(),
        patient_pk=patient.patient_pk,
        patient=patient,
        primary_insurance_id=insurance.insurance_id if insurance else None,
        primary_insurance=insurance,
        status="open",
        total_charges=0,
        total_payments=0,
        total_adjustments=0,
        balance=0,
        created_by=user_id,
        updated_by=user_id,
    )
    append_billing_status_history(
        billing_account=account,
        from_status=None,
        to_status="open",
        user_id=user_id,
        reason="Billing account opened",
        notes="Created automatically for billing workflow",
    )
    db.add(account)
    db.flush()
    return account


def recalculate_account(account: ClinicalBillingAccount) -> None:
    active_charges = [charge for charge in account.charges if charge.status not in VOID_CHARGE_STATUSES and not charge.is_deleted]
    account.total_charges = round_money(sum(charge.total_amount for charge in active_charges))
    account.total_payments = round_money(sum(payment.payment_amount for payment in account.payments))
    account.total_adjustments = round_money(sum(payment.adjustment_amount for payment in account.payments))
    account.balance = round_money(account.total_charges - account.total_payments - account.total_adjustments)
    if account.balance <= 0 and account.total_charges > 0:
        account.status = "closed"
    elif account.total_charges > 0:
        account.status = "open"


def append_billing_workflow_audit(
    *,
    workflow: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    preview_value: str,
    status_before: str | None,
    status_after: str | None,
    reason: str,
    changes: dict[str, Any],
) -> tuple[WorkflowOperation, str]:
    operation = WorkflowOperation(
        workflow=workflow,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        preview_hash=preview_value,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        changes=changes,
    )
    operation, audit_path = append_workflow_operation(operation)
    return operation, str(audit_path)


def insurance_verification_preview(db: Session, payload: InsuranceVerificationPreviewRequest) -> BillingPreviewResponse:
    patient = patient_by_identifier(db, payload.patient_id)
    insurance = patient_insurance_by_id(db, payload.patient_insurance_id)
    issues: list[BillingBlockingIssue] = []
    warnings: list[BillingWarning] = []
    if not patient:
        issues.append(_issue("unknown_patient", "patient_id", "Patient/donor profile was not found."))
    if payload.patient_insurance_id is not None and not insurance:
        issues.append(_issue("unknown_insurance", "patient_insurance_id", "Patient insurance record was not found."))
    if patient and insurance and insurance.patient_pk != patient.patient_pk:
        issues.append(_issue("insurance_patient_mismatch", "patient_insurance_id", "Insurance belongs to a different patient/donor."))
    if patient and not insurance:
        warnings.append(_warning("manual_insurance_context", "patient_insurance_id", "Verification will use payer details supplied in this workflow."))
    changes = payload.model_dump(mode="json")
    changes["patient"] = patient_context(patient)
    changes["insurance"] = insurance_context(insurance)
    return _preview(
        workflow="billing.insurance_verify",
        entity_type="clinical_insurance_verification",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Insurance verification is ready to commit." if not issues else "Insurance verification preview found blocking issues.",
    )


def charge_capture_preview(db: Session, payload: ChargeCapturePreviewRequest) -> BillingPreviewResponse:
    patient = patient_by_identifier(db, payload.patient_id)
    encounter = encounter_by_id(db, payload.encounter_id)
    order = order_by_id(db, payload.order_id)
    result = order_result_by_id(db, payload.order_result_id)
    care_plan = care_plan_by_id(db, payload.care_plan_id)
    task = care_plan_task_by_id(db, payload.care_plan_task_id)
    issues: list[BillingBlockingIssue] = []
    warnings: list[BillingWarning] = []
    if not patient:
        issues.append(_issue("unknown_patient", "patient_id", "Patient/donor profile was not found."))
    if payload.encounter_id is not None and not encounter:
        issues.append(_issue("unknown_encounter", "encounter_id", "Encounter was not found."))
    if payload.order_id is not None and not order:
        issues.append(_issue("unknown_order", "order_id", "Order was not found."))
    if payload.order_result_id is not None and not result:
        issues.append(_issue("unknown_order_result", "order_result_id", "Order result was not found."))
    if payload.care_plan_id is not None and not care_plan:
        issues.append(_issue("unknown_care_plan", "care_plan_id", "Care plan was not found."))
    if payload.care_plan_task_id is not None and not task:
        issues.append(_issue("unknown_care_plan_task", "care_plan_task_id", "Care plan task was not found."))
    for field, value in [
        ("encounter_id", encounter),
        ("order_id", order),
        ("care_plan_id", care_plan),
    ]:
        if patient and value and value.patient_pk != patient.patient_pk:
            issues.append(_issue(f"{field}_patient_mismatch", field, "Linked billing context belongs to a different patient/donor."))
    if patient and task and task.care_plan and task.care_plan.patient_pk != patient.patient_pk:
        issues.append(_issue("care_plan_task_patient_mismatch", "care_plan_task_id", "Care plan task belongs to a different patient/donor."))
    if result and order is None:
        issues.append(_issue("order_required_for_result", "order_id", "Link an order when linking an order result."))
    if result and order and result.order_id != order.order_id:
        issues.append(_issue("order_result_mismatch", "order_result_id", "Order result does not belong to the linked order."))
    if encounter and encounter.status not in {"signed", "amended"}:
        warnings.append(_warning("encounter_not_signed", "encounter_id", "Signed or amended encounters are preferred for charge capture."))
    if order and order.status != "resulted":
        warnings.append(_warning("order_not_resulted", "order_id", "Resulted orders are preferred for charge capture."))
    total = round_money(payload.quantity * payload.unit_amount)
    changes = payload.model_dump(mode="json")
    changes["total_amount"] = total
    changes["patient"] = patient_context(patient)
    changes["context"] = {
        "encounter_number": encounter.encounter_number if encounter else None,
        "order_number": order.order_number if order else None,
        "order_result": f"{result.result_name}: {result.result_value}" if result else None,
        "care_plan_number": care_plan.care_plan_number if care_plan else None,
        "care_plan_task_title": task.title if task else None,
    }
    return _preview(
        workflow="billing.charge_capture",
        entity_type="clinical_charge",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Charge is ready to capture." if not issues else "Charge preview found blocking issues.",
    )


def claim_draft_preview(db: Session, payload: ClaimDraftPreviewRequest) -> BillingPreviewResponse:
    charges = [charge_by_id(db, charge_id) for charge_id in payload.charge_ids]
    charges = [charge for charge in charges if charge is not None]
    issues: list[BillingBlockingIssue] = []
    warnings: list[BillingWarning] = []
    missing = sorted(set(payload.charge_ids) - {charge.charge_id for charge in charges})
    for charge_id in missing:
        issues.append(_issue("unknown_charge", "charge_ids", f"Charge {charge_id} was not found."))
    if not charges:
        issues.append(_issue("no_charges", "charge_ids", "At least one eligible charge is required."))
    patient_pks = {charge.patient_pk for charge in charges}
    if len(patient_pks) > 1:
        issues.append(_issue("mixed_patients", "charge_ids", "All claim charges must belong to the same patient/donor."))
    if payload.patient_id:
        patient = patient_by_identifier(db, payload.patient_id)
        if not patient:
            issues.append(_issue("unknown_patient", "patient_id", "Patient/donor profile was not found."))
        elif charges and any(charge.patient_pk != patient.patient_pk for charge in charges):
            issues.append(_issue("charge_patient_mismatch", "patient_id", "Selected charges do not belong to the supplied patient/donor."))
    else:
        patient = charges[0].patient if charges else None
    for charge in charges:
        if charge.status in VOID_CHARGE_STATUSES:
            issues.append(_issue("charge_not_claimable", "charge_ids", f"Charge {charge.charge_number} is {charge.status} and cannot be claimed."))
        if charge.claim_lines:
            warnings.append(_warning("charge_already_on_claim", "charge_ids", f"Charge {charge.charge_number} already has claim line history."))
    account = charges[0].billing_account if charges else None
    insurance = patient_insurance_by_id(db, payload.patient_insurance_id)
    if payload.patient_insurance_id is not None and not insurance:
        issues.append(_issue("unknown_insurance", "patient_insurance_id", "Patient insurance record was not found."))
    if patient and insurance and insurance.patient_pk != patient.patient_pk:
        issues.append(_issue("insurance_patient_mismatch", "patient_insurance_id", "Insurance belongs to a different patient/donor."))
    if not insurance and account and account.primary_insurance:
        insurance = account.primary_insurance
    if not insurance:
        warnings.append(_warning("no_verified_payer", "patient_insurance_id", "Claim can be drafted without payer verification, but review is required."))
    line_items = [
        {
            "charge_id": charge.charge_id,
            "charge_number": charge.charge_number,
            "code": charge.code,
            "code_type": charge.code_type,
            "description": charge.description,
            "quantity": charge.quantity,
            "unit_amount": charge.unit_amount,
            "line_amount": round_money(charge.total_amount),
        }
        for charge in charges
    ]
    total = round_money(sum(line["line_amount"] for line in line_items))
    changes = payload.model_dump(mode="json")
    changes.update(
        {
            "patient": patient_context(patient),
            "insurance": insurance_context(insurance),
            "billing_account_id": account.account_id if account else None,
            "account_number": account.account_number if account else None,
            "line_items": line_items,
            "total_amount": total,
            "balance": total,
        }
    )
    return _preview(
        workflow="billing.claim_create",
        entity_type="clinical_claim",
        entity_id="draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Claim draft is ready to create." if not issues else "Claim preview found blocking issues.",
    )


def payment_post_preview(db: Session, payload: PaymentPostPreviewRequest) -> BillingPreviewResponse:
    claim = claim_by_id(db, payload.claim_id)
    issues: list[BillingBlockingIssue] = []
    warnings: list[BillingWarning] = []
    if not claim:
        issues.append(_issue("unknown_claim", "claim_id", "Claim was not found."))
    elif claim.status in PAID_CLAIM_STATUSES:
        warnings.append(_warning("claim_already_closed", "claim_id", "Claim is already paid or closed."))
    amount = round_money(payload.payment_amount + payload.adjustment_amount)
    if claim and amount > round_money(claim.balance):
        issues.append(_issue("payment_exceeds_balance", "payment_amount", "Payment plus adjustment exceeds claim balance."))
    next_balance = round_money((claim.balance if claim else 0) - amount)
    changes = payload.model_dump(mode="json")
    changes.update(
        {
            "claim_number": claim.claim_number if claim else None,
            "account_number": claim.account_number if claim else None,
            "patient": patient_context(claim.patient if claim else None),
            "status_before": claim.status if claim else None,
            "balance_before": claim.balance if claim else None,
            "balance_after": next_balance if claim else None,
        }
    )
    return _preview(
        workflow="billing.payment_post",
        entity_type="clinical_payment",
        entity_id=claim.claim_number if claim else "draft",
        changes=changes,
        blocking_issues=issues,
        warnings=warnings,
        summary="Payment is ready to post." if not issues else "Payment preview found blocking issues.",
    )


def denial_capture_preview(db: Session, payload: DenialCapturePreviewRequest) -> BillingPreviewResponse:
    claim = claim_by_id(db, payload.claim_id)
    claim_line = claim_line_by_id(db, payload.claim_line_id)
    issues: list[BillingBlockingIssue] = []
    if not claim:
        issues.append(_issue("unknown_claim", "claim_id", "Claim was not found."))
    if payload.claim_line_id is not None and not claim_line:
        issues.append(_issue("unknown_claim_line", "claim_line_id", "Claim line was not found."))
    if claim and claim_line and claim_line.claim_id != claim.claim_id:
        issues.append(_issue("claim_line_mismatch", "claim_line_id", "Claim line does not belong to the supplied claim."))
    changes = payload.model_dump(mode="json")
    changes.update(
        {
            "claim_number": claim.claim_number if claim else None,
            "claim_status_before": claim.status if claim else None,
            "line_number": claim_line.line_number if claim_line else None,
        }
    )
    return _preview(
        workflow="billing.denial_capture",
        entity_type="clinical_denial",
        entity_id=claim.claim_number if claim else "draft",
        changes=changes,
        blocking_issues=issues,
        summary="Denial is ready to capture." if not issues else "Denial preview found blocking issues.",
    )


def charge_changes(charge: ClinicalCharge) -> dict[str, Any]:
    return {
        "charge_id": charge.charge_id,
        "charge_number": charge.charge_number,
        "billing_account_id": charge.billing_account_id,
        "patient_id": charge.patient_id,
        "encounter_id": charge.encounter_id,
        "order_id": charge.order_id,
        "order_result_id": charge.order_result_id,
        "care_plan_id": charge.care_plan_id,
        "care_plan_task_id": charge.care_plan_task_id,
        "service_date": charge.service_date.isoformat(),
        "code": charge.code,
        "code_type": charge.code_type,
        "description": charge.description,
        "quantity": charge.quantity,
        "unit_amount": charge.unit_amount,
        "total_amount": charge.total_amount,
        "status": charge.status,
    }


def claim_changes(claim: ClinicalClaim) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "claim_number": claim.claim_number,
        "billing_account_id": claim.billing_account_id,
        "patient_id": claim.patient_id,
        "patient_insurance_id": claim.patient_insurance_id,
        "status": claim.status,
        "total_amount": claim.total_amount,
        "paid_amount": claim.paid_amount,
        "adjustment_amount": claim.adjustment_amount,
        "balance": claim.balance,
        "lines": [
            {
                "line_id": line.line_id,
                "charge_id": line.charge_id,
                "line_number": line.line_number,
                "code": line.code,
                "line_amount": line.line_amount,
            }
            for line in claim.lines
        ],
    }


def payment_changes(payment: ClinicalPayment, claim: ClinicalClaim) -> dict[str, Any]:
    return {
        "payment_id": payment.payment_id,
        "claim_id": payment.claim_id,
        "claim_number": claim.claim_number,
        "billing_account_id": payment.billing_account_id,
        "payment_amount": payment.payment_amount,
        "adjustment_amount": payment.adjustment_amount,
        "payment_method": payment.payment_method,
        "payer_type": payment.payer_type,
        "reference_number": payment.reference_number,
        "claim_balance": claim.balance,
        "claim_status": claim.status,
    }


def denial_changes(denial: ClinicalDenial, claim: ClinicalClaim) -> dict[str, Any]:
    return {
        "denial_id": denial.denial_id,
        "claim_id": denial.claim_id,
        "claim_number": claim.claim_number,
        "claim_line_id": denial.claim_line_id,
        "denial_code": denial.denial_code,
        "denial_reason": denial.denial_reason,
        "status": denial.status,
        "assigned_to": denial.assigned_to,
        "due_date": denial.due_date.isoformat() if denial.due_date else None,
    }


def verification_changes(verification: ClinicalInsuranceVerification) -> dict[str, Any]:
    return {
        "verification_id": verification.verification_id,
        "patient_id": verification.patient_id,
        "patient_insurance_id": verification.patient_insurance_id,
        "verification_status": verification.verification_status,
        "payer_name": verification.payer_name,
        "plan_name": verification.plan_name,
        "member_id": verification.member_id,
        "group_number": verification.group_number,
        "coverage_start": verification.coverage_start.isoformat() if verification.coverage_start else None,
        "coverage_end": verification.coverage_end.isoformat() if verification.coverage_end else None,
    }
