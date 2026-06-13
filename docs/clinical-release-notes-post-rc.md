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

## Cloud Provider WORM Adapter Readiness

Update: CLINICAL-POST-RC-08

Date: 2026-06-13

- Added `backend/app/services/clinical_audit_mirror_providers.py` with a provider adapter contract, local filesystem provider, Azure Blob readiness provider, and provider readiness summaries.
- Preserved existing local mirror behavior while adding stat, metadata, list, and checksum verification through the local provider.
- Added Azure Blob readiness validation for account URL, container, prefix, credential mode, immutability expectation, legal-hold expectation, and checksum validation expectation.
- Added SDK-free Azure dry-run behavior; no Azure SDK import or network call is required for tests or readiness summaries.
- Extended recovery drill summaries with provider readiness, expected URI prefix, capability flags, manifest count, and mirrored object count.
- Extended production startup gates for required Azure Blob mirror configuration and unsafe credential modes.
- Added focused tests for provider registry, local compatibility, Azure validation, SDK-free readiness, provider dry-run summaries, recovery drill provider readiness, and Azure production gate behavior.
- Added `docs/clinical-audit-worm-provider-adapters.md` and `docs/clinical-azure-blob-worm-readiness.md`; updated WORM mirror, recovery drill, retention/legal-hold, production readiness, security readiness, and production gate docs.

## Remaining Post-RC-08 Items

- Superseded by Post-RC-09 guarded Azure SDK operation paths; live-cloud validation remains pending.
- Validate Azure immutability and legal-hold state from provider APIs.
- Persist provider object metadata and manifest payload objects in the approved WORM container.
- Add production recovery drills that compare DB audit rows, mirror records, manifest payloads, and Azure object inventory.

## Azure Blob WORM SDK Operations Foundation

Update: CLINICAL-POST-RC-09

Date: 2026-06-13

- Added a fakeable Azure Blob client boundary and guarded SDK adapter in `backend/app/services/clinical_audit_mirror_providers.py`.
- Implemented Azure provider operation methods for object upload, stat/head, metadata read, prefix listing, and checksum verification.
- Added `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO`; real SDK construction is disabled by default and required only for approved live Azure I/O.
- Preserved SDK-free readiness and local/test behavior when Azure packages are absent.
- Extended recovery verification to use the active provider contract instead of local filesystem assumptions only.
- Extended production startup gates so required Azure real I/O fails when `azure-storage-blob` or identity dependencies are unavailable.
- Added fake-client tests for payload bytes, checksum metadata, URI construction, idempotency, metadata reads, prefix listing, checksum pass/fail, SDK-missing behavior, recovery verification, and Azure production gates.
- Updated WORM provider, Azure readiness, recovery drill, production readiness, production gate, and security readiness documentation.

## Remaining Post-RC-09 Items

- Superseded by Post-RC-10 skipped-by-default live integration skeletons; approved live execution remains pending.
- Validate provider-side immutable retention and legal-hold state from Azure APIs.
- Confirm managed/workload identity role assignment and least-privilege access in the hosted environment.
- Persist signed manifest payload objects in the approved WORM container when compliance owners approve that package flow.

## Azure WORM Live Integration Readiness Harness

Update: CLINICAL-POST-RC-10

Date: 2026-06-13

- Added `backend/app/services/clinical_azure_worm_live_readiness.py` with explicit live-test flag, prefix safety, and readiness report helpers.
- Added pytest marker `azure_worm_live` and skipped-by-default integration skeletons under `tests/integration`.
- Added `scripts/check_azure_worm_readiness.py` for dry-run provider readiness output and explicit `--live-write` future validation.
- Added safety tests for default skip posture, explicit env-flag enablement, dedicated non-production test prefixes, override warnings, and script dry-run no-upload behavior.
- Added `docs/clinical-azure-worm-live-validation.md` with Azure resource assumptions, retention/legal-hold checklist, identity checklist, live validation steps, evidence capture, and cleanup notes.
- Updated Azure WORM readiness, provider adapter, recovery drill, production readiness, security gate, and security readiness docs.

## Remaining Post-RC-10 Items

- Provision or identify approved Azure storage resources outside the repository.
- Run live Azure validation only after managed/workload identity, WORM policy, and test prefix approvals.
- Validate provider-side immutability and legal-hold state from Azure APIs.
- Add evidence-package signing with approved key management when compliance owners approve the flow.

## Azure WORM Validation Evidence Package

Update: CLINICAL-POST-RC-11

Date: 2026-06-13

- Added `backend/app/services/clinical_azure_worm_evidence.py` for sanitized Azure WORM validation evidence generation.
- Added `--evidence-out` to `scripts/check_azure_worm_readiness.py` for dry-run and approved live-write evidence artifacts.
- Included provider, environment, real-I/O, live-test, live-write, upload, network, account/container/prefix, credential mode, immutability, legal hold, checksum, blocker, warning, validation result, and data-safety summaries.
- Preserved repo-safe defaults: dry-run evidence requires no credentials, performs no uploads, performs no network calls, and excludes raw credentials and PHI/ePHI.
- Added focused tests for evidence JSON creation, dry-run no-upload/no-network posture, incomplete-config blockers, prefix safety status, sanitizer behavior, and default live-test skip posture.
- Added `docs/clinical-azure-worm-validation-evidence-template.md` and `docs/clinical-azure-worm-operator-checklist.md`.
- Updated Azure WORM live validation, Azure Blob readiness, provider adapter, recovery drill, production readiness, production gate, and security readiness documentation.

## Remaining Post-RC-11 Items

- Run live Azure validation only after external storage, identity, WORM policy, and compliance approvals.
- Validate provider-side immutability and legal-hold state from Azure APIs.
- Add approved cryptographic signing for evidence packages.
- Keep external evidence delivery and automated cleanup out of scope until separately approved.

## Cryptographic Manifest Signing Foundation

Update: CLINICAL-POST-RC-12

Date: 2026-06-13

- Added `backend/app/services/clinical_audit_signing.py` with deterministic canonical signing payloads and signing modes for disabled, checksum placeholder, local HMAC, external KMS placeholder, and Azure Key Vault placeholder.
- Integrated signing into audit mirror manifest generation while preserving manifest checksums and metadata persistence.
- Added local HMAC signature verification and tamper detection for dev/test manifests.
- Added manifest checksum and signature verification status to recovery drill summaries.
- Extended sanitized Azure WORM evidence output with manifest signing mode, required flag, algorithm, key reference, and verification status without key material.
- Extended production security gates for required signing, disabled/checksum-placeholder modes, local HMAC allowance, external/KMS key references, Azure Key Vault placeholder metadata, and unsafe algorithms.
- Added `docs/clinical-audit-manifest-signing.md` and updated WORM, Azure readiness, recovery, production, security, and operator documentation.

## Remaining Post-RC-12 Items

- Implement approved live external KMS or Azure Key Vault signing and verification.
- Validate provider-side immutability and legal-hold state from Azure APIs.
- Superseded by Post-RC-15 lifecycle readiness runbooks; cloud-side key lifecycle execution remains pending.
- Keep live-cloud signing and Azure WORM validation opt-in until compliance owners approve execution.

## Azure Key Vault Signing SDK Operations Readiness

Update: CLINICAL-POST-RC-13

Date: 2026-06-13

- Added real-capable `azure_key_vault` manifest signing mode behind `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO`.
- Added an injectable Azure Key Vault signing client boundary plus a guarded SDK wrapper for future `azure-keyvault-keys` and `azure-identity` use.
- Kept local/dev/test safe without Azure SDK packages unless real Key Vault I/O is explicitly enabled.
- Added fake-client tests for deterministic canonical payload signing, verification success, manifest tamper failure, key reference handling, SDK-missing behavior, and sanitized evidence metadata.
- Extended audit manifest generation and verification to accept injected signing clients while preserving existing local HMAC behavior.
- Extended sanitized Azure WORM evidence output with Key Vault readiness, real-I/O state, credential mode, key name/version, SDK availability, and verification metadata without key material.
- Extended production gates for required Key Vault metadata, safe credential mode, and SDK dependencies when real I/O is enabled.
- Added `docs/clinical-azure-key-vault-signing-readiness.md` and updated Azure WORM, production gate, readiness, security, evidence, and operator docs.

## Remaining Post-RC-13 Items

- Run live Azure Key Vault validation only after Key Vault, identity, SDK, logging, and compliance approvals.
- Superseded by Post-RC-15 lifecycle readiness runbooks; cloud-side key rotation, access review execution, and incident recovery exercises remain pending.
- Keep live Azure WORM validation and Key Vault signing out of normal CI unless separately approved.

