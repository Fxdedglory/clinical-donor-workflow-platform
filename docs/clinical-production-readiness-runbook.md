# Clinical Production Readiness Runbook

RC1 review date: 2026-06-13

RC2 update date: 2026-06-13

Post-RC audit durability update date: 2026-06-13

Post-RC PHI/export hardening update date: 2026-06-13

Post-RC production startup gate update date: 2026-06-13

Post-RC route drift and analytics suppression update date: 2026-06-13

Post-RC UI masking update date: 2026-06-13

Post-RC WORM mirror foundation update date: 2026-06-13

Post-RC WORM provider readiness update date: 2026-06-13

Post-RC Azure Blob adapter readiness update date: 2026-06-13

Post-RC Azure Blob SDK operations foundation update date: 2026-06-13

Post-RC Azure WORM live harness update date: 2026-06-13

This runbook prepares the clinical platform for production signoff. It does not replace environment-specific deployment documentation in `docs/azure/`.

## Environment Variables

Required production settings:

- `APP_ENV=prod`
- `DATABASE_URL` with production database credentials and TLS
- `SECRET_KEY` generated outside Git
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax` unless partner redirect testing requires another approved value
- `CORS_ORIGINS` restricted to approved production domains
- `ENCRYPTION_KEY` generated outside Git
- `WORKFLOW_AUDIT_STORAGE=db_with_json_mirror`
- `WORKFLOW_AUDIT_DB_REQUIRED=true`
- `AUDIT_OBJECT_MIRROR_MODE=disabled` until an approved WORM target is configured, or `object_storage` with approved provider settings
- `AUDIT_OBJECT_MIRROR_REQUIRED=false` until production compliance policy requires object/WORM mirroring
- `AUDIT_OBJECT_MIRROR_PROVIDER`, `AUDIT_OBJECT_MIRROR_CONTAINER`, and `AUDIT_OBJECT_MIRROR_PREFIX` when `AUDIT_OBJECT_MIRROR_REQUIRED=true` and object storage is the approved target
- `AUDIT_OBJECT_MIRROR_RETENTION_POLICY` when manifests are required
- `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED` and `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE` when legal hold is required
- `AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=true` only after manifest retention is approved
- `AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED=true`, `AUDIT_OBJECT_MIRROR_SIGNATURE_ALGORITHM`, and `AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF` only after signature policy is approved
- `AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL`, `AUDIT_OBJECT_MIRROR_AZURE_CONTAINER`, `AUDIT_OBJECT_MIRROR_AZURE_PREFIX`, and `AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE` when Azure Blob is the approved provider
- `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true` only in approved environments with Azure SDK dependencies installed and managed/workload identity configured
- `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true` and `AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX` only for approved non-production live validation runs
- `AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED`, `AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED`, and `AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED` only after provider-side controls are approved
- `DEFAULT_ANALYTICS_EXPORT_PROFILE=aggregate_safe`
- `DEFAULT_COMPLIANCE_EXPORT_PROFILE=compliance_evidence`
- `DEFAULT_AUDIT_EXPORT_PROFILE=audit_metadata`
- `PHI_REDACTION_ENABLED=true`
- `ALLOW_GENERIC_FOUNDATION_COMMIT=false`
- `GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY=true`
- `AUTHENTICATION_ENABLED=true`
- `BACKUP_ENCRYPTION_KEY` before hosted backup automation is enabled
- `EMAIL_PROVIDER` and provider credentials if notification delivery is enabled
- `VITE_API_BASE_URL` only when frontend and backend are hosted separately

Disallowed production values:

- demo `SECRET_KEY`
- predictable `MFA_DEV_BYPASS_CODE`
- demo/shared passwords
- local database credentials
- local `.env` values copied into hosted settings without review
- wildcard or localhost `CORS_ORIGINS`
- SQLite or JSON-only workflow audit settings
- `DEBUG=true`, reload/dev server startup modes, or auth bypass flags

## Migration Sequence

1. Confirm target database backup and rollback point.
2. Confirm Alembic configuration points at the target database.
3. Run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

4. Confirm the Sprint 2 through Sprint 11 clinical migrations from `docs/clinical-migration-runbook.md` are applied.
5. Confirm `202606130001_clinical_workflow_audit_events.py` is applied.
6. Confirm `202606130002_clinical_audit_worm_mirror.py` is applied.
7. Confirm `202606130003_clinical_audit_worm_manifests.py` is applied.
8. If `metadata/workflow_operations.json` contains historical entries, run the JSON backfill helper in the target environment and retain the source JSON file.
9. If object/WORM mirroring is enabled after DB backfill, run mirror replay for DB rows without successful mirror attempts.
10. Generate a manifest for the accepted mirror evidence package and persist manifest metadata if compliance owners approve the package.
11. Run the recovery drill summary for the selected evidence window and retain the report.
12. Run application smoke tests before opening user traffic.
13. Confirm the production startup security gate passes with target hosted settings.

## Validation Commands

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
```

