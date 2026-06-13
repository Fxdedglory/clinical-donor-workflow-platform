from types import SimpleNamespace

from app.services.clinical_phi import (
    REDACTED_VALUE,
    classify_field,
    export_profile_denial_reason,
    redact_audit_changes,
    redact_payload,
)


def test_phi_sensitivity_registry_returns_expected_classifications() -> None:
    assert classify_field("patients", "date_of_birth") == "phi"
    assert classify_field("encounters", "note_content") == "ephi"
    assert classify_field("billing", "member_id") == "financial"
    assert classify_field("quality", "evidence_summary") == "compliance_sensitive"
    assert classify_field("reports", "row_counts") == "internal"
    assert classify_field("patients", "status") == "public"


def test_aggregate_safe_profile_redacts_direct_identifiers() -> None:
    payload = {
        "patient_id": "PT-SECRET",
        "entity_id": "QE-SECRET",
        "row_counts": {"patients": 12},
        "status": "open",
    }

    redacted = redact_payload(payload, "aggregate_safe", module="reports")

    assert redacted["patient_id"] == REDACTED_VALUE
    assert redacted["entity_id"] == REDACTED_VALUE
    assert redacted["row_counts"] == {"patients": 12}
    assert redacted["status"] == "open"


def test_external_safe_profile_redacts_phi_ephi_and_financial_fields() -> None:
    payload = {
        "patient_name": "Sensitive Person",
        "note": "Clinical narrative",
        "member_id": "INS-SECRET",
        "workflow": "reports.analytics_export",
    }

    redacted = redact_payload(payload, "external_safe", module="audit")

    assert redacted["patient_name"] == REDACTED_VALUE
    assert redacted["note"] == REDACTED_VALUE
    assert redacted["member_id"] == REDACTED_VALUE
    assert redacted["workflow"] == "reports.analytics_export"


def test_audit_change_redaction_removes_identifiers_and_narratives() -> None:
    changes = {
        "export_profile": "aggregate_safe",
        "patient_id": "PT-SECRET",
        "entity_id": "QE-SECRET",
        "note": "Detailed clinical narrative",
        "field": "status",
    }

    redacted = redact_audit_changes(changes)

    assert redacted["export_profile"] == "aggregate_safe"
    assert redacted["patient_id"] == REDACTED_VALUE
    assert redacted["entity_id"] == REDACTED_VALUE
    assert redacted["note"] == REDACTED_VALUE
    assert redacted["field"] == "status"


def test_compliance_evidence_profile_requires_compliance_or_admin_permission() -> None:
    internal_user = SimpleNamespace(is_external=False, external_user_flag=False, account_type="internal", user_type="internal", role="Clinical Reviewer")
    compliance_user = SimpleNamespace(is_external=False, external_user_flag=False, account_type="internal", user_type="internal", role="Quality Assurance Specialist")

    denied = export_profile_denial_reason("compliance_evidence", internal_user, {"reports.export"})
    allowed = export_profile_denial_reason("compliance_evidence", compliance_user, {"quality.export"})

    assert denied is not None
    assert allowed is None
