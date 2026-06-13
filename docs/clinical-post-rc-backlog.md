# Clinical Post-RC Backlog

Post-RC-16 update date: 2026-06-13

## External Azure Validation

- Execute real Azure WORM validation after storage account, container, identity, retention, legal hold, and logging approvals.
- Execute real Azure Key Vault validation after Key Vault, key version, identity, SDK, and logging approvals.
- Verify provider-side immutable retention from Azure evidence.
- Verify provider-side legal hold from Azure evidence.
- Complete a key rotation live exercise.
- Complete Azure Monitor access-log evidence review.
- Complete incident recovery tabletop and retain signoff evidence.
- Decide whether live-cloud integration tests should remain manual-only or move into a gated CI lane.

## Clinical Integrations

- Snowflake analytics delivery.
- Power BI semantic/reporting delivery.
- FHIR/HL7 export.
- Clearinghouse/EDI billing submission.
- Notification delivery through approved email/SMS/provider channels.
- Approval execution with full workflow assignment, delegation, and escalation.

## Product And Frontend Follow-Up

- Broader frontend component decomposition for large operational screens.
- Centralized UI field policy for masking and minimum-necessary display.
- Product Owner browser signoff for all go-live workflows.
- Accessibility pass for high-volume clinical workflows.

## Security And Operations Follow-Up

- Production secret-store integration.
- Entra-backed MFA and identity hardening.
- CI-visible Python vulnerability scanning with approved tooling.
- Production backup and restore automation.
- Evidence package retention automation after compliance approval.
