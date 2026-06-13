export const REDACTED_LABEL = "Redacted";
export const PHI_PROTECTED_LABEL = "PHI protected";
export const SUPPRESSED_LABEL = "Suppressed";
export const SMALL_CELL_LABEL = "Small-cell suppression";

export const EXPORT_PROFILE_OPTIONS = [
  { value: "aggregate_safe", label: "Aggregate safe" },
  { value: "external_safe", label: "External safe" },
  { value: "audit_metadata", label: "Audit metadata" },
  { value: "internal_detail", label: "Internal detail" },
  { value: "compliance_evidence", label: "Compliance evidence" },
];

const EXTERNAL_ROLES = new Set(["Partner External User", "Supplier External User"]);
const INTERNAL_DETAIL_ROLES = new Set([
  "System Administrator",
  "Operations Manager",
  "Clinical Reviewer",
  "Quality Assurance Specialist",
  "Business Technology Analyst",
  "Donor Intake Coordinator",
]);
const DETAIL_PERMISSIONS = new Set([
  "system.admin",
  "reports.export",
  "quality.export",
  "audit.review",
  "clinical_admin.manage",
  "patients.read",
  "patients.manage",
  "screening.read",
  "encounters.read",
  "orders.read",
  "care_plans.read",
  "billing.read",
  "quality.read",
]);

const SENSITIVE_FIELDS = new Set([
  "patient",
  "patient_donor",
  "patient_id",
  "patient_name",
  "name",
  "full_name",
  "date_of_birth",
  "dob",
  "contact",
  "phone",
  "email",
  "address",
  "member_id",
  "group_number",
  "payer_name",
  "note",
  "notes",
  "description",
  "reason",
  "denial_reason",
  "amendment_reason",
  "chief_complaint",
  "clinical_indication",
  "latest_result",
  "order_result",
  "order_result_summary",
  "result_value",
  "value",
  "answer",
  "finding",
  "evidence_summary",
  "corrective_action_recommendation",
  "closure_reason",
  "outcome_summary",
  "progress_note",
  "goal",
  "intervention",
  "title",
  "member",
  "immediate_action_taken",
  "entity_id",
]);

const PROFILE_INFO = {
  aggregate_safe: {
    label: "Aggregate safe",
    redactionActive: true,
    suppressionActive: true,
    warning: "Details are intentionally omitted for aggregate analytics.",
  },
  external_safe: {
    label: "External safe",
    redactionActive: true,
    suppressionActive: true,
    warning: "Internal, PHI/ePHI, financial, compliance, and audit-sensitive fields are omitted.",
  },
  audit_metadata: {
    label: "Audit metadata",
    redactionActive: true,
    suppressionActive: false,
    warning: "Audit evidence avoids raw clinical narratives and sensitive free text.",
  },
  internal_detail: {
    label: "Internal detail",
    redactionActive: false,
    suppressionActive: false,
    warning: "Internal detail should be used only by approved operational roles.",
  },
  compliance_evidence: {
    label: "Compliance evidence",
    redactionActive: false,
    suppressionActive: false,
    warning: "Compliance evidence may include sensitive details and requires approved access.",
  },
};

export function normalizePrivacyField(field) {
  return String(field || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function isSensitiveClinicalField(field) {
  const normalized = normalizePrivacyField(field);
  if (SENSITIVE_FIELDS.has(normalized)) return true;
  return normalized.includes("patient") || normalized.includes("note") || normalized.includes("reason");
}

export function isSuppressedCell(value) {
  return Boolean(value && typeof value === "object" && value.suppressed === true);
}

export function formatSuppressedCell(value) {
  if (!isSuppressedCell(value)) {
    return { suppressed: false, value };
  }
  return {
    suppressed: true,
    label: SUPPRESSED_LABEL,
    badge: SMALL_CELL_LABEL,
    reason: value.suppression_reason || "small_cell",
    threshold: value.threshold,
  };
}

export function isExternalClinicalUser(user) {
  const role = user?.role_name || user?.role || "";
  return Boolean(
    user?.is_external ||
      user?.external_user_flag ||
      ["partner", "supplier", "external"].includes(user?.account_type) ||
      ["partner", "supplier", "external"].includes(user?.user_type) ||
      EXTERNAL_ROLES.has(role),
  );
}

export function canViewOperationalDetail(user) {
  if (!user || isExternalClinicalUser(user)) return false;
  const role = user.role_name || user.role || "";
  const permissions = new Set(user.permissions || []);
  if (INTERNAL_DETAIL_ROLES.has(role)) return true;
  return [...DETAIL_PERMISSIONS].some((permission) => permissions.has(permission));
}

export function clinicalPrivacyMode(user) {
  if (!user) {
    return { label: "Safe display", maskClinicalDetail: true, reason: "Role context unavailable" };
  }
  if (isExternalClinicalUser(user)) {
    return { label: "External safe display", maskClinicalDetail: true, reason: "External partner/supplier access" };
  }
  if (canViewOperationalDetail(user)) {
    return { label: "Internal operational detail", maskClinicalDetail: false, reason: "Internal clinical role" };
  }
  return { label: "Safe display", maskClinicalDetail: true, reason: "Limited clinical role context" };
}

export function displayClinicalValue(value, field, user, options = {}) {
  if (isSuppressedCell(value)) {
    return { kind: "suppressed", ...formatSuppressedCell(value) };
  }
  const empty = value === null || value === undefined || value === "";
  if (empty) return { kind: "empty", value: "" };

  const sensitive = options.sensitive ?? isSensitiveClinicalField(field);
  const mode = clinicalPrivacyMode(user);
  if (sensitive && mode.maskClinicalDetail) {
    return {
      kind: "redacted",
      label: REDACTED_LABEL,
      indicator: PHI_PROTECTED_LABEL,
      reason: mode.reason,
    };
  }
  return { kind: "value", value };
}

export function exportProfileInfo(profile) {
  return PROFILE_INFO[profile] || PROFILE_INFO.aggregate_safe;
}

export function suppressionSummary(metadata) {
  const details = metadata?.small_cell_suppression || metadata;
  if (!details) {
    return { applied: false, threshold: undefined, suppressedCells: 0 };
  }
  return {
    applied: Boolean(details.applied),
    threshold: details.threshold,
    suppressedCells: Number(details.suppressed_cells || 0),
  };
}
