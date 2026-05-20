"""Enterprise workflow orchestration metadata.

Revision ID: 202605200001
Revises: 202605190004
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "202605200001"
down_revision = "202605190004"
branch_labels = None
depends_on = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.alter_column(
        "fact_donor_review",
        "intake_status",
        server_default="Draft Intake",
        schema=OPERATIONAL,
    )
    op.add_column(
        "workflow_state_machine",
        sa.Column("allowed_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        schema=OPERATIONAL,
    )
    op.add_column(
        "workflow_state_machine",
        sa.Column("allowed_actions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        schema=OPERATIONAL,
    )
    op.add_column(
        "workflow_state_machine",
        sa.Column("next_possible_states", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        schema=OPERATIONAL,
    )
    op.add_column(
        "workflow_state_machine",
        sa.Column("sla_hours", sa.Integer(), nullable=False, server_default="24"),
        schema=OPERATIONAL,
    )
    op.add_column(
        "workflow_state_machine",
        sa.Column("escalation_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        schema=OPERATIONAL,
    )
    op.add_column(
        "workflow_state_machine",
        sa.Column("notification_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        schema=OPERATIONAL,
    )
    op.add_column(
        "workflow_state_machine",
        sa.Column("is_terminal_state", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema=OPERATIONAL,
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {OPERATIONAL}.workflow_state_machine
               SET is_terminal_state = is_terminal
            """
        )
    )

    op.add_column(
        "fact_notification",
        sa.Column("workflow_task_id", sa.Integer(), nullable=True),
        schema=OPERATIONAL,
    )
    op.add_column(
        "fact_notification",
        sa.Column("workflow_context", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        schema=OPERATIONAL,
    )
    op.create_foreign_key(
        "fk_fact_notification_workflow_task_id",
        "fact_notification",
        "fact_workflow_task",
        ["workflow_task_id"],
        ["task_id"],
        source_schema=OPERATIONAL,
        referent_schema=OPERATIONAL,
    )

    op.create_table(
        "workflow_transition_event",
        sa.Column("transition_id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.String(length=80), nullable=False),
        sa.Column("record_type", sa.String(length=100), nullable=False),
        sa.Column("from_state", sa.String(length=100), nullable=False),
        sa.Column("to_state", sa.String(length=100), nullable=False),
        sa.Column("action_taken", sa.String(length=120), nullable=False),
        sa.Column("performed_by", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("decision_context", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["performed_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_workflow_transition_event_transition_id", "workflow_transition_event", ["transition_id"], schema=OPERATIONAL)
    op.create_index("ix_workflow_transition_event_record_id", "workflow_transition_event", ["record_id"], schema=OPERATIONAL)
    op.create_index("ix_workflow_transition_event_timestamp", "workflow_transition_event", ["timestamp"], schema=OPERATIONAL)

    op.create_table(
        "workflow_escalation_rule",
        sa.Column("escalation_rule_id", sa.Integer(), primary_key=True),
        sa.Column("workflow_state", sa.String(length=100), nullable=False),
        sa.Column("trigger_condition", sa.String(length=140), nullable=False),
        sa.Column("threshold_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("target_role_id", sa.Integer(), nullable=True),
        sa.Column("escalation_type", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="High"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["target_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_workflow_escalation_rule_escalation_rule_id", "workflow_escalation_rule", ["escalation_rule_id"], schema=OPERATIONAL)

    op.create_table(
        "workflow_notification_rule",
        sa.Column("notification_rule_id", sa.Integer(), primary_key=True),
        sa.Column("workflow_state", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("target_role_id", sa.Integer(), nullable=True),
        sa.Column("notification_type", sa.String(length=80), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="Normal"),
        sa.Column("template", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["target_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_workflow_notification_rule_notification_rule_id", "workflow_notification_rule", ["notification_rule_id"], schema=OPERATIONAL)

    op.create_table(
        "workflow_navigation_route",
        sa.Column("route_id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(length=100), nullable=False),
        sa.Column("workflow_state", sa.String(length=100), nullable=True),
        sa.Column("page_key", sa.String(length=100), nullable=False),
        sa.Column("route_label", sa.String(length=140), nullable=False),
        sa.Column("preserve_context", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_workflow_navigation_route_route_id", "workflow_navigation_route", ["route_id"], schema=OPERATIONAL)

    op.execute(
        sa.text(
            f"""
            UPDATE {OPERATIONAL}.fact_workflow_task
               SET workflow_state = CASE workflow_state
                    WHEN 'Pending Intake Review' THEN 'Pending Intake Validation'
                    WHEN 'Clinical Escalation' THEN 'Operations Escalation'
                    WHEN 'Pending QA Review' THEN 'QA Investigation'
                    ELSE workflow_state
               END
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {OPERATIONAL}.fact_donor_review
               SET intake_status = CASE intake_status
                    WHEN 'Pending' THEN 'Pending Intake Validation'
                    WHEN 'Under Review' THEN 'Pending Clinical Review'
                    WHEN 'Deferred' THEN 'Pending Additional Information'
                    WHEN 'Pending Intake Review' THEN 'Pending Intake Validation'
                    WHEN 'Pending QA Review' THEN 'QA Investigation'
                    WHEN 'Clinical Escalation' THEN 'Operations Escalation'
                    ELSE intake_status
               END
            """
        )
    )


def downgrade() -> None:
    op.alter_column(
        "fact_donor_review",
        "intake_status",
        server_default="Pending",
        schema=OPERATIONAL,
    )
    op.drop_table("workflow_navigation_route", schema=OPERATIONAL)
    op.drop_table("workflow_notification_rule", schema=OPERATIONAL)
    op.drop_table("workflow_escalation_rule", schema=OPERATIONAL)
    op.drop_table("workflow_transition_event", schema=OPERATIONAL)
    op.drop_constraint("fk_fact_notification_workflow_task_id", "fact_notification", schema=OPERATIONAL, type_="foreignkey")
    op.drop_column("fact_notification", "workflow_context", schema=OPERATIONAL)
    op.drop_column("fact_notification", "workflow_task_id", schema=OPERATIONAL)
    op.drop_column("workflow_state_machine", "is_terminal_state", schema=OPERATIONAL)
    op.drop_column("workflow_state_machine", "notification_rules", schema=OPERATIONAL)
    op.drop_column("workflow_state_machine", "escalation_rules", schema=OPERATIONAL)
    op.drop_column("workflow_state_machine", "sla_hours", schema=OPERATIONAL)
    op.drop_column("workflow_state_machine", "next_possible_states", schema=OPERATIONAL)
    op.drop_column("workflow_state_machine", "allowed_actions", schema=OPERATIONAL)
    op.drop_column("workflow_state_machine", "allowed_roles", schema=OPERATIONAL)
