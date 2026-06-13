import { formatSuppressedCell, isSuppressedCell } from "./clinicalPrivacyDisplay";

export function ClinicalSuppressedMetric({ cell, value, formatter }) {
  if (!isSuppressedCell(cell)) {
    const displayValue = formatter ? formatter(value ?? cell) : value ?? cell;
    return <>{displayValue}</>;
  }

  const summary = formatSuppressedCell(cell);
  const thresholdText = summary.threshold ? `< ${summary.threshold}` : "";
  return (
    <span className="clinical-suppressed-metric" aria-label={`${summary.label}: ${summary.badge}`}>
      <span>{summary.label}</span>
      <small>{summary.badge}{thresholdText ? ` ${thresholdText}` : ""}</small>
    </span>
  );
}
