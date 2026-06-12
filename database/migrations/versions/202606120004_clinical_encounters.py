"""clinical encounters

Revision ID: 202606120004
Revises: 202606120003
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120004"
down_revision: str | None = "202606120003"
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
        "clinical_note_templates",
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("note_type", sa.String(length=80), nullable=False, server_default="clinical_note"),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("template_id"),
        sa.UniqueConstraint("template_key"),
        schema=SCHEMA,
    )
    for column in ["template_id", "template_key", "name", "note_type", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_note_templates_{column}"), "clinical_note_templates", [column], schema=SCHEMA)

    op.create_table(
        "clinical_encounters",
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("encounter_number", sa.String(length=40), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("screening_session_id", sa.Integer(), nullable=True),
        sa.Column("encounter_type", sa.String(length=80), nullable=False, server_default="donor_screening"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="draft"),
        sa.Column("chief_complaint", sa.Text(), nullable=False, server_default=""),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_encounters"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["appointment_id"], [f"{SCHEMA}.appointments.appointment_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["screening_session_id"], [f"{SCHEMA}.clinical_screening_sessions.session_id"]),
        sa.ForeignKeyConstraint(["signed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("encounter_id"),
        sa.UniqueConstraint("encounter_number"),
        schema=SCHEMA,
    )
    for column in [
        "encounter_id",
        "encounter_number",
        "patient_pk",
        "appointment_id",
        "screening_session_id",
        "encounter_type",
        "status",
        "started_at",
    ]:
        op.create_index(op.f(f"ix_operational_clinical_encounters_{column}"), "clinical_encounters", [column], schema=SCHEMA)

    op.create_table(
        "clinical_encounter_notes",
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("note_type", sa.String(length=80), nullable=False, server_default="clinical_note"),
        sa.Column("title", sa.String(length=180), nullable=False, server_default="Clinical encounter note"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_addendum", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("amended_from_note_id", sa.Integer(), nullable=True),
        sa.Column("amendment_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["amended_from_note_id"], [f"{SCHEMA}.clinical_encounter_notes.note_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.ForeignKeyConstraint(["signed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["template_id"], [f"{SCHEMA}.clinical_note_templates.template_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("note_id"),
        schema=SCHEMA,
    )
    for column in ["note_id", "encounter_id", "template_id", "note_type", "status", "amended_from_note_id"]:
        op.create_index(op.f(f"ix_operational_clinical_encounter_notes_{column}"), "clinical_encounter_notes", [column], schema=SCHEMA)

    op.create_table(
        "clinical_encounter_diagnoses",
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("display", sa.String(length=220), nullable=False),
        sa.Column("diagnosis_type", sa.String(length=80), nullable=False, server_default="problem"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.PrimaryKeyConstraint("diagnosis_id"),
        schema=SCHEMA,
    )
    for column in ["diagnosis_id", "encounter_id", "code", "diagnosis_type", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_encounter_diagnoses_{column}"), "clinical_encounter_diagnoses", [column], schema=SCHEMA)

    op.create_table(
        "clinical_patient_allergies",
        sa.Column("allergy_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("allergen", sa.String(length=180), nullable=False),
        sa.Column("reaction", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("allergy_id"),
        schema=SCHEMA,
    )
    for column in ["allergy_id", "patient_pk", "allergen", "severity", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_patient_allergies_{column}"), "clinical_patient_allergies", [column], schema=SCHEMA)

    op.create_table(
        "clinical_patient_medications",
        sa.Column("medication_id", sa.Integer(), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("medication_name", sa.String(length=180), nullable=False),
        sa.Column("dose", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("route", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("frequency", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("indication", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("medication_id"),
        schema=SCHEMA,
    )
    for column in ["medication_id", "patient_pk", "medication_name", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_patient_medications_{column}"), "clinical_patient_medications", [column], schema=SCHEMA)

    op.create_table(
        "clinical_encounter_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=60), nullable=True),
        sa.Column("to_status", sa.String(length=60), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["encounter_id"], [f"{SCHEMA}.clinical_encounters.encounter_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    for column in ["history_id", "encounter_id", "to_status", "changed_at"]:
        op.create_index(op.f(f"ix_operational_clinical_encounter_status_history_{column}"), "clinical_encounter_status_history", [column], schema=SCHEMA)

    op.execute(
        f"""
        INSERT INTO {SCHEMA}.clinical_note_templates (template_key, name, note_type, body)
        VALUES
            ('donor_screening_encounter_v1', 'Donor screening encounter', 'clinical_note', 'Subjective:\n\nObjective:\n\nAssessment:\n\nPlan:\n'),
            ('clinical_review_addendum_v1', 'Clinical review addendum', 'addendum', 'Addendum:\n\nReason for amendment:\n')
        ON CONFLICT (template_key) DO NOTHING
        """
    )

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
    sign_roles = (
        "System Administrator",
        "Clinical Reviewer",
        "Quality Assurance Specialist",
        "Operations Manager",
    )
    _grant_permission(read_roles, "encounters.read")
    _grant_permission(manage_roles, "encounters.manage")
    _grant_permission(sign_roles, "encounters.sign")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('encounters.read', 'encounters.manage', 'encounters.sign')
        """
    )

    for column in ["history_id", "encounter_id", "to_status", "changed_at"]:
        op.drop_index(op.f(f"ix_operational_clinical_encounter_status_history_{column}"), table_name="clinical_encounter_status_history", schema=SCHEMA)
    op.drop_table("clinical_encounter_status_history", schema=SCHEMA)

    for column in ["medication_id", "patient_pk", "medication_name", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_patient_medications_{column}"), table_name="clinical_patient_medications", schema=SCHEMA)
    op.drop_table("clinical_patient_medications", schema=SCHEMA)

    for column in ["allergy_id", "patient_pk", "allergen", "severity", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_patient_allergies_{column}"), table_name="clinical_patient_allergies", schema=SCHEMA)
    op.drop_table("clinical_patient_allergies", schema=SCHEMA)

    for column in ["diagnosis_id", "encounter_id", "code", "diagnosis_type", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_encounter_diagnoses_{column}"), table_name="clinical_encounter_diagnoses", schema=SCHEMA)
    op.drop_table("clinical_encounter_diagnoses", schema=SCHEMA)

    for column in ["note_id", "encounter_id", "template_id", "note_type", "status", "amended_from_note_id"]:
        op.drop_index(op.f(f"ix_operational_clinical_encounter_notes_{column}"), table_name="clinical_encounter_notes", schema=SCHEMA)
    op.drop_table("clinical_encounter_notes", schema=SCHEMA)

    for column in [
        "encounter_id",
        "encounter_number",
        "patient_pk",
        "appointment_id",
        "screening_session_id",
        "encounter_type",
        "status",
        "started_at",
    ]:
        op.drop_index(op.f(f"ix_operational_clinical_encounters_{column}"), table_name="clinical_encounters", schema=SCHEMA)
    op.drop_table("clinical_encounters", schema=SCHEMA)

    for column in ["template_id", "template_key", "name", "note_type", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_note_templates_{column}"), table_name="clinical_note_templates", schema=SCHEMA)
    op.drop_table("clinical_note_templates", schema=SCHEMA)
