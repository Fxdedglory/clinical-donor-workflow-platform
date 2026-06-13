# Clinical Security Readiness

RC1 review date: 2026-06-13

RC2 update date: 2026-06-13

Post-RC-02 PHI/export hardening update date: 2026-06-13

Post-RC-03 production startup gate update date: 2026-06-13

Post-RC-04 route drift and analytics suppression update date: 2026-06-13

Post-RC-06 WORM mirror foundation update date: 2026-06-13

Post-RC-07 WORM provider readiness update date: 2026-06-13

Post-RC-08 Azure Blob adapter readiness update date: 2026-06-13

Post-RC-09 Azure Blob SDK operations foundation update date: 2026-06-13

Post-RC-10 Azure WORM live harness update date: 2026-06-13

Post-RC-11 Azure WORM evidence package update date: 2026-06-13

Post-RC-12 manifest signing foundation update date: 2026-06-13

Post-RC-13 Azure Key Vault signing readiness update date: 2026-06-13

Post-RC-14 Azure Key Vault live validation harness update date: 2026-06-13

Post-RC-15 Azure Key Vault lifecycle readiness update date: 2026-06-13

Scope: Release Candidate Security / Production Readiness Pass. This review documents the current security posture without adding new clinical modules or introducing new heavyweight scanners.

## Repository-Native Review Process

| Area | Command or source | RC1 result |
| --- | --- | --- |
| Worktree hygiene | `git status --short`; `git diff -- backend/app/cli.py` | Only protected `backend/app/cli.py` was dirty at start. It contains pre-existing seed-data timestamp/referral edits and is excluded from RC1 changes. |
| Secret/config scan | `.\.venv\Scripts\python.exe scripts\preflight_check.py` | Passed. Required docs exist, generated paths are ignored, tracked high-signal secret patterns are absent. |
| Tracked secret check | `git ls-files .env .env.example ...` plus targeted `rg` scan for secret/config names | `.env` is ignored and not tracked; `.env.example` intentionally contains local/demo placeholders. |
| Python dependency consistency | `.\.venv\Scripts\python.exe -m pip check` | Passed. No broken installed requirements found. |
| Python dependency inventory | `pyproject.toml`, `requirements.txt` | No repo-native vulnerability scanner such as `pip-audit` or `safety` is configured. Do not add one in RC1 without platform approval. |
| Frontend dependency review | `cd frontend; npm audit --audit-level=high` | Failed with two high-severity advisories through Vite/esbuild. Suggested npm fix requires a Vite 8 major upgrade, so remediation is deferred to RC2 compatibility testing. |
| Frontend dependency inventory | `frontend/package.json`, `frontend/package-lock.json` | Lockfile is present. Current Vite dependency resolves to Vite 7.x and esbuild 0.27.x in the lockfile. |

## RC2 Dependency Update

RC2 completed the bounded frontend dependency remediation:

- upgraded `vite` from `^7.2.4` to `^8.0.16`;
- upgraded `@vitejs/plugin-react` from `^5.1.1` to `^6.0.2`;
- confirmed local Node `v24.11.0` satisfies Vite 8 and plugin engine requirements;
- ran `npm run build` successfully with Vite `8.0.16`;
- ran `npm audit --audit-level=high` successfully with `found 0 vulnerabilities`.

No RC2 Vite/esbuild release exception remains open.

## Sensitive Configuration Handling

Production deployments must inject sensitive values through managed app settings, deployment secrets, or an equivalent secret store. They must not use repository defaults or local `.env` values.

