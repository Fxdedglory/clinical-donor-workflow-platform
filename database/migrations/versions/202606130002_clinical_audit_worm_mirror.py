"""clinical audit WORM mirror foundation

Revision ID: 202606130002
Revises: 202606130001
Create Date: 2026-06-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606130002"
down_revision: str | None = "202606130001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"
TABLE_NAME = "clinical_workflow_audit_mirror_events"
APPEND_ONLY_FUNCTION = "reject_clinical_workflow_audit_mirror_event_mutation"
APPEND_ONLY_TRIGGER = "trg_clinical_workflow_audit_mirror_events_append_only"


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_operational_{table_name}_{column}"), table_name, [column], schema=SCHEMA)


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.drop_index(op.f(f"ix_operational_{table_name}_{column}"), table_name=table_name, schema=SCHEMA)


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("mirror_event_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.String(length=80), nullable=False),
        sa.Column("mirror_mode", sa.String(length=80), nullable=False),
        sa.Column("mirror_status", sa.String(length=40), nullable=False),
        sa.Column("payload_profile", sa.String(length=80), nullable=False, server_default="audit_metadata"),
        sa.Column("mirrored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mirror_uri", sa.Text(), nullable=True),
        sa.Column("mirror_checksum", sa.String(length=128), nullable=True),
        sa.Column("mirror_error", sa.Text(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("mirror_event_id"),
        schema=SCHEMA,
    )
    _create_indexes(
        TABLE_NAME,
        (
            "mirror_event_id",
            "operation_id",
            "mirror_mode",
            "mirror_status",
            "payload_profile",
            "mirrored_at",
            "mirror_checksum",
            "dry_run",
            "created_at",
        ),
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.{APPEND_ONLY_FUNCTION}()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'clinical_workflow_audit_mirror_events is append-only';
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
            "mirror_event_id",
            "operation_id",
            "mirror_mode",
            "mirror_status",
            "payload_profile",
            "mirrored_at",
            "mirror_checksum",
            "dry_run",
            "created_at",
        ),
    )
    op.drop_table(TABLE_NAME, schema=SCHEMA)
