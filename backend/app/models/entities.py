from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

OPERATIONAL_SCHEMA = "operational"


class User(Base):
    __tablename__ = "dim_user"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False, default="Clinical Operations")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    donor_reviews: Mapped[list["DonorReview"]] = relationship(back_populates="reviewer")


class Vendor(Base):
    __tablename__ = "dim_vendor"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    vendor_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    system_name: Mapped[str] = mapped_column(String(120), nullable=False)
    criticality: Mapped[str] = mapped_column(String(40), nullable=False, default="Tier 2")
    sla_target_percent: Mapped[float] = mapped_column(Float, nullable=False, default=99.5)
    business_owner: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Active")

    incidents: Mapped[list["VendorIncident"]] = relationship(back_populates="vendor")


class SOP(Base):
    __tablename__ = "dim_sop"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    sop_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sop_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Effective")
    revision_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class RiskCategory(Base):
    __tablename__ = "dim_risk_category"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    risk_category_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    min_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    default_action: Mapped[str] = mapped_column(String(80), nullable=False)


class DonorReview(Base):
    __tablename__ = "fact_donor_review"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    donor_name: Mapped[str] = mapped_column(String(160), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    infectious_history: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    travel_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    missing_required_fields: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False, default="Low")
    recommended_action: Mapped[str] = mapped_column(String(80), nullable=False, default="Approve")
    review_priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Routine")
    intake_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Pending")
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    clinical_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attachment_placeholder: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewer: Mapped[User | None] = relationship(back_populates="donor_reviews")


class AuditLog(Base):
    __tablename__ = "fact_audit_log"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    table_name: Mapped[str] = mapped_column(String(120), nullable=False)
    record_id: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class ChangeControl(Base):
    __tablename__ = "fact_change_control"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    change_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    requested_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    sop_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_sop.sop_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Draft")
    capa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    investigation_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    implementation_due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VendorIncident(Base):
    __tablename__ = "fact_vendor_incident"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    incident_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_vendor.vendor_id"), nullable=False
    )
    ticket_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")
    uptime_percent: Mapped[float] = mapped_column(Float, nullable=False, default=99.9)
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_age_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    resolution_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    vendor: Mapped[Vendor] = relationship(back_populates="incidents")

