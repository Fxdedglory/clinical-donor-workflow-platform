"""Role-centered workspace engine.

Revision ID: 202605190003
Revises: 202605190002
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "202605190003"
down_revision = "202605190002"
branch_labels = None
depends_on = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.add_column(
        "fact_workflow_task",
        sa.Column("workflow_state", sa.String(length=100), nullable=False, server_default="Assigned"),
        schema=OPERATIONAL,
    )
    op.add_column(
        "fact_workflow_task",
        sa.Column("queue_name", sa.String(length=120), nullable=False, server_default="General Work Queue"),
        schema=OPERATIONAL,
    )
    op.add_column(
        "fact_notification",
        sa.Column("related_record_type", sa.String(length=100), nullable=True),
        schema=OPERATIONAL,
    )
    op.add_column(
        "fact_notification",
        sa.Column("related_record_id", sa.String(length=80), nullable=True),
        schema=OPERATIONAL,
    )
    op.add_column(
        "fact_notification",
        sa.Column("action_route", sa.String(length=120), nullable=True),
        schema=OPERATIONAL,
    )

    op.execute(
        """
        UPDATE operational.fact_workflow_task
        SET workflow_state = CASE
            WHEN task_type = 'Donor Review Task' THEN 'Pending Clinical Review'
            WHEN task_type = 'SLA Investigation Task' THEN 'Vendor SLA Investigation'
            WHEN task_type = 'SOP Deviation Investigation' THEN 'CAPA Investigation'
            ELSE status
        END,
        queue_name = CASE
            WHEN task_type = 'Donor Review Task' THEN 'Clinical Review Workbench'
            WHEN task_type = 'SLA Investigation Task' THEN 'Vendor Operations Workbench'
            WHEN task_type = 'SOP Deviation Investigation' THEN 'QA Investigation Workbench'
            ELSE 'General Work Queue'
        END
        """
    )

    op.create_table(
        "role_workspace_config",
        sa.Column("config_id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("workspace_name", sa.String(length=140), nullable=False),
        sa.Column("workspace_purpose", sa.Text(), nullable=False, server_default=""),
        sa.Column("dashboard_layout", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("visible_tabs", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("enabled_widgets", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("workbench_columns", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("default_queue", sa.String(length=120), nullable=False),
        sa.Column("notification_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("theme_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        sa.UniqueConstraint("role_id"),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_role_workspace_config_config_id",
        "role_workspace_config",
        ["config_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "role_navigation_config",
        sa.Column("nav_id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("tab_label", sa.String(length=100), nullable=False),
        sa.Column("page_key", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("required_permission", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_role_navigation_config_nav_id", "role_navigation_config", ["nav_id"], schema=OPERATIONAL)
    op.create_index("ix_role_navigation_role_order", "role_navigation_config", ["role_id", "sort_order"], schema=OPERATIONAL)

    op.create_table(
        "role_dashboard_widget",
        sa.Column("widget_id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("widget_key", sa.String(length=100), nullable=False),
        sa.Column("widget_title", sa.String(length=140), nullable=False),
        sa.Column("widget_type", sa.String(length=60), nullable=False, server_default="metric"),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_role_dashboard_widget_widget_id", "role_dashboard_widget", ["widget_id"], schema=OPERATIONAL)
    op.create_index("ix_role_dashboard_widget_role_order", "role_dashboard_widget", ["role_id", "sort_order"], schema=OPERATIONAL)

    op.create_table(
        "workflow_state_machine",
        sa.Column("state_id", sa.Integer(), primary_key=True),
        sa.Column("state_name", sa.String(length=100), nullable=False),
        sa.Column("state_category", sa.String(length=80), nullable=False),
        sa.Column("owning_role_id", sa.Integer(), nullable=True),
        sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["owning_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        sa.UniqueConstraint("state_name"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_workflow_state_machine_state_id", "workflow_state_machine", ["state_id"], schema=OPERATIONAL)

    op.create_table(
        "workflow_transition_rule",
        sa.Column("transition_id", sa.Integer(), primary_key=True),
        sa.Column("action_name", sa.String(length=100), nullable=False),
        sa.Column("action_label", sa.String(length=140), nullable=False),
        sa.Column("from_state", sa.String(length=100), nullable=False),
        sa.Column("to_state", sa.String(length=100), nullable=False),
        sa.Column("source_role_id", sa.Integer(), nullable=True),
        sa.Column("target_role_id", sa.Integer(), nullable=True),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("notification_type", sa.String(length=80), nullable=False),
        sa.Column("audit_action", sa.String(length=100), nullable=False),
        sa.Column("sla_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["source_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        sa.ForeignKeyConstraint(["target_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        sa.UniqueConstraint("action_name"),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_workflow_transition_rule_transition_id",
        "workflow_transition_rule",
        ["transition_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "workflow_assignment_rule",
        sa.Column("assignment_rule_id", sa.Integer(), primary_key=True),
        sa.Column("trigger_type", sa.String(length=100), nullable=False),
        sa.Column("from_role_id", sa.Integer(), nullable=True),
        sa.Column("to_role_id", sa.Integer(), nullable=True),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("priority_rule", sa.String(length=100), nullable=False, server_default="inherit"),
        sa.Column("sla_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["from_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        sa.ForeignKeyConstraint(["to_role_id"], [f"{OPERATIONAL}.dim_role.role_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_workflow_assignment_rule_assignment_rule_id",
        "workflow_assignment_rule",
        ["assignment_rule_id"],
        schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_table("workflow_assignment_rule", schema=OPERATIONAL)
    op.drop_table("workflow_transition_rule", schema=OPERATIONAL)
    op.drop_table("workflow_state_machine", schema=OPERATIONAL)
    op.drop_table("role_dashboard_widget", schema=OPERATIONAL)
    op.drop_table("role_navigation_config", schema=OPERATIONAL)
    op.drop_table("role_workspace_config", schema=OPERATIONAL)
    op.drop_column("fact_notification", "action_route", schema=OPERATIONAL)
    op.drop_column("fact_notification", "related_record_id", schema=OPERATIONAL)
    op.drop_column("fact_notification", "related_record_type", schema=OPERATIONAL)
    op.drop_column("fact_workflow_task", "queue_name", schema=OPERATIONAL)
    op.drop_column("fact_workflow_task", "workflow_state", schema=OPERATIONAL)
