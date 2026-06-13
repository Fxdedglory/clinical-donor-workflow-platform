from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVITY_LEVELS = {
    "public",
    "internal",
    "phi",
    "ephi",
    "financial",
    "compliance_sensitive",
    "audit_sensitive",
}

EXPORT_PROFILE_NAMES = {
    "aggregate_safe",
    "internal_detail",
    "compliance_evidence",
    "external_safe",
    "audit_metadata",
}

DEFAULT_AGGREGATE_EXPORT_PROFILE = "aggregate_safe"
DEFAULT_COMPLIANCE_EXPORT_PROFILE = "compliance_evidence"
DEFAULT_AUDIT_EXPORT_PROFILE = "audit_metadata"
REDACTED_VALUE = "[redacted]"

FIELD_SENSITIVITY: dict[str, dict[str, str]] = {
    "patients": {
        "patient_id": "phi",
        "patient_pk": "phi",
        "donor_reference": "phi",
        "first_name": "phi",
        "middle_name": "phi",
        "last_name": "phi",
        "patient_name": "phi",
        "date_of_birth": "phi",
        "phone": "phi",
        "email": "phi",
        "address_line1": "phi",
        "address_line2": "phi",
        "city": "phi",
        "state": "phi",
        "postal_code": "phi",
    },
    "contacts": {
        "full_name": "phi",
        "contact_name": "phi",
        "phone": "phi",
        "email": "phi",
        "relationship": "phi",
    },
    "insurance": {
        "member_id": "financial",
        "group_number": "financial",
        "payer_name": "financial",
        "plan_name": "financial",
        "eligibility_status": "financial",
        "verification_notes": "financial",
    },
    "scheduling": {
        "appointment_number": "phi",
        "reason": "phi",
        "cancellation_reason": "phi",
        "no_show_reason": "phi",
    },
    "screening": {
        "session_number": "phi",
        "answers": "ephi",
        "answer_value": "ephi",
        "vitals": "ephi",
        "notes": "ephi",
        "deferral_reason": "ephi",
    },
    "encounters": {
        "encounter_number": "phi",
        "chief_complaint": "ephi",
        "note": "ephi",
        "note_content": "ephi",
        "content": "ephi",
        "diagnosis_code": "ephi",
        "diagnosis": "ephi",
        "allergen": "ephi",
        "reaction": "ephi",
        "medication_name": "ephi",
        "dose": "ephi",
        "indication": "ephi",
    },
    "orders": {
        "order_number": "phi",
        "clinical_indication": "ephi",
        "result_name": "ephi",
        "result_value": "ephi",
        "reference_range": "ephi",
        "result_notes": "ephi",
        "acknowledgement_note": "ephi",
    },
    "care_plans": {
        "care_plan_number": "phi",
        "title": "ephi",
        "goal": "ephi",
        "intervention": "ephi",
        "progress_note": "ephi",
        "closure_reason": "ephi",
        "outcome_summary": "ephi",
    },
    "billing": {
        "account_number": "financial",
        "claim_number": "financial",
        "charge_number": "financial",
        "payment_reference": "financial",
        "reference_number": "financial",
        "denial_reason": "financial",
        "resolution_notes": "financial",
        "diagnosis_code": "ephi",
        "member_id": "financial",
        "group_number": "financial",
    },
    "quality": {
        "event_number": "compliance_sensitive",
        "adverse_event_number": "compliance_sensitive",
        "description": "ephi",
        "immediate_action_taken": "ephi",
        "reporter": "phi",
        "evidence_summary": "compliance_sensitive",
        "finding": "compliance_sensitive",
        "root_cause": "compliance_sensitive",
        "root_cause_category": "compliance_sensitive",
        "corrective_action_recommendation": "compliance_sensitive",
        "resolution_summary": "compliance_sensitive",
        "closure_reason": "compliance_sensitive",
    },
    "audit": {
        "entity_id": "audit_sensitive",
        "actor": "audit_sensitive",
        "changes": "audit_sensitive",
        "criteria": "audit_sensitive",
        "payload": "audit_sensitive",
    },
    "reports": {
        "row_counts": "internal",
        "filters": "audit_sensitive",
        "modules": "internal",
        "export_profile": "internal",
    },
    "admin": {
        "permissions": "compliance_sensitive",
        "role": "compliance_sensitive",
    },
}

DIRECT_IDENTIFIER_KEYS = {
    "patient_id",
    "patient_pk",
    "patient_name",
    "donor_reference",
    "first_name",
    "middle_name",
    "last_name",
    "date_of_birth",
    "phone",
    "email",
    "address_line1",
    "address_line2",
    "postal_code",
    "entity_id",
    "event_number",
    "adverse_event_number",
    "appointment_number",
    "session_number",
    "encounter_number",
    "order_number",
    "care_plan_number",
    "claim_number",
    "charge_number",
    "account_number",
    "member_id",
    "group_number",
    "reference_number",
}

