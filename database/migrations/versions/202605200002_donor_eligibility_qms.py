"""Donor eligibility and QMS workflow expansion.

Revision ID: 202605200002
Revises: 202605200001
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "202605200002"
down_revision = "202605200001"
branch_labels = None
depends_on = None

OPERATIONAL = "operational"


def upgrade() -> None:
    op.create_table(
        "dim_referral_source",
        sa.Column("source_id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("contact_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("region", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("source_name"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_referral_source_source_id", "dim_referral_source", ["source_id"], schema=OPERATIONAL)

    op.create_table(
        "dim_tissue_type",
        sa.Column("tissue_type_id", sa.Integer(), primary_key=True),
        sa.Column("tissue_name", sa.String(length=120), nullable=False),
        sa.Column("tissue_category", sa.String(length=80), nullable=False),
        sa.Column("min_age", sa.Integer(), nullable=True),
        sa.Column("max_age", sa.Integer(), nullable=True),
        sa.Column("max_ischemic_hours", sa.Float(), nullable=True),
        sa.Column("preservation_window_hours", sa.Float(), nullable=True),
        sa.Column("sop_reference", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("tissue_name"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_tissue_type_tissue_type_id", "dim_tissue_type", ["tissue_type_id"], schema=OPERATIONAL)

    op.create_table(
        "dim_disposition",
        sa.Column("disposition_id", sa.Integer(), primary_key=True),
        sa.Column("disposition_name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("disposition_name"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_disposition_disposition_id", "dim_disposition", ["disposition_id"], schema=OPERATIONAL)

    op.create_table(
        "dim_eligibility_rule",
        sa.Column("rule_id", sa.Integer(), primary_key=True),
        sa.Column("rule_name", sa.String(length=180), nullable=False),
        sa.Column("rule_category", sa.String(length=80), nullable=False),
        sa.Column("condition_field", sa.String(length=120), nullable=False),
        sa.Column("condition_operator", sa.String(length=40), nullable=False),
        sa.Column("condition_value", sa.String(length=240), nullable=False),
        sa.Column("outcome", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("required_role", sa.String(length=100), nullable=True),
        sa.Column("sop_reference", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.String(length=20), nullable=False, server_default="1.0"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.ForeignKeyConstraint(["approved_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        sa.UniqueConstraint("rule_name"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_eligibility_rule_rule_id", "dim_eligibility_rule", ["rule_id"], schema=OPERATIONAL)

    op.create_table(
        "dim_infectious_disease_test",
        sa.Column("test_id", sa.Integer(), primary_key=True),
        sa.Column("test_name", sa.String(length=120), nullable=False),
        sa.Column("pathogen", sa.String(length=80), nullable=False),
        sa.Column("test_method", sa.String(length=80), nullable=False),
        sa.Column("valid_window_hours", sa.Integer(), nullable=False, server_default="168"),
        sa.Column("rejection_if_positive", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("review_if_positive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("test_name"),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_dim_infectious_disease_test_test_id",
        "dim_infectious_disease_test",
        ["test_id"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "dim_donor",
        sa.Column("donor_pk", sa.Integer(), primary_key=True),
        sa.Column("donor_identifier", sa.String(length=40), nullable=False),
        sa.Column("donor_review_id", sa.Integer(), nullable=True),
        sa.Column("donor_name", sa.String(length=160), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("blood_type", sa.String(length=8), nullable=True),
        sa.Column("sex", sa.String(length=20), nullable=True),
        sa.Column("referral_source_id", sa.Integer(), nullable=True),
        sa.Column("time_of_death", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_organization", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("donor_history", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("current_workflow_state", sa.String(length=120), nullable=False, server_default="Referral Received"),
        sa.Column("eligibility_status", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("final_disposition", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["donor_review_id"], [f"{OPERATIONAL}.fact_donor_review.review_id"]),
        sa.ForeignKeyConstraint(["referral_source_id"], [f"{OPERATIONAL}.dim_referral_source.source_id"]),
        sa.UniqueConstraint("donor_identifier"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_dim_donor_donor_pk", "dim_donor", ["donor_pk"], schema=OPERATIONAL)
    op.create_index("ix_dim_donor_donor_identifier", "dim_donor", ["donor_identifier"], schema=OPERATIONAL)

    op.create_table(
        "fact_donor_screening",
        sa.Column("screening_id", sa.Integer(), primary_key=True),
        sa.Column("donor_pk", sa.Integer(), nullable=False),
        sa.Column("referral_id", sa.String(length=40), nullable=False),
        sa.Column("administrative_outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("medical_social_outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("infectious_disease_outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("tissue_suitability_outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("recovery_suitability_outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("qa_outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("automated_rule_outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("current_decision", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        sa.UniqueConstraint("referral_id"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_donor_screening_screening_id", "fact_donor_screening", ["screening_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_donor_screening_donor_pk", "fact_donor_screening", ["donor_pk"], schema=OPERATIONAL)

    op.create_table(
        "fact_eligibility_decision",
        sa.Column("decision_id", sa.Integer(), primary_key=True),
        sa.Column("donor_pk", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("decision_stage", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("required_role", sa.String(length=100), nullable=True),
        sa.Column("triggered_rules", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("final_disposition", sa.String(length=80), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        sa.ForeignKeyConstraint(["rule_id"], [f"{OPERATIONAL}.dim_eligibility_rule.rule_id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_eligibility_decision_decision_id",
        "fact_eligibility_decision",
        ["decision_id"],
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_eligibility_decision_donor_pk", "fact_eligibility_decision", ["donor_pk"], schema=OPERATIONAL)
    op.create_index("ix_fact_eligibility_decision_created_at", "fact_eligibility_decision", ["created_at"], schema=OPERATIONAL)

    op.create_table(
        "fact_infectious_disease_result",
        sa.Column("result_id", sa.Integer(), primary_key=True),
        sa.Column("donor_pk", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("result_value", sa.String(length=40), nullable=False),
        sa.Column("specimen_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("specimen_window_valid", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_status", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        sa.ForeignKeyConstraint(["test_id"], [f"{OPERATIONAL}.dim_infectious_disease_test.test_id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], [f"{OPERATIONAL}.dim_user.user_id"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_infectious_disease_result_result_id",
        "fact_infectious_disease_result",
        ["result_id"],
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_infectious_disease_result_donor_pk",
        "fact_infectious_disease_result",
        ["donor_pk"],
        schema=OPERATIONAL,
    )

    op.create_table(
        "fact_medical_social_history",
        sa.Column("history_id", sa.Integer(), primary_key=True),
        sa.Column("donor_pk", sa.Integer(), nullable=False),
        sa.Column("cancer_history", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("neurological_disease", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("autoimmune_disease", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("transmissible_disease_history", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("iv_drug_use", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("incarceration_history", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("travel_exposure", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("high_risk_behavior", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unknown_history", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("review_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        schema=OPERATIONAL,
    )
    op.create_index(
        "ix_fact_medical_social_history_history_id",
        "fact_medical_social_history",
        ["history_id"],
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_medical_social_history_donor_pk", "fact_medical_social_history", ["donor_pk"], schema=OPERATIONAL)

    op.create_table(
        "fact_recovery_suitability",
        sa.Column("recovery_id", sa.Integer(), primary_key=True),
        sa.Column("donor_pk", sa.Integer(), nullable=False),
        sa.Column("tissue_type_id", sa.Integer(), nullable=False),
        sa.Column("refrigeration_timing_hours", sa.Float(), nullable=True),
        sa.Column("body_cooling_status", sa.String(length=80), nullable=False, server_default="Unknown"),
        sa.Column("trauma_contamination", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("blood_draw_timing_hours", sa.Float(), nullable=True),
        sa.Column("hospital_release_status", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("recovery_environment", sa.String(length=100), nullable=False, server_default="Hospital"),
        sa.Column("recovery_window_hours", sa.Float(), nullable=True),
        sa.Column("outcome", sa.String(length=100), nullable=False, server_default="Pending"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        sa.ForeignKeyConstraint(["tissue_type_id"], [f"{OPERATIONAL}.dim_tissue_type.tissue_type_id"]),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_recovery_suitability_recovery_id", "fact_recovery_suitability", ["recovery_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_recovery_suitability_donor_pk", "fact_recovery_suitability", ["donor_pk"], schema=OPERATIONAL)

    op.create_table(
        "fact_processing_release",
        sa.Column("release_id", sa.Integer(), primary_key=True),
        sa.Column("release_identifier", sa.String(length=40), nullable=False),
        sa.Column("donor_pk", sa.Integer(), nullable=False),
        sa.Column("tissue_type_id", sa.Integer(), nullable=False),
        sa.Column("sterility_testing", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("bioburden_status", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("environmental_monitoring", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("packaging_qc", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("labeling_verification", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("traceability_verification", sa.String(length=80), nullable=False, server_default="Pending"),
        sa.Column("chain_of_custody_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deviation_id", sa.Integer(), nullable=True),
        sa.Column("capa_id", sa.Integer(), nullable=True),
        sa.Column("release_status", sa.String(length=100), nullable=False, server_default="Pending QA Review"),
        sa.Column("final_disposition", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        sa.ForeignKeyConstraint(["tissue_type_id"], [f"{OPERATIONAL}.dim_tissue_type.tissue_type_id"]),
        sa.UniqueConstraint("release_identifier"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_processing_release_release_id", "fact_processing_release", ["release_id"], schema=OPERATIONAL)
    op.create_index("ix_fact_processing_release_donor_pk", "fact_processing_release", ["donor_pk"], schema=OPERATIONAL)

    op.create_table(
        "fact_deviation",
        sa.Column("deviation_id", sa.Integer(), primary_key=True),
        sa.Column("deviation_code", sa.String(length=40), nullable=False),
        sa.Column("donor_pk", sa.Integer(), nullable=True),
        sa.Column("release_id", sa.Integer(), nullable=True),
        sa.Column("deviation_category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="Open"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        sa.UniqueConstraint("deviation_code"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_deviation_deviation_id", "fact_deviation", ["deviation_id"], schema=OPERATIONAL)

    op.create_table(
        "fact_capa",
        sa.Column("capa_id", sa.Integer(), primary_key=True),
        sa.Column("capa_code", sa.String(length=40), nullable=False),
        sa.Column("donor_pk", sa.Integer(), nullable=True),
        sa.Column("deviation_id", sa.Integer(), nullable=True),
        sa.Column("release_id", sa.Integer(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=False, server_default=""),
        sa.Column("corrective_action_owner", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="Open"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["donor_pk"], [f"{OPERATIONAL}.dim_donor.donor_pk"]),
        sa.ForeignKeyConstraint(["deviation_id"], [f"{OPERATIONAL}.fact_deviation.deviation_id"]),
        sa.UniqueConstraint("capa_code"),
        schema=OPERATIONAL,
    )
    op.create_index("ix_fact_capa_capa_id", "fact_capa", ["capa_id"], schema=OPERATIONAL)


def downgrade() -> None:
    op.drop_table("fact_capa", schema=OPERATIONAL)
    op.drop_table("fact_deviation", schema=OPERATIONAL)
    op.drop_table("fact_processing_release", schema=OPERATIONAL)
    op.drop_table("fact_recovery_suitability", schema=OPERATIONAL)
    op.drop_table("fact_medical_social_history", schema=OPERATIONAL)
    op.drop_table("fact_infectious_disease_result", schema=OPERATIONAL)
    op.drop_table("fact_eligibility_decision", schema=OPERATIONAL)
    op.drop_table("fact_donor_screening", schema=OPERATIONAL)
    op.drop_table("dim_donor", schema=OPERATIONAL)
    op.drop_table("dim_infectious_disease_test", schema=OPERATIONAL)
    op.drop_table("dim_eligibility_rule", schema=OPERATIONAL)
    op.drop_table("dim_disposition", schema=OPERATIONAL)
    op.drop_table("dim_tissue_type", schema=OPERATIONAL)
    op.drop_table("dim_referral_source", schema=OPERATIONAL)
