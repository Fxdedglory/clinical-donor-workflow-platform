import { PHI_PROTECTED_LABEL, REDACTED_LABEL } from "./clinicalPrivacyDisplay";

export function ClinicalRedactedValue({ label = REDACTED_LABEL, indicator = PHI_PROTECTED_LABEL }) {
  return (
    <span className="clinical-redacted-value" aria-label={`${label}: ${indicator}`}>
      <span>{label}</span>
      <small>{indicator}</small>
    </span>
  );
}