Run from the frontend directory:

```powershell
npm run build
```

RC1 and RC2 also used these readiness checks:

```powershell
.\.venv\Scripts\python.exe -m pip check
cd frontend
npm audit --audit-level=high
```

RC2 upgraded Vite and the React plugin to resolve the RC1 Vite/esbuild advisories. `npm audit --audit-level=high` now reports zero vulnerabilities in the frontend package set.

## Manual QA Checklist Reference

Use `docs/clinical-rc-qa-checklist.md` for manual module QA. RC1 production signoff should include at least:

- patient/donor registration preview and commit;
- scheduling appointment lifecycle;
- screening questionnaire, vitals, result, and override;
- encounter note, sign, amendment, diagnosis, allergy, medication;
- order, result, correction, acknowledgement, cancellation;
- care plan goals, interventions, tasks, progress, closure;
- billing charge, claim, payment, denial, insurance verification;
- quality event, adverse event, investigation, CAPA, closure;
- reporting dashboard and analytics export preview/commit;
- clinical admin configuration preview/commit;
- audit evidence filtering.

## Smoke Test Checklist

1. Login succeeds with an approved internal user.
2. External partner user cannot access internal clinical modules.
3. `/clinical/dashboard` and all `/clinical/...` routes render.
4. `/api/clinical/status` and `/api/clinical/modules` return expected module inventory.
5. A representative commit endpoint rejects missing `X-Confirm-Generation`.
6. The same endpoint accepts `X-Confirm-Generation: true`.
7. A workflow operation audit entry is written.
8. `operational.clinical_workflow_audit_events` contains the new operation.
9. `metadata/workflow_operations.json` still receives the compatibility mirror entry.
10. Reports analytics export preview and commit work for an authorized export role.
11. Reports analytics export preview records `export_profile=aggregate_safe` by default and redacts direct identifiers in returned filters.
12. Reports analytics export preview suppresses nonzero row counts below 5 for `aggregate_safe` and records suppression metadata.
13. Reports analytics export commit writes DB/JSON workflow audit changes without raw PHI/ePHI payloads and includes suppression metadata.
14. Quality compliance export preview/commit require authorized quality/audit/compliance access and record the selected export profile.
15. Quality audit evidence works for an authorized QA/audit role, reads DB-backed operations after backfill, and supports safe profile redaction such as `external_safe`.
16. Generic `/api/clinical/workflows/commit` rejects external users and internal users without `clinical_admin.manage` or `system.admin`.
17. `scripts/start_app_service.py --check` reports `production_security_gate=passed` in the target environment.
18. Clinical admin mutation requires admin mutation permission and confirmation.
19. External or missing role context in the clinical frontend renders high-risk identifiers/free text as `Redacted` with `PHI protected`.
20. Reports and quality export workflows display the selected export profile, redaction status, suppression status, and profile warnings.
21. Suppressed report/export metric cells render as `Suppressed` without showing hidden raw counts.
22. Audit mirror disabled mode does not affect DB audit append or JSON compatibility mirror.
23. If a local simulation mirror is enabled, mirror payloads are redacted and checksum metadata is recorded.
24. If `AUDIT_OBJECT_MIRROR_REQUIRED=true`, startup fails unless required object mirror configuration is present.
25. If manifest/signature policy is required, startup fails unless retention, legal-hold, signature algorithm, and signature key reference settings are present.
26. WORM recovery drill summary reports no missing mirror rows, missing objects, checksum mismatches, or manifest mismatches for the accepted package.
27. Azure Blob provider readiness summary reports the expected URI prefix, safe credential mode, SDK availability, real-I/O enabled/disabled state, and no validation errors before Azure mirroring is required.
28. If `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true`, confirm `azure-storage-blob` and `azure-identity` are installed in the runtime image and a non-production live-cloud smoke test has been signed off.
29. Run `scripts/check_azure_worm_readiness.py --json` and retain the dry-run output before any live Azure write is approved.
30. Confirm any `azure_worm_live` pytest run used a dedicated non-production prefix and was explicitly enabled with `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true`.

