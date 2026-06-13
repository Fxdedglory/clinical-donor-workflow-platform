"""clinical administration foundation

Revision ID: 202606120009
Revises: 202606120008
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120009"
down_revision: str | None = "202606120008"
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
    op.add_column(
        "appointment_types",
        sa.Column("category", sa.String(length=80), nullable=False, server_default="general"),
        schema=SCHEMA,
    )
    op.add_column(
        "appointment_types",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        schema=SCHEMA,
    )
    op.add_column(
        "appointment_types",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_appointment_types_category"), "appointment_types", ["category"], schema=SCHEMA)

    op.add_column(
        "clinical_note_templates",
        sa.Column("sections", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        schema=SCHEMA,
    )
    op.add_column(
        "clinical_order_catalog_items",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        schema=SCHEMA,
    )

    op.create_table(
        "clinical_admin_config_versions",
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("config_type", sa.String(length=100), nullable=False),
        sa.Column("config_key", sa.String(length=160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("version_id"),
        schema=SCHEMA,
    )
    _create_indexes(
        "clinical_admin_config_versions",
        ("version_id", "config_type", "config_key", "version", "status", "entity_type", "entity_id", "effective_from"),
    )

    op.create_table(
        "clinical_provider_schedule_templates",
        sa.Column("schedule_template_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("date_pattern", sa.String(length=80), nullable=False, server_default="weekly"),
        sa.Column("start_time", sa.Time(timezone=False), nullable=False),
        sa.Column("end_time", sa.Time(timezone=False), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["provider_id"], [f"{SCHEMA}.clinical_providers.provider_id"]),
        sa.ForeignKeyConstraint(["room_id"], [f"{SCHEMA}.clinical_rooms.room_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("schedule_template_id"),
        schema=SCHEMA,
    )
    _create_indexes(
        "clinical_provider_schedule_templates",
        ("schedule_template_id", "provider_id", "weekday", "date_pattern", "room_id", "active"),
    )

    op.create_table(
        "clinical_screening_template_versions",
        sa.Column("template_version_id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=False),
        sa.Column("template_name", sa.String(length=180), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("required_questions", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["retired_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("template_version_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_screening_template_versions", ("template_version_id", "template_key", "template_name", "version", "active"))

    for table_name, default_type in (
        ("clinical_eligibility_rule_versions", "eligibility"),
        ("clinical_deferral_rule_versions", "deferral"),
    ):
        op.create_table(
            table_name,
            sa.Column("rule_version_id", sa.Integer(), nullable=False),
            sa.Column("rule_key", sa.String(length=100), nullable=False),
            sa.Column("rule_name", sa.String(length=180), nullable=False),
            sa.Column("rule_type", sa.String(length=80), nullable=False, server_default=default_type),
            sa.Column("severity", sa.String(length=40), nullable=False, server_default="medium"),
            sa.Column("expression", sa.Text(), nullable=False, server_default=""),
            sa.Column("criteria", sa.JSON(), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("retired_by", sa.Integer(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False, server_default=""),
            sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
            sa.ForeignKeyConstraint(["retired_by"], [f"{SCHEMA}.dim_user.user_id"]),
            sa.PrimaryKeyConstraint("rule_version_id"),
            schema=SCHEMA,
        )
        _create_indexes(table_name, ("rule_version_id", "rule_key", "rule_name", "rule_type", "severity", "active", "version"))

    op.create_table(
        "clinical_billing_code_catalog",
        sa.Column("code_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("code_type", sa.String(length=40), nullable=False, server_default="internal"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("code_id"),
        sa.UniqueConstraint("code"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_billing_code_catalog", ("code_id", "code", "code_type", "active"))

    op.create_table(
        "clinical_quality_categories",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("category_key", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=160), nullable=False),
        sa.Column("severity_mapping", sa.JSON(), nullable=False),
        sa.Column("closure_approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("category_id"),
        sa.UniqueConstraint("category_key"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_quality_categories", ("category_id", "category_key", "category", "active"))

    op.create_table(
        "clinical_quality_severity_matrix",
        sa.Column("matrix_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("response_sla_hours", sa.Integer(), nullable=False, server_default="72"),
        sa.Column("investigation_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("matrix_id"),
        sa.UniqueConstraint("severity"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_quality_severity_matrix", ("matrix_id", "severity", "active"))

    op.create_table(
        "clinical_admin_approval_paths",
        sa.Column("path_id", sa.Integer(), nullable=False),
        sa.Column("workflow", sa.String(length=120), nullable=False),
        sa.Column("path_name", sa.String(length=180), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("path_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_admin_approval_paths", ("path_id", "workflow", "path_name", "version", "active"))

    op.create_table(
        "clinical_admin_approval_steps",
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("path_id", sa.Integer(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("permission", sa.String(length=120), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["path_id"], [f"{SCHEMA}.clinical_admin_approval_paths.path_id"]),
        sa.PrimaryKeyConstraint("step_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_admin_approval_steps", ("step_id", "path_id", "step_order", "role", "permission", "active"))

    op.create_table(
        "clinical_notification_templates",
        sa.Column("notification_template_id", sa.Integer(), nullable=False),
        sa.Column("workflow", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False, server_default="in_app"),
        sa.Column("subject", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("notification_template_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_notification_templates", ("notification_template_id", "workflow", "channel", "active"))

    op.create_table(
        "clinical_admin_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("config_type", sa.String(length=100), nullable=False),
        sa.Column("config_id", sa.String(length=120), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_admin_status_history", ("history_id", "config_type", "config_id", "to_status", "changed_at"))

    read_roles = ("System Administrator", "Clinical Reviewer", "Quality Assurance Specialist", "Operations Manager", "Business Technology Analyst")
    manage_roles = ("System Administrator", "Quality Assurance Specialist", "Operations Manager")
    _grant_permission(read_roles, "clinical_admin.read")
    _grant_permission(manage_roles, "clinical_admin.manage")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('clinical_admin.read', 'clinical_admin.manage')
        """
    )

    _drop_indexes("clinical_admin_status_history", ("history_id", "config_type", "config_id", "to_status", "changed_at"))
    op.drop_table("clinical_admin_status_history", schema=SCHEMA)

    _drop_indexes("clinical_notification_templates", ("notification_template_id", "workflow", "channel", "active"))
    op.drop_table("clinical_notification_templates", schema=SCHEMA)

    _drop_indexes("clinical_admin_approval_steps", ("step_id", "path_id", "step_order", "role", "permission", "active"))
    op.drop_table("clinical_admin_approval_steps", schema=SCHEMA)

    _drop_indexes("clinical_admin_approval_paths", ("path_id", "workflow", "path_name", "version", "active"))
    op.drop_table("clinical_admin_approval_paths", schema=SCHEMA)

    _drop_indexes("clinical_quality_severity_matrix", ("matrix_id", "severity", "active"))
    op.drop_table("clinical_quality_severity_matrix", schema=SCHEMA)

    _drop_indexes("clinical_quality_categories", ("category_id", "category_key", "category", "active"))
    op.drop_table("clinical_quality_categories", schema=SCHEMA)

    _drop_indexes("clinical_billing_code_catalog", ("code_id", "code", "code_type", "active"))
    op.drop_table("clinical_billing_code_catalog", schema=SCHEMA)

    for table_name in ("clinical_deferral_rule_versions", "clinical_eligibility_rule_versions"):
        _drop_indexes(table_name, ("rule_version_id", "rule_key", "rule_name", "rule_type", "severity", "active", "version"))
        op.drop_table(table_name, schema=SCHEMA)

    _drop_indexes("clinical_screening_template_versions", ("template_version_id", "template_key", "template_name", "version", "active"))
    op.drop_table("clinical_screening_template_versions", schema=SCHEMA)

    _drop_indexes(
        "clinical_provider_schedule_templates",
        ("schedule_template_id", "provider_id", "weekday", "date_pattern", "room_id", "active"),
    )
    op.drop_table("clinical_provider_schedule_templates", schema=SCHEMA)

    _drop_indexes(
        "clinical_admin_config_versions",
        ("version_id", "config_type", "config_key", "version", "status", "entity_type", "entity_id", "effective_from"),
    )
    op.drop_table("clinical_admin_config_versions", schema=SCHEMA)

    op.drop_column("clinical_order_catalog_items", "version", schema=SCHEMA)
    op.drop_column("clinical_note_templates", "sections", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_appointment_types_category"), table_name="appointment_types", schema=SCHEMA)
    op.drop_column("appointment_types", "version", schema=SCHEMA)
    op.drop_column("appointment_types", "description", schema=SCHEMA)
    op.drop_column("appointment_types", "category", schema=SCHEMA)
