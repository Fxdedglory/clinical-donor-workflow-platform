"""clinical billing insurance

Revision ID: 202606120007
Revises: 202606120006
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120007"
down_revision: str | None = "202606120006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"


def _grant_permission(role_names: tuple[str, ...], permission_name: str) -> None:
    quoted_roles = ", ".join(f"'{role_name}'" for role_name in role_names)
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.bridge_role_permission (role_id, permission_name)
        SELECT role_id, '{permission_name}'
        FROM {SCHEMA}.dim_role
        WHERE role_name IN ({quoted_roles})
        ON CONFLICT DO NOTHING
        """
    )


def upgrade() -> None:
    op.create_table(
        "clinical_billing_accounts",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("account_number", sa.String(length=40), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("primary_insurance_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("total_charges", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_payments", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_adjustments", sa.Float(), nullable=False, server_default="0"),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["primary_insurance_id"], [f"{SCHEMA}.patient_insurance.insurance_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("account_id"),
        sa.UniqueConstraint("account_number"),
        schema=SCHEMA,
    )
    for column in ["account_id", "account_number", "patient_pk", "primary_insurance_id", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_billing_accounts_{column}"), "clinical_billing_accounts", [column], schema=SCHEMA)

    op.create_table(
        "clinical_insurance_verifications",
        sa.Column("verification_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("patient_insurance_id", sa.Integer(), nullable=True),
        sa.Column("verification_status", sa.String(length=80), nullable=False, server_default="verified"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.Integer(), nullable=True),
        sa.Column("payer_name", sa.String(length=160), nullable=True),
        sa.Column("plan_name", sa.String(length=160), nullable=True),
        sa.Column("member_id", sa.String(length=120), nullable=True),
        sa.Column("group_number", sa.String(length=120), nullable=True),
        sa.Column("coverage_start", sa.Date(), nullable=True),
        sa.Column("coverage_end", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_insurance_id"], [f"{SCHEMA}.patient_insurance.insurance_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["verified_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("verification_id"),
        schema=SCHEMA,
    )
    for column in ["verification_id", "patient_pk", "patient_insurance_id", "verification_status", "verified_at", "payer_name"]:
        op.create_index(op.f(f"ix_operational_clinical_insurance_verifications_{column}"), "clinical_insurance_verifications", [column], schema=SCHEMA)

    op.create_table(
        "clinical_charges",
        sa.Column("charge_id", sa.Integer(), nullable=False),
        sa.Column("charge_number", sa.String(length=40), nullable=False),
        sa.Column("billing_account_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("order_result_id", sa.Integer(), nullable=True),
        sa.Column("care_plan_id", sa.Integer(), nullable=True),
        sa.Column("care_plan_task_id", sa.Integer(), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("code_type", sa.String(length=40), nullable=False, server_default="internal"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1"),
        sa.Column("unit_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="captured"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["billing_account_id"], [f"{SCHEMA}.clinical_billing_accounts.account_id"]),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["care_plan_task_id"], [f"{SCHEMA}.clinical_care_plan_tasks.task_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.ForeignKeyConstraint(["order_id"], [f"{SCHEMA}.clinical_orders.order_id"]),
        sa.ForeignKeyConstraint(["order_result_id"], [f"{SCHEMA}.clinical_order_results.result_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("charge_id"),
        sa.UniqueConstraint("charge_number"),
        schema=SCHEMA,
    )
    for column in [
        "charge_id",
        "charge_number",
        "billing_account_id",
        "patient_pk",
        "encounter_id",
        "order_id",
        "order_result_id",
        "care_plan_id",
        "care_plan_task_id",
        "service_date",
        "code",
        "code_type",
        "status",
    ]:
        op.create_index(op.f(f"ix_operational_clinical_charges_{column}"), "clinical_charges", [column], schema=SCHEMA)

    op.create_table(
        "clinical_claims",
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("claim_number", sa.String(length=40), nullable=False),
        sa.Column("billing_account_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("patient_insurance_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="ready_for_review"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("adjustment_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["billing_account_id"], [f"{SCHEMA}.clinical_billing_accounts.account_id"]),
        sa.ForeignKeyConstraint(["closed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_insurance_id"], [f"{SCHEMA}.patient_insurance.insurance_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["submitted_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("claim_id"),
        sa.UniqueConstraint("claim_number"),
        schema=SCHEMA,
    )
    for column in ["claim_id", "claim_number", "billing_account_id", "patient_pk", "patient_insurance_id", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_claims_{column}"), "clinical_claims", [column], schema=SCHEMA)

    op.create_table(
        "clinical_claim_lines",
        sa.Column("line_id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("charge_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("code_type", sa.String(length=40), nullable=False, server_default="internal"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1"),
        sa.Column("unit_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("line_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("diagnosis_code", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="ready_for_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["charge_id"], [f"{SCHEMA}.clinical_charges.charge_id"]),
        sa.ForeignKeyConstraint(["claim_id"], [f"{SCHEMA}.clinical_claims.claim_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("line_id"),
        schema=SCHEMA,
    )
    for column in ["line_id", "claim_id", "charge_id", "line_number", "code", "code_type", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_claim_lines_{column}"), "clinical_claim_lines", [column], schema=SCHEMA)

    op.create_table(
        "clinical_payments",
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("billing_account_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("payment_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("adjustment_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(length=80), nullable=False, server_default="eft"),
        sa.Column("payer_type", sa.String(length=80), nullable=False, server_default="insurance"),
        sa.Column("reference_number", sa.String(length=120), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("posted_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["billing_account_id"], [f"{SCHEMA}.clinical_billing_accounts.account_id"]),
        sa.ForeignKeyConstraint(["claim_id"], [f"{SCHEMA}.clinical_claims.claim_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["posted_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("payment_id"),
        schema=SCHEMA,
    )
    for column in ["payment_id", "claim_id", "billing_account_id", "patient_pk", "reference_number", "posted_at"]:
        op.create_index(op.f(f"ix_operational_clinical_payments_{column}"), "clinical_payments", [column], schema=SCHEMA)

    op.create_table(
        "clinical_denials",
        sa.Column("denial_id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("claim_line_id", sa.Integer(), nullable=True),
        sa.Column("denial_code", sa.String(length=80), nullable=True),
        sa.Column("denial_reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("assigned_to", sa.String(length=160), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], [f"{SCHEMA}.clinical_claims.claim_id"]),
        sa.ForeignKeyConstraint(["claim_line_id"], [f"{SCHEMA}.clinical_claim_lines.line_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["resolved_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("denial_id"),
        schema=SCHEMA,
    )
    for column in ["denial_id", "claim_id", "claim_line_id", "denial_code", "status", "assigned_to", "due_date"]:
        op.create_index(op.f(f"ix_operational_clinical_denials_{column}"), "clinical_denials", [column], schema=SCHEMA)

    op.create_table(
        "clinical_billing_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("billing_account_id", sa.Integer(), nullable=True),
        sa.Column("claim_id", sa.Integer(), nullable=True),
        sa.Column("charge_id", sa.Integer(), nullable=True),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["billing_account_id"], [f"{SCHEMA}.clinical_billing_accounts.account_id"]),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["charge_id"], [f"{SCHEMA}.clinical_charges.charge_id"]),
        sa.ForeignKeyConstraint(["claim_id"], [f"{SCHEMA}.clinical_claims.claim_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    for column in ["history_id", "billing_account_id", "claim_id", "charge_id", "to_status", "changed_at"]:
        op.create_index(op.f(f"ix_operational_clinical_billing_status_history_{column}"), "clinical_billing_status_history", [column], schema=SCHEMA)

    billing_roles = (
        "System Administrator",
        "Donor Intake Coordinator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    _grant_permission(billing_roles, "billing.read")
    _grant_permission(billing_roles, "billing.manage")
    _grant_permission(("System Administrator", "Operations Manager", "Quality Assurance Specialist"), "billing.payment_post")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('billing.read', 'billing.manage', 'billing.payment_post')
        """
    )

    for column in ["history_id", "billing_account_id", "claim_id", "charge_id", "to_status", "changed_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_billing_status_history_{column}"), table_name="clinical_billing_status_history", schema=SCHEMA)
    op.drop_table("clinical_billing_status_history", schema=SCHEMA)

    for column in ["denial_id", "claim_id", "claim_line_id", "denial_code", "status", "assigned_to", "due_date"]:
        op.drop_index(op.f(f"ix_operational_clinical_denials_{column}"), table_name="clinical_denials", schema=SCHEMA)
    op.drop_table("clinical_denials", schema=SCHEMA)

    for column in ["payment_id", "claim_id", "billing_account_id", "patient_pk", "reference_number", "posted_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_payments_{column}"), table_name="clinical_payments", schema=SCHEMA)
    op.drop_table("clinical_payments", schema=SCHEMA)

    for column in ["line_id", "claim_id", "charge_id", "line_number", "code", "code_type", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_claim_lines_{column}"), table_name="clinical_claim_lines", schema=SCHEMA)
    op.drop_table("clinical_claim_lines", schema=SCHEMA)

    for column in ["claim_id", "claim_number", "billing_account_id", "patient_pk", "patient_insurance_id", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_claims_{column}"), table_name="clinical_claims", schema=SCHEMA)
    op.drop_table("clinical_claims", schema=SCHEMA)

    for column in [
        "charge_id",
        "charge_number",
        "billing_account_id",
        "patient_pk",
        "encounter_id",
        "order_id",
        "order_result_id",
        "care_plan_id",
        "care_plan_task_id",
        "service_date",
        "code",
        "code_type",
        "status",
    ]:
        op.drop_index(op.f(f"ix_operational_clinical_charges_{column}"), table_name="clinical_charges", schema=SCHEMA)
    op.drop_table("clinical_charges", schema=SCHEMA)

    for column in ["verification_id", "patient_pk", "patient_insurance_id", "verification_status", "verified_at", "payer_name"]:
        op.drop_index(op.f(f"ix_operational_clinical_insurance_verifications_{column}"), table_name="clinical_insurance_verifications", schema=SCHEMA)
    op.drop_table("clinical_insurance_verifications", schema=SCHEMA)

    for column in ["account_id", "account_number", "patient_pk", "primary_insurance_id", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_billing_accounts_{column}"), table_name="clinical_billing_accounts", schema=SCHEMA)
    op.drop_table("clinical_billing_accounts", schema=SCHEMA)
