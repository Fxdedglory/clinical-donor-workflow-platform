from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import (
    ClinicalBillingAccount,
    ClinicalCharge,
    ClinicalClaim,
    ClinicalClaimLine,
    ClinicalDenial,
    ClinicalInsuranceVerification,
    ClinicalPayment,
    Patient,
    PatientInsurance,
    User,
)
from app.schemas.clinical_billing import (
    BillingAccountResponse,
    BillingCommitResponse,
    BillingListResponse,
    BillingPreviewResponse,
    BillingWorkQueueResponse,
    ChargeCaptureCommitRequest,
    ChargeCapturePreviewRequest,
    ChargeListResponse,
    ClaimDraftCommitRequest,
    ClaimDraftPreviewRequest,
    ClaimListResponse,
    ClaimResponse,
    DenialCaptureCommitRequest,
    DenialCapturePreviewRequest,
    InsuranceVerificationCommitRequest,
    InsuranceVerificationPreviewRequest,
    PaymentPostCommitRequest,
    PaymentPostPreviewRequest,
)
from app.services.clinical_billing import (
    append_billing_status_history,
    append_billing_workflow_audit,
    billing_account_by_id,
    billing_actor,
    care_plan_by_id,
    care_plan_task_by_id,
    charge_by_id,
    charge_capture_preview,
    charge_changes,
    claim_by_id,
    claim_changes,
    claim_draft_preview,
    claim_line_by_id,
    denial_capture_preview,
    denial_changes,
    encounter_by_id,
    ensure_billing_account,
    insurance_verification_preview,
    new_charge_number,
    new_claim_number,
    now_utc,
    order_by_id,
    order_result_by_id,
    patient_by_identifier,
    patient_insurance_by_id,
    payment_changes,
    payment_post_preview,
    recalculate_account,
    round_money,
    verification_changes,
)
from app.services.clinical_workflows import require_generation_confirmation

router = APIRouter(prefix="/api/clinical/billing", tags=["Clinical Billing"])

READ_PERMISSIONS = {"system.admin", "billing.read", "billing.manage", "patients.read"}
MUTATION_PERMISSIONS = {"system.admin", "billing.manage"}
PAYMENT_PERMISSIONS = {"system.admin", "billing.manage", "billing.payment_post"}
EXTERNAL_ROLES = {"Partner External User", "Supplier External User"}


def _is_external_user(user: User) -> bool:
    return bool(
        user.is_external
        or user.external_user_flag
        or user.account_type in {"partner", "supplier", "external"}
        or user.user_type in {"partner", "supplier", "external"}
        or user.role in EXTERNAL_ROLES
    )


def _permission_set(db: Session, user: User) -> set[str]:
    return set(getattr(user, "permissions", []) or []) | set(get_user_permissions(db, user))


def require_billing_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot access billing")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(READ_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Billing read permission required")
    return current_user


def require_billing_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot mutate billing")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(MUTATION_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Billing mutation permission required")
    return current_user


def require_payment_mutation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if _is_external_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="External users cannot post billing payments")
    permissions = _permission_set(db, current_user)
    if permissions.isdisjoint(PAYMENT_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Billing payment permission required")
    return current_user


def _reject_blocking(preview: BillingPreviewResponse) -> None:
    if preview.blocking_issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "billing_validation_failed",
                "message": "Blocking billing issues prevent commit.",
                "blocking_issues": [issue.model_dump(mode="json") for issue in preview.blocking_issues],
            },
        )


def _patient_primary_insurance(patient: Patient) -> PatientInsurance | None:
    active = [insurance for insurance in patient.insurance_profiles if not insurance.is_deleted and insurance.status == "active"]
    primary = next((insurance for insurance in active if insurance.priority == "primary"), None)
    return primary or (active[0] if active else None)