## Azure Key Vault Signing Live Validation Harness

Update: CLINICAL-POST-RC-14

Date: 2026-06-13

- Added `azure_key_vault_live` pytest marker and skipped-by-default live integration skeletons.
- Added `backend/app/services/clinical_azure_key_vault_live_readiness.py` for live flag handling, key identifier safety checks, readiness summaries, sanitized evidence, and no-network dry-run posture.
- Added `scripts/check_azure_key_vault_signing_readiness.py` with `--json`, `--evidence-out`, and explicit `--live-sign`.
- Added fail-closed guards requiring `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true`, safe Key Vault metadata, safe credential mode, SDK availability, and dedicated non-production key identifiers before live signing.
- Added focused tests for default skip posture, explicit live flag, key identifier safety, dry-run no-sign/no-network behavior, evidence JSON, evidence sanitization, and incomplete-config blockers.
- Added `docs/clinical-azure-key-vault-live-validation.md` and `docs/clinical-azure-key-vault-operator-checklist.md`; updated signing, evidence, operator, production, security, and readiness docs.

## Remaining Post-RC-14 Items

- Execute live Key Vault validation only after Azure resources, identity permissions, SDK runtime, access logging, and compliance approval are in place.
- Superseded by Post-RC-15 lifecycle readiness runbooks; cloud-side key rotation execution, access-log evidence review, and incident recovery exercises remain pending.
- Keep Key Vault live signing and Azure WORM live validation out of normal CI unless separately approved.

## Azure Key Vault Signing Lifecycle Readiness

Update: CLINICAL-POST-RC-15

Date: 2026-06-13

- Added `backend/app/services/clinical_key_vault_lifecycle.py` for sanitized Key Vault lifecycle readiness parsing, validation, logical current/next key references, and data-safety metadata.
- Added lifecycle settings for rotation requirement, rotation interval, next key name/version, retirement policy reference, access-log review reference, and incident recovery reference.
- Extended Key Vault signing readiness reports and evidence artifacts with `lifecycle_summary`.
- Extended production gates so required Key Vault signing fails when required rotation, retirement, access-log review, or incident recovery metadata is incomplete.
- Added focused tests for lifecycle sanitizer behavior, secret/key-material exclusion, rotation validation, evidence output, and production gate blockers.
- Added Key Vault lifecycle, rotation, access-log review, and incident recovery runbooks.
- Updated signing, live validation, operator, production gate, production readiness, and security readiness documentation.

## Remaining Post-RC-15 Items

- Execute cloud-side key rotation only through approved Azure/change-control procedures.
- Validate access-log evidence from Azure Monitor or the approved logging platform outside repository tests.
- Run incident recovery tabletop exercises and retain signoff evidence.
- Keep Key Vault live signing, Azure WORM live validation, and incident actions out of normal CI unless separately approved.

## Production Evidence Bundle And Go-Live Signoff

Update: CLINICAL-POST-RC-16

Date: 2026-06-13

- Added `scripts/build_clinical_production_evidence_bundle.py` to generate a repo-safe dry-run production evidence bundle without credentials, PHI/ePHI, live cloud tests, or network calls.
- Evidence bundle includes git commit, Alembic head, validation command checklist, clinical module inventory, documentation references, production security gate summary, audit durability summary, WORM readiness, Azure WORM dry-run readiness, Key Vault signing dry-run readiness, key lifecycle readiness, known limitations, and external approval checklist.
- Added `docs/clinical-production-go-live-signoff.md` with Product Owner, Security/Compliance, and Operations signoff sections.
- Added `docs/clinical-live-validation-decision-log.md` documenting skipped-by-default Azure WORM and Key Vault live validation policy.
- Added `docs/clinical-post-rc-backlog.md` for deferred external Azure validation, analytics delivery, FHIR/HL7, clearinghouse/EDI, notification delivery, approval execution, and frontend decomposition.
- Updated production readiness, security readiness, Azure WORM operator, and Key Vault operator documentation.

## Remaining Post-RC-16 Items

- Complete human go-live signoff in the target deployment environment.
- Execute external Azure live validations only after approval and resource readiness.
- Retain generated production evidence bundles in the approved evidence repository.
- Continue backlog execution for external integrations and production operations automation.
