"""security compliance hardening

Revision ID: 202605200003
Revises: 202605200002
Create Date: 2026-05-20 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605200003"
down_revision: str | None = "202605200002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"


def upgrade() -> None:
    op.create_table(
        "dim_external_organization",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("organization_name", sa.String(length=180), nullable=False),
        sa.Column("organization_type", sa.String(length=80), nullable=False, server_default="Internal"),
        sa.Column("approval_status", sa.String(length=40), nullable=False, server_default="Approved"),
        sa.Column("identity_provider", sa.String(length=80), nullable=False, server_default="Local"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("organization_id"),
        sa.UniqueConstraint("organization_name"),
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_dim_external_organization_organization_id"),
        "dim_external_organization",
        ["organization_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "dim_user_approval_status",
        sa.Column("approval_status_id", sa.Integer(), nullable=False),
        sa.Column("status_name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("approval_status_id"),
        sa.UniqueConstraint("status_name"),
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_dim_user_approval_status_approval_status_id"),
        "dim_user_approval_status",
        ["approval_status_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.add_column(
        "dim_user",
        sa.Column("user_type", sa.String(length=40), nullable=False, server_default="Internal"),
        schema=SCHEMA,
    )
    op.add_column("dim_user", sa.Column("organization_id", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column(
        "dim_user",
        sa.Column("external_user_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user",
        sa.Column("approval_status", sa.String(length=40), nullable=False, server_default="Approved"),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user",
        sa.Column("identity_provider", sa.String(length=80), nullable=False, server_default="Local"),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user",
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        schema=SCHEMA,
    )
    op.add_column("dim_user", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA)
    op.add_column(
        "dim_user", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "dim_user", sa.Column("password_expires_at", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "dim_user",
        sa.Column("password_history", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user", sa.Column("last_password_reset_at", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA
    )
    op.create_foreign_key(
        "fk_dim_user_external_organization",
        "dim_user",
        "dim_external_organization",
        ["organization_id"],
        ["organization_id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )

    op.add_column("fact_donor_review", sa.Column("donor_id_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column("fact_donor_review", sa.Column("donor_id_hash", sa.String(length=96), nullable=True), schema=SCHEMA)
    op.add_column("fact_donor_review", sa.Column("donor_name_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column("fact_donor_review", sa.Column("clinical_notes_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column("fact_donor_review", sa.Column("rejection_reason_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.create_index(
        op.f("ix_operational_fact_donor_review_donor_id_hash"),
        "fact_donor_review",
        ["donor_id_hash"],
        unique=False,
        schema=SCHEMA,
    )

    op.add_column("dim_donor", sa.Column("donor_identifier_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column("dim_donor", sa.Column("donor_identifier_hash", sa.String(length=96), nullable=True), schema=SCHEMA)
    op.add_column("dim_donor", sa.Column("donor_name_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column("dim_donor", sa.Column("source_organization_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column("dim_donor", sa.Column("donor_history_encrypted", sa.Text(), nullable=True), schema=SCHEMA)
    op.create_index(
        op.f("ix_operational_dim_donor_donor_identifier_hash"),
        "dim_donor",
        ["donor_identifier_hash"],
        unique=False,
        schema=SCHEMA,
    )

    op.add_column(
        "fact_infectious_disease_result",
        sa.Column("result_value_encrypted", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "fact_medical_social_history",
        sa.Column("review_notes_encrypted", sa.Text(), nullable=True),
        schema=SCHEMA,
    )

    op.create_table(
        "dim_auth_identity",
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("identity_provider", sa.String(length=80), nullable=False, server_default="Local"),
        sa.Column("provider_subject", sa.String(length=180), nullable=False),
        sa.Column("user_type", sa.String(length=40), nullable=False, server_default="Internal"),
        sa.Column("mfa_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("external_user_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_authenticated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("identity_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_auth_identity_identity_id"), "dim_auth_identity", ["identity_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_auth_identity_user_id"), "dim_auth_identity", ["user_id"], schema=SCHEMA)

    op.create_table(
        "dim_user_session",
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("device", sa.String(length=180), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("session_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_user_session_user_id"), "dim_user_session", ["user_id"], schema=SCHEMA)

    op.create_table(
        "dim_mfa_configuration",
        sa.Column("mfa_config_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=40), nullable=False, server_default="TOTP"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("required_by_policy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("secret_encrypted", sa.Text(), nullable=True),
        sa.Column("recovery_codes_encrypted", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("mfa_config_id"),
        sa.UniqueConstraint("user_id"),
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_dim_mfa_configuration_mfa_config_id"),
        "dim_mfa_configuration",
        ["mfa_config_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "fact_security_audit",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("device", sa.String(length=180), nullable=True),
        sa.Column("route", sa.String(length=240), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_security_audit_event_id"), "fact_security_audit", ["event_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_security_audit_event_type"), "fact_security_audit", ["event_type"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_security_audit_timestamp"), "fact_security_audit", ["timestamp"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_security_audit_user_id"), "fact_security_audit", ["user_id"], schema=SCHEMA)

    op.create_table(
        "dim_secure_document",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(length=100), nullable=False),
        sa.Column("record_id", sa.String(length=80), nullable=False),
        sa.Column("document_name", sa.String(length=180), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("storage_uri_encrypted", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=96), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("access_classification", sa.String(length=40), nullable=False, server_default="Protected"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["uploaded_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("document_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_secure_document_document_id"), "dim_secure_document", ["document_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_secure_document_record_id"), "dim_secure_document", ["record_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_secure_document_record_type"), "dim_secure_document", ["record_type"], schema=SCHEMA)

    op.create_table(
        "fact_document_access",
        sa.Column("access_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("route", sa.String(length=240), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["document_id"], [f"{SCHEMA}.dim_secure_document.document_id"]),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("access_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_document_access_access_id"), "fact_document_access", ["access_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_document_access_document_id"), "fact_document_access", ["document_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_document_access_user_id"), "fact_document_access", ["user_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_document_access_timestamp"), "fact_document_access", ["timestamp"], schema=SCHEMA)

    op.create_table(
        "fact_password_reset_token",
        sa.Column("reset_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("reset_id"),
        sa.UniqueConstraint("token_hash"),
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_fact_password_reset_token_reset_id"),
        "fact_password_reset_token",
        ["reset_id"],
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_fact_password_reset_token_user_id"),
        "fact_password_reset_token",
        ["user_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_operational_fact_password_reset_token_user_id"), table_name="fact_password_reset_token", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_password_reset_token_reset_id"), table_name="fact_password_reset_token", schema=SCHEMA)
    op.drop_table("fact_password_reset_token", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_document_access_timestamp"), table_name="fact_document_access", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_document_access_user_id"), table_name="fact_document_access", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_document_access_document_id"), table_name="fact_document_access", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_document_access_access_id"), table_name="fact_document_access", schema=SCHEMA)
    op.drop_table("fact_document_access", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_secure_document_record_type"), table_name="dim_secure_document", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_secure_document_record_id"), table_name="dim_secure_document", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_secure_document_document_id"), table_name="dim_secure_document", schema=SCHEMA)
    op.drop_table("dim_secure_document", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_security_audit_user_id"), table_name="fact_security_audit", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_security_audit_timestamp"), table_name="fact_security_audit", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_security_audit_event_type"), table_name="fact_security_audit", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_security_audit_event_id"), table_name="fact_security_audit", schema=SCHEMA)
    op.drop_table("fact_security_audit", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_mfa_configuration_mfa_config_id"), table_name="dim_mfa_configuration", schema=SCHEMA)
    op.drop_table("dim_mfa_configuration", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_user_session_user_id"), table_name="dim_user_session", schema=SCHEMA)
    op.drop_table("dim_user_session", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_auth_identity_user_id"), table_name="dim_auth_identity", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_auth_identity_identity_id"), table_name="dim_auth_identity", schema=SCHEMA)
    op.drop_table("dim_auth_identity", schema=SCHEMA)

    op.drop_column("fact_medical_social_history", "review_notes_encrypted", schema=SCHEMA)
    op.drop_column("fact_infectious_disease_result", "result_value_encrypted", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_donor_donor_identifier_hash"), table_name="dim_donor", schema=SCHEMA)
    op.drop_column("dim_donor", "donor_history_encrypted", schema=SCHEMA)
    op.drop_column("dim_donor", "source_organization_encrypted", schema=SCHEMA)
    op.drop_column("dim_donor", "donor_name_encrypted", schema=SCHEMA)
    op.drop_column("dim_donor", "donor_identifier_hash", schema=SCHEMA)
    op.drop_column("dim_donor", "donor_identifier_encrypted", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_donor_review_donor_id_hash"), table_name="fact_donor_review", schema=SCHEMA)
    op.drop_column("fact_donor_review", "rejection_reason_encrypted", schema=SCHEMA)
    op.drop_column("fact_donor_review", "clinical_notes_encrypted", schema=SCHEMA)
    op.drop_column("fact_donor_review", "donor_name_encrypted", schema=SCHEMA)
    op.drop_column("fact_donor_review", "donor_id_hash", schema=SCHEMA)
    op.drop_column("fact_donor_review", "donor_id_encrypted", schema=SCHEMA)

    op.drop_constraint("fk_dim_user_external_organization", "dim_user", schema=SCHEMA, type_="foreignkey")
    for column_name in [
        "last_password_reset_at",
        "password_history",
        "password_expires_at",
        "password_changed_at",
        "locked_until",
        "failed_login_count",
        "mfa_enabled",
        "identity_provider",
        "approval_status",
        "external_user_flag",
        "organization_id",
        "user_type",
    ]:
        op.drop_column("dim_user", column_name, schema=SCHEMA)
    op.drop_index(
        op.f("ix_operational_dim_user_approval_status_approval_status_id"),
        table_name="dim_user_approval_status",
        schema=SCHEMA,
    )
    op.drop_table("dim_user_approval_status", schema=SCHEMA)
    op.drop_index(
        op.f("ix_operational_dim_external_organization_organization_id"),
        table_name="dim_external_organization",
        schema=SCHEMA,
    )
    op.drop_table("dim_external_organization", schema=SCHEMA)