@router.get("/accounts", response_model=BillingListResponse)
def list_billing_accounts(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    patient_id: str | None = Query(default=None),
    payer: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_billing_read),
    db: Session = Depends(get_db),
) -> BillingListResponse:
    query = select(ClinicalBillingAccount).where(ClinicalBillingAccount.is_deleted.is_(False))
    joined_patient = False
    joined_insurance = False
    if status_filter:
        query = query.where(ClinicalBillingAccount.status == status_filter)
    if patient_id:
        query = query.join(Patient)
        joined_patient = True
        query = query.where(Patient.patient_id == patient_id)
    if payer:
        query = query.join(PatientInsurance, ClinicalBillingAccount.primary_insurance_id == PatientInsurance.insurance_id)
        joined_insurance = True
        query = query.where(func.lower(PatientInsurance.payer_name).like(f"%{payer.strip().lower()}%"))
    if date_filter:
        start_of_day = datetime.combine(date_filter, time.min)
        end_of_day = datetime.combine(date_filter, time.max)
        query = query.where(ClinicalBillingAccount.created_at >= start_of_day, ClinicalBillingAccount.created_at <= end_of_day)
    if q:
        like = f"%{q.strip().lower()}%"
        if not joined_patient:
            query = query.join(Patient)
        if not joined_insurance:
            query = query.outerjoin(PatientInsurance, ClinicalBillingAccount.primary_insurance_id == PatientInsurance.insurance_id)
        query = query.where(
            or_(
                func.lower(ClinicalBillingAccount.account_number).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
                func.lower(PatientInsurance.payer_name).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalBillingAccount.updated_at.desc())).scalars().all())
    return BillingListResponse(accounts=rows[offset : offset + limit], total=len(rows))


@router.get("/accounts/{account_id}", response_model=BillingAccountResponse)
def get_billing_account(
    account_id: int,
    current_user: User = Depends(require_billing_read),
    db: Session = Depends(get_db),
) -> ClinicalBillingAccount:
    account = billing_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing account not found")
    return account


@router.get("/charges", response_model=ChargeListResponse)
def list_charges(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    patient_id: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_billing_read),
    db: Session = Depends(get_db),
) -> ChargeListResponse:
    query = select(ClinicalCharge).where(ClinicalCharge.is_deleted.is_(False))
    joined_patient = False
    if status_filter:
        query = query.where(ClinicalCharge.status == status_filter)
    if patient_id:
        query = query.join(Patient)
        joined_patient = True
        query = query.where(Patient.patient_id == patient_id)
    if date_filter:
        query = query.where(ClinicalCharge.service_date == date_filter)
    if q:
        like = f"%{q.strip().lower()}%"
        if not joined_patient:
            query = query.join(Patient)
        query = query.where(
            or_(
                func.lower(ClinicalCharge.charge_number).like(like),
                func.lower(ClinicalCharge.code).like(like),
                func.lower(ClinicalCharge.description).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalCharge.created_at.desc())).scalars().all())
    return ChargeListResponse(charges=rows[offset : offset + limit], total=len(rows))


