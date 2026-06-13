"""clinical reporting analytics readiness

Revision ID: 202606120010
Revises: 202606120009
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120010"
down_revision: str | None = "202606120009"
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


def _create_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_operational_{table_name}_{column}"), table_name, [column], schema=SCHEMA)


def _drop_indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.drop_index(op.f(f"ix_operational_{table_name}_{column}"), table_name=table_name, schema=SCHEMA)


def upgrade() -> None:
    op.create_table(
        "clinical_report_exports",
        sa.Column("export_id", sa.Integer(), nullable=False),
        sa.Column("export_number", sa.String(length=40), nullable=False),
        sa.Column("modules", sa.JSON(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("export_format", sa.String(length=20), nullable=False, server_default="json"),
        sa.Column("row_counts", sa.JSON(), nullable=False),
        sa.Column("payload_metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="generated"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("generated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["generated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("export_id"),
        sa.UniqueConstraint("export_number"),
        schema=SCHEMA,
    )
    _create_indexes(
        "clinical_report_exports",
        ("export_id", "export_number", "date_from", "date_to", "export_format", "status", "generated_at"),
    )

    op.create_table(
        "clinical_report_export_items",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("export_id", sa.Integer(), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("report_name", sa.String(length=120), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["export_id"], [f"{SCHEMA}.clinical_report_exports.export_id"]),
        sa.PrimaryKeyConstraint("item_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_report_export_items", ("item_id", "export_id", "module", "report_name"))

    op.create_table(
        "clinical_report_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("export_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["export_id"], [f"{SCHEMA}.clinical_report_exports.export_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_report_status_history", ("history_id", "export_id", "to_status", "changed_at"))

    read_roles = (
        "System Administrator",
        "Donor Intake Coordinator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
        "Business Technology Analyst",
    )
    export_roles = ("System Administrator", "Quality Assurance Specialist", "Operations Manager", "Business Technology Analyst")
    _grant_permission(read_roles, "reports.read")
    _grant_permission(export_roles, "reports.export")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('reports.read', 'reports.export')
        """
    )

    _drop_indexes("clinical_report_status_history", ("history_id", "export_id", "to_status", "changed_at"))
    op.drop_table("clinical_report_status_history", schema=SCHEMA)

    _drop_indexes("clinical_report_export_items", ("item_id", "export_id", "module", "report_name"))
    op.drop_table("clinical_report_export_items", schema=SCHEMA)

    _drop_indexes(
        "clinical_report_exports",
        ("export_id", "export_number", "date_from", "date_to", "export_format", "status", "generated_at"),
    )
    op.drop_table("clinical_report_exports", schema=SCHEMA)
