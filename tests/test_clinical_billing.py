import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
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
    ClinicalOrderCatalogItem,
    ClinicalOrderResult,
    ClinicalPayment,
    Patient,
    PatientInsurance,
)
from app.services import clinical_workflows


class _PermissionResult:
    def __init__(self, permissions: list[str]) -> None:
        self.permissions = permissions

    def all(self):
        return [(permission,) for permission in self.permissions]


class _Rows:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows


def _compiled(statement) -> str:
    try:
        return str(statement.compile(compile_kwargs={"literal_binds": True}))
    except Exception:
        return str(statement)


def _id_filter(rows: list[object], attr: str, sql: str) -> list[object]:
    match = re.search(rf"{attr}\s*=\s*(\d+)", sql)
    if not match:
        return rows
    value = int(match.group(1))
    return [row for row in rows if getattr(row, attr) == value]


def _patient_pk_filter(rows: list[object], sql: str) -> list[object]:
    match = re.search(r"patient_pk\s*=\s*(\d+)", sql)
    if not match:
        return rows
    value = int(match.group(1))
    return [row for row in rows if getattr(row, "patient_pk", None) == value]


class _ClinicalBillingDb:
    def __init__(
        self,
        *,
        permissions: list[str] | None = None,
        patients: list[Patient] | None = None,
        encounters: list[ClinicalEncounter] | None = None,
        orders: list[ClinicalOrder] | None = None,
        care_plans: list[ClinicalCarePlan] | None = None,
        accounts: list[ClinicalBillingAccount] | None = None,
        charges: list[ClinicalCharge] | None = None,
        claims: list[ClinicalClaim] | None = None,
        denials: list[ClinicalDenial] | None = None,
        verifications: list[ClinicalInsuranceVerification] | None = None,
    ) -> None:
        self.permissions = permissions or ["billing.read", "billing.manage", "billing.payment_post", "patients.read"]
        self.patients = patients or [_patient()]
        self.encounters = encounters or [_encounter(self.patients[0])]
        self.orders = orders or [_order(self.patients[0], self.encounters[0])]
        self.care_plans = care_plans or [_care_plan(self.patients[0])]
        self.accounts = accounts or []
        self.charges = charges or []
        self.claims = claims or []
        self.denials = denials or []
        self.verifications = verifications or []
        self.committed = False
        self._next_account_id = max([account.account_id or 0 for account in self.accounts] + [0]) + 1
        self._next_charge_id = max([charge.charge_id or 0 for charge in self.charges] + [0]) + 1
        self._next_claim_id = max([claim.claim_id or 0 for claim in self.claims] + [0]) + 1
        self._next_line_id = 1
        self._next_payment_id = 1
        self._next_denial_id = max([denial.denial_id or 0 for denial in self.denials] + [0]) + 1
        self._next_verification_id = 1
        self._next_history_id = 1
        for patient in self.patients:
            patient.billing_accounts = list(getattr(patient, "billing_accounts", []) or [])
            patient.charges = list(getattr(patient, "charges", []) or [])
            patient.claims = list(getattr(patient, "claims", []) or [])
            patient.payments = list(getattr(patient, "payments", []) or [])
            patient.insurance_verifications = list(getattr(patient, "insurance_verifications", []) or [])
        for account in self.accounts:
            self._prepare_account(account)
        for charge in self.charges:
            self._prepare_charge(charge)
        for claim in self.claims:
            self._prepare_claim(claim)
        for denial in self.denials:
            self._prepare_denial(denial)

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
        if "clinical_insurance_verifications" in sql:
            return _Rows(self.verifications)
        if "clinical_billing_accounts" in sql:
            return _Rows(_id_filter(_patient_pk_filter(self.accounts, sql), "account_id", sql))
        if "clinical_claim_lines" in sql:
            return _Rows(_id_filter(self._lines(), "line_id", sql))
        if "clinical_claims" in sql:
            return _Rows(_id_filter(_patient_pk_filter(self.claims, sql), "claim_id", sql))
        if "clinical_charges" in sql:
            return _Rows(_id_filter(_patient_pk_filter(self.charges, sql), "charge_id", sql))
        if "clinical_denials" in sql:
            return _Rows(_id_filter(self.denials, "denial_id", sql))
        if "clinical_care_plan_tasks" in sql:
            return _Rows(_id_filter(self._tasks(), "task_id", sql))
        if "clinical_care_plans" in sql:
            return _Rows(_id_filter(self.care_plans, "care_plan_id", sql))
        if "clinical_order_results" in sql and "clinical_orders" not in sql:
            return _Rows(_id_filter(self._results(), "result_id", sql))
        if "clinical_orders" in sql:
            return _Rows(_id_filter(self.orders, "order_id", sql))
        if "clinical_encounters" in sql:
            return _Rows(_id_filter(self.encounters, "encounter_id", sql))
        if "patient_insurance" in sql:
            return _Rows(_id_filter(self._insurance(), "insurance_id", sql))
        if "patients" in sql:
            patient_id_match = re.search(r"patients\.patient_id\s*=\s*'([^']+)'", sql)
            if patient_id_match:
                patient_id = patient_id_match.group(1)
                return _Rows([patient for patient in self.patients if patient.patient_id == patient_id])
            return _Rows(self.patients)
        return _Rows([])

    def add(self, value):
        if isinstance(value, ClinicalBillingAccount) and value not in self.accounts:
            self.accounts.append(value)
            self._prepare_account(value)
        if isinstance(value, ClinicalInsuranceVerification) and value not in self.verifications:
            self.verifications.append(value)
            self._prepare_verification(value)

    def flush(self) -> None:
        for account in self.accounts:
            self._prepare_account(account)
        for charge in self.charges:
            self._prepare_charge(charge)
        for claim in self.claims:
            self._prepare_claim(claim)
        for denial in self.denials:
            self._prepare_denial(denial)
        for verification in self.verifications:
            self._prepare_verification(verification)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        if isinstance(value, ClinicalBillingAccount):
            self._prepare_account(value)
        if isinstance(value, ClinicalCharge):
            self._prepare_charge(value)
        if isinstance(value, ClinicalClaim):
            self._prepare_claim(value)
        if isinstance(value, ClinicalPayment):
            self._prepare_payment(value)
        if isinstance(value, ClinicalDenial):
            self._prepare_denial(value)
        if isinstance(value, ClinicalInsuranceVerification):
            self._prepare_verification(value)

    def _insurance(self) -> list[PatientInsurance]:
        return [insurance for patient in self.patients for insurance in patient.insurance_profiles]

    def _results(self) -> list[ClinicalOrderResult]:
        return [result for order in self.orders for result in order.results]

    def _tasks(self) -> list[ClinicalCarePlanTask]:
        return [task for care_plan in self.care_plans for task in care_plan.tasks]

    def _lines(self) -> list[ClinicalClaimLine]:
        return [line for claim in self.claims for line in claim.lines]

    def _prepare_account(self, account: ClinicalBillingAccount) -> None:
        now = datetime.now(UTC)
        if account.account_id is None:
            account.account_id = self._next_account_id
            self._next_account_id += 1
        account.created_at = account.created_at or now
        account.updated_at = account.updated_at or now
        account.is_deleted = bool(account.is_deleted)
        account.patient = account.patient or self.patients[0]
        account.patient_pk = account.patient_pk or account.patient.patient_pk
        if account not in self.accounts:
            self.accounts.append(account)
        if account not in account.patient.billing_accounts:
            account.patient.billing_accounts.append(account)
        if account.primary_insurance_id:
            account.primary_insurance = account.primary_insurance or next((item for item in self._insurance() if item.insurance_id == account.primary_insurance_id), None)
        account.charges = list(getattr(account, "charges", []) or [])
        account.claims = list(getattr(account, "claims", []) or [])
        account.payments = list(getattr(account, "payments", []) or [])
        account.status_history = list(getattr(account, "status_history", []) or [])
        for charge in account.charges:
            self._prepare_charge(charge)
        for claim in account.claims:
            self._prepare_claim(claim)
        for payment in account.payments:
            self._prepare_payment(payment)
        self._prepare_history(account.status_history, account=account)

    def _prepare_charge(self, charge: ClinicalCharge) -> None:
        now = datetime.now(UTC)
        if charge.charge_id is None:
            charge.charge_id = self._next_charge_id
            self._next_charge_id += 1
        charge.created_at = charge.created_at or now
        charge.updated_at = charge.updated_at or now
        charge.is_deleted = bool(charge.is_deleted)
        charge.patient = charge.patient or self.patients[0]
        charge.patient_pk = charge.patient_pk or charge.patient.patient_pk
        if charge not in charge.patient.charges:
            charge.patient.charges.append(charge)
        if charge.billing_account is None:
            charge.billing_account = next((account for account in self.accounts if account.account_id == charge.billing_account_id), None) or _account(charge.patient)
        charge.billing_account_id = charge.billing_account_id or charge.billing_account.account_id
        if charge.billing_account not in self.accounts:
            self._prepare_account(charge.billing_account)
        if charge not in charge.billing_account.charges:
            charge.billing_account.charges.append(charge)
        charge.encounter = charge.encounter or next((item for item in self.encounters if item.encounter_id == charge.encounter_id), None)
        charge.order = charge.order or next((item for item in self.orders if item.order_id == charge.order_id), None)
        charge.order_result = charge.order_result or next((item for item in self._results() if item.result_id == charge.order_result_id), None)
        charge.care_plan = charge.care_plan or next((item for item in self.care_plans if item.care_plan_id == charge.care_plan_id), None)
        charge.care_plan_task = charge.care_plan_task or next((item for item in self._tasks() if item.task_id == charge.care_plan_task_id), None)
        charge.claim_lines = list(getattr(charge, "claim_lines", []) or [])
        charge.status_history = list(getattr(charge, "status_history", []) or [])
        if charge not in self.charges:
            self.charges.append(charge)
        self._prepare_history(charge.status_history, charge=charge)

    def _prepare_claim(self, claim: ClinicalClaim) -> None:
        now = datetime.now(UTC)
        if claim.claim_id is None:
            claim.claim_id = self._next_claim_id
            self._next_claim_id += 1
        claim.created_at = claim.created_at or now
        claim.updated_at = claim.updated_at or now
        claim.is_deleted = bool(claim.is_deleted)
        claim.patient = claim.patient or self.patients[0]
        claim.patient_pk = claim.patient_pk or claim.patient.patient_pk
        if claim not in claim.patient.claims:
            claim.patient.claims.append(claim)
        if claim.billing_account is None:
            claim.billing_account = next((account for account in self.accounts if account.account_id == claim.billing_account_id), None) or _account(claim.patient)
        claim.billing_account_id = claim.billing_account_id or claim.billing_account.account_id
        if claim.billing_account not in self.accounts:
            self._prepare_account(claim.billing_account)
        if claim not in claim.billing_account.claims:
            claim.billing_account.claims.append(claim)
        if claim.patient_insurance_id:
            claim.patient_insurance = claim.patient_insurance or next((item for item in self._insurance() if item.insurance_id == claim.patient_insurance_id), None)
        claim.lines = list(getattr(claim, "lines", []) or [])
        claim.payments = list(getattr(claim, "payments", []) or [])
        claim.denials = list(getattr(claim, "denials", []) or [])
        claim.status_history = list(getattr(claim, "status_history", []) or [])
        for line in claim.lines:
            if line.line_id is None:
                line.line_id = self._next_line_id
                self._next_line_id += 1
            line.claim_id = claim.claim_id
            line.claim = claim
            line.created_at = line.created_at or now
            line.charge = line.charge or next((charge for charge in self.charges if charge.charge_id == line.charge_id), None)
            if line.charge and line not in line.charge.claim_lines:
                line.charge.claim_lines.append(line)
        for payment in claim.payments:
            self._prepare_payment(payment)
        for denial in claim.denials:
            self._prepare_denial(denial)
        if claim not in self.claims:
            self.claims.append(claim)
        self._prepare_history(claim.status_history, claim=claim)

    def _prepare_payment(self, payment: ClinicalPayment) -> None:
        now = datetime.now(UTC)
        if payment.payment_id is None:
            payment.payment_id = self._next_payment_id
            self._next_payment_id += 1
        payment.created_at = payment.created_at or now
        payment.posted_at = payment.posted_at or now
        payment.claim = payment.claim or next((claim for claim in self.claims if claim.claim_id == payment.claim_id), None)
        payment.billing_account = payment.billing_account or next((account for account in self.accounts if account.account_id == payment.billing_account_id), None)
        payment.patient = payment.patient or self.patients[0]
        payment.patient_pk = payment.patient_pk or payment.patient.patient_pk
        if payment.claim and payment not in payment.claim.payments:
            payment.claim.payments.append(payment)
        if payment.billing_account and payment not in payment.billing_account.payments:
            payment.billing_account.payments.append(payment)
        if payment not in payment.patient.payments:
            payment.patient.payments.append(payment)

    def _prepare_denial(self, denial: ClinicalDenial) -> None:
        now = datetime.now(UTC)
        if denial.denial_id is None:
            denial.denial_id = self._next_denial_id
            self._next_denial_id += 1
        denial.created_at = denial.created_at or now
        denial.updated_at = denial.updated_at or now
        denial.claim = denial.claim or next((claim for claim in self.claims if claim.claim_id == denial.claim_id), None)
        denial.claim_line = denial.claim_line or next((line for line in self._lines() if line.line_id == denial.claim_line_id), None)
        if denial.claim and denial not in denial.claim.denials:
            denial.claim.denials.append(denial)
        if denial.claim_line and denial not in denial.claim_line.denials:
            denial.claim_line.denials.append(denial)
        if denial not in self.denials:
            self.denials.append(denial)

    def _prepare_verification(self, verification: ClinicalInsuranceVerification) -> None:
        now = datetime.now(UTC)
        if verification.verification_id is None:
            verification.verification_id = self._next_verification_id
            self._next_verification_id += 1
        verification.created_at = verification.created_at or now
        verification.updated_at = verification.updated_at or now
        verification.patient = verification.patient or self.patients[0]
        verification.patient_pk = verification.patient_pk or verification.patient.patient_pk
        verification.patient_insurance = verification.patient_insurance or next((item for item in self._insurance() if item.insurance_id == verification.patient_insurance_id), None)
        if verification not in verification.patient.insurance_verifications:
            verification.patient.insurance_verifications.append(verification)

    def _prepare_history(self, history_rows, *, account=None, claim=None, charge=None) -> None:
        for history in history_rows:
            if history.history_id is None:
                history.history_id = self._next_history_id
                self._next_history_id += 1
            history.billing_account = account
            history.claim = claim
            history.charge = charge
            history.billing_account_id = account.account_id if account else history.billing_account_id
            history.claim_id = claim.claim_id if claim else history.claim_id
            history.charge_id = charge.charge_id if charge else history.charge_id
            history.changed_at = history.changed_at or datetime.now(UTC)
            history.reason = history.reason or ""
            history.notes = history.notes or ""


