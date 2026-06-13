"""clinical audit WORM manifest foundation

Revision ID: 202606130003
Revises: 202606130002
Create Date: 2026-06-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606130003"
down_revision: str | None = "202606130002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"
TABLE_NAME = "clinical_workflow_audit_mirror_manifests"
APPEND_ONLY_FUNCTION = "reject_clinical_workflow_audit_mirror_manifest_mutation"
APPEND_ONLY_TRIGGER = "trg_clinical_workflow_audit_mirror_manifests_append_only"


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
        sa.Column("manifest_id", sa.String(length=120), nullable=False),
        sa.Column("manifest_status", sa.String(length=40), nullable=False, server_default="generated"),
        sa.Column("mirror_mode", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("uri_prefix", sa.Text(), nullable=True),
        sa.Column("audit_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manifest_checksum", sa.String(length=128), nullable=False),
        sa.Column("signature_status", sa.String(length=40), nullable=False, server_default="not_required"),
        sa.Column("signature_algorithm", sa.String(length=80), nullable=True),
        sa.Column("signature_key_ref", sa.String(length=180), nullable=True),
        sa.Column("retention_policy", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("legal_hold_reference", sa.Text(), nullable=True),
        sa.Column("manifest_uri", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.String(length=180), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_id"),
        schema=SCHEMA,
    )
    _create_indexes(
        TABLE_NAME,
        (
            "id",
            "manifest_id",
            "manifest_status",
            "mirror_mode",
            "provider",
            "audit_event_count",
            "manifest_checksum",
            "signature_status",
            "retention_policy",
            "legal_hold",
            "generated_at",
            "generated_by",
            "created_at",
        ),
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.{APPEND_ONLY_FUNCTION}()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'clinical_workflow_audit_mirror_manifests is append-only';
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
            "manifest_id",
            "manifest_status",
            "mirror_mode",
            "provider",
            "audit_event_count",
            "manifest_checksum",
            "signature_status",
            "retention_policy",
            "legal_hold",
            "generated_at",
            "generated_by",
            "created_at",
        ),
    )
    op.drop_table(TABLE_NAME, schema=SCHEMA)
