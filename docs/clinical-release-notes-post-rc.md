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

- Object-storage immutability/WORM mirror remains planned.
- Full role-aware UI masking and production free-text review remain planned.
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

- Small-cell suppression for report aggregates remains planned.
- Full role-aware UI field masking remains planned.
- Object-storage immutability/WORM mirror remains planned.
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

- Route-permission drift inventory tests remain planned.
- Small-cell suppression remains planned.
- Full role-aware UI field masking remains planned.
- Object-storage immutability/WORM mirror remains planned.
- External secret manager and Entra-backed MFA integration remain future deployment-hardening work.