NARRATIVE_KEYS = {
    "description",
    "note",
    "notes",
    "content",
    "body",
    "reason",
    "cancellation_reason",
    "no_show_reason",
    "denial_reason",
    "resolution_notes",
    "resolution_summary",
    "closure_reason",
    "outcome_summary",
    "evidence_summary",
    "finding",
    "root_cause",
    "root_cause_category",
    "corrective_action_recommendation",
    "immediate_action_taken",
    "acknowledgement_note",
    "progress_note",
}

PROFILE_REDACTION_LEVELS = {
    "aggregate_safe": {"phi", "ephi", "financial", "compliance_sensitive", "audit_sensitive"},
    "external_safe": {"internal", "phi", "ephi", "financial", "compliance_sensitive", "audit_sensitive"},
    "audit_metadata": {"phi", "ephi", "financial", "compliance_sensitive"},
    "internal_detail": {"ephi"},
    "compliance_evidence": set(),
}

INTERNAL_DETAIL_PERMISSIONS = {
    "system.admin",
    "reports.export",
    "quality.export",
    "audit.review",
    "clinical_admin.manage",
}

COMPLIANCE_EVIDENCE_PERMISSIONS = {
    "system.admin",
    "quality.export",
    "audit.review",
    "qms.manage",
    "clinical_admin.manage",
}


def normalize_export_profile(profile: str | None, *, default: str = DEFAULT_AGGREGATE_EXPORT_PROFILE) -> str:
    value = (profile or default).strip().lower()
    if value not in EXPORT_PROFILE_NAMES:
        raise ValueError(f"Unknown export profile: {profile}")
    return value


def classify_field(module: str, field_name: str) -> str:
    module_key = module.strip().lower()
    field_key = field_name.strip().lower()
    module_fields = FIELD_SENSITIVITY.get(module_key, {})
    if field_key in module_fields:
        return module_fields[field_key]
    for fields in FIELD_SENSITIVITY.values():
        if field_key in fields:
            return fields[field_key]
    return "public"


def is_external_user(user: Any) -> bool:
    role = getattr(user, "role", "")
    return bool(
        getattr(user, "is_external", False)
        or getattr(user, "external_user_flag", False)
        or getattr(user, "account_type", None) in {"partner", "supplier", "external"}
        or getattr(user, "user_type", None) in {"partner", "supplier", "external"}
        or role in {"Partner External User", "Supplier External User"}
    )


def export_profile_denial_reason(profile: str, user: Any, permissions: set[str]) -> str | None:
    normalized = normalize_export_profile(profile)
    if is_external_user(user) and normalized not in {"aggregate_safe", "external_safe"}:
        return "External users can only use aggregate_safe or external_safe export profiles."
    if normalized == "internal_detail" and permissions.isdisjoint(INTERNAL_DETAIL_PERMISSIONS):
        return "internal_detail export profile requires an internal export, audit, or admin permission."
    if normalized == "compliance_evidence" and permissions.isdisjoint(COMPLIANCE_EVIDENCE_PERMISSIONS):
        return "compliance_evidence export profile requires compliance, audit, QMS, or admin permission."
    return None


def _should_redact(key: str, profile: str, module: str | None) -> bool:
    key_name = key.strip().lower()
    normalized = normalize_export_profile(profile)
    if normalized in {"aggregate_safe", "external_safe"} and key_name in DIRECT_IDENTIFIER_KEYS:
        return True
    if normalized == "audit_metadata" and key_name in NARRATIVE_KEYS:
        return True
    sensitivity = classify_field(module or "", key_name)
    return sensitivity in PROFILE_REDACTION_LEVELS[normalized]


def redact_payload(payload: Any, profile: str, *, module: str | None = None) -> Any:
    normalized = normalize_export_profile(profile)
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            if _should_redact(str(key), normalized, module):
                redacted[key] = REDACTED_VALUE
            else:
                redacted[key] = redact_payload(value, normalized, module=module)
        return redacted
    if isinstance(payload, list):
        return [redact_payload(item, normalized, module=module) for item in payload]
    return deepcopy(payload)


def redact_workflow_operation(operation: dict[str, Any], profile: str) -> dict[str, Any]:
    normalized = normalize_export_profile(profile, default=DEFAULT_AUDIT_EXPORT_PROFILE)
    redacted = redact_payload(operation, normalized, module="audit")
    if isinstance(redacted, dict) and "changes" in redacted and isinstance(operation.get("changes"), dict):
        redacted["changes"] = redact_payload(operation["changes"], normalized, module="audit")
    return redacted


def redact_workflow_operations(operations: list[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
    return [redact_workflow_operation(operation, profile) for operation in operations]


def redact_audit_changes(changes: dict[str, Any]) -> dict[str, Any]:
    return redact_payload(changes, DEFAULT_AGGREGATE_EXPORT_PROFILE, module="audit")
