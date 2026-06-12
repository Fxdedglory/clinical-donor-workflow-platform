"""clinical orders and results

Revision ID: 202606120005
Revises: 202606120004
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120005"
down_revision: str | None = "202606120004"
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


def upgrade() -> None:
    op.create_table(
        "clinical_order_catalog_items",
        sa.Column("catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("order_type", sa.String(length=80), nullable=False, server_default="laboratory"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_priority", sa.String(length=40), nullable=False, server_default="routine"),
        sa.Column("specimen_type", sa.String(length=120), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("catalog_item_id"),
        sa.UniqueConstraint("code"),
        schema=SCHEMA,
    )
    for column in ["catalog_item_id", "code", "name", "order_type", "active"]:
        op.create_index(op.f(f"ix_operational_clinical_order_catalog_items_{column}"), "clinical_order_catalog_items", [column], schema=SCHEMA)

    op.create_table(
        "clinical_orders",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("order_number", sa.String(length=40), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("screening_session_id", sa.Integer(), nullable=True),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("order_type", sa.String(length=80), nullable=False, server_default="laboratory"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="routine"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="ordered"),
        sa.Column("clinical_indication", sa.Text(), nullable=False, server_default=""),
        sa.Column("ordering_provider", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_orders"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["appointment_id"], [f"{SCHEMA}.appointments.appointment_id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["catalog_item_id"], [f"{SCHEMA}.clinical_order_catalog_items.catalog_item_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["screening_session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("order_id"),
        sa.UniqueConstraint("order_number"),
        schema=SCHEMA,
    )
    for column in [
        "order_id",
        "order_number",
        "patient_pk",
        "encounter_id",
        "screening_session_id",
        "appointment_id",
        "catalog_item_id",
        "order_type",
        "priority",
        "status",
        "ordered_at",
    ]:
        op.create_index(op.f(f"ix_operational_clinical_orders_{column}"), "clinical_orders", [column], schema=SCHEMA)

    op.create_table(
        "clinical_order_results",
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("result_name", sa.String(length=180), nullable=False),
        sa.Column("result_value", sa.String(length=180), nullable=False),
        sa.Column("result_unit", sa.String(length=80), nullable=True),
        sa.Column("reference_range", sa.String(length=160), nullable=True),
        sa.Column("result_status", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("abnormal_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("critical_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resulted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resulted_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("corrected_from_result_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["corrected_from_result_id"], [f"{SCHEMA}.clinical_order_results.result_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["order_id"], [f"{SCHEMA}.clinical_orders.order_id"]),
        sa.ForeignKeyConstraint(["resulted_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("result_id"),
        schema=SCHEMA,
    )
    for column in ["result_id", "order_id", "result_name", "result_status", "abnormal_flag", "critical_flag", "resulted_at", "corrected_from_result_id"]:
        op.create_index(op.f(f"ix_operational_clinical_order_results_{column}"), "clinical_order_results", [column], schema=SCHEMA)

    op.create_table(
        "clinical_order_result_acknowledgements",
        sa.Column("acknowledgement_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("acknowledged_by", sa.Integer(), nullable=True),
        sa.Column("acknowledgement_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["acknowledged_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["order_id"], [f"{SCHEMA}.clinical_orders.order_id"]),
        sa.ForeignKeyConstraint(["result_id"], [f"{SCHEMA}.clinical_order_results.result_id"]),
        sa.PrimaryKeyConstraint("acknowledgement_id"),
        schema=SCHEMA,
    )
    for column in ["acknowledgement_id", "order_id", "result_id", "acknowledged_at"]:
        op.create_index(op.f(f"ix_operational_clinical_order_result_acknowledgements_{column}"), "clinical_order_result_acknowledgements", [column], schema=SCHEMA)

    op.create_table(
        "clinical_order_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["order_id"], [f"{SCHEMA}.clinical_orders.order_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    for column in ["history_id", "order_id", "to_status", "changed_at"]:
        op.create_index(op.f(f"ix_operational_clinical_order_status_history_{column}"), "clinical_order_status_history", [column], schema=SCHEMA)

    op.execute(
        f"""
        INSERT INTO {SCHEMA}.clinical_order_catalog_items
            (code, name, order_type, description, default_priority, specimen_type)
        VALUES
            ('ID-NAT-PANEL', 'Infectious disease NAT panel', 'infectious_disease', 'Clinical order wrapper for existing donor infectious disease testing assets.', 'urgent', 'blood'),
            ('ID-SEROLOGY-PANEL', 'Infectious disease serology panel', 'infectious_disease', 'Serology testing catalog entry preserving existing donor eligibility result facts.', 'routine', 'blood'),
            ('CBC', 'Complete blood count', 'laboratory', 'General hematology screening order.', 'routine', 'whole blood'),
            ('CMP', 'Comprehensive metabolic panel', 'laboratory', 'General chemistry screening order.', 'routine', 'serum')
        ON CONFLICT (code) DO NOTHING
        """
    )

    read_roles = (
        "System Administrator",
        "Donor Intake Coordinator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    manage_roles = read_roles
    acknowledge_roles = (
        "System Administrator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    _grant_permission(read_roles, "orders.read")
    _grant_permission(manage_roles, "orders.manage")
    _grant_permission(acknowledge_roles, "orders.acknowledge")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('orders.read', 'orders.manage', 'orders.acknowledge')
        """
    )

    for column in ["history_id", "order_id", "to_status", "changed_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_order_status_history_{column}"), table_name="clinical_order_status_history", schema=SCHEMA)
    op.drop_table("clinical_order_status_history", schema=SCHEMA)

    for column in ["acknowledgement_id", "order_id", "result_id", "acknowledged_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_order_result_acknowledgements_{column}"), table_name="clinical_order_result_acknowledgements", schema=SCHEMA)
    op.drop_table("clinical_order_result_acknowledgements", schema=SCHEMA)

    for column in ["result_id", "order_id", "result_name", "result_status", "abnormal_flag", "critical_flag", "resulted_at", "corrected_from_result_id"]:
        op.drop_index(op.f(f"ix_operational_clinical_order_results_{column}"), table_name="clinical_order_results", schema=SCHEMA)
    op.drop_table("clinical_order_results", schema=SCHEMA)

    for column in [
        "order_id",
        "order_number",
        "patient_pk",
        "encounter_id",
        "screening_session_id",
        "appointment_id",
        "catalog_item_id",
        "order_type",
        "priority",
        "status",
        "ordered_at",
    ]:
        op.drop_index(op.f(f"ix_operational_clinical_orders_{column}"), table_name="clinical_orders", schema=SCHEMA)
    op.drop_table("clinical_orders", schema=SCHEMA)

    for column in ["catalog_item_id", "code", "name", "order_type", "active"]:
        op.drop_index(op.f(f"ix_operational_clinical_order_catalog_items_{column}"), table_name="clinical_order_catalog_items", schema=SCHEMA)
    op.drop_table("clinical_order_catalog_items", schema=SCHEMA)