@router.post("/charges/preview", response_model=BillingPreviewResponse)
def preview_capture_charge(
    payload: ChargeCapturePreviewRequest,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingPreviewResponse:
    return charge_capture_preview(db, payload)


@router.post("/charges", response_model=BillingCommitResponse, status_code=status.HTTP_201_CREATED)
def capture_charge(
    payload: ChargeCaptureCommitRequest,
    request: Request,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingCommitResponse:
    require_generation_confirmation(request)
    preview = charge_capture_preview(db, payload)
    _reject_blocking(preview)
    patient = patient_by_identifier(db, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Billing patient context changed after preview")
    insurance = _patient_primary_insurance(patient)
    account = ensure_billing_account(db, patient, insurance=insurance, user_id=current_user.user_id)
    charge = ClinicalCharge(
        charge_number=new_charge_number(),
        billing_account_id=account.account_id,
        billing_account=account,
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_id=payload.encounter_id,
        encounter=encounter_by_id(db, payload.encounter_id),
        order_id=payload.order_id,
        order=order_by_id(db, payload.order_id),
        order_result_id=payload.order_result_id,
        order_result=order_result_by_id(db, payload.order_result_id),
        care_plan_id=payload.care_plan_id,
        care_plan=care_plan_by_id(db, payload.care_plan_id),
        care_plan_task_id=payload.care_plan_task_id,
        care_plan_task=care_plan_task_by_id(db, payload.care_plan_task_id),
        service_date=payload.service_date,
        code=payload.code,
        code_type=payload.code_type,
        description=payload.description,
        quantity=payload.quantity,
        unit_amount=payload.unit_amount,
        total_amount=round_money(payload.quantity * payload.unit_amount),
        status=payload.status,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    if charge not in account.charges:
        account.charges.append(charge)
    append_billing_status_history(
        charge=charge,
        from_status=None,
        to_status=payload.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Charge captured",
    )
    recalculate_account(account)
    db.flush()
    db.commit()
    db.refresh(charge)
    operation, audit_path = append_billing_workflow_audit(
        workflow="billing.charge_capture",
        entity_type="clinical_charge",
        entity_id=charge.charge_number,
        actor=billing_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=charge.status,
        reason=payload.reason,
        changes=charge_changes(charge),
    )
    return BillingCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, account=account, charge=charge)


@router.get("/claims", response_model=ClaimListResponse)
def list_claims(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    patient_id: str | None = Query(default=None),
    payer: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_billing_read),
    db: Session = Depends(get_db),
) -> ClaimListResponse:
    query = select(ClinicalClaim).where(ClinicalClaim.is_deleted.is_(False))
    joined_patient = False
    joined_insurance = False
    if status_filter:
        query = query.where(ClinicalClaim.status == status_filter)
    if patient_id:
        query = query.join(Patient)
        joined_patient = True
        query = query.where(Patient.patient_id == patient_id)
    if payer:
        query = query.join(PatientInsurance, ClinicalClaim.patient_insurance_id == PatientInsurance.insurance_id)
        joined_insurance = True
        query = query.where(func.lower(PatientInsurance.payer_name).like(f"%{payer.strip().lower()}%"))
    if q:
        like = f"%{q.strip().lower()}%"
        if not joined_patient:
            query = query.join(Patient)
        if not joined_insurance:
            query = query.outerjoin(PatientInsurance, ClinicalClaim.patient_insurance_id == PatientInsurance.insurance_id)
        query = query.where(
            or_(
                func.lower(ClinicalClaim.claim_number).like(like),
                func.lower(Patient.patient_id).like(like),
                func.lower(Patient.first_name).like(like),
                func.lower(Patient.last_name).like(like),
                func.lower(PatientInsurance.payer_name).like(like),
            )
        )
    rows = list(db.execute(query.order_by(ClinicalClaim.updated_at.desc())).scalars().all())
    return ClaimListResponse(claims=rows[offset : offset + limit], total=len(rows))


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: int,
    current_user: User = Depends(require_billing_read),
    db: Session = Depends(get_db),
) -> ClinicalClaim:
    claim = claim_by_id(db, claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.post("/claims/preview", response_model=BillingPreviewResponse)
def preview_create_claim(
    payload: ClaimDraftPreviewRequest,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingPreviewResponse:
    return claim_draft_preview(db, payload)


@router.post("/claims", response_model=BillingCommitResponse, status_code=status.HTTP_201_CREATED)
def create_claim(
    payload: ClaimDraftCommitRequest,
    request: Request,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingCommitResponse:
    require_generation_confirmation(request)
    preview = claim_draft_preview(db, payload)
    _reject_blocking(preview)
    charges = [charge_by_id(db, charge_id) for charge_id in payload.charge_ids]
    charges = [charge for charge in charges if charge is not None]
    if not charges:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Claim charges changed after preview")
    patient = charges[0].patient
    account = charges[0].billing_account
    insurance = patient_insurance_by_id(db, payload.patient_insurance_id) or account.primary_insurance
    total = round_money(sum(charge.total_amount for charge in charges))
    claim = ClinicalClaim(
        claim_number=new_claim_number(),
        billing_account_id=account.account_id,
        billing_account=account,
        patient_pk=patient.patient_pk,
        patient=patient,
        patient_insurance_id=insurance.insurance_id if insurance else None,
        patient_insurance=insurance,
        status=payload.status,
        total_amount=total,
        paid_amount=0,
        adjustment_amount=0,
        balance=total,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    for index, charge in enumerate(charges, start=1):
        claim.lines.append(
            ClinicalClaimLine(
                charge_id=charge.charge_id,
                charge=charge,
                line_number=index,
                code=charge.code,
                code_type=charge.code_type,
                description=charge.description,
                quantity=charge.quantity,
                unit_amount=charge.unit_amount,
                line_amount=round_money(charge.total_amount),
                diagnosis_code=payload.diagnosis_code,
                status=payload.status,
                created_by=current_user.user_id,
            )
        )
        before = charge.status
        charge.status = "claimed"
        charge.updated_by = current_user.user_id
        append_billing_status_history(
            charge=charge,
            from_status=before,
            to_status=charge.status,
            user_id=current_user.user_id,
            reason=payload.reason,
            notes=f"Charge added to claim {claim.claim_number}",
        )
    append_billing_status_history(
        claim=claim,
        from_status=None,
        to_status=payload.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Claim draft created",
    )
    account.claims.append(claim)
    db.flush()
    db.commit()
    db.refresh(claim)
    operation, audit_path = append_billing_workflow_audit(
        workflow="billing.claim_create",
        entity_type="clinical_claim",
        entity_id=claim.claim_number,
        actor=billing_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=None,
        status_after=claim.status,
        reason=payload.reason,
        changes=claim_changes(claim),
    )
    return BillingCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, account=account, claim=claim)


@router.post("/payments/preview", response_model=BillingPreviewResponse)
def preview_post_payment(
    payload: PaymentPostPreviewRequest,
    current_user: User = Depends(require_payment_mutation),
    db: Session = Depends(get_db),
) -> BillingPreviewResponse:
    return payment_post_preview(db, payload)


@router.post("/payments", response_model=BillingCommitResponse, status_code=status.HTTP_201_CREATED)
def post_payment(
    payload: PaymentPostCommitRequest,
    request: Request,
    current_user: User = Depends(require_payment_mutation),
    db: Session = Depends(get_db),
) -> BillingCommitResponse:
    require_generation_confirmation(request)
    preview = payment_post_preview(db, payload)
    _reject_blocking(preview)
    claim = claim_by_id(db, payload.claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment claim changed after preview")
    status_before = claim.status
    posted_at = payload.posted_at or now_utc()
    payment = ClinicalPayment(
        claim_id=claim.claim_id,
        claim=claim,
        billing_account_id=claim.billing_account_id,
        billing_account=claim.billing_account,
        patient_pk=claim.patient_pk,
        patient=claim.patient,
        payment_amount=payload.payment_amount,
        adjustment_amount=payload.adjustment_amount,
        payment_method=payload.payment_method,
        payer_type=payload.payer_type,
        reference_number=payload.reference_number,
        posted_at=posted_at,
        posted_by=current_user.user_id,
        notes=payload.notes,
        created_by=current_user.user_id,
    )
    claim.payments.append(payment)
    claim.billing_account.payments.append(payment)
    claim.paid_amount = round_money(claim.paid_amount + payload.payment_amount)
    claim.adjustment_amount = round_money(claim.adjustment_amount + payload.adjustment_amount)
    claim.balance = round_money(claim.total_amount - claim.paid_amount - claim.adjustment_amount)
    claim.status = "paid" if claim.balance <= 0 else "partially_paid"
    if claim.status == "paid":
        claim.closed_at = posted_at
        claim.closed_by = current_user.user_id
    claim.updated_by = current_user.user_id
    recalculate_account(claim.billing_account)
    append_billing_status_history(
        claim=claim,
        from_status=status_before,
        to_status=claim.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes="Payment posted",
    )
    db.flush()
    db.commit()
    db.refresh(payment)
    operation, audit_path = append_billing_workflow_audit(
        workflow="billing.payment_post",
        entity_type="clinical_payment",
        entity_id=str(payment.payment_id),
        actor=billing_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=claim.status,
        reason=payload.reason,
        changes=payment_changes(payment, claim),
    )
    return BillingCommitResponse(
        operation_id=operation.operation_id,
        audit_path=audit_path,
        account=claim.billing_account,
        claim=claim,
        payment=payment,
    )


@router.post("/denials/preview", response_model=BillingPreviewResponse)
def preview_capture_denial(
    payload: DenialCapturePreviewRequest,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingPreviewResponse:
    return denial_capture_preview(db, payload)


@router.post("/denials", response_model=BillingCommitResponse, status_code=status.HTTP_201_CREATED)
def capture_denial(
    payload: DenialCaptureCommitRequest,
    request: Request,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingCommitResponse:
    require_generation_confirmation(request)
    preview = denial_capture_preview(db, payload)
    _reject_blocking(preview)
    claim = claim_by_id(db, payload.claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Denial claim changed after preview")
    claim_line = claim_line_by_id(db, payload.claim_line_id)
    status_before = claim.status
    denial = ClinicalDenial(
        claim_id=claim.claim_id,
        claim=claim,
        claim_line_id=claim_line.line_id if claim_line else None,
        claim_line=claim_line,
        denial_code=payload.denial_code,
        denial_reason=payload.denial_reason,
        status=payload.status,
        assigned_to=payload.assigned_to,
        due_date=payload.due_date,
        resolution_notes=payload.resolution_notes,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    claim.denials.append(denial)
    if claim_line:
        claim_line.status = "denied"
    claim.status = "denied"
    claim.updated_by = current_user.user_id
    append_billing_status_history(
        claim=claim,
        from_status=status_before,
        to_status=claim.status,
        user_id=current_user.user_id,
        reason=payload.reason,
        notes=payload.denial_reason,
    )
    db.flush()
    db.commit()
    db.refresh(denial)
    operation, audit_path = append_billing_workflow_audit(
        workflow="billing.denial_capture",
        entity_type="clinical_denial",
        entity_id=str(denial.denial_id),
        actor=billing_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=claim.status,
        reason=payload.reason,
        changes=denial_changes(denial, claim),
    )
    return BillingCommitResponse(operation_id=operation.operation_id, audit_path=audit_path, claim=claim, denial=denial)


@router.post("/insurance-verifications/preview", response_model=BillingPreviewResponse)
def preview_verify_insurance(
    payload: InsuranceVerificationPreviewRequest,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingPreviewResponse:
    return insurance_verification_preview(db, payload)


@router.post("/insurance-verifications", response_model=BillingCommitResponse, status_code=status.HTTP_201_CREATED)
def verify_insurance(
    payload: InsuranceVerificationCommitRequest,
    request: Request,
    current_user: User = Depends(require_billing_mutation),
    db: Session = Depends(get_db),
) -> BillingCommitResponse:
    require_generation_confirmation(request)
    preview = insurance_verification_preview(db, payload)
    _reject_blocking(preview)
    patient = patient_by_identifier(db, payload.patient_id)
    insurance = patient_insurance_by_id(db, payload.patient_insurance_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insurance verification context changed after preview")
    verified_at = payload.verified_at or now_utc()
    verification = ClinicalInsuranceVerification(
        patient_pk=patient.patient_pk,
        patient=patient,
        patient_insurance_id=insurance.insurance_id if insurance else None,
        patient_insurance=insurance,
        verification_status=payload.verification_status,
        verified_at=verified_at,
        verified_by=current_user.user_id,
        payer_name=payload.payer_name or (insurance.payer_name if insurance else None),
        plan_name=payload.plan_name or (insurance.plan_type if insurance else None),
        member_id=payload.member_id or (insurance.member_id if insurance else None),
        group_number=payload.group_number or (insurance.group_number if insurance else None),
        coverage_start=payload.coverage_start,
        coverage_end=payload.coverage_end,
        notes=payload.notes,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    status_before = insurance.eligibility_status if insurance else None
    if insurance:
        insurance.eligibility_status = payload.verification_status
        insurance.updated_by = current_user.user_id
    db.add(verification)
    db.flush()
    db.commit()
    db.refresh(verification)
    operation, audit_path = append_billing_workflow_audit(
        workflow="billing.insurance_verify",
        entity_type="clinical_insurance_verification",
        entity_id=str(verification.verification_id),
        actor=billing_actor(current_user),
        preview_value=payload.preview_hash or preview.preview_hash,
        status_before=status_before,
        status_after=verification.verification_status,
        reason=payload.reason,
        changes=verification_changes(verification),
    )
    return BillingCommitResponse(
        operation_id=operation.operation_id,
        audit_path=audit_path,
        insurance_verification=verification,
    )


@router.get("/work-queue", response_model=BillingWorkQueueResponse)
def billing_work_queue(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    patient_id: str | None = Query(default=None),
    payer: str | None = Query(default=None),
    date_filter: date | None = Query(default=None, alias="date"),
    claim_status: str | None = Query(default=None),
    denial_status: str | None = Query(default=None),
    current_user: User = Depends(require_billing_read),
    db: Session = Depends(get_db),
) -> BillingWorkQueueResponse:
    account_query = select(ClinicalBillingAccount).where(ClinicalBillingAccount.is_deleted.is_(False))
    charge_query = select(ClinicalCharge).where(ClinicalCharge.is_deleted.is_(False))
    claim_query = select(ClinicalClaim).where(ClinicalClaim.is_deleted.is_(False))
    denial_query = select(ClinicalDenial)
    verification_query = select(ClinicalInsuranceVerification)
    if status_filter:
        account_query = account_query.where(ClinicalBillingAccount.status == status_filter)
        charge_query = charge_query.where(ClinicalCharge.status == status_filter)
    if claim_status:
        claim_query = claim_query.where(ClinicalClaim.status == claim_status)
    if denial_status:
        denial_query = denial_query.where(ClinicalDenial.status == denial_status)
    else:
        denial_query = denial_query.where(ClinicalDenial.status == "open")
    if patient_id:
        patient = patient_by_identifier(db, patient_id)
        if patient:
            account_query = account_query.where(ClinicalBillingAccount.patient_pk == patient.patient_pk)
            charge_query = charge_query.where(ClinicalCharge.patient_pk == patient.patient_pk)
            claim_query = claim_query.where(ClinicalClaim.patient_pk == patient.patient_pk)
            verification_query = verification_query.where(ClinicalInsuranceVerification.patient_pk == patient.patient_pk)
    if payer:
        like_payer = f"%{payer.strip().lower()}%"
        account_query = account_query.join(PatientInsurance, ClinicalBillingAccount.primary_insurance_id == PatientInsurance.insurance_id).where(
            func.lower(PatientInsurance.payer_name).like(like_payer)
        )
        claim_query = claim_query.join(PatientInsurance, ClinicalClaim.patient_insurance_id == PatientInsurance.insurance_id).where(
            func.lower(PatientInsurance.payer_name).like(like_payer)
        )
        verification_query = verification_query.where(func.lower(ClinicalInsuranceVerification.payer_name).like(like_payer))
    if date_filter:
        start_of_day = datetime.combine(date_filter, time.min)
        end_of_day = datetime.combine(date_filter, time.max)
        charge_query = charge_query.where(ClinicalCharge.service_date == date_filter)
        claim_query = claim_query.where(ClinicalClaim.created_at >= start_of_day, ClinicalClaim.created_at <= end_of_day)
        verification_query = verification_query.where(
            ClinicalInsuranceVerification.created_at >= start_of_day,
            ClinicalInsuranceVerification.created_at <= end_of_day,
        )
    accounts = list(db.execute(account_query.order_by(ClinicalBillingAccount.updated_at.desc()).limit(25)).scalars().all())
    charges = list(db.execute(charge_query.order_by(ClinicalCharge.created_at.desc()).limit(50)).scalars().all())
    claims = list(db.execute(claim_query.order_by(ClinicalClaim.updated_at.desc()).limit(50)).scalars().all())
    denials = list(db.execute(denial_query.order_by(ClinicalDenial.updated_at.desc()).limit(50)).scalars().all())
    verifications = list(db.execute(verification_query.order_by(ClinicalInsuranceVerification.created_at.desc()).limit(25)).scalars().all())
    if q:
        needle = q.strip().lower()

        def match_account(account: ClinicalBillingAccount) -> bool:
            return needle in account.account_number.lower() or needle in account.patient_id.lower() or needle in account.patient_name.lower()

        def match_charge(charge: ClinicalCharge) -> bool:
            return needle in charge.charge_number.lower() or needle in charge.patient_id.lower() or needle in charge.patient_name.lower()

        def match_claim(claim: ClinicalClaim) -> bool:
            return needle in claim.claim_number.lower() or needle in claim.patient_id.lower() or needle in claim.patient_name.lower()

        accounts = [account for account in accounts if match_account(account)]
        charges = [charge for charge in charges if match_charge(charge)]
        claims = [claim for claim in claims if match_claim(claim)]
    payments = [payment for claim in claims for payment in claim.payments]
    return BillingWorkQueueResponse(
        accounts=accounts,
        charges=charges,
        claims=claims,
        payments=payments,
        denials=denials,
        insurance_verifications=verifications,
    )
