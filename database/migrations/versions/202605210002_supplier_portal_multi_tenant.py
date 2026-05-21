"""supplier portal multi-tenant collaboration

Revision ID: 202605210002
Revises: 202605210001
Create Date: 2026-05-21 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605210002"
down_revision: str | None = "202605210001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"


def upgrade() -> None:
    op.add_column("dim_organization", sa.Column("contact_email", sa.String(length=180), nullable=True), schema=SCHEMA)
    op.add_column(
        "dim_organization",
        sa.Column("mfa_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema=SCHEMA,
    )

    op.create_table(
        "dim_supplier_relationship",
        sa.Column("relationship_id", sa.Integer(), nullable=False),
        sa.Column("internal_organization_id", sa.Integer(), nullable=False),
        sa.Column("external_organization_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False, server_default="Supplier"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Pending Approval"),
        sa.Column("onboarding_status", sa.String(length=60), nullable=False, server_default="Invited"),
        sa.Column("risk_tier", sa.String(length=40), nullable=False, server_default="Medium"),
        sa.Column("primary_contact_user_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["approved_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["external_organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["internal_organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["primary_contact_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("relationship_id"),
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_dim_supplier_relationship_relationship_id"),
        "dim_supplier_relationship",
        ["relationship_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_supplier_relationship_external_org",
        "dim_supplier_relationship",
        ["external_organization_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_supplier_relationship_internal_org",
        "dim_supplier_relationship",
        ["internal_organization_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "dim_external_invitation",
        sa.Column("invitation_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("invited_by", sa.Integer(), nullable=True),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Pending Acceptance"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["approved_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["created_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["invited_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["role_id"], [f"{SCHEMA}.dim_role.role_id"]),
        sa.PrimaryKeyConstraint("invitation_id"),
        sa.UniqueConstraint("token_hash"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_external_invitation_email"), "dim_external_invitation", ["email"], schema=SCHEMA)
    op.create_index(
        op.f("ix_operational_dim_external_invitation_invitation_id"),
        "dim_external_invitation",
        ["invitation_id"],
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_dim_external_invitation_organization_id"),
        "dim_external_invitation",
        ["organization_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "dim_document_version",
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("document_status", sa.String(length=60), nullable=False, server_default="Submitted"),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("storage_uri_encrypted", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=96), nullable=True),
        sa.Column("approval_status", sa.String(length=60), nullable=False, server_default="Pending Review"),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["approved_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["document_id"], [f"{SCHEMA}.dim_secure_document.document_id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("version_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_document_version_document_id"), "dim_document_version", ["document_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_document_version_version_id"), "dim_document_version", ["version_id"], schema=SCHEMA)

    op.create_table(
        "fact_signature_event",
        sa.Column("signature_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("record_type", sa.String(length=100), nullable=False),
        sa.Column("record_id", sa.String(length=80), nullable=False),
        sa.Column("signature_type", sa.String(length=80), nullable=False, server_default="Workflow Approval"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False, server_default=""),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("signature_hash", sa.String(length=128), nullable=False),
        sa.Column("prior_state", sa.String(length=100), nullable=True),
        sa.Column("new_state", sa.String(length=100), nullable=True),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("signature_id"),
        sa.UniqueConstraint("signature_hash"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_signature_event_organization_id"), "fact_signature_event", ["organization_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_signature_event_record_id"), "fact_signature_event", ["record_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_signature_event_record_type"), "fact_signature_event", ["record_type"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_signature_event_signature_id"), "fact_signature_event", ["signature_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_signature_event_signed_at"), "fact_signature_event", ["signed_at"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_signature_event_user_id"), "fact_signature_event", ["user_id"], schema=SCHEMA)

    op.create_table(
        "fact_background_job",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Queued"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="Normal"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.PrimaryKeyConstraint("job_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_background_job_job_id"), "fact_background_job", ["job_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_background_job_job_type"), "fact_background_job", ["job_type"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_background_job_organization_id"), "fact_background_job", ["organization_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_background_job_scheduled_for"), "fact_background_job", ["scheduled_for"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_background_job_status"), "fact_background_job", ["status"], schema=SCHEMA)

    op.create_table(
        "fact_realtime_event",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=False, server_default="operations"),
        sa.Column("audience_user_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("record_type", sa.String(length=100), nullable=True),
        sa.Column("record_id", sa.String(length=80), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["audience_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_realtime_event_audience_user_id"), "fact_realtime_event", ["audience_user_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_realtime_event_created_at"), "fact_realtime_event", ["created_at"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_realtime_event_event_id"), "fact_realtime_event", ["event_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_realtime_event_event_type"), "fact_realtime_event", ["event_type"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_realtime_event_organization_id"), "fact_realtime_event", ["organization_id"], schema=SCHEMA)

    op.create_table(
        "dim_training_record",
        sa.Column("training_record_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sop_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="Assigned"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("competency_status", sa.String(length=60), nullable=False, server_default="Pending Validation"),
        sa.Column("validated_by", sa.Integer(), nullable=True),
        sa.Column("validation_notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["sop_id"], [f"{SCHEMA}.dim_sop.sop_id"]),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["validated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("training_record_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_training_record_organization_id"), "dim_training_record", ["organization_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_training_record_training_record_id"), "dim_training_record", ["training_record_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_training_record_user_id"), "dim_training_record", ["user_id"], schema=SCHEMA)

    op.create_table(
        "fact_validation_evidence",
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.Column("change_control_id", sa.Integer(), nullable=True),
        sa.Column("evidence_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="Draft"),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["approved_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["change_control_id"], [f"{SCHEMA}.fact_change_control.change_id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("evidence_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_validation_evidence_change_control_id"), "fact_validation_evidence", ["change_control_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_validation_evidence_created_at"), "fact_validation_evidence", ["created_at"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_validation_evidence_evidence_id"), "fact_validation_evidence", ["evidence_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index(op.f("ix_operational_fact_validation_evidence_evidence_id"), table_name="fact_validation_evidence", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_validation_evidence_created_at"), table_name="fact_validation_evidence", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_validation_evidence_change_control_id"), table_name="fact_validation_evidence", schema=SCHEMA)
    op.drop_table("fact_validation_evidence", schema=SCHEMA)

    op.drop_index(op.f("ix_operational_dim_training_record_user_id"), table_name="dim_training_record", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_training_record_training_record_id"), table_name="dim_training_record", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_training_record_organization_id"), table_name="dim_training_record", schema=SCHEMA)
    op.drop_table("dim_training_record", schema=SCHEMA)

    op.drop_index(op.f("ix_operational_fact_realtime_event_organization_id"), table_name="fact_realtime_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_realtime_event_event_type"), table_name="fact_realtime_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_realtime_event_event_id"), table_name="fact_realtime_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_realtime_event_created_at"), table_name="fact_realtime_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_realtime_event_audience_user_id"), table_name="fact_realtime_event", schema=SCHEMA)
    op.drop_table("fact_realtime_event", schema=SCHEMA)

    op.drop_index(op.f("ix_operational_fact_background_job_status"), table_name="fact_background_job", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_background_job_scheduled_for"), table_name="fact_background_job", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_background_job_organization_id"), table_name="fact_background_job", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_background_job_job_type"), table_name="fact_background_job", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_background_job_job_id"), table_name="fact_background_job", schema=SCHEMA)
    op.drop_table("fact_background_job", schema=SCHEMA)

    op.drop_index(op.f("ix_operational_fact_signature_event_user_id"), table_name="fact_signature_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_signature_event_signed_at"), table_name="fact_signature_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_signature_event_signature_id"), table_name="fact_signature_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_signature_event_record_type"), table_name="fact_signature_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_signature_event_record_id"), table_name="fact_signature_event", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_signature_event_organization_id"), table_name="fact_signature_event", schema=SCHEMA)
    op.drop_table("fact_signature_event", schema=SCHEMA)

    op.drop_index(op.f("ix_operational_dim_document_version_version_id"), table_name="dim_document_version", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_document_version_document_id"), table_name="dim_document_version", schema=SCHEMA)
    op.drop_table("dim_document_version", schema=SCHEMA)

    op.drop_index(op.f("ix_operational_dim_external_invitation_organization_id"), table_name="dim_external_invitation", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_external_invitation_invitation_id"), table_name="dim_external_invitation", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_external_invitation_email"), table_name="dim_external_invitation", schema=SCHEMA)
    op.drop_table("dim_external_invitation", schema=SCHEMA)

    op.drop_index("ix_supplier_relationship_internal_org", table_name="dim_supplier_relationship", schema=SCHEMA)
    op.drop_index("ix_supplier_relationship_external_org", table_name="dim_supplier_relationship", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_supplier_relationship_relationship_id"), table_name="dim_supplier_relationship", schema=SCHEMA)
    op.drop_table("dim_supplier_relationship", schema=SCHEMA)

    op.drop_column("dim_organization", "mfa_required", schema=SCHEMA)
    op.drop_column("dim_organization", "contact_email", schema=SCHEMA)
