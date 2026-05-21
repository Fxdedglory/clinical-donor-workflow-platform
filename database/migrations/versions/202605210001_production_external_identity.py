"""production external-ready identity foundations

Revision ID: 202605210001
Revises: 202605200003
Create Date: 2026-05-21 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605210001"
down_revision: str | None = "202605200003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"


def _add_archive_columns(table_name: str, *, org_scope: bool = True) -> None:
    if org_scope:
        op.add_column(table_name, sa.Column("organization_id", sa.Integer(), nullable=True), schema=SCHEMA)
        op.create_foreign_key(
            f"fk_{table_name}_organization",
            table_name,
            "dim_organization",
            ["organization_id"],
            ["organization_id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
        )
    op.add_column(
        table_name,
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=SCHEMA,
    )
    op.add_column(table_name, sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA)
    op.add_column(table_name, sa.Column("archived_by", sa.Integer(), nullable=True), schema=SCHEMA)
    op.create_foreign_key(
        f"fk_{table_name}_archived_by",
        table_name,
        "dim_user",
        ["archived_by"],
        ["user_id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )


def upgrade() -> None:
    op.create_table(
        "dim_organization",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("organization_name", sa.String(length=180), nullable=False),
        sa.Column("organization_type", sa.String(length=80), nullable=False, server_default="internal"),
        sa.Column("approval_status", sa.String(length=40), nullable=False, server_default="Approved"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("organization_id"),
        sa.UniqueConstraint("organization_name"),
        schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_operational_dim_organization_organization_id"),
        "dim_organization",
        ["organization_id"],
        schema=SCHEMA,
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.dim_organization (
            organization_id, organization_name, organization_type, approval_status, is_active, created_at
        )
        SELECT
            organization_id,
            organization_name,
            lower(organization_type),
            approval_status,
            is_active,
            created_at
        FROM {SCHEMA}.dim_external_organization
        ON CONFLICT (organization_name) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.dim_organization (
            organization_id, organization_name, organization_type, approval_status, is_active
        )
        VALUES (1, 'Internal Operations', 'internal', 'Approved', true)
        ON CONFLICT (organization_name) DO NOTHING
        """
    )
    op.execute(
        f"""
        SELECT setval(
            pg_get_serial_sequence('{SCHEMA}.dim_organization', 'organization_id'),
            COALESCE((SELECT MAX(organization_id) FROM {SCHEMA}.dim_organization), 1)
        )
        """
    )

    op.create_table(
        "dim_account_type",
        sa.Column("account_type_id", sa.Integer(), nullable=False),
        sa.Column("account_type_name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_external", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("account_type_id"),
        sa.UniqueConstraint("account_type_name"),
        schema=SCHEMA,
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.dim_account_type (
            account_type_name, description, is_internal, is_external, requires_approval
        )
        VALUES
            ('internal', 'Native platform account for internal operations.', true, false, false),
            ('supplier', 'Future supplier account scoped to an approved organization.', false, true, true),
            ('partner', 'Future partner account with organization-scoped access.', false, true, true),
            ('external', 'Future external auditor or contractor account.', false, true, true)
        """
    )

    op.add_column("dim_user", sa.Column("display_name", sa.String(length=120), nullable=True), schema=SCHEMA)
    op.add_column(
        "dim_user",
        sa.Column("account_type", sa.String(length=40), nullable=False, server_default="internal"),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user",
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user",
        sa.Column("is_external", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=SCHEMA,
    )
    op.add_column(
        "dim_user",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema=SCHEMA,
    )
    op.add_column("dim_user", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA)
    op.add_column("dim_user", sa.Column("archived_by", sa.Integer(), nullable=True), schema=SCHEMA)
    op.execute(f"UPDATE {SCHEMA}.dim_user SET display_name = full_name WHERE display_name IS NULL")
    op.execute(
        f"""
        UPDATE {SCHEMA}.dim_user
        SET
            account_type = lower(COALESCE(user_type, 'internal')),
            user_type = lower(COALESCE(user_type, 'internal')),
            identity_provider = 'Platform Native',
            is_internal = lower(COALESCE(user_type, 'internal')) = 'internal',
            is_external = lower(COALESCE(user_type, 'internal')) <> 'internal',
            external_user_flag = lower(COALESCE(user_type, 'internal')) <> 'internal'
        """
    )
    op.drop_constraint("fk_dim_user_external_organization", "dim_user", schema=SCHEMA, type_="foreignkey")
    op.create_foreign_key(
        "fk_dim_user_organization",
        "dim_user",
        "dim_organization",
        ["organization_id"],
        ["organization_id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )

    op.create_table(
        "dim_user_preference",
        sa.Column("preference_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("preference_key", sa.String(length=80), nullable=False),
        sa.Column("preference_value", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("preference_id"),
        sa.UniqueConstraint("user_id", "preference_key", name="uq_user_preference_key"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_dim_user_preference_user_id"), "dim_user_preference", ["user_id"], schema=SCHEMA)

    op.create_table(
        "dim_sidebar_state",
        sa.Column("state_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sidebar_collapsed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_route", sa.String(length=240), nullable=False, server_default="/dashboard"),
        sa.Column("recently_viewed", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("pinned_records", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("state_id"),
        sa.UniqueConstraint("user_id"),
        schema=SCHEMA,
    )

    op.create_table(
        "dim_deployment_environment",
        sa.Column("environment_id", sa.Integer(), nullable=False),
        sa.Column("environment_name", sa.String(length=40), nullable=False),
        sa.Column("base_url", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("database_url_masked", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deployed_version", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("environment_id"),
        sa.UniqueConstraint("environment_name"),
        schema=SCHEMA,
    )

    op.create_table(
        "fact_system_health",
        sa.Column("health_id", sa.Integer(), nullable=False),
        sa.Column("component_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Unknown"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.PrimaryKeyConstraint("health_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_system_health_component_name"), "fact_system_health", ["component_name"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_system_health_checked_at"), "fact_system_health", ["checked_at"], schema=SCHEMA)

    op.create_table(
        "fact_security_incident",
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("incident_key", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False, server_default="Medium"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Open"),
        sa.Column("event_type", sa.String(length=100), nullable=False, server_default="Security Alert"),
        sa.Column("source_event_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.dim_organization.organization_id"]),
        sa.ForeignKeyConstraint(["source_event_id"], [f"{SCHEMA}.fact_security_audit.event_id"]),
        sa.PrimaryKeyConstraint("incident_id"),
        sa.UniqueConstraint("incident_key"),
        schema=SCHEMA,
    )

    op.create_table(
        "fact_data_export",
        sa.Column("export_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("export_type", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("route", sa.String(length=240), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("export_id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_operational_fact_data_export_created_at"), "fact_data_export", ["created_at"], schema=SCHEMA)
    op.create_index(op.f("ix_operational_fact_data_export_user_id"), "fact_data_export", ["user_id"], schema=SCHEMA)

    for table_name in [
        "fact_donor_review",
        "dim_donor",
        "fact_processing_release",
        "fact_deviation",
        "fact_capa",
        "fact_workflow_task",
        "dim_secure_document",
    ]:
        _add_archive_columns(table_name)
        op.execute(f"UPDATE {SCHEMA}.{table_name} SET organization_id = 1 WHERE organization_id IS NULL")

    op.add_column("fact_notification", sa.Column("organization_id", sa.Integer(), nullable=True), schema=SCHEMA)
    op.create_foreign_key(
        "fk_fact_notification_organization",
        "fact_notification",
        "dim_organization",
        ["organization_id"],
        ["organization_id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.execute(f"UPDATE {SCHEMA}.fact_notification SET organization_id = 1 WHERE organization_id IS NULL")

    _add_archive_columns("fact_vendor_incident", org_scope=False)


def downgrade() -> None:
    op.drop_constraint("fk_fact_vendor_incident_archived_by", "fact_vendor_incident", schema=SCHEMA, type_="foreignkey")
    for column in ["archived_by", "archived_at", "is_archived"]:
        op.drop_column("fact_vendor_incident", column, schema=SCHEMA)

    op.drop_constraint("fk_fact_notification_organization", "fact_notification", schema=SCHEMA, type_="foreignkey")
    op.drop_column("fact_notification", "organization_id", schema=SCHEMA)

    for table_name in [
        "dim_secure_document",
        "fact_workflow_task",
        "fact_capa",
        "fact_deviation",
        "fact_processing_release",
        "dim_donor",
        "fact_donor_review",
    ]:
        op.drop_constraint(f"fk_{table_name}_archived_by", table_name, schema=SCHEMA, type_="foreignkey")
        op.drop_constraint(f"fk_{table_name}_organization", table_name, schema=SCHEMA, type_="foreignkey")
        for column in ["archived_by", "archived_at", "is_archived", "organization_id"]:
            op.drop_column(table_name, column, schema=SCHEMA)

    op.drop_index(op.f("ix_operational_fact_data_export_user_id"), table_name="fact_data_export", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_data_export_created_at"), table_name="fact_data_export", schema=SCHEMA)
    op.drop_table("fact_data_export", schema=SCHEMA)
    op.drop_table("fact_security_incident", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_system_health_checked_at"), table_name="fact_system_health", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_fact_system_health_component_name"), table_name="fact_system_health", schema=SCHEMA)
    op.drop_table("fact_system_health", schema=SCHEMA)
    op.drop_table("dim_deployment_environment", schema=SCHEMA)
    op.drop_table("dim_sidebar_state", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_user_preference_user_id"), table_name="dim_user_preference", schema=SCHEMA)
    op.drop_table("dim_user_preference", schema=SCHEMA)

    op.drop_constraint("fk_dim_user_organization", "dim_user", schema=SCHEMA, type_="foreignkey")
    op.create_foreign_key(
        "fk_dim_user_external_organization",
        "dim_user",
        "dim_external_organization",
        ["organization_id"],
        ["organization_id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    for column in [
        "archived_by",
        "archived_at",
        "is_archived",
        "is_external",
        "is_internal",
        "account_type",
        "display_name",
    ]:
        op.drop_column("dim_user", column, schema=SCHEMA)

    op.drop_table("dim_account_type", schema=SCHEMA)
    op.drop_index(op.f("ix_operational_dim_organization_organization_id"), table_name="dim_organization", schema=SCHEMA)
    op.drop_table("dim_organization", schema=SCHEMA)
