"""clinical scheduling

Revision ID: 202606120002
Revises: 202606120001
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606120002"
down_revision: str | None = "202606120001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "operational"


def _set_sequence(table_name: str, column_name: str) -> None:
    op.execute(
        f"""
        SELECT setval(
            pg_get_serial_sequence('{SCHEMA}.{table_name}', '{column_name}'),
            COALESCE((SELECT MAX({column_name}) FROM {SCHEMA}.{table_name}), 1)
        )
        """
    )


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
        "clinical_providers",
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("provider_code", sa.String(length=40), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False, server_default="Clinician"),
        sa.Column("specialty", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("provider_id"),
        sa.UniqueConstraint("provider_code"),
        schema=SCHEMA,
    )
    for column in ["provider_id", "provider_code", "full_name", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_providers_{column}"), "clinical_providers", [column], schema=SCHEMA)

    op.create_table(
        "clinical_rooms",
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("room_code", sa.String(length=40), nullable=False),
        sa.Column("room_name", sa.String(length=160), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("room_id"),
        sa.UniqueConstraint("room_code"),
        schema=SCHEMA,
    )
    for column in ["room_id", "room_code", "room_name", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_rooms_{column}"), "clinical_rooms", [column], schema=SCHEMA)

    op.create_table(
        "clinical_equipment",
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("equipment_code", sa.String(length=40), nullable=False),
        sa.Column("equipment_name", sa.String(length=160), nullable=False),
        sa.Column("equipment_type", sa.String(length=80), nullable=False, server_default="clinical"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("equipment_id"),
        sa.UniqueConstraint("equipment_code"),
        schema=SCHEMA,
    )
    for column in ["equipment_id", "equipment_code", "equipment_name", "status"]:
        op.create_index(op.f(f"ix_operational_clinical_equipment_{column}"), "clinical_equipment", [column], schema=SCHEMA)

    op.create_table(
        "appointment_types",
        sa.Column("appointment_type_id", sa.Integer(), nullable=False),
        sa.Column("type_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("default_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("requires_room", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("appointment_type_id"),
        sa.UniqueConstraint("type_code"),
        schema=SCHEMA,
    )
    for column in ["appointment_type_id", "type_code", "name", "status"]:
        op.create_index(op.f(f"ix_operational_appointment_types_{column}"), "appointment_types", [column], schema=SCHEMA)

    op.create_table(
        "appointments",
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("appointment_number", sa.String(length=40), nullable=False),
        sa.Column("patient_pk", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("appointment_type_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="scheduled"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("no_show_reason", sa.Text(), nullable=True),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="clinical_scheduling"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["appointment_type_id"], [f"{SCHEMA}.appointment_types.appointment_type_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["patient_pk"], [f"{SCHEMA}.patients.patient_pk"]),
        sa.ForeignKeyConstraint(["provider_id"], [f"{SCHEMA}.clinical_providers.provider_id"]),
        sa.ForeignKeyConstraint(["room_id"], [f"{SCHEMA}.clinical_rooms.room_id"]),
        sa.ForeignKeyConstraint(["updated_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("appointment_id"),
        sa.UniqueConstraint("appointment_number"),
        schema=SCHEMA,
    )
    for column in [
        "appointment_id",
        "appointment_number",
        "patient_pk",
        "provider_id",
        "room_id",
        "appointment_type_id",
        "scheduled_start",
        "scheduled_end",
        "status",
    ]:
        op.create_index(op.f(f"ix_operational_appointments_{column}"), "appointments", [column], schema=SCHEMA)

    op.create_table(
        "appointment_resources",
        sa.Column("appointment_resource_id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["appointment_id"], [f"{SCHEMA}.appointments.appointment_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["equipment_id"], [f"{SCHEMA}.clinical_equipment.equipment_id"]),
        sa.PrimaryKeyConstraint("appointment_resource_id"),
        schema=SCHEMA,
    )
    for column in ["appointment_resource_id", "appointment_id", "equipment_id"]:
        op.create_index(op.f(f"ix_operational_appointment_resources_{column}"), "appointment_resources", [column], schema=SCHEMA)

    op.create_table(
        "appointment_status_history",
        sa.Column("history_id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["appointment_id"], [f"{SCHEMA}.appointments.appointment_id"]),
        sa.ForeignKeyConstraint(["changed_by"], [f"{SCHEMA}.dim_user.user_id"]),
        sa.PrimaryKeyConstraint("history_id"),
        schema=SCHEMA,
    )
    for column in ["history_id", "appointment_id", "to_status", "changed_at"]:
        op.create_index(op.f(f"ix_operational_appointment_status_history_{column}"), "appointment_status_history", [column], schema=SCHEMA)

    op.execute(
        f"""
        INSERT INTO {SCHEMA}.clinical_providers (provider_id, provider_code, full_name, role, specialty)
        VALUES
            (1, 'PROV-INTAKE', 'Jordan Ellis, RN', 'Nurse', 'Donor intake'),
            (2, 'PROV-REVIEW', 'Morgan Patel, MD', 'Physician', 'Clinical review'),
            (3, 'PROV-QA', 'Riley Chen, RN', 'Nurse', 'Quality follow-up')
        ON CONFLICT (provider_code) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.clinical_rooms (room_id, room_code, room_name, location)
        VALUES
            (1, 'ROOM-101', 'Intake Room 101', 'Clinical wing'),
            (2, 'ROOM-102', 'Screening Room 102', 'Clinical wing'),
            (3, 'ROOM-TELE', 'Telehealth Slot', 'Virtual')
        ON CONFLICT (room_code) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.clinical_equipment (equipment_id, equipment_code, equipment_name, equipment_type)
        VALUES
            (1, 'EQ-VITALS-1', 'Vitals Cart 1', 'vitals'),
            (2, 'EQ-PHLEB-1', 'Phlebotomy Kit 1', 'collection'),
            (3, 'EQ-TELE-1', 'Telehealth Workstation', 'telehealth')
        ON CONFLICT (equipment_code) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.appointment_types (
            appointment_type_id, type_code, name, default_duration_minutes, requires_room
        )
        VALUES
            (1, 'DONOR-INTAKE', 'Donor intake appointment', 60, true),
            (2, 'SCREENING-FOLLOWUP', 'Screening follow-up', 45, true),
            (3, 'TELE-REVIEW', 'Telehealth clinical review', 30, false)
        ON CONFLICT (type_code) DO NOTHING
        """
    )
    _set_sequence("clinical_providers", "provider_id")
    _set_sequence("clinical_rooms", "room_id")
    _set_sequence("clinical_equipment", "equipment_id")
    _set_sequence("appointment_types", "appointment_type_id")

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
        "Operations Manager",
    )
    _grant_permission(read_roles, "scheduling.read")
    _grant_permission(manage_roles, "scheduling.manage")


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM {SCHEMA}.bridge_role_permission
        WHERE permission_name IN ('scheduling.read', 'scheduling.manage')
        """
    )

    for column in ["history_id", "appointment_id", "to_status", "changed_at"]:
        op.drop_index(op.f(f"ix_operational_appointment_status_history_{column}"), table_name="appointment_status_history", schema=SCHEMA)
    op.drop_table("appointment_status_history", schema=SCHEMA)

    for column in ["appointment_resource_id", "appointment_id", "equipment_id"]:
        op.drop_index(op.f(f"ix_operational_appointment_resources_{column}"), table_name="appointment_resources", schema=SCHEMA)
    op.drop_table("appointment_resources", schema=SCHEMA)

    for column in [
        "appointment_id",
        "appointment_number",
        "patient_pk",
        "provider_id",
        "room_id",
        "appointment_type_id",
        "scheduled_start",
        "scheduled_end",
        "status",
    ]:
        op.drop_index(op.f(f"ix_operational_appointments_{column}"), table_name="appointments", schema=SCHEMA)
    op.drop_table("appointments", schema=SCHEMA)

    for column in ["appointment_type_id", "type_code", "name", "status"]:
        op.drop_index(op.f(f"ix_operational_appointment_types_{column}"), table_name="appointment_types", schema=SCHEMA)
    op.drop_table("appointment_types", schema=SCHEMA)

    for column in ["equipment_id", "equipment_code", "equipment_name", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_equipment_{column}"), table_name="clinical_equipment", schema=SCHEMA)
    op.drop_table("clinical_equipment", schema=SCHEMA)

    for column in ["room_id", "room_code", "room_name", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_rooms_{column}"), table_name="clinical_rooms", schema=SCHEMA)
    op.drop_table("clinical_rooms", schema=SCHEMA)

    for column in ["provider_id", "provider_code", "full_name", "status"]:
        op.drop_index(op.f(f"ix_operational_clinical_providers_{column}"), table_name="clinical_providers", schema=SCHEMA)
    op.drop_table("clinical_providers", schema=SCHEMA)
