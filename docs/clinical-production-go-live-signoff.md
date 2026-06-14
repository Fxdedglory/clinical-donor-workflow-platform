# Clinical Production Go-Live Signoff

Post-RC-16 update date: 2026-06-13

Deployment provisioning package update date: 2026-06-14

## Release Baseline

Baseline accepted commit before the Post-RC-16 evidence package: `177abc8 Add Key Vault lifecycle readiness`.

The final deployment commit must be recorded from `clinical-production-evidence-bundle.json` before production release approval.

Latest deployment packaging baseline:

- `48d804b Add clinical deployment packaging dry run`
- DEPLOY-02 provisioning documentation package must be reviewed before external Azure provisioning begins.

## Completed Module List

- Clinical Dashboard
- Patients / Donors
- Scheduling
- Donor Screening
- Encounters
- Orders / Results
- Care Plans
- Billing
- Quality
- Reports
- Clinical Admin

No new clinical modules are added by the go-live evidence package.

## Validation Evidence Checklist

- `scripts/preflight_check.py` passes.
- Full pytest passes.
- Frontend build passes.
- `pip check` passes or has an approved exception.
- `npm audit --audit-level=high` reports zero high vulnerabilities or has an approved exception.
- `scripts/start_app_service.py --check` passes in the target environment.
- `scripts/build_clinical_production_evidence_bundle.py --out <approved-evidence-path>` produces sanitized JSON and markdown evidence.

## Deployment Provisioning Checklist

- `docs/clinical-azure-provisioning-checklist.md` is reviewed and accepted by Operations and Security/Compliance.
- `docs/clinical-production-postgres-checklist.md` is reviewed and accepted by DBA/Operations.
- `docs/clinical-app-service-settings-checklist.md` is reviewed and mapped to target App Service settings or approved secret store references.
- `docs/clinical-dns-custom-domain-checklist.md` is reviewed with the DNS owner and site-wide owner.
- `docs/clinical-deployment-execution-runbook.md` is reviewed by the release operator and rollback owner.
- `docs/clinical-site-integration-manifest.json` is reviewed for SITE-WIDE-00 planning.
- Preferred URL decision is confirmed: `https://clinical.teemails.com`.
- Preferred hosting decision is confirmed: single App Service-style FastAPI plus built React frontend.
- Site-wide integration decision is recorded: subdomain launcher link first, or approved path routing alternative with documented rewrite/cookie/API risks.
- Final Product Owner, Security/Compliance, and Operations signoff items below are completed before production cutover.

## Migration Readiness Checklist

- Target database backup and rollback point are confirmed.
- Alembic current revision is checked before migration.
- Alembic head is recorded in the evidence bundle.
- Sprint 2 through Sprint 11 clinical migrations are applied in order.
- Post-RC audit, WORM mirror, and manifest migrations are applied.
- Historical JSON workflow operations are backfilled when required.
- Rollback owner and deployment window are recorded.

## RBAC / Export Readiness Checklist

- `docs/clinical-rbac-matrix.md` is reviewed and accepted.
- `docs/clinical-export-permission-review.md` is reviewed and accepted.
- Export metadata access is approved for reports and quality roles.
- External users remain blocked from internal clinical modules and high-risk export paths.
- Generic workflow commit remains admin-only and confirmation-guarded.

## PHI/ePHI Readiness Checklist

- `docs/clinical-phi-field-inventory.md` is reviewed and accepted.
- Export profiles use approved redaction behavior.
- Small-cell suppression threshold is accepted for shared aggregate analytics.
- Frontend masking is reviewed for external and non-care contexts.
- Evidence bundle confirms no raw credentials, secret values, PHI, or ePHI are included.

## Audit / WORM Readiness Checklist

- DB-backed append-only workflow audit is primary.
- `metadata/workflow_operations.json` remains a compatibility mirror only.
- WORM mirror configuration is approved for the target environment.
- Manifest signing mode and key reference are approved.
- Recovery drill summary is retained for the accepted evidence window.
- Production security gates pass with target hosted settings.

## Azure WORM External Approval Checklist

- Approved storage account and container are identified.
- Immutable retention and legal hold evidence is retained outside the repository.
- Managed/workload identity has least-privilege storage access.
- Live-test prefix is dedicated to non-production validation or has explicit approval.
- `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true` is used only during an approved live-validation window.
- Live WORM validation remains skipped until approvals are complete.

## Key Vault External Approval Checklist

- Approved Key Vault, signing key name, and key version are identified.
- Managed/workload identity has least-privilege sign/verify access.
- Diagnostic/access logging is enabled and review evidence is retained.
- Key lifecycle, rotation, access-log review, and incident recovery references are approved.
- `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true` is used only during an approved live-validation window.
- Live Key Vault signing remains skipped until approvals are complete.

## Live Validation Pending Items

- Real Azure WORM write/stat/checksum validation.
- Real Azure Key Vault sign/verify validation.
- Provider-side immutable retention verification.
- Provider-side legal hold verification.
- Key rotation live exercise.
- Azure Monitor access-log evidence review.
- Incident recovery tabletop.

## Accepted Limitations

- This signoff package does not create Azure resources.
- This signoff package does not run live cloud tests by default.
- This signoff package does not implement production key rotation automation.
- This signoff package does not ingest real Azure access logs.
- Snowflake, Power BI, FHIR/HL7, EDI, notification delivery, and approval execution remain backlog items.

## Product Owner Signoff

Product Owner:

Date:

Decision:

Conditions / Exceptions:

## Security/Compliance Signoff

Security/Compliance Owner:

Date:

Decision:

Conditions / Exceptions:

## Operations Signoff

Operations Owner:

Date:

Decision:

Deployment Window / Rollback Owner:
