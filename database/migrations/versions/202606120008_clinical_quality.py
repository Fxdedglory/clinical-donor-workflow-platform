"""clinical quality compliance

Revision ID: 202606120008
Revises: 202606120007
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120008"
down_revision: str | None = "202606120007"
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
        "clinical_quality_events",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("event_number", sa.String(length=40), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=True),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("screening_session_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("order_result_id", sa.Integer(), nullable=True),
        sa.Column("care_plan_id", sa.Integer(), nullable=True),
        sa.Column("charge_id", sa.Integer(), nullable=True),
        sa.Column("claim_id", sa.Integer(), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("denial_id", sa.Integer(), nullable=True),
        sa.Column("deviation_id", sa.Integer(), nullable=True),
        sa.Column("capa_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("owner", sa.String(length=160), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("source_module", sa.String(length=80), nullable=False, server_default="clinical_quality"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("closure_reason", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["appointment_id"], [f"{SCHEMA}.appointments.appointment_id"]),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["capa_id"], [f"{SCHEMA}.fact_capa.capa_id"]),
        sa.ForeignKeyConstraint(["charge_id"], [f"{SCHEMA}.clinical_charges.charge_id"]),
        sa.ForeignKeyConstraint(["claim_id"], [f"{SCHEMA}.clinical_claims.claim_id"]),
        sa.ForeignKeyConstraint(["closed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["denial_id"], [f"{SCHEMA}.clinical_denials.denial_id"]),
        sa.ForeignKeyConstraint(["deviation_id"], [f"{SCHEMA}.fact_deviation.deviation_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.ForeignKeyConstraint(["order_id"], [f"{SCHEMA}.clinical_orders.order_id"]),
        sa.ForeignKeyConstraint(["order_result_id"], [f"{SCHEMA}.clinical_order_results.result_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["payment_id"], [f"{SCHEMA}.clinical_payments.payment_id"]),
        sa.ForeignKeyConstraint(["screening_session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("event_number"),
        schema=SCHEMA,
    )
    _create_indexes(
        "clinical_quality_events",
        (
            "event_id",
            "event_number",
            "patient_pk",
            "appointment_id",
            "screening_session_id",
            "encounter_id",
            "order_id",
            "order_result_id",
            "care_plan_id",
            "charge_id",
            "claim_id",
            "payment_id",
            "denial_id",
            "deviation_id",
            "capa_id",
            "category",
            "severity",
            "status",
            "owner",
            "due_date",
            "source_module",
        ),
    )

    op.create_table(
        "clinical_adverse_events",
        sa.Column("adverse_event_id", sa.Integer(), nullable=False),
        sa.Column("adverse_event_number", sa.String(length=40), nullable=False),
        sa.Column("quality_event_id", sa.Integer(), nullable=True),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("screening_session_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("order_result_id", sa.Integer(), nullable=True),
        sa.Column("care_plan_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("immediate_action_taken", sa.Text(), nullable=False, server_default=""),
        sa.Column("reporter", sa.String(length=160), nullable=False),
        sa.Column("follow_up_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.ForeignKeyConstraint(["order_id"], [f"{SCHEMA}.clinical_orders.order_id"]),
        sa.ForeignKeyConstraint(["order_result_id"], [f"{SCHEMA}.clinical_order_results.result_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["quality_event_id"], [f"{SCHEMA}.clinical_quality_events.event_id"]),
        sa.ForeignKeyConstraint(["screening_session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("adverse_event_id"),
        sa.UniqueConstraint("adverse_event_number"),
        schema=SCHEMA,
    )
    _create_indexes(
        "clinical_adverse_events",
        (
            "adverse_event_id",
            "adverse_event_number",
            "quality_event_id",
            "patient_pk",
            "screening_session_id",
            "encounter_id",
            "order_id",
            "order_result_id",
            "care_plan_id",
            "event_type",
            "severity",
            "event_at",
            "reporter",
            "status",
        ),
    )

    op.create_table(
        "clinical_quality_event_links",
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=220), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["event_id"], [f"{SCHEMA}.clinical_quality_events.event_id"]),
        sa.PrimaryKeyConstraint("link_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_quality_event_links", ("link_id", "event_id", "entity_type", "entity_id"))

    op.create_table(
        "clinical_quality_investigations",
        sa.Column("investigation_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=160), nullable=True),
        sa.Column("finding", sa.Text(), nullable=True),
        sa.Column("root_cause_category", sa.String(length=120), nullable=True),
        sa.Column("corrective_action_recommendation", sa.Text(), nullable=True),
        sa.Column("follow_up_due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["event_id"], [f"{SCHEMA}.clinical_quality_events.event_id"]),
        sa.PrimaryKeyConstraint("investigation_id"),
        schema=SCHEMA,
    )
    _create_indexes(
        "clinical_quality_investigations",
        ("investigation_id", "event_id", "owner", "root_cause_category", "follow_up_due_date", "created_at"),
    )

    op.create_table(
        "clinical_quality_approvals",
        sa.Column("approval_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("approval_type", sa.String(length=80), nullable=False, server_default="closure"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="approved"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["approved_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["event_id"], [f"{SCHEMA}.clinical_quality_events.event_id"]),
        sa.PrimaryKeyConstraint("approval_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_quality_approvals", ("approval_id", "event_id", "approval_type", "status", "approved_at"))

    op.create_table(
        "clinical_compliance_exports",
        sa.Column("export_id", sa.Integer(), nullable=False),
        sa.Column("export_number", sa.String(length=40), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("modules", sa.JSON(), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="generated"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("generated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["generated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("export_id"),
        sa.UniqueConstraint("export_number"),
        schema=SCHEMA,
    )
    _create_indexes(
        "clinical_compliance_exports",
        ("export_id", "export_number", "date_from", "date_to", "status", "generated_at"),
    )

    op.create_table(
        "clinical_quality_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["event_id"], [f"{SCHEMA}.clinical_quality_events.event_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    _create_indexes("clinical_quality_status_history", ("history_id", "event_id", "to_status", "changed_at"))

    quality_roles = ("System Administrator", "Clinical Reviewer", "Quality Assurance Specialist", "Operations Manager")
    manager_roles = ("System Administrator", "Quality Assurance Specialist", "Operations Manager")
    close_roles = ("System Administrator", "Quality Assurance Specialist")
    _grant_permission(quality_roles, "quality.read")
    _grant_permission(manager_roles, "quality.manage")
    _grant_permission(close_roles, "quality.close")
    _grant_permission(manager_roles, "quality.export")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('quality.read', 'quality.manage', 'quality.close', 'quality.export')
        """
    )

    _drop_indexes("clinical_quality_status_history", ("history_id", "event_id", "to_status", "changed_at"))
    op.drop_table("clinical_quality_status_history", schema=SCHEMA)

    _drop_indexes("clinical_compliance_exports", ("export_id", "export_number", "date_from", "date_to", "status", "generated_at"))
    op.drop_table("clinical_compliance_exports", schema=SCHEMA)

    _drop_indexes("clinical_quality_approvals", ("approval_id", "event_id", "approval_type", "status", "approved_at"))
    op.drop_table("clinical_quality_approvals", schema=SCHEMA)

    _drop_indexes(
        "clinical_quality_investigations",
        ("investigation_id", "event_id", "owner", "root_cause_category", "follow_up_due_date", "created_at"),
    )
    op.drop_table("clinical_quality_investigations", schema=SCHEMA)

    _drop_indexes("clinical_quality_event_links", ("link_id", "event_id", "entity_type", "entity_id"))
    op.drop_table("clinical_quality_event_links", schema=SCHEMA)

    _drop_indexes(
        "clinical_adverse_events",
        (
            "adverse_event_id",
            "adverse_event_number",
            "quality_event_id",
            "patient_pk",
            "screening_session_id",
            "encounter_id",
            "order_id",
            "order_result_id",
            "care_plan_id",
            "event_type",
            "severity",
            "event_at",
            "reporter",
            "status",
        ),
    )
    op.drop_table("clinical_adverse_events", schema=SCHEMA)

    _drop_indexes(
        "clinical_quality_events",
        (
            "event_id",
            "event_number",
            "patient_pk",
            "appointment_id",
            "screening_session_id",
            "encounter_id",
            "order_id",
            "order_result_id",
            "care_plan_id",
            "charge_id",
            "claim_id",
            "payment_id",
            "denial_id",
            "deviation_id",
            "capa_id",
            "category",
            "severity",
            "status",
            "owner",
            "due_date",
            "source_module",
        ),
    )
    op.drop_table("clinical_quality_events", schema=SCHEMA)
