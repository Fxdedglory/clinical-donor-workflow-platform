"""clinical patient registration

Revision ID: 202606120001
Revises: 202605210003
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120001"
down_revision: str | None = "202605210003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.String(length=40), nullable=False),
        sa.Column("donor_reference", sa.String(length=80), nullable=True),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("middle_name", sa.String(length=80), nullable=True),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("sex_at_birth", sa.String(length=40), nullable=False),
        sa.Column("gender_identity", sa.String(length=80), nullable=True),
        sa.Column("preferred_language", sa.String(length=80), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=180), nullable=True),
        sa.Column("address_line1", sa.String(length=180), nullable=True),
        sa.Column("address_line2", sa.String(length=180), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=60), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_registration"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("patient_pk"),
        sa.UniqueConstraint("patient_id"),
        schema=SCHEMA,
    )
    for column in [
        "patient_pk",
        "patient_id",
        "donor_reference",
        "first_name",
        "last_name",
        "date_of_birth",
        "phone",
        "email",
        "status",
    ]:
        op.create_index(op.f(f"ix_operational_patients_{column}"), "patients", [column], schema=SCHEMA)

    op.create_table(
        "patient_contacts",
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("contact_type", sa.String(length=80), nullable=False, server_default="emergency"),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("relationship", sa.String(length=80), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=180), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_registration"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("contact_id"),
        schema=SCHEMA,
    )
    for column in ["contact_id", "patient_pk", "contact_type", "status"]:
        op.create_index(op.f(f"ix_operational_patient_contacts_{column}"), "patient_contacts", [column], schema=SCHEMA)

    op.create_table(
        "patient_insurance",
        sa.Column("insurance_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("payer_name", sa.String(length=160), nullable=False),
        sa.Column("member_id", sa.String(length=120), nullable=True),
        sa.Column("group_number", sa.String(length=120), nullable=True),
        sa.Column("plan_type", sa.String(length=80), nullable=True),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="primary"),
        sa.Column("eligibility_status", sa.String(length=80), nullable=False, server_default="not_verified"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_registration"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("insurance_id"),
        schema=SCHEMA,
    )
    for column in ["insurance_id", "patient_pk", "payer_name", "priority", "status"]:
        op.create_index(op.f(f"ix_operational_patient_insurance_{column}"), "patient_insurance", [column], schema=SCHEMA)

    op.create_table(
        "patient_consents",
        sa.Column("consent_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("consent_type", sa.String(length=120), nullable=False),
        sa.Column("consent_status", sa.String(length=40), nullable=False, server_default="captured"),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_by_name", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_registration"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("consent_id"),
        schema=SCHEMA,
    )
    for column in ["consent_id", "patient_pk", "consent_type", "consent_status"]:
        op.create_index(op.f(f"ix_operational_patient_consents_{column}"), "patient_consents", [column], schema=SCHEMA)


def downgrade() -> None:
    for column in ["consent_id", "patient_pk", "consent_type", "consent_status"]:
        op.drop_index(op.f(f"ix_operational_patient_consents_{column}"), table_name="patient_consents", schema=SCHEMA)
    op.drop_table("patient_consents", schema=SCHEMA)

    for column in ["insurance_id", "patient_pk", "payer_name", "priority", "status"]:
        op.drop_index(op.f(f"ix_operational_patient_insurance_{column}"), table_name="patient_insurance", schema=SCHEMA)
    op.drop_table("patient_insurance", schema=SCHEMA)

    for column in ["contact_id", "patient_pk", "contact_type", "status"]:
        op.drop_index(op.f(f"ix_operational_patient_contacts_{column}"), table_name="patient_contacts", schema=SCHEMA)
    op.drop_table("patient_contacts", schema=SCHEMA)

    for column in [
        "patient_pk",
        "patient_id",
        "donor_reference",
        "first_name",
        "last_name",
        "date_of_birth",
        "phone",
        "email",
        "status",
    ]:
        op.drop_index(op.f(f"ix_operational_patients_{column}"), table_name="patients", schema=SCHEMA)
    op.drop_table("patients", schema=SCHEMA)
