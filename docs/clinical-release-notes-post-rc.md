# Clinical Release Notes Post-RC

Update: CLINICAL-POST-RC-01

Date: 2026-06-13

## Audit Durability Foundation

- Added database-backed append-only workflow audit storage at `operational.clinical_workflow_audit_events`.
- Added Alembic migration `202606130001_clinical_workflow_audit_events.py` with indexes and an update/delete rejection trigger.
- Updated successful clinical workflow commits to write DB audit rows when a DB session is available.
- Preserved `metadata/workflow_operations.json` as a compatibility mirror and fallback.
- Updated quality audit evidence and report audit activity readers to use DB rows first, then JSON fallback.
- Added JSON backfill helper `backfill_workflow_operations_from_json` that inserts valid JSON entries into DB audit storage without deleting the source file.
- Added focused tests for DB append, JSON mirror preservation, DB-first readers, and non-destructive backfill.

## Deferred Items

- Object-storage immutability/WORM provider integration remains planned.
- Centralized UI field-policy management and production free-text review remain planned.
- Production startup fail-closed checks are implemented in CLINICAL-POST-RC-03.

## PHI/ePHI Export Hardening And Generic Commit Lockdown

Update: CLINICAL-POST-RC-02

Date: 2026-06-13

- Added lightweight PHI/ePHI sensitivity registry and reusable export profiles in `backend/app/services/clinical_phi.py`.
- Added `aggregate_safe`, `internal_detail`, `compliance_evidence`, `external_safe`, and `audit_metadata` redaction profiles.
- Applied profile selection/enforcement to reports analytics exports, quality compliance exports, quality audit evidence, and report audit activity.
- Recorded selected export profiles in export metadata and preview responses.
- Redacted workflow audit change payloads before DB append and JSON mirror/fallback writes.
- Locked down generic `POST /api/clinical/workflows/commit` to internal authenticated users with `clinical_admin.manage` or `system.admin`.
- Kept module-specific commit endpoints unchanged and preferred for real clinical workflow mutations.
- Added focused tests for registry classification, profile redaction, profile permission checks, export redaction behavior, audit evidence/report activity safe profiles, and generic commit lockdown.

## Remaining Post-RC Items

- Centralized UI field-policy management remains planned.
- Object-storage immutability/WORM provider integration remains planned.
- External secret manager and Entra-backed MFA integration remain planned.
- External warehouse, FHIR/HL7, Power BI, clearinghouse, and object export delivery remain out of scope until separately approved.

## Production Startup Fail-Closed Security Gates

Update: CLINICAL-POST-RC-03

Date: 2026-06-13

- Added deterministic production startup gate service in `backend/app/services/production_security_gates.py`.
- Wired the gate into `backend/app/main.py` so production-like environments fail before app startup when unsafe defaults are present.
- Added App Service startup check and preflight visibility without breaking normal local development.
- Added settings for workflow audit mode, export profile defaults, PHI redaction, generic foundation commit lockdown, debug mode, and auth bypass controls.
- Added focused tests for local warning behavior, production failure conditions, and safe production config pass behavior.
- Added `docs/clinical-production-security-gates.md` and updated readiness/runbook documentation.

## Remaining Post-RC Security Items

- Centralized UI field-policy management remains planned.
- Object-storage immutability/WORM provider integration remains planned.
- External secret manager and Entra-backed MFA integration remain future deployment-hardening work.

## Route Drift Tests And Analytics Small-Cell Suppression

Update: CLINICAL-POST-RC-04

Date: 2026-06-13

- Added live FastAPI route-permission drift tests for `/api/clinical` sensitive routes.
- Documented route permission categories across API inventory and RBAC docs, including `public_or_health`, `internal_read`, `internal_mutation`, `clinical_admin`, `compliance_export`, `analytics_export`, `audit_evidence`, `external_partner_denied`, and `generic_foundation_restricted`.
- Added reusable small-cell suppression helpers for aggregate report/export count cells.
- Applied suppression to clinical report read endpoints for `aggregate_safe` and `external_safe` profiles.
- Applied suppression to analytics export preview and commit row-count contracts.
- Persisted suppression metadata in analytics export metadata and workflow audit changes.
- Kept `internal_detail` available for authorized internal export/audit/admin users without small-cell suppression.
- Added tests for suppression threshold behavior, profile behavior, export metadata, audit changes, and route-permission drift.

## Remaining Post-RC Hardening Items

