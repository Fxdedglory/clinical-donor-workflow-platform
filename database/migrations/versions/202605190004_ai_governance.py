"""AI governance and workflow intelligence.

Revision ID: 202605190004
Revises: 202605190003
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "202605190004"
down_revision = "202605190003"
branch_labels = None
depends_on = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.create_table(
        "dim_ai_model_version",
        sa.Column("model_version_id", sa.Integer(), primary_key=True),
        sa.Column("version_name", sa.String(length=80), nullable=False),
        sa.Column("deployment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Active"),
        sa.Column("change_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["approved_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.UniqueConstraint("version_name"),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_dim_ai_model_version_model_version_id",
        "dim_ai_model_version",
        ["model_version_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "dim_ai_risk_rule",
        sa.Column("rule_id", sa.Integer(), primary_key=True),
        sa.Column("rule_name", sa.String(length=140), nullable=False),
        sa.Column("risk_category", sa.String(length=60), nullable=False),
        sa.Column("condition_type", sa.String(length=80), nullable=False),
        sa.Column("condition_operator", sa.String(length=40), nullable=False),
        sa.Column("condition_value", sa.String(length=240), nullable=False),
        sa.Column("risk_score_delta", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("auto_escalate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["approved_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.UniqueConstraint("rule_name"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_ai_risk_rule_rule_id", "dim_ai_risk_rule", ["rule_id"], schema=OPERATIONAL)

    op.create_table(
        "fact_ai_decision",
        sa.Column("decision_id", sa.Integer(), primary_key=True),
        sa.Column("donor_id", sa.String(length=40), nullable=False),
        sa.Column("model_version_id", sa.Integer(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=120), nullable=False),
        sa.Column("triggered_rules", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("workflow_stage", sa.String(length=100), nullable=False),
        sa.Column("confidence_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("escalation_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("workflow_impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("human_override", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("final_decision", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(["model_version_id"], [f"{OPERATIONAL}.dim_ai_model_version.model_version_id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_ai_decision_decision_id", "fact_ai_decision", ["decision_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_ai_decision_donor_id", "fact_ai_decision", ["donor_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_ai_decision_created_at", "fact_ai_decision", ["created_at"], schema=OPERATIONAL)

    op.create_table(
        "fact_ai_override_event",
        sa.Column("override_id", sa.Integer(), primary_key=True),
        sa.Column("decision_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=False),
        sa.Column("previous_decision", sa.String(length=120), nullable=False),
        sa.Column("new_decision", sa.String(length=80), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["decision_id"], [f"{OPERATIONAL}.fact_ai_decision.decision_id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_ai_override_event_override_id",
        "fact_ai_override_event",
        ["override_id"],
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_ai_override_event_timestamp",
        "fact_ai_override_event",
        ["timestamp"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "fact_workflow_timeline_event",
        sa.Column("timeline_event_id", sa.Integer(), primary_key=True),
        sa.Column("related_record_type", sa.String(length=100), nullable=False),
        sa.Column("related_record_id", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_summary", sa.String(length=240), nullable=False),
        sa.Column("event_detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_workflow_timeline_event_timeline_event_id",
        "fact_workflow_timeline_event",
        ["timeline_event_id"],
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_workflow_timeline_record",
        "fact_workflow_timeline_event",
        ["related_record_type", "related_record_id", "created_at"],
        schema=OPERATIONAL,
    )


def downgrade() -> None:
    op.drop_table("fact_workflow_timeline_event", schema=OPERATIONAL)
    op.drop_table("fact_ai_override_event", schema=OPERATIONAL)
    op.drop_table("fact_ai_decision", schema=OPERATIONAL)
    op.drop_table("dim_ai_risk_rule", schema=OPERATIONAL)
    op.drop_table("dim_ai_model_version", schema=OPERATIONAL)
