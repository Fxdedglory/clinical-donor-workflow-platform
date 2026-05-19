"""Initial regulated healthcare workflow schema.

Revision ID: 202605190001
Revises:
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "202605190001"
down_revision = None
branch_labels = None
depends_on = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")
    op.execute("CREATE SCHEMA IF NOT EXISTS operational")
    op.execute("CREATE SCHEMA IF NOT EXISTS marts")

    op.create_table(
        "dim_user",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False, server_default="Clinical Operations"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("email"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_user_user_id", "dim_user", ["user_id"], schema=OPERATIONAL)

    op.create_table(
        "dim_vendor",
        sa.Column("vendor_id", sa.Integer(), primary_key=True),
        sa.Column("vendor_name", sa.String(length=120), nullable=False),
        sa.Column("system_name", sa.String(length=120), nullable=False),
        sa.Column("criticality", sa.String(length=40), nullable=False, server_default="Tier 2"),
        sa.Column("sla_target_percent", sa.Float(), nullable=False, server_default="99.5"),
        sa.Column("business_owner", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Active"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_vendor_vendor_id", "dim_vendor", ["vendor_id"], schema=OPERATIONAL)

    op.create_table(
        "dim_sop",
        sa.Column("sop_id", sa.Integer(), primary_key=True),
        sa.Column("sop_code", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Effective"),
        sa.Column("revision_notes", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["approved_by_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.UniqueConstraint("sop_code"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_sop_sop_id", "dim_sop", ["sop_id"], schema=OPERATIONAL)

    op.create_table(
        "dim_risk_category",
        sa.Column("risk_category_id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(length=40), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("default_action", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("label"),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_dim_risk_category_risk_category_id",
        "dim_risk_category",
        ["risk_category_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "fact_donor_review",
        sa.Column("review_id", sa.Integer(), primary_key=True),
        sa.Column("donor_id", sa.String(length=40), nullable=False),
        sa.Column("donor_name", sa.String(length=160), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("blood_type", sa.String(length=8), nullable=True),
        sa.Column("infectious_history", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("travel_risk", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("missing_required_fields", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(length=40), nullable=False, server_default="Low"),
        sa.Column("recommended_action", sa.String(length=80), nullable=False, server_default="Approve"),
        sa.Column("review_priority", sa.String(length=40), nullable=False, server_default="Routine"),
        sa.Column("intake_status", sa.String(length=40), nullable=False, server_default="Pending"),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("attachment_placeholder", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reviewer_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.UniqueConstraint("donor_id"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_donor_review_review_id", "fact_donor_review", ["review_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_donor_review_donor_id", "fact_donor_review", ["donor_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_donor_review_status", "fact_donor_review", ["intake_status"], schema=OPERATIONAL)
    op.create_index("ix_fact_donor_review_risk", "fact_donor_review", ["risk_level", "risk_score"], schema=OPERATIONAL)

    op.create_table(
        "fact_audit_log",
        sa.Column("audit_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("table_name", sa.String(length=120), nullable=False),
        sa.Column("record_id", sa.String(length=80), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_audit_log_audit_id", "fact_audit_log", ["audit_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_audit_log_timestamp", "fact_audit_log", ["timestamp"], schema=OPERATIONAL)

    op.create_table(
        "fact_change_control",
        sa.Column("change_id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=40), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=True),
        sa.Column("sop_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=40), nullable=False),
        sa.Column("approval_status", sa.String(length=40), nullable=False, server_default="Draft"),
        sa.Column("capa_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("investigation_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("implementation_due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["requested_by_id"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["sop_id"], [f"{OPERATIONAL}.dim_sop.sop_id"]),
        sa.UniqueConstraint("request_id"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_change_control_change_id", "fact_change_control", ["change_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_change_control_status", "fact_change_control", ["approval_status"], schema=OPERATIONAL)

    op.create_table(
        "fact_vendor_incident",
        sa.Column("incident_id", sa.Integer(), primary_key=True),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("ticket_number", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Open"),
        sa.Column("uptime_percent", sa.Float(), nullable=False, server_default="99.9"),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ticket_age_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("resolution_minutes", sa.Integer(), nullable=True),
        sa.Column("impact_summary", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["vendor_id"], [f"{OPERATIONAL}.dim_vendor.vendor_id"]),
        sa.UniqueConstraint("ticket_number"),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_vendor_incident_incident_id",
        "fact_vendor_incident",
        ["incident_id"],
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_vendor_incident_status",
        "fact_vendor_incident",
        ["status", "sla_breached"],
        schema=OPERATIONAL,
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW marts.vw_dashboard_daily_reviews AS
        SELECT
            date(created_at) AS review_date,
            intake_status,
            risk_level,
            count(*) AS review_count,
            avg(risk_score)::numeric(5,2) AS avg_risk_score
        FROM operational.fact_donor_review
        GROUP BY date(created_at), intake_status, risk_level
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW marts.vw_vendor_sla_summary AS
        SELECT
            v.vendor_name,
            v.system_name,
            count(i.incident_id) AS incident_count,
            sum(CASE WHEN i.sla_breached THEN 1 ELSE 0 END) AS sla_breach_count,
            avg(i.uptime_percent)::numeric(5,2) AS avg_uptime_percent
        FROM operational.dim_vendor v
        LEFT JOIN operational.fact_vendor_incident i ON i.vendor_id = v.vendor_id
        GROUP BY v.vendor_name, v.system_name
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS marts.vw_vendor_sla_summary")
    op.execute("DROP VIEW IF EXISTS marts.vw_dashboard_daily_reviews")
    op.drop_table("fact_vendor_incident", schema=OPERATIONAL)
    op.drop_table("fact_change_control", schema=OPERATIONAL)
    op.drop_table("fact_audit_log", schema=OPERATIONAL)
    op.drop_table("fact_donor_review", schema=OPERATIONAL)
    op.drop_table("dim_risk_category", schema=OPERATIONAL)
    op.drop_table("dim_sop", schema=OPERATIONAL)
    op.drop_table("dim_vendor", schema=OPERATIONAL)
    op.drop_table("dim_user", schema=OPERATIONAL)
    op.execute("DROP SCHEMA IF EXISTS marts")
    op.execute("DROP SCHEMA IF EXISTS operational")
    op.execute("DROP SCHEMA IF EXISTS staging")

