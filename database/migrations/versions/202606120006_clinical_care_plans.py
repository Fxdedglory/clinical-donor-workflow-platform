"""clinical care plans

Revision ID: 202606120006
Revises: 202606120005
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120006"
down_revision: str | None = "202606120005"
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
        "clinical_care_plans",
        sa.Column("care_plan_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_number", sa.String(length=40), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("screening_session_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("order_result_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("plan_type", sa.String(length=80), nullable=False, server_default="case_management"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="routine"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("closure_reason", sa.Text(), nullable=True),
        sa.Column("outcome_summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_care_plans"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["closed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.ForeignKeyConstraint(["order_id"], [f"{SCHEMA}.clinical_orders.order_id"]),
        sa.ForeignKeyConstraint(["order_result_id"], [f"{SCHEMA}.clinical_order_results.result_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["screening_session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("care_plan_id"),
        sa.UniqueConstraint("care_plan_number"),
        schema=SCHEMA,
    )
    for column in [
        "care_plan_id",
        "care_plan_number",
        "patient_pk",
        "encounter_id",
        "screening_session_id",
        "order_id",
        "order_result_id",
        "title",
        "plan_type",
        "priority",
        "status",
        "start_date",
        "target_date",
    ]:
        op.create_index(op.f(f"ix_operational_clinical_care_plans_{column}"), "clinical_care_plans", [column], schema=SCHEMA)

    op.create_table(
        "clinical_care_plan_goals",
        sa.Column("goal_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_id", sa.Integer(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("priority", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("goal_id"),
        schema=SCHEMA,
    )
    for column in ["goal_id", "care_plan_id", "target_date", "status", "priority"]:
        op.create_index(op.f(f"ix_operational_clinical_care_plan_goals_{column}"), "clinical_care_plan_goals", [column], schema=SCHEMA)

    op.create_table(
        "clinical_care_plan_interventions",
        sa.Column("intervention_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_id", sa.Integer(), nullable=False),
        sa.Column("intervention", sa.Text(), nullable=False),
        sa.Column("intervention_type", sa.String(length=80), nullable=False, server_default="follow_up"),
        sa.Column("owner", sa.String(length=160), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="planned"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("intervention_id"),
        schema=SCHEMA,
    )
    for column in ["intervention_id", "care_plan_id", "intervention_type", "owner", "due_date", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_care_plan_interventions_{column}"), "clinical_care_plan_interventions", [column], schema=SCHEMA)

    op.create_table(
        "clinical_care_plan_tasks",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=160), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="routine"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["completed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("task_id"),
        schema=SCHEMA,
    )
    for column in ["task_id", "care_plan_id", "title", "owner", "due_date", "priority", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_care_plan_tasks_{column}"), "clinical_care_plan_tasks", [column], schema=SCHEMA)

    op.create_table(
        "clinical_care_plan_progress_notes",
        sa.Column("progress_note_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_id", sa.Integer(), nullable=False),
        sa.Column("progress_note", sa.Text(), nullable=False),
        sa.Column("status_update", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("progress_note_id"),
        schema=SCHEMA,
    )
    for column in ["progress_note_id", "care_plan_id", "status_update", "created_at"]:
        op.create_index(op.f(f"ix_operational_clinical_care_plan_progress_notes_{column}"), "clinical_care_plan_progress_notes", [column], schema=SCHEMA)

    op.create_table(
        "clinical_care_plan_team_members",
        sa.Column("team_member_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_id", sa.Integer(), nullable=False),
        sa.Column("member_name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False, server_default="care_team"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("team_member_id"),
        schema=SCHEMA,
    )
    for column in ["team_member_id", "care_plan_id", "member_name", "role"]:
        op.create_index(op.f(f"ix_operational_clinical_care_plan_team_members_{column}"), "clinical_care_plan_team_members", [column], schema=SCHEMA)

    op.create_table(
        "clinical_care_plan_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["care_plan_id"], [f"{SCHEMA}.clinical_care_plans.care_plan_id"]),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    for column in ["history_id", "care_plan_id", "to_status", "changed_at"]:
        op.create_index(op.f(f"ix_operational_clinical_care_plan_status_history_{column}"), "clinical_care_plan_status_history", [column], schema=SCHEMA)

    read_roles = (
        "System Administrator",
        "Donor Intake Coordinator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    manage_roles = read_roles
    close_roles = (
        "System Administrator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    _grant_permission(read_roles, "care_plans.read")
    _grant_permission(manage_roles, "care_plans.manage")
    _grant_permission(close_roles, "care_plans.close")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('care_plans.read', 'care_plans.manage', 'care_plans.close')
        """
    )

    for column in ["history_id", "care_plan_id", "to_status", "changed_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_care_plan_status_history_{column}"), table_name="clinical_care_plan_status_history", schema=SCHEMA)
    op.drop_table("clinical_care_plan_status_history", schema=SCHEMA)

    for column in ["team_member_id", "care_plan_id", "member_name", "role"]:
        op.drop_index(op.f(f"ix_operational_clinical_care_plan_team_members_{column}"), table_name="clinical_care_plan_team_members", schema=SCHEMA)
    op.drop_table("clinical_care_plan_team_members", schema=SCHEMA)

    for column in ["progress_note_id", "care_plan_id", "status_update", "created_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_care_plan_progress_notes_{column}"), table_name="clinical_care_plan_progress_notes", schema=SCHEMA)
    op.drop_table("clinical_care_plan_progress_notes", schema=SCHEMA)

    for column in ["task_id", "care_plan_id", "title", "owner", "due_date", "priority", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_care_plan_tasks_{column}"), table_name="clinical_care_plan_tasks", schema=SCHEMA)
    op.drop_table("clinical_care_plan_tasks", schema=SCHEMA)

    for column in ["intervention_id", "care_plan_id", "intervention_type", "owner", "due_date", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_care_plan_interventions_{column}"), table_name="clinical_care_plan_interventions", schema=SCHEMA)
    op.drop_table("clinical_care_plan_interventions", schema=SCHEMA)

    for column in ["goal_id", "care_plan_id", "target_date", "status", "priority"]:
        op.drop_index(op.f(f"ix_operational_clinical_care_plan_goals_{column}"), table_name="clinical_care_plan_goals", schema=SCHEMA)
    op.drop_table("clinical_care_plan_goals", schema=SCHEMA)

    for column in [
        "care_plan_id",
        "care_plan_number",
        "patient_pk",
        "encounter_id",
        "screening_session_id",
        "order_id",
        "order_result_id",
        "title",
        "plan_type",
        "priority",
        "status",
        "start_date",
        "target_date",
    ]:
        op.drop_index(op.f(f"ix_operational_clinical_care_plans_{column}"), table_name="clinical_care_plans", schema=SCHEMA)
    op.drop_table("clinical_care_plans", schema=SCHEMA)
