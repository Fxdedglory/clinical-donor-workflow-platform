"""partner portal lifecycle

Revision ID: 202605210003
Revises: 202605210002
Create Date: 2026-05-21 18:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605210003"
down_revision: str | None = "202605210002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"


def _json_default() -> sa.TextClause:
    return sa.text("'{}'::json")


def upgrade() -> None:
    op.create_table(
        "dim_external_status_mapping",
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("internal_state", sa.String(length=120), nullable=False),
        sa.Column("external_status", sa.String(length=80), nullable=False),
        sa.Column("external_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("mapping_id"),
        sa.UniqueConstraint("internal_state"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_external_status_mapping_mapping_id"), "dim_external_status_mapping", ["mapping_id"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_external_status_mapping_internal_state"), "dim_external_status_mapping", ["internal_state"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_dim_external_status_mapping_external_status"), "dim_external_status_mapping", ["external_status"], schema=SCHEMA)

    op.create_table(
        "dim_partner_submission",
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("submission_code", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("submission_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("partner_visible_status", sa.String(length=80), nullable=False, server_default="Submitted"),
        sa.Column("internal_state", sa.String(length=120), nullable=False, server_default="Pending Intake Validation"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="Standard"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("product_or_tissue", sa.String(length=120), nullable=True),
        sa.Column("batch_or_reference", sa.String(length=120), nullable=True),
        sa.Column("estimated_completion_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=_json_default()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("submission_id"),
        sa.UniqueConstraint("submission_code"),
        schema=SCHEMA,
    )
    for column in ["submission_id", "submission_code", "organization_id", "submitted_at", "submission_type", "partner_visible_status"]:
        op.create_index(op.f(f"ix_operational_dim_partner_submission_{column}"), "dim_partner_submission", [column], schema=SCHEMA)

    op.create_table(
        "fact_partner_submission_status",
        sa.Column("status_event_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=80), nullable=True),
        sa.Column("to_status", sa.String(length=80), nullable=False),
        sa.Column("internal_state", sa.String(length=120), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("partner_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["changed_by_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["submission_id"], [f"{SCHEMA}.dim_partner_submission.submission_id"]),
        sa.PrimaryKeyConstraint("status_event_id"),
        schema=SCHEMA,
    )
    for column in ["status_event_id", "submission_id", "to_status", "changed_at"]:
        op.create_index(op.f(f"ix_operational_fact_partner_submission_status_{column}"), "fact_partner_submission_status", [column], schema=SCHEMA)

    op.create_table(
        "fact_partner_complaint",
        sa.Column("complaint_id", sa.Integer(), nullable=False),
        sa.Column("complaint_code", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("product_or_batch", sa.String(length=160), nullable=False),
        sa.Column("issue_category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False, server_default="Medium"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact_assessment", sa.Text(), nullable=False, server_default=""),
        sa.Column("contact_email", sa.String(length=180), nullable=True),
        sa.Column("partner_visible_status", sa.String(length=80), nullable=False, server_default="Submitted"),
        sa.Column("internal_state", sa.String(length=120), nullable=False, server_default="Pending QA Review"),
        sa.Column("investigation_id", sa.Integer(), nullable=True),
        sa.Column("capa_id", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=_json_default()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["capa_id"], [f"{SCHEMA}.fact_capa.capa_id"]),
        sa.ForeignKeyConstraint(["investigation_id"], [f"{SCHEMA}.fact_deviation.deviation_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("complaint_id"),
        sa.UniqueConstraint("complaint_code"),
        schema=SCHEMA,
    )
    for column in ["complaint_id", "complaint_code", "organization_id", "submitted_at", "severity", "issue_category", "partner_visible_status"]:
        op.create_index(op.f(f"ix_operational_fact_partner_complaint_{column}"), "fact_partner_complaint", [column], schema=SCHEMA)

    op.create_table(
        "fact_partner_message",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("complaint_id", sa.Integer(), nullable=True),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column("audience", sa.String(length=40), nullable=False, server_default="Partner"),
        sa.Column("subject", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attachment_document_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["attachment_document_id"], [f"{SCHEMA}.dim_secure_document.document_id"]),
        sa.ForeignKeyConstraint(["complaint_id"], [f"{SCHEMA}.fact_partner_complaint.complaint_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["sender_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["submission_id"], [f"{SCHEMA}.dim_partner_submission.submission_id"]),
        sa.PrimaryKeyConstraint("message_id"),
        schema=SCHEMA,
    )
    for column in ["message_id", "organization_id", "submission_id", "complaint_id", "created_at"]:
        op.create_index(op.f(f"ix_operational_fact_partner_message_{column}"), "fact_partner_message", [column], schema=SCHEMA)

    op.create_table(
        "dim_partner_document",
        sa.Column("partner_document_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("complaint_id", sa.Integer(), nullable=True),
        sa.Column("document_category", sa.String(length=80), nullable=False, server_default="Submission Evidence"),
        sa.Column("request_status", sa.String(length=60), nullable=False, server_default="Submitted"),
        sa.Column("partner_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["complaint_id"], [f"{SCHEMA}.fact_partner_complaint.complaint_id"]),
        sa.ForeignKeyConstraint(["document_id"], [f"{SCHEMA}.dim_secure_document.document_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["submission_id"], [f"{SCHEMA}.dim_partner_submission.submission_id"]),
        sa.PrimaryKeyConstraint("partner_document_id"),
        sa.UniqueConstraint("document_id"),
        schema=SCHEMA,
    )
    for column in ["partner_document_id", "document_id", "organization_id", "submission_id", "complaint_id", "created_at"]:
        op.create_index(op.f(f"ix_operational_dim_partner_document_{column}"), "dim_partner_document", [column], schema=SCHEMA)

    op.create_table(
        "fact_partner_task_response",
        sa.Column("response_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("responded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("response_status", sa.String(length=60), nullable=False, server_default="Submitted"),
        sa.Column("response_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("attachment_document_id", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["attachment_document_id"], [f"{SCHEMA}.dim_secure_document.document_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["responded_by_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["task_id"], [f"{SCHEMA}.fact_workflow_task.task_id"]),
        sa.PrimaryKeyConstraint("response_id"),
        schema=SCHEMA,
    )
    for column in ["response_id", "task_id", "organization_id", "submitted_at"]:
        op.create_index(op.f(f"ix_operational_fact_partner_task_response_{column}"), "fact_partner_task_response", [column], schema=SCHEMA)


def downgrade() -> None:
    for column in ["response_id", "task_id", "organization_id", "submitted_at"]:
        op.drop_index(op.f(f"ix_operational_fact_partner_task_response_{column}"), table_name="fact_partner_task_response", schema=SCHEMA)
    op.drop_table("fact_partner_task_response", schema=SCHEMA)

    for column in ["partner_document_id", "document_id", "organization_id", "submission_id", "complaint_id", "created_at"]:
        op.drop_index(op.f(f"ix_operational_dim_partner_document_{column}"), table_name="dim_partner_document", schema=SCHEMA)
    op.drop_table("dim_partner_document", schema=SCHEMA)

    for column in ["message_id", "organization_id", "submission_id", "complaint_id", "created_at"]:
        op.drop_index(op.f(f"ix_operational_fact_partner_message_{column}"), table_name="fact_partner_message", schema=SCHEMA)
    op.drop_table("fact_partner_message", schema=SCHEMA)

    for column in ["complaint_id", "complaint_code", "organization_id", "submitted_at", "severity", "issue_category", "partner_visible_status"]:
        op.drop_index(op.f(f"ix_operational_fact_partner_complaint_{column}"), table_name="fact_partner_complaint", schema=SCHEMA)
    op.drop_table("fact_partner_complaint", schema=SCHEMA)

    for column in ["status_event_id", "submission_id", "to_status", "changed_at"]:
        op.drop_index(op.f(f"ix_operational_fact_partner_submission_status_{column}"), table_name="fact_partner_submission_status", schema=SCHEMA)
    op.drop_table("fact_partner_submission_status", schema=SCHEMA)

    for column in ["submission_id", "submission_code", "organization_id", "submitted_at", "submission_type", "partner_visible_status"]:
        op.drop_index(op.f(f"ix_operational_dim_partner_submission_{column}"), table_name="dim_partner_submission", schema=SCHEMA)
    op.drop_table("dim_partner_submission", schema=SCHEMA)

    op.drop_index(op.f("ix_operational_dim_external_status_mapping_external_status"), table_name="dim_external_status_mapping", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_external_status_mapping_internal_state"), table_name="dim_external_status_mapping", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_external_status_mapping_mapping_id"), table_name="dim_external_status_mapping", schema=SCHEMA)
    op.drop_table("dim_external_status_mapping", schema=SCHEMA)