| Setting | Local/dev expectation | Production expectation |
| --- | --- | --- |
| `APP_ENV` | `dev` is acceptable locally. | Set `APP_ENV=prod` and use it as the operational signal for stricter deployment gates. |
| `DATABASE_URL` | Local or container database URL may use demo credentials. | Use production database credentials, TLS, least-privilege runtime user, and a rotation plan. |
| `SECRET_KEY` | Demo placeholder exists for local bootstrapping. | Generate a strong unique value outside Git. Rotate with a planned session invalidation window. |
| `ENCRYPTION_KEY` | May be empty while field-level encryption is not implemented. | Required before production-grade sensitive-field encryption is enabled. Store outside Git. |
| `BACKUP_ENCRYPTION_KEY` | May be empty for local demos. | Required before hosted backup routines are enabled. |
| `COOKIE_SECURE` | `false` can be used for local HTTP. | Set `true` behind HTTPS. |
| `COOKIE_SAMESITE` | `lax` is acceptable locally. | Prefer `lax`; review partner portal redirect requirements before changing. |
| `CORS_ORIGINS` | Localhost origins are acceptable. | Restrict to approved production domains only. |
| `MFA_DEV_BYPASS_CODE` | Predictable local value exists for development. | Must not be predictable or enabled as a bypass in production. |
| Email/API provider keys | Empty or console provider is acceptable. | Store `SENDGRID_API_KEY`, `MAILGUN_API_KEY`, SMTP credentials, or cloud provider secrets outside Git. |
| `CLOUDFLARE_TUNNEL_TOKEN` | Developer-local only if used. | Do not commit; rotate if copied outside the managed environment. |

## Local/Dev Versus Production Assumptions

Local and demo environments are allowed to prioritize reproducible workflows and seed data. Production must treat the same clinical records as PHI/ePHI-bearing data and enforce stricter controls.

| Control | Local/dev assumption | Production assumption |
| --- | --- | --- |
| Authentication | JWT auth, session records, and RBAC are enabled for operational routes. | Same, plus hardened secrets, cookie security, and external identity/MFA roadmap completion. |
| Demo credentials | Seeded/demo passwords can exist locally. | No shared demo credentials. Seeded users must be removed, disabled, or reset during deployment. |
| Audit storage | `metadata/workflow_operations.json` supports local evidence and testability; local filesystem WORM mirror simulation, Azure Blob readiness checks, fake-client SDK operation tests, skipped-by-default live harnesses, sanitized validation evidence artifacts, manifest generation, local HMAC manifest signing, provider-placeholder signing metadata, real-capable Azure Key Vault signing hooks behind an explicit feature flag, Key Vault lifecycle readiness gates, and recovery drill helpers are available for development/testing. | Database-backed append-only audit storage is primary; object-storage/WORM mirror provider, retention, legal hold, live Key Vault signing validation, provider checksum validation, key lifecycle evidence, and recovery drill evidence must be approved before production evidence immutability signoff. |
| Export delivery | Clinical analytics/compliance exports store metadata and row-count contracts. | External warehouse/clearinghouse delivery remains out of scope until dedicated controls are implemented. |
| PHI masking | Post-RC-02 includes deterministic export/audit redaction profiles. Post-RC-04 adds small-cell suppression for aggregate report/export count cells. Post-RC-05 adds lightweight UI masking. | Centralized UI field policy and approved external delivery controls remain production gate items. |
| Dependency scanning | Preflight, `pip check`, and `npm audit` are used in RC1. | CI should include an approved Python vulnerability scanner and npm audit policy gate. |

## Post-RC-02 PHI/ePHI Export Hardening

Post-RC-02 added `backend/app/services/clinical_phi.py` as a lightweight sensitivity registry and profile redactor. The implementation is intentionally deterministic and limited to export-like/reporting/audit surfaces; it is not a full policy engine.

Hardened endpoints:

- `POST /api/clinical/reports/analytics-exports/preview`
- `POST /api/clinical/reports/analytics-exports`
- `POST /api/clinical/quality/compliance-exports/preview`
- `POST /api/clinical/quality/compliance-exports`
- `GET /api/clinical/quality/audit-evidence`
- `GET /api/clinical/reports/audit-activity`

Implemented profiles:

- `aggregate_safe`
- `internal_detail`
- `compliance_evidence`
- `external_safe`
- `audit_metadata`

Generic foundation commit hardening:

