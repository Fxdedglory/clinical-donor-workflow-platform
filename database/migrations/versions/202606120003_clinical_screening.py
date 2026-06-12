"""clinical screening

Revision ID: 202606120003
Revises: 202606120002
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120003"
down_revision: str | None = "202606120002"
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
        "clinical_screening_sessions",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("session_number", sa.String(length=40), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("donor_pk", sa.Integer(), nullable=True),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.String(length=80), nullable=False, server_default="minimal_donor_screening_v1"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="not_started"),
        sa.Column("current_outcome", sa.String(length=80), nullable=True),
        sa.Column("supervisor_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_screening"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["appointment_id"], [f"{SCHEMA}.appointments.appointment_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{SCHEMA}.dim_donor.donor_pk"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("session_id"),
        sa.UniqueConstraint("session_number"),
        schema=SCHEMA,
    )
    for column in [
        "session_id",
        "session_number",
        "patient_pk",
        "donor_pk",
        "appointment_id",
        "status",
        "current_outcome",
    ]:
        op.create_index(op.f(f"ix_operational_clinical_screening_sessions_{column}"), "clinical_screening_sessions", [column], schema=SCHEMA)

    op.create_table(
        "clinical_screening_answers",
        sa.Column("answer_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("question_key", sa.String(length=120), nullable=False),
        sa.Column("answer_value", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("answer_id"),
        schema=SCHEMA,
    )
    for column in ["answer_id", "session_id", "question_key"]:
        op.create_index(op.f(f"ix_operational_clinical_screening_answers_{column}"), "clinical_screening_answers", [column], schema=SCHEMA)

    op.create_table(
        "clinical_screening_vitals",
        sa.Column("vitals_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("blood_pressure_systolic", sa.Integer(), nullable=False),
        sa.Column("blood_pressure_diastolic", sa.Integer(), nullable=False),
        sa.Column("pulse", sa.Integer(), nullable=False),
        sa.Column("respiration_rate", sa.Integer(), nullable=True),
        sa.Column("oxygen_saturation", sa.Float(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("captured_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["captured_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.PrimaryKeyConstraint("vitals_id"),
        schema=SCHEMA,
    )
    for column in ["vitals_id", "session_id", "captured_at"]:
        op.create_index(op.f(f"ix_operational_clinical_screening_vitals_{column}"), "clinical_screening_vitals", [column], schema=SCHEMA)

    op.create_table(
        "clinical_screening_outcomes",
        sa.Column("outcome_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("proposed_outcome", sa.String(length=80), nullable=True),
        sa.Column("committed_outcome", sa.String(length=80), nullable=True),
        sa.Column("original_outcome", sa.String(length=80), nullable=True),
        sa.Column("override_outcome", sa.String(length=80), nullable=True),
        sa.Column("deferral_type", sa.String(length=40), nullable=True),
        sa.Column("supervisor_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocking_issues", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("rule_results", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.PrimaryKeyConstraint("outcome_id"),
        schema=SCHEMA,
    )
    for column in ["outcome_id", "session_id", "committed_outcome", "created_at"]:
        op.create_index(op.f(f"ix_operational_clinical_screening_outcomes_{column}"), "clinical_screening_outcomes", [column], schema=SCHEMA)

    op.create_table(
        "clinical_deferrals",
        sa.Column("deferral_id", sa.Integer(), nullable=False),
        sa.Column("deferral_number", sa.String(length=40), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("donor_pk", sa.Integer(), nullable=True),
        sa.Column("deferral_type", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{SCHEMA}.dim_donor.donor_pk"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.PrimaryKeyConstraint("deferral_id"),
        sa.UniqueConstraint("deferral_number"),
        schema=SCHEMA,
    )
    for column in ["deferral_id", "deferral_number", "session_id", "patient_pk", "donor_pk", "deferral_type", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_deferrals_{column}"), "clinical_deferrals", [column], schema=SCHEMA)

    op.create_table(
        "clinical_screening_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=60), nullable=True),
        sa.Column("to_status", sa.String(length=60), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    for column in ["history_id", "session_id", "to_status", "changed_at"]:
        op.create_index(op.f(f"ix_operational_clinical_screening_status_history_{column}"), "clinical_screening_status_history", [column], schema=SCHEMA)

    read_roles = (
        "System Administrator",
        "Donor Intake Coordinator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    manage_roles = (
        "System Administrator",
        "Donor Intake Coordinator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    override_roles = (
        "System Administrator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    _grant_permission(read_roles, "screening.read")
    _grant_permission(manage_roles, "screening.manage")
    _grant_permission(override_roles, "screening.override")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('screening.read', 'screening.manage', 'screening.override')
        """
    )

    for column in ["history_id", "session_id", "to_status", "changed_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_screening_status_history_{column}"), table_name="clinical_screening_status_history", schema=SCHEMA)
    op.drop_table("clinical_screening_status_history", schema=SCHEMA)

    for column in ["deferral_id", "deferral_number", "session_id", "patient_pk", "donor_pk", "deferral_type", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_deferrals_{column}"), table_name="clinical_deferrals", schema=SCHEMA)
    op.drop_table("clinical_deferrals", schema=SCHEMA)

    for column in ["outcome_id", "session_id", "committed_outcome", "created_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_screening_outcomes_{column}"), table_name="clinical_screening_outcomes", schema=SCHEMA)
    op.drop_table("clinical_screening_outcomes", schema=SCHEMA)

    for column in ["vitals_id", "session_id", "captured_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_screening_vitals_{column}"), table_name="clinical_screening_vitals", schema=SCHEMA)
    op.drop_table("clinical_screening_vitals", schema=SCHEMA)

    for column in ["answer_id", "session_id", "question_key"]:
        op.drop_index(op.f(f"ix_operational_clinical_screening_answers_{column}"), table_name="clinical_screening_answers", schema=SCHEMA)
    op.drop_table("clinical_screening_answers", schema=SCHEMA)

    for column in [
        "session_id",
        "session_number",
        "patient_pk",
        "donor_pk",
        "appointment_id",
        "status",
        "current_outcome",
    ]:
        op.drop_index(op.f(f"ix_operational_clinical_screening_sessions_{column}"), table_name="clinical_screening_sessions", schema=SCHEMA)
    op.drop_table("clinical_screening_sessions", schema=SCHEMA)