- Full centralized UI field-policy management remains planned after the lightweight Post-RC-05 masking foundation.
- Object-storage immutability/WORM provider integration remains planned.
- External secret manager and Entra-backed MFA integration remain future deployment-hardening work.

## Role-Aware UI PHI Masking And Export Indicators

Update: CLINICAL-POST-RC-05

Date: 2026-06-13

- Added frontend privacy display helpers for redacted PHI/ePHI values and suppressed aggregate cells.
- Applied role-aware masking indicators to high-risk clinical surfaces for patients, scheduling, screening, encounters, orders, care plans, billing, quality, and reports.
- Defaulted missing frontend role context to safer masked display while preserving backend RBAC as the authorization boundary.
- Added export profile selectors and indicators in reports analytics exports and quality compliance exports.
- Displayed redaction active/inactive status, small-cell suppression active/inactive status, thresholds, suppressed-cell counts, and profile warnings.
- Rendered suppressed report/export metric cells as `Suppressed` without showing hidden raw counts.
- Added focused helper/source tests in `tests/test_clinical_ui_privacy_helpers.py`.
- Added `docs/clinical-ui-phi-masking.md` and updated export, suppression, PHI inventory, RBAC, and production readiness docs.

## Remaining Post-RC-05 Items

- Replace the lightweight frontend masking helper with a centralized approved field-policy engine if granular partner-facing clinical views are approved.
- Object-storage immutability/WORM provider integration remains planned.
- External warehouse, FHIR/HL7, Power BI, clearinghouse, notification delivery, and approval execution integrations remain out of scope until separately approved.

## Object/WORM Audit Mirror Foundation

Update: CLINICAL-POST-RC-06

Date: 2026-06-13

- Added `backend/app/services/clinical_audit_mirror.py` with disabled mode, local filesystem simulation, future object-storage provider placeholders, deterministic checksum calculation, and replay support.
- Added append-only `operational.clinical_workflow_audit_mirror_events` via migration `202606130002_clinical_audit_worm_mirror.py`.
- Wired workflow audit append to keep DB-first behavior, preserve JSON mirror/fallback, and optionally record object/WORM mirror attempts.
- Defensively redacted mirror payload changes with the existing audit redactor and stored SHA-256 checksums over canonical JSON.
- Added production startup gate checks for `AUDIT_OBJECT_MIRROR_REQUIRED=true`, missing provider/container/prefix settings, and unsafe local filesystem production use.
- Added tests for disabled mode, local simulation, redacted payloads, deterministic checksums, mirror failure policy, replay/backfill behavior, and production gates.
- Added `docs/clinical-audit-worm-mirror.md` and updated audit durability, production readiness, security gate, and security readiness documentation.

## Remaining Post-RC-06 Items

- Implement real cloud provider SDK integration for the approved WORM target.
- Configure immutable retention, legal hold, access logging, lifecycle policy, and recovery checks in the selected provider.
- Add signed manifests or evidence package signing if compliance owners require tamper-evident export packages.
- Keep external warehouse, FHIR/HL7, Power BI, clearinghouse, notification delivery, and approval execution integrations out of scope until separately approved.

## WORM Provider Readiness, Manifests, And Recovery Drills

Update: CLINICAL-POST-RC-07

Date: 2026-06-13

- Added `backend/app/services/clinical_audit_manifest.py` with deterministic manifest generation, manifest checksums, checksum-placeholder signatures, local verification, and recovery drill summaries.
- Added append-only `operational.clinical_workflow_audit_mirror_manifests` via migration `202606130003_clinical_audit_worm_manifests.py`.
- Added manifest persistence helpers for accepted evidence packages.
- Added local mirror verification for missing payloads, checksum mismatches, and manifest/object mismatches.
- Added read-only recovery drill summaries comparing DB audit rows to successful mirror events.
- Added production startup gate checks for required retention policy, legal hold reference, manifest policy, and signature key reference.
- Added tests for manifest determinism, checksum changes, persistence, verification, recovery drill behavior, and provider readiness gates.
- Added `docs/clinical-audit-worm-recovery-drill.md` and `docs/clinical-audit-worm-retention-legal-hold.md`; updated WORM mirror, durability, migration, production readiness, security readiness, and security gate docs.

## Remaining Post-RC-07 Items

- Implement real cloud provider SDK upload/list/checksum verification.
- Configure and validate provider-side immutable retention and legal hold.
- Replace checksum-placeholder signatures with approved cryptographic signing and key management.
- Execute environment-specific recovery drills with compliance and database owner signoff.