- `POST /api/clinical/workflows/commit` now requires an internal authenticated user with `clinical_admin.manage` or `system.admin`.
- External partner/supplier users are rejected even if they can reach the route.
- Module-specific commit endpoints remain the preferred path for real clinical workflows.

## Post-RC-03 Production Startup Gates

Post-RC-03 adds `backend/app/services/production_security_gates.py` and wires it into `backend/app/main.py`. Production-like startup now fails closed before the application opens traffic when critical security, audit, export, auth, or database defaults are unsafe.

Production-like values are `prod`, `production`, `stage`, and `staging` from `APP_ENV`, `ENVIRONMENT`, or `CLINICAL_ENV`.

The gate blocks:

- default or missing `SECRET_KEY` and `ENCRYPTION_KEY`;
- insecure cookie settings;
- wildcard or localhost CORS origins;
- `DEBUG=true` and reload/dev startup modes;
- missing, SQLite, non-PostgreSQL, or localhost `DATABASE_URL`;
- JSON-only workflow audit storage;
- unsafe default export profiles or disabled PHI/ePHI redaction;
- broadly enabled generic foundation commit;
- disabled authentication, demo auth bypass, demo user mode, or predictable MFA bypass code.

Local/dev mode returns warnings instead of raising, and `scripts/preflight_check.py` reports the warning inventory without requiring production secrets.

Reference: `docs/clinical-production-security-gates.md`.

## Post-RC-04 Route Drift And Small-Cell Suppression

Post-RC-04 adds `tests/test_clinical_route_permission_drift.py`, which enumerates registered FastAPI routes under `/api/clinical` and verifies sensitive routes remain documented in `docs/clinical-api-inventory.md` and classified in the RBAC model.

Route category tokens include:

- `public_or_health`
- `internal_read`
- `internal_mutation`
- `clinical_admin`
- `compliance_export`
- `analytics_export`
- `audit_evidence`
- `external_partner_denied`
- `generic_foundation_restricted`

Post-RC-04 also adds `backend/app/services/clinical_reporting_privacy.py` for deterministic small-cell suppression. For `aggregate_safe` and `external_safe` report/export profiles, nonzero count cells below 5 are replaced with suppression metadata before responses or export row-count contracts are returned. Authorized `internal_detail` usage remains visible for operational review.

## Post-RC-06 Object/WORM Audit Mirror Foundation

Post-RC-06 adds `backend/app/services/clinical_audit_mirror.py` and migration `202606130002_clinical_audit_worm_mirror.py`.

Implemented:

- append-only `operational.clinical_workflow_audit_mirror_events`;
- disabled mode by default;
- local filesystem mirror simulation for deterministic development/testing;
- future object-storage provider placeholders without network calls;
- SHA-256 checksum over canonical redacted audit payloads;
- optional versus required mirror failure policy;
- replay helper for DB audit rows without successful mirror attempts;
- production gate checks when `AUDIT_OBJECT_MIRROR_REQUIRED=true`.

Not implemented:

- Azure/AWS/GCP SDK integration;
- provider-side immutable retention or legal hold creation;
- real cryptographic signing;
- external evidence delivery.

## Post-RC-07 WORM Provider Readiness

Post-RC-07 adds `backend/app/services/clinical_audit_manifest.py` and migration `202606130003_clinical_audit_worm_manifests.py`.

Implemented:

- deterministic signed manifest foundation over successful mirror events;
- append-only `operational.clinical_workflow_audit_mirror_manifests`;
- checksum-placeholder signature metadata without requiring real signing keys;
- local simulation checksum verification for mirrored payloads;
- manifest/object URI and checksum mismatch detection;
- read-only recovery drill summary comparing DB audit rows to mirror records;
- production startup gate checks for required retention policy, legal hold reference, manifest policy, and signature key reference.

Not implemented:

- real Azure/AWS/GCP object listing or checksum readback;
- provider-side immutable retention or legal-hold enforcement;
- real cryptographic signing or external key management;
- automated restore, delete, or production audit mutation.

