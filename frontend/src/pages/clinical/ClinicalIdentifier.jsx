const IDENTIFIER_FIELD_TERMS = [
  "id",
  "number",
  "reference",
  "ref",
  "code",
  "hash",
  "entity",
  "export",
];

const TOKEN_FIELD_TERMS = [
  "workflow",
  "module",
  "profile",
  "type",
  "category",
  "source",
  "method",
  "format",
];

function normalizedField(field) {
  return String(field || "")
    .replaceAll("-", "_")
    .replaceAll(" ", "_")
    .toLowerCase();
}

export function clinicalCellKind(field, value) {
  const name = normalizedField(field);
  const text = String(value ?? "");
  if (!text) return "empty";
  if (name.includes("email") || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) return "contact";
  if (name.includes("phone")) return "contact";
  if (name.includes("date") || name.includes("timestamp") || name.endsWith("_at")) return "nowrap";
  if (IDENTIFIER_FIELD_TERMS.some((term) => name === term || name.endsWith(`_${term}`) || name.includes(`_${term}_`))) {
    return "identifier";
  }
  if (/^[A-Z]{2,}(?:-[A-Z0-9]+)+$/.test(text) || /^[A-Z]{2,}:[A-Z0-9-]+$/.test(text)) {
    return "identifier";
  }
  if (TOKEN_FIELD_TERMS.some((term) => name === term || name.endsWith(`_${term}`) || name.includes(`_${term}_`))) {
    return "token";
  }
  return "text";
}

export function ClinicalIdentifier({ value, className = "" }) {
  const text = String(value ?? "");
  if (!text) return "";
  return (
    <span className={`clinical-id clinical-truncate ${className}`.trim()} title={text}>
      {text}
    </span>
  );
}