def _internal_user():
    return SimpleNamespace(
        user_id=7,
        username="billing",
        email="billing@example.org",
        full_name="Billing User",
        role="Operations Manager",
        role_id=6,
        account_type="internal",
        user_type="internal",
        is_external=False,
        external_user_flag=False,
    )


def _external_user():
    return SimpleNamespace(
        user_id=8,
        username="partner",
        email="partner@example.org",
        full_name="Partner User",
        role="Partner External User",
        role_id=8,
        account_type="partner",
        user_type="partner",
        is_external=True,
        external_user_flag=True,
    )


def _patient(patient_pk: int = 1, patient_id: str = "PT-BILL-001") -> Patient:
    patient = Patient(
        patient_pk=patient_pk,
        patient_id=patient_id,
        first_name="Billing",
        last_name="Patient",
        date_of_birth=date(1988, 4, 5),
        sex_at_birth="Female",
        status="active",
        source="clinical_registration",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    insurance = PatientInsurance(
        insurance_id=patient_pk,
        patient_pk=patient_pk,
        patient=patient,
        payer_name="Acme Health",
        member_id=f"MEM-{patient_pk}",
        group_number="GRP-1",
        plan_type="ppo",
        priority="primary",
        eligibility_status="not_verified",
        status="active",
        source="clinical_registration",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    patient.insurance_profiles = [insurance]
    patient.billing_accounts = []
    patient.charges = []
    patient.claims = []
    patient.payments = []
    patient.insurance_verifications = []
    return patient


def _encounter(patient: Patient, encounter_id: int = 1) -> ClinicalEncounter:
    return ClinicalEncounter(
        encounter_id=encounter_id,
        encounter_number=f"ENC-BILL-{encounter_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_type="billing",
        status="signed",
        chief_complaint="Billing context",
        reason="Signed encounter",
        started_at=datetime.now(UTC),
        signed_at=datetime.now(UTC),
        signed_by=7,
        source="clinical_encounters",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )


def _order(patient: Patient, encounter: ClinicalEncounter, order_id: int = 1) -> ClinicalOrder:
    catalog = ClinicalOrderCatalogItem(catalog_item_id=1, code="LAB", name="Lab", order_type="lab", active=True)
    order = ClinicalOrder(
        order_id=order_id,
        order_number=f"ORD-BILL-{order_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        encounter_id=encounter.encounter_id,
        encounter=encounter,
        catalog_item_id=1,
        catalog_item=catalog,
        order_type="lab",
        priority="routine",
        status="resulted",
        clinical_indication="Billing order",
        ordering_provider="Billing Provider",
        ordered_at=datetime.now(UTC),
        source="clinical_orders",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    result = ClinicalOrderResult(
        result_id=order_id,
        order_id=order.order_id,
        order=order,
        result_name="Result",
        result_value="normal",
        result_status="normal",
        abnormal_flag=False,
        critical_flag=False,
        resulted_at=datetime.now(UTC),
        notes="",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    order.results = [result]
    order.acknowledgements = []
    order.charges = []
    return order


def _care_plan(patient: Patient, care_plan_id: int = 1) -> ClinicalCarePlan:
    care_plan = ClinicalCarePlan(
        care_plan_id=care_plan_id,
        care_plan_number=f"CP-BILL-{care_plan_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        title="Billing care plan",
        plan_type="case_management",
        priority="routine",
        status="active",
        reason="Care coordination",
        source="clinical_care_plans",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    task = ClinicalCarePlanTask(
        task_id=care_plan_id,
        care_plan_id=care_plan.care_plan_id,
        care_plan=care_plan,
        title="Billable care coordination",
        owner="Coordinator",
        due_date=date(2026, 6, 20),
        priority="routine",
        status="open",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    care_plan.tasks = [task]
    care_plan.charges = []
    return care_plan


def _account(patient: Patient, account_id: int = 1) -> ClinicalBillingAccount:
    account = ClinicalBillingAccount(
        account_id=account_id,
        account_number=f"BA-BILL-{account_id:03d}",
        patient_pk=patient.patient_pk,
        patient=patient,
        primary_insurance_id=patient.insurance_profiles[0].insurance_id,
        primary_insurance=patient.insurance_profiles[0],
        status="open",
        total_charges=0,
        total_payments=0,
        total_adjustments=0,
        balance=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    account.charges = []
    account.claims = []
    account.payments = []
    account.status_history = []
    patient.billing_accounts.append(account)
    return account


def _charge(patient: Patient, account: ClinicalBillingAccount, charge_id: int = 1, status: str = "captured") -> ClinicalCharge:
    charge = ClinicalCharge(
        charge_id=charge_id,
        charge_number=f"CHG-BILL-{charge_id:03d}",
        billing_account_id=account.account_id,
        billing_account=account,
        patient_pk=patient.patient_pk,
        patient=patient,
        service_date=date(2026, 6, 12),
        code="LAB100",
        code_type="internal",
        description="Billable lab service",
        quantity=2,
        unit_amount=50,
        total_amount=100,
        status=status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    charge.claim_lines = []
    charge.status_history = []
    account.charges.append(charge)
    patient.charges.append(charge)
    account.total_charges += 0 if status in {"voided", "cancelled"} else charge.total_amount
    account.balance = account.total_charges
    return charge


def _claim(patient: Patient, account: ClinicalBillingAccount, charge: ClinicalCharge, claim_id: int = 1, balance: float = 100) -> ClinicalClaim:
    claim = ClinicalClaim(
        claim_id=claim_id,
        claim_number=f"CLM-BILL-{claim_id:03d}",
        billing_account_id=account.account_id,
        billing_account=account,
        patient_pk=patient.patient_pk,
        patient=patient,
        patient_insurance_id=patient.insurance_profiles[0].insurance_id,
        patient_insurance=patient.insurance_profiles[0],
        status="ready_for_review",
        total_amount=100,
        paid_amount=100 - balance,
        adjustment_amount=0,
        balance=balance,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_deleted=False,
    )
    line = ClinicalClaimLine(
        line_id=1,
        claim_id=claim.claim_id,
        claim=claim,
        charge_id=charge.charge_id,
        charge=charge,
        line_number=1,
        code=charge.code,
        code_type=charge.code_type,
        description=charge.description,
        quantity=charge.quantity,
        unit_amount=charge.unit_amount,
        line_amount=charge.total_amount,
        status="ready_for_review",
        created_at=datetime.now(UTC),
    )
    claim.lines = [line]
    claim.payments = []
    claim.denials = []
    claim.status_history = []
    charge.claim_lines = [line]
    account.claims.append(claim)
    patient.claims.append(claim)
    return claim


def _override_dependencies(session: _ClinicalBillingDb, user) -> None:
    def _db_dependency():
        yield session

    app.dependency_overrides[get_db] = _db_dependency
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _charge_payload() -> dict[str, object]:
    return {
        "patient_id": "PT-BILL-001",
        "encounter_id": 1,
        "order_id": 1,
        "order_result_id": 1,
        "care_plan_id": 1,
        "care_plan_task_id": 1,
        "service_date": "2026-06-12",
        "code": "LAB100",
        "code_type": "internal",
        "description": "Billable lab service",
        "quantity": 2,
        "unit_amount": 50,
    }


def test_insurance_verification_preview_validates_patient_linkage() -> None:
    db = _ClinicalBillingDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/billing/insurance-verifications/preview", json={"patient_id": "PT-MISSING", "patient_insurance_id": 1})
    finally:
        _clear_overrides()
    assert response.status_code == 200
    assert response.json()["validation_status"] == "failed"
    assert any(issue["issue_type"] == "unknown_patient" for issue in response.json()["blocking_issues"])


def test_insurance_verification_commit_requires_confirmation_and_writes_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalBillingDb()
    _override_dependencies(db, _internal_user())
    payload = {"patient_id": "PT-BILL-001", "patient_insurance_id": 1, "verification_status": "verified", "preview_hash": "verify-hash"}
    try:
        missing = TestClient(app).post("/api/clinical/billing/insurance-verifications", json=payload)
        valid = TestClient(app).post("/api/clinical/billing/insurance-verifications", headers={"X-Confirm-Generation": "true"}, json=payload)
    finally:
        _clear_overrides()
    assert missing.status_code == 409
    assert valid.status_code == 201
    assert db.patients[0].insurance_profiles[0].eligibility_status == "verified"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "billing.insurance_verify"


def test_charge_capture_preview_validates_encounter_patient_linkage() -> None:
    patient = _patient()
    other = _patient(2, "PT-BILL-002")
    db = _ClinicalBillingDb(patients=[patient, other], encounters=[_encounter(other, 2)])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/billing/charges/preview", json={**_charge_payload(), "encounter_id": 2})
    finally:
        _clear_overrides()
    assert response.status_code == 200
    assert any(issue["issue_type"] == "encounter_id_patient_mismatch" for issue in response.json()["blocking_issues"])


def test_charge_capture_preview_validates_order_and_result_patient_linkage() -> None:
    patient = _patient()
    other = _patient(2, "PT-BILL-002")
    other_encounter = _encounter(other, 2)
    db = _ClinicalBillingDb(patients=[patient, other], orders=[_order(other, other_encounter, 2)])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/billing/charges/preview", json={**_charge_payload(), "order_id": 2, "order_result_id": 2})
    finally:
        _clear_overrides()
    assert response.status_code == 200
    assert any(issue["issue_type"] == "order_id_patient_mismatch" for issue in response.json()["blocking_issues"])


def test_charge_capture_commit_rejects_missing_header_and_succeeds_with_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalBillingDb()
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post("/api/clinical/billing/charges", json=_charge_payload())
        valid = TestClient(app).post("/api/clinical/billing/charges", headers={"X-Confirm-Generation": "true"}, json={**_charge_payload(), "preview_hash": "charge-hash"})
    finally:
        _clear_overrides()
    assert missing.status_code == 409
    assert valid.status_code == 201
    assert len(db.accounts) == 1
    assert db.accounts[0].total_charges == 100
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "billing.charge_capture"


def test_billing_account_is_reused_for_patient_charges(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    patient = _patient()
    account = _account(patient)
    db = _ClinicalBillingDb(patients=[patient], accounts=[account])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/billing/charges", headers={"X-Confirm-Generation": "true"}, json=_charge_payload())
    finally:
        _clear_overrides()
    assert response.status_code == 201
    assert len(db.accounts) == 1
    assert response.json()["account"]["account_id"] == account.account_id


def test_claim_preview_rejects_voided_charges_and_calculates_totals() -> None:
    patient = _patient()
    account = _account(patient)
    captured = _charge(patient, account, 1)
    voided = _charge(patient, account, 2, "voided")
    db = _ClinicalBillingDb(patients=[patient], accounts=[account], charges=[captured, voided])
    _override_dependencies(db, _internal_user())
    try:
        good = TestClient(app).post("/api/clinical/billing/claims/preview", json={"patient_id": "PT-BILL-001", "charge_ids": [1], "patient_insurance_id": 1})
        bad = TestClient(app).post("/api/clinical/billing/claims/preview", json={"patient_id": "PT-BILL-001", "charge_ids": [2], "patient_insurance_id": 1})
    finally:
        _clear_overrides()
    assert good.status_code == 200
    assert good.json()["changes"]["total_amount"] == 100
    assert bad.json()["validation_status"] == "failed"
    assert any(issue["issue_type"] == "charge_not_claimable" for issue in bad.json()["blocking_issues"])


def test_claim_commit_writes_lines_and_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    patient = _patient()
    account = _account(patient)
    charge = _charge(patient, account, 1)
    db = _ClinicalBillingDb(patients=[patient], accounts=[account], charges=[charge])
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/billing/claims",
            headers={"X-Confirm-Generation": "true"},
            json={"patient_id": "PT-BILL-001", "charge_ids": [1], "patient_insurance_id": 1, "preview_hash": "claim-hash"},
        )
    finally:
        _clear_overrides()
    assert response.status_code == 201
    assert len(db.claims[0].lines) == 1
    assert db.claims[0].balance == 100
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "billing.claim_create"


def test_payment_posting_updates_partial_and_full_balances_and_audit(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    patient = _patient()
    account = _account(patient)
    charge = _charge(patient, account, 1)
    claim = _claim(patient, account, charge, balance=100)
    db = _ClinicalBillingDb(patients=[patient], accounts=[account], charges=[charge], claims=[claim])
    _override_dependencies(db, _internal_user())
    try:
        partial = TestClient(app).post(
            "/api/clinical/billing/payments",
            headers={"X-Confirm-Generation": "true"},
            json={"claim_id": 1, "payment_amount": 40, "adjustment_amount": 0, "payment_method": "eft", "payer_type": "insurance"},
        )
        full = TestClient(app).post(
            "/api/clinical/billing/payments",
            headers={"X-Confirm-Generation": "true"},
            json={"claim_id": 1, "payment_amount": 60, "adjustment_amount": 0, "payment_method": "eft", "payer_type": "insurance"},
        )
    finally:
        _clear_overrides()
    assert partial.status_code == 201
    assert partial.json()["claim"]["status"] == "partially_paid"
    assert partial.json()["claim"]["balance"] == 60
    assert full.status_code == 201
    assert full.json()["claim"]["status"] == "paid"
    assert full.json()["claim"]["balance"] == 0
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "billing.payment_post"


def test_denial_capture_requires_reason_writes_audit_and_appears_in_queue(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    patient = _patient()
    account = _account(patient)
    charge = _charge(patient, account, 1)
    claim = _claim(patient, account, charge, balance=100)
    db = _ClinicalBillingDb(patients=[patient], accounts=[account], charges=[charge], claims=[claim])
    _override_dependencies(db, _internal_user())
    try:
        missing = TestClient(app).post("/api/clinical/billing/denials", headers={"X-Confirm-Generation": "true"}, json={"claim_id": 1, "denial_reason": ""})
        denial = TestClient(app).post(
            "/api/clinical/billing/denials",
            headers={"X-Confirm-Generation": "true"},
            json={"claim_id": 1, "claim_line_id": 1, "denial_code": "CO-16", "denial_reason": "Missing information"},
        )
        queue = TestClient(app).get("/api/clinical/billing/work-queue")
    finally:
        _clear_overrides()
    assert missing.status_code == 422
    assert denial.status_code == 201
    assert queue.status_code == 200
    assert queue.json()["denials"][0]["status"] == "open"
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "billing.denial_capture"


def test_external_partner_billing_mutation_is_rejected() -> None:
    db = _ClinicalBillingDb(permissions=["partner.portal"])
    _override_dependencies(db, _external_user())
    try:
        response = TestClient(app).post("/api/clinical/billing/charges/preview", json=_charge_payload())
    finally:
        _clear_overrides()
    assert response.status_code == 403
