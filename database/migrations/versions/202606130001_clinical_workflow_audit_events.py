"""clinical workflow audit event durability

Revision ID: 202606130001
Revises: 202606120010
Create Date: 2026-06-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606130001"
down_revision: str | None = "202606120010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"
TABLE_NAME = "clinical_workflow_audit_events"
APPEND_ONLY_FUNCTION = "reject_clinical_workflow_audit_event_mutation"
APPEND_ONLY_TRIGGER = "trg_clinical_workflow_audit_events_append_only"


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_operational_{table_name}_{column}"), table_name, [column], schema=SCHEMA)


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.drop_index(op.f(f"ix_operational_{table_name}_{column}"), table_name=table_name, schema=SCHEMA)


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.String(length=80), nullable=False),
        sa.Column("workflow", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=160), nullable=False),
        sa.Column("actor", sa.String(length=180), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preview_hash", sa.String(length=128), nullable=False),
        sa.Column("commit_confirmed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status_before", sa.Text(), nullable=True),
        sa.Column("status_after", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("changes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="workflow_commit"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation_id"),
        schema=SCHEMA,
    )
    _create_indexes(
        TABLE_NAME,
        (
            "id",
            "operation_id",
            "workflow",
            "entity_type",
            "entity_id",
            "actor",
            "timestamp",
            "commit_confirmed",
            "source",
            "created_at",
        ),
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.{APPEND_ONLY_FUNCTION}()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'clinical_workflow_audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {APPEND_ONLY_TRIGGER}
        BEFORE UPDATE OR DELETE ON {SCHEMA}.{TABLE_NAME}
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.{APPEND_ONLY_FUNCTION}()
        """
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {APPEND_ONLY_TRIGGER} ON {SCHEMA}.{TABLE_NAME}")
    op.execute(f"DROP FUNCTION IF EXISTS {SCHEMA}.{APPEND_ONLY_FUNCTION}()")
    _drop_indexes(
        TABLE_NAME,
        (
            "id",
            "operation_id",
            "workflow",
            "entity_type",
            "entity_id",
            "actor",
            "timestamp",
            "commit_confirmed",
            "source",
            "created_at",
        ),
    )
    op.drop_table(TABLE_NAME, schema=SCHEMA)