## Post-RC-08 Cloud Provider Adapter Readiness

Post-RC-08 adds `backend/app/services/clinical_audit_mirror_providers.py`.

Implemented:

- provider adapter contract for put/stat/metadata/list/checksum readiness;
- local filesystem provider wrapping existing simulation behavior;
- Azure Blob readiness provider with guarded real-operation methods;
- SDK-free Azure config validation and expected URI prefix reporting;
- provider readiness output in recovery drill summaries;
- production gate checks for required Azure account URL, container, prefix, credential mode, immutability, legal hold, and checksum validation settings.

Post-RC-09 supersedes the upload/list/head/readback limitation with guarded SDK operation paths. Azure resource creation, role assignment, provider-side immutability/legal-hold enforcement, and live-cloud validation remain future work.

## Post-RC-09 Azure Blob SDK Operations Foundation

Post-RC-09 extends `backend/app/services/clinical_audit_mirror_providers.py`.

Implemented:

- injectable Azure Blob client boundary for fake-client tests;
- guarded SDK adapter for upload, stat/head, metadata read, prefix listing, and checksum verification;
- `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO` feature flag;
- SDK-free readiness summaries that report SDK availability, real-I/O state, supported methods, and no-network dry-run status;
- provider-contract verification in recovery drill inventory checks;
- production startup gate checks for required Azure SDK dependencies when real I/O is enabled.

Post-RC-10 supersedes the live-cloud integration test limitation with skipped-by-default skeletons. Azure resource creation, role assignment, retention policy creation, legal-hold automation, provider-side immutable retention/legal-hold enforcement from code, and external evidence delivery remain future work.

## Post-RC-10 Azure WORM Live Readiness Harness

Post-RC-10 adds a skipped-by-default live validation harness for future Azure Blob WORM checks.

Implemented:

- pytest marker `azure_worm_live`;
- integration skeletons under `tests/integration` that skip unless `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true`;
- live-test prefix guard requiring `AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX`;
- dry-run readiness command `scripts/check_azure_worm_readiness.py --json`;
- explicit `--live-write` switch for future manual write/stat/list/checksum checks;
- tests proving dry-run mode does not require credentials or perform uploads.

Not implemented:

- Azure resource provisioning;
- live-cloud tests in normal CI;
- provider-side immutable retention or legal-hold enforcement from code;
- automatic cleanup of WORM validation objects.

## Post-RC-11 Azure WORM Evidence Package

Post-RC-11 adds a sanitized evidence package for Azure WORM validation readiness.

Implemented:

- reusable evidence builder in `backend/app/services/clinical_azure_worm_evidence.py`;
- `--evidence-out` support in `scripts/check_azure_worm_readiness.py`;
- dry-run evidence fields for provider, real-I/O, live-test, live-write, upload, network, prefix safety, credential mode, immutability, legal hold, checksum validation, blockers, warnings, and validation result;
- sanitizer guardrails that exclude raw credentials and PHI/ePHI from the retained artifact;
- tests proving dry-run evidence writes JSON, performs no uploads or network calls, records incomplete-config blockers, records prefix safety, and excludes secret-like fields and values;
- `docs/clinical-azure-worm-validation-evidence-template.md` and `docs/clinical-azure-worm-operator-checklist.md`.

Not implemented:

- Azure resource provisioning;
- provider-side retention or legal-hold creation;
- live-cloud validation in normal CI;
- cryptographic signing of the evidence package.

## Post-RC-12 Manifest Signing Foundation

Post-RC-12 adds deterministic manifest signing and verification foundations without live KMS or Azure Key Vault calls.

Implemented:

- reusable signing abstraction in `backend/app/services/clinical_audit_signing.py`;
- manifest signing modes for disabled, checksum placeholder, local HMAC, external KMS placeholder, and Azure Key Vault placeholder;
- deterministic canonical signing payloads;
- local HMAC signature generation and verification for dev/test;
- manifest checksum and signature verification status in recovery drill summaries;
- signing metadata in sanitized Azure WORM evidence artifacts;
- production gate failures for required signing with disabled or checksum-placeholder modes, local HMAC without explicit allowance, incomplete Azure Key Vault metadata, missing key reference, or unsafe algorithms;
- `docs/clinical-audit-manifest-signing.md`.

Not implemented:

- live external KMS or Azure Key Vault signing;
- Azure Key Vault verify API calls;
- production private-key lifecycle management;
- evidence package signing outside manifest payloads.

## Post-RC-13 Azure Key Vault Signing SDK Readiness

Post-RC-13 adds a real-capable Azure Key Vault signing boundary while keeping normal tests SDK-free and network-free.

Implemented:

- `azure_key_vault` signing mode behind `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO`;
- guarded optional imports for `azure-keyvault-keys` and `azure-identity`;
- injectable fake-client signing and verification tests;
- Azure Key Vault readiness summaries with vault URL presence, key name/version, credential mode, SDK availability, real-I/O state, and HSM expectation;
- sanitized evidence output for Key Vault signing readiness without raw vault credentials, key material, PHI, or ePHI;
- production gate failures for incomplete Key Vault metadata, unsafe credential mode, and missing SDK dependencies when real I/O is enabled;
- `docs/clinical-azure-key-vault-signing-readiness.md`.

Not implemented:

- Azure resource creation or role assignment;
- live Key Vault validation in normal CI;
- production key rotation automation;
- access-log review workflow;
- incident recovery procedures for compromised or retired signing keys.

## Post-RC-14 Azure Key Vault Live Validation Harness

Post-RC-14 adds a skipped-by-default live validation harness and sanitized evidence package for Key Vault signing.

Implemented:

- pytest marker `azure_key_vault_live`;
- skipped-by-default integration skeletons under `tests/integration`;
- live environment flag `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS`;
- fail-closed key identifier safety for ambiguous or production-like key names/references;
- readiness script `scripts/check_azure_key_vault_signing_readiness.py`;
- `--evidence-out` JSON artifact for dry-run and approved live-sign checks;
- explicit `--live-sign` switch before any Key Vault sign/verify attempt;
- tests proving dry-run no-sign/no-network behavior, evidence sanitization, incomplete-config blockers, and default live-test skip posture;
- `docs/clinical-azure-key-vault-live-validation.md` and `docs/clinical-azure-key-vault-operator-checklist.md`.

Not implemented:

- Azure resource creation;
- live signing in normal CI;
- key rotation automation;
- access-log ingestion;
- incident response automation.

## Post-RC-15 Azure Key Vault Lifecycle Readiness

Post-RC-15 adds repository-safe Key Vault signing lifecycle readiness without live Azure access.

Implemented:

- `backend/app/services/clinical_key_vault_lifecycle.py` for sanitized lifecycle configuration parsing, validation, logical key references, and readiness summaries;
- settings for rotation requirement, rotation interval, next key name/version, retirement policy reference, access-log review reference, and incident recovery reference;
- `lifecycle_summary` in Key Vault signing readiness reports and evidence artifacts;
- production gate failures when required Key Vault signing has incomplete lifecycle metadata;
- focused tests for sanitizer behavior, rotation validation, evidence metadata, and production gate blockers;
- `docs/clinical-azure-key-vault-key-lifecycle.md`, `docs/clinical-azure-key-vault-rotation-runbook.md`, `docs/clinical-azure-key-vault-access-log-review.md`, and `docs/clinical-azure-key-vault-incident-recovery.md`.

Not implemented:

- Azure key creation, version rotation, or permission changes;
- Azure Monitor access-log queries or ingestion;
- automated incident response actions;
- deleting, disabling, purging, or restoring Key Vault keys.

## Known Findings