## Audit And Export Review Checklist

- Confirm `operational.clinical_workflow_audit_events` is the production query source of truth.
- Confirm `metadata/workflow_operations.json` is retained only as compatibility mirror/fallback evidence.
- Confirm update/delete rejection trigger exists on `operational.clinical_workflow_audit_events`.
- Confirm update/delete rejection trigger exists on `operational.clinical_workflow_audit_mirror_events`.
- Confirm production runtime DB role does not have update/delete grants on workflow audit rows.
- Confirm production runtime DB role does not have update/delete grants on workflow mirror rows.
- Confirm historical JSON audit entries are backfilled without deleting source JSON.
- Confirm mirror replay skips already mirrored operation ids and records checksum/URI metadata for newly mirrored rows.
- Confirm signed manifest metadata exists in `operational.clinical_workflow_audit_mirror_manifests` for accepted evidence packages.
- Confirm manifest checksum and placeholder signature are retained with the evidence package.
- Confirm recovery drill summary is retained and reports `recovery_ready=true` for accepted packages.
- Confirm provider readiness summary is retained with the recovery drill report.
- Confirm Azure credential mode uses managed identity, workload identity, or another approved non-inline secret mode before Azure mirroring is required.
- Confirm `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO` remains false until the approved Azure container, identity role assignment, SDK dependencies, and live-cloud smoke test are complete.
- Confirm live Azure WORM validation uses `AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX` and does not run in normal CI.
- Confirm object/WORM provider retention and legal hold settings are approved before setting `AUDIT_OBJECT_MIRROR_REQUIRED=true`.
- Confirm export metadata retention and access are approved.
- Confirm report audit activity is scoped to approved roles.
- Confirm `aggregate_safe`, `external_safe`, `audit_metadata`, `internal_detail`, and `compliance_evidence` profile behavior is approved for the target environment.
- Confirm small-cell suppression threshold 5 is approved for shared aggregate analytics and export row-count contracts.
- Confirm frontend export profile indicators and suppression labels match approved profile behavior.
- Confirm frontend masking has been reviewed against approved role policy for any external or non-care users.
- Confirm workflow audit change payloads do not store raw PHI/ePHI details after redaction.
- Confirm no external delivery is enabled for analytics/compliance exports.
- Confirm PHI/ePHI UI masking and free-text review requirements are documented before detailed or external exports.
- Confirm `docs/clinical-production-security-gates.md` required variables are set in the hosted app configuration.

## Rollback Notes

- Keep a database backup before migration.
- Roll back application deployment first if validation fails after deployment.
- Use Alembic downgrade only when the migration explicitly supports safe downgrade and clinical data loss has been reviewed.
- Do not delete workflow audit evidence as part of rollback.
- Preserve generated export/audit metadata for incident review.
- If application rollback happens after audit migration, keep the audit table and JSON mirror unless compliance and database owners approve a separate evidence-retention action.

## Known Limitations

- Workflow operation audit is now DB-backed with JSON mirror/fallback, an object/WORM mirror foundation, Azure Blob readiness checks, guarded Azure SDK operation paths, skipped-by-default live harnesses, signed manifest metadata, and recovery drill helpers. Azure resource provisioning, retention policy creation, legal-hold automation, and real cryptographic signing are not implemented by the repository.
- Post-RC-02 adds export/audit redaction profiles, Post-RC-04 adds small-cell suppression for aggregate report/export count cells, and Post-RC-05 adds lightweight role-aware UI masking. A full centralized field-policy engine remains future work.
- Vite/esbuild audit advisories were resolved in RC2 with the bounded Vite 8 upgrade.
- Production startup now fails closed on unsafe production-like secrets, cookie, CORS, database, audit, export, auth, and generic commit settings.
- Analytics/compliance exports are metadata/evidence contracts only; external warehouse, FHIR/HL7, Power BI, clearinghouse, and notification delivery integrations remain out of scope.
