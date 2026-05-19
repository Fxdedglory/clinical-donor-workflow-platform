"""Enterprise operations upgrade.

Revision ID: 202605190002
Revises: 202605190001
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "202605190002"
down_revision = "202605190001"
branch_labels = None
depends_on = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.create_table(
        "dim_role",
        sa.Column("role_id", sa.Integer(), primary_key=True),
        sa.Column("role_name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("role_name"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_role_role_id", "dim_role", ["role_id"], schema=OPERATIONAL)

    op.create_table(
        "bridge_role_permission",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_name", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_name"),
        schema=OPERATIONAL,
    )

    op.create_table(
        "dim_role_responsibility",
        sa.Column("responsibility_id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("assigned_workflows", sa.JSON(), nullable=False),
        sa.Column("operational_kpis", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_dim_role_responsibility_responsibility_id",
        "dim_role_responsibility",
        ["responsibility_id"],
        schema=OPERATIONAL,
    )

    op.add_column("dim_user", sa.Column("username", sa.String(length=80), nullable=True), schema=OPERATIONAL)
    op.add_column(
        "dim_user", sa.Column("hashed_password", sa.String(length=255), nullable=True), schema=OPERATIONAL
    )
    op.add_column("dim_user", sa.Column("role_id", sa.Integer(), nullable=True), schema=OPERATIONAL)
    op.add_column("dim_user", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True), schema=OPERATIONAL)
    op.add_column(
        "dim_user",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_user_username", "dim_user", ["username"], unique=True, schema=OPERATIONAL)
    op.create_foreign_key(
        "fk_dim_user_role_id_dim_role",
        "dim_user",
        "dim_role",
        ["role_id"],
        ["role_id"],
        source_schema=OPERATIONAL,
        referent_schema=OPERATIONAL,
    )

    op.add_column("fact_audit_log", sa.Column("entity_type", sa.String(length=120), nullable=True), schema=OPERATIONAL)
    op.add_column("fact_audit_log", sa.Column("entity_id", sa.String(length=80), nullable=True), schema=OPERATIONAL)
    op.add_column("fact_audit_log", sa.Column("ip_address", sa.String(length=64), nullable=True), schema=OPERATIONAL)
    op.execute(
        """
        UPDATE operational.fact_audit_log
        SET entity_type = table_name,
            entity_id = record_id
        WHERE entity_type IS NULL
        """
    )

    op.create_table(
        "fact_workflow_task",
        sa.Column("task_id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("assigned_role_id", sa.Integer(), nullable=True),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="Routine"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Pending"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_record_id", sa.String(length=80), nullable=False),
        sa.Column("related_record_type", sa.String(length=100), nullable=False),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["assigned_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_workflow_task_task_id", "fact_workflow_task", ["task_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_workflow_task_status", "fact_workflow_task", ["status", "priority"], schema=OPERATIONAL)
    op.create_index(
        "ix_fact_workflow_task_assignment",
        "fact_workflow_task",
        ["assigned_to_user_id", "assigned_role_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "fact_notification",
        sa.Column("notification_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=80), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="Normal"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_notification_notification_id", "fact_notification", ["notification_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_notification_user", "fact_notification", ["user_id", "is_read"], schema=OPERATIONAL)

    op.create_table(
        "fact_escalation_event",
        sa.Column("escalation_id", sa.Integer(), primary_key=True),
        sa.Column("related_task_id", sa.Integer(), nullable=False),
        sa.Column("escalation_type", sa.String(length=100), nullable=False),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Open"),
        sa.ForeignKeyConstraint(["related_task_id"], [f"{OPERATIONAL}.fact_workflow_task.task_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_escalation_event_escalation_id",
        "fact_escalation_event",
        ["escalation_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "fact_sop_training_assignment",
        sa.Column("assignment_id", sa.Integer(), primary_key=True),
        sa.Column("sop_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("assigned_role_id", sa.Integer(), nullable=True),
        sa.Column("assigned_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledgment_status", sa.String(length=40), nullable=False, server_default="Assigned"),
        sa.ForeignKeyConstraint(["sop_id"], [f"{OPERATIONAL}.dim_sop.sop_id"]),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["assigned_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_sop_training_assignment_assignment_id",
        "fact_sop_training_assignment",
        ["assignment_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "fact_training_completion",
        sa.Column("completion_id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("completed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("completion_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledgment_status", sa.String(length=40), nullable=False, server_default="Acknowledged"),
        sa.Column("attestation_text", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["assignment_id"], [f"{OPERATIONAL}.fact_sop_training_assignment.assignment_id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_training_completion_completion_id",
        "fact_training_completion",
        ["completion_id"],
        schema=OPERATIONAL,
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW marts.vw_workforce_task_summary AS
        SELECT
            COALESCE(u.full_name, r.role_name, 'Unassigned') AS owner,
            t.status,
            t.priority,
            count(*) AS task_count,
            avg(EXTRACT(epoch FROM (now() - t.created_at)) / 3600)::numeric(8,2) AS avg_age_hours
        FROM operational.fact_workflow_task t
        LEFT JOIN operational.dim_user u ON u.user_id = t.assigned_to_user_id
        LEFT JOIN operational.dim_role r ON r.role_id = t.assigned_role_id
        GROUP BY COALESCE(u.full_name, r.role_name, 'Unassigned'), t.status, t.priority
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW marts.vw_compliance_training_summary AS
        SELECT
            s.sop_code,
            s.title,
            a.acknowledgment_status,
            count(*) AS assignment_count,
            sum(CASE WHEN a.due_date < now()
                      AND a.acknowledgment_status NOT IN ('Completed', 'Acknowledged')
                     THEN 1 ELSE 0 END) AS overdue_count
        FROM operational.fact_sop_training_assignment a
        JOIN operational.dim_sop s ON s.sop_id = a.sop_id
        GROUP BY s.sop_code, s.title, a.acknowledgment_status
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS marts.vw_compliance_training_summary")
    op.execute("DROP VIEW IF EXISTS marts.vw_workforce_task_summary")
    op.drop_table("fact_training_completion", schema=OPERATIONAL)
    op.drop_table("fact_sop_training_assignment", schema=OPERATIONAL)
    op.drop_table("fact_escalation_event", schema=OPERATIONAL)
    op.drop_table("fact_notification", schema=OPERATIONAL)
    op.drop_table("fact_workflow_task", schema=OPERATIONAL)
    op.drop_column("fact_audit_log", "ip_address", schema=OPERATIONAL)
    op.drop_column("fact_audit_log", "entity_id", schema=OPERATIONAL)
    op.drop_column("fact_audit_log", "entity_type", schema=OPERATIONAL)
    op.drop_constraint("fk_dim_user_role_id_dim_role", "dim_user", schema=OPERATIONAL, type_="foreignkey")
    op.drop_index("ix_dim_user_username", table_name="dim_user", schema=OPERATIONAL)
    op.drop_column("dim_user", "created_at", schema=OPERATIONAL)
    op.drop_column("dim_user", "last_login", schema=OPERATIONAL)
    op.drop_column("dim_user", "role_id", schema=OPERATIONAL)
    op.drop_column("dim_user", "hashed_password", schema=OPERATIONAL)
    op.drop_column("dim_user", "username", schema=OPERATIONAL)
    op.drop_table("dim_role_responsibility", schema=OPERATIONAL)
    op.drop_table("bridge_role_permission", schema=OPERATIONAL)
    op.drop_table("dim_role", schema=OPERATIONAL)