| Finding | Severity | Evidence | RC1 disposition | Remediation |
| --- | --- | --- | --- | --- |
| Vite/esbuild advisories from `npm audit` | High | RC1 `npm audit --audit-level=high` reported two high-severity advisories and recommended a Vite 8 major upgrade. | Resolved in RC2 with bounded Vite 8 / React plugin 6 upgrade. | Continue to run `npm audit --audit-level=high` in release validation. |
| Production defaults are fail-open if not overridden | High | `SECRET_KEY`, `COOKIE_SECURE=false`, `MFA_DEV_BYPASS_CODE=000000`, local CORS/database defaults, and optional encryption keys exist as defaults/examples. | Resolved in Post-RC-03 with production-like startup gates. | Keep deployment settings aligned to `docs/clinical-production-security-gates.md`. |
| Workflow audit remains filesystem-backed | High | `metadata/workflow_operations.json` full-file append pattern. | Resolved by Post-RC-01 DB-backed append-only audit storage with JSON mirror/fallback; Post-RC-06 adds WORM mirror foundation; Post-RC-07 adds manifest and recovery drill foundations; Post-RC-08 adds Azure Blob adapter readiness; Post-RC-09 adds guarded Azure SDK operation paths; Post-RC-10 adds a skipped-by-default live harness; Post-RC-11 adds sanitized Azure WORM evidence artifacts; Post-RC-12 adds manifest signing foundations; Post-RC-13 adds Azure Key Vault signing SDK readiness hooks; Post-RC-14 adds skipped-by-default Key Vault live validation evidence; Post-RC-15 adds Key Vault lifecycle readiness gates and runbooks. | Complete approved live Azure validation, retention policy enforcement, legal hold automation, provider checksum readback signoff, live Key Vault signing validation, cloud-side key rotation execution, access-log evidence review, and incident recovery tabletop/signoff before production evidence immutability signoff. |
| Generic foundation workflow commit lacks user auth | Medium | `/api/clinical/workflows/commit` requires confirmation header but does not require an authenticated user. | Resolved in Post-RC-02. | Continue to prefer module-specific commit endpoints and keep generic commit admin-only. |
| Report audit activity is available through broad report-read access | Medium | `/api/clinical/reports/audit-activity` uses report read guard. | Documented as minimum-necessary review item. | RC2: split audit activity access behind `audit.review` or a dedicated audit reporting permission. |
| No repository-native Python vulnerability scanner | Medium | `pyproject.toml` dev extras include pytest/httpx/ruff only. | Documented. | RC2: add approved scanner to CI after dependency policy is agreed. |
| Route-permission drift tests were missing | Medium | New clinical routes could be added without matching inventory/RBAC docs. | Resolved in Post-RC-04 with live FastAPI route drift tests for sensitive routes. | Keep docs and category tests updated as routes are added. |
| Small aggregate cohorts could disclose re-identification risk | Medium | Report/export counts previously returned visible nonzero values below 5. | Resolved for aggregate report/export count cells in Post-RC-04. | Review threshold with compliance owners before external analytics sharing. |

## Remediation Plan

1. Keep the Post-RC-03 production startup gate enabled and expand it as new production-only flags are introduced.
2. Keep frontend dependency audit in release validation after the RC2 Vite 8 remediation.
3. Configure and validate live object-storage/WORM provider integration for workflow audit evidence if immutable off-database evidence is required.
4. Split report audit activity and export metadata permissions where compliance owners require least-privilege separation.
5. Add CI-visible vulnerability scanning for Python and frontend dependencies using approved tooling.
6. Add centralized UI field policy and production policy signoff before external delivery.
7. Keep the Post-RC-04 route drift and small-cell suppression tests in release validation.
8. Keep signed manifest and recovery drill evidence in production readiness review once provider integration is approved.
9. Keep Azure Blob provider readiness output, real-I/O dependency gate checks, skipped-by-default live harness evidence, sanitized `--evidence-out` artifacts, manifest signing verification output, Azure Key Vault signing readiness metadata, Key Vault lifecycle summary, and Key Vault live-sign evidence controls in release validation when Azure is selected as the WORM target.
