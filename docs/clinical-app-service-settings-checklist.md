# Clinical App Service Settings Checklist

Task: `CLINICAL-DEPLOY-02`

Sources:

- `docs/clinical-production-env-template.md`
- `docs/clinical-deployment-env-vars.md`
- `docs/clinical-production-security-gates.md`

This checklist defines production App Service application settings for the preferred single-host deployment. It uses placeholders only and does not contain real secret values.

## Required Non-Secret Settings

| Status | Setting | Expected production-safe value | Security gate relevance | Validation check |
| --- | --- | --- | --- | --- |
| [ ] | `APP_ENV` | `prod` | Enables production-like safety gates. | Startup check reports production gate pass. |
| [ ] | `ENVIRONMENT` | `prod` or aligned with platform standard. | Production-like detector. | Confirm not `dev`, `local`, or `demo`. |
| [ ] | `CLINICAL_ENV` | `prod` | Clinical-specific production-like detector. | Confirm production gate treats environment as production-like. |
| [ ] | `APP_BASE_URL` | `https://clinical.teemails.com` | Link and email base URL correctness. | Verify generated links use the approved host. |
| [ ] | `STARTUP_MODE` | `fastapi_react` | Blocks dev/reload startup values. | `scripts/start_app_service.py --check`. |
| [ ] | `SERVE_FRONTEND` | `true` | Required for single-host frontend serving. | Check `/clinical/dashboard` returns SPA HTML. |
| [ ] | `FRONTEND_DIST_DIR` | `frontend/dist` | Startup reports static directory. | Confirm `frontend/dist/index.html` exists after build. |
| [ ] | `DEBUG` | `false` | Fails if true in production. | Production gate check. |
| [ ] | `COOKIE_SECURE` | `true` | Required for HTTPS production cookies. | Production gate check and browser session smoke. |
| [ ] | `COOKIE_SAMESITE` | `lax` or approved `strict`. | Blocks unsafe SameSite values. | Production gate check. |
| [ ] | `CORS_ORIGINS` | `["https://clinical.teemails.com","https://teemails.com","https://www.teemails.com"]` or approved exact set. | Blocks wildcard, localhost, and loopback origins. | Production gate check and browser API smoke. |
| [ ] | `AUTHENTICATION_ENABLED` | `true` | Auth disabled blocks production startup. | Login/session smoke. |
| [ ] | `AUTH_DISABLED` | `false` | Auth disabled blocks production startup. | Production gate check. |
| [ ] | `ALLOW_DEMO_AUTH_BYPASS` | `false` | Demo bypass blocks production startup. | Production gate check. |
| [ ] | `TEST_AUTH_BYPASS_ENABLED` | `false` | Demo/test bypass must not be enabled. | Production gate check. |
| [ ] | `DEMO_USERS_ENABLED` | `false` | Demo users must not be enabled. | Production gate check. |

## Required Secret Settings

| Status | Setting | Expected production-safe value | Security gate relevance | Validation check |
| --- | --- | --- | --- | --- |
| [ ] | `DATABASE_URL` | TLS PostgreSQL URL from approved secret store. | Required; blocks SQLite, non-PostgreSQL, local hosts, missing host. | `scripts/start_app_service.py --check`, then `/api/monitoring/health`. |
| [ ] | `SECRET_KEY` | Generated value of at least 32 characters. | Placeholder or short value blocks production startup. | Production gate check. |
| [ ] | `ENCRYPTION_KEY` | Generated value of at least 32 characters. | Missing or placeholder value blocks production startup. | Production gate check. |
| [ ] | `MFA_DEV_BYPASS_CODE` | Approved non-demo, non-predictable value or replaced provider flow. | Missing, predictable, or local demo value blocks production startup. | Production gate check. |
| [ ] | `BACKUP_ENCRYPTION_KEY` | Generated value when hosted backup automation is enabled. | Required before backup automation approval. | Backup readiness review. |
| [ ] | Provider credentials | `SMTP_PASSWORD`, `SENDGRID_API_KEY`, `MAILGUN_API_KEY`, or approved provider secret only when provider is enabled. | Secret hygiene and outbound mail approval. | Secret scan and notification provider smoke if enabled. |

## PHI, Export, And Commit Safety

| Status | Setting | Expected production-safe value | Security gate relevance | Validation check |
| --- | --- | --- | --- | --- |
| [ ] | `PHI_REDACTION_ENABLED` | `true` | Disabling PHI redaction blocks production startup. | Production gate check and export smoke. |
| [ ] | `PHI_REDACTION_DISABLED` | `false` | Explicit disable blocks production startup. | Production gate check. |
| [ ] | `DEFAULT_ANALYTICS_EXPORT_PROFILE` | `aggregate_safe` or approved safe profile. | Unsafe analytics profile blocks production startup. | Reports/export smoke. |
| [ ] | `DEFAULT_COMPLIANCE_EXPORT_PROFILE` | `compliance_evidence` or `audit_metadata`. | Unsafe compliance profile blocks production startup. | Quality export smoke. |
| [ ] | `DEFAULT_AUDIT_EXPORT_PROFILE` | `audit_metadata`, `aggregate_safe`, or `external_safe`. | Unsafe audit profile blocks production startup. | Audit export smoke. |
| [ ] | `ALLOW_GENERIC_FOUNDATION_COMMIT` | `false` | Broad generic commit blocks production startup. | Production gate check. |
| [ ] | `GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY` | `true` | Non-admin generic commit blocks production startup. | Permission smoke. |

## Audit Durability Settings

| Status | Setting | Expected production-safe value | Security gate relevance | Validation check |
| --- | --- | --- | --- | --- |
| [ ] | `WORKFLOW_AUDIT_STORAGE` | `db_with_json_mirror` | JSON-only audit mode blocks production startup. | Commit preview/commit smoke and DB audit table check. |
| [ ] | `WORKFLOW_AUDIT_DB_REQUIRED` | `true` | Must remain true in production. | Production gate check. |
| [ ] | `WORKFLOW_AUDIT_PATH` | `metadata/workflow_operations.json` compatibility mirror path. | Not production source of truth. | Confirm DB-backed audit remains primary. |

## WORM Mirror And Azure Blob Settings

| Status | Setting | Expected production-safe value | Security gate relevance | Validation check |
| --- | --- | --- | --- | --- |
| [ ] | `AUDIT_OBJECT_MIRROR_REQUIRED` | `false` for first launch unless Compliance approves WORM. | If true, complete mirror config is required. | Production gate check. |
| [ ] | `AUDIT_OBJECT_MIRROR_MODE` | `disabled` until approved; approved object storage mode later. | Required when mirror is required. | Production gate check. |
| [ ] | `AUDIT_OBJECT_MIRROR_PROVIDER` | Blank until approved; `azure_blob` if approved. | Required for provider placeholder/object storage mode. | Production gate check. |
| [ ] | `AUDIT_OBJECT_MIRROR_CONTAINER` | Approved immutable container when required. | Required when mirror is required. | WORM readiness check. |
| [ ] | `AUDIT_OBJECT_MIRROR_PREFIX` | Approved environment-specific prefix. | Required when mirror is required. | WORM readiness check. |
| [ ] | `AUDIT_OBJECT_MIRROR_RETENTION_POLICY` | Approved retention reference when manifests/immutability are required. | Required when manifest/immutability policy is enabled. | Compliance evidence review. |
| [ ] | `AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL` | Approved storage account URL when Azure WORM is enabled. | Required for Azure mirror when required. | `scripts/check_azure_worm_readiness.py --json`, no live I/O unless approved. |
| [ ] | `AUDIT_OBJECT_MIRROR_AZURE_CONTAINER` | Approved immutable container when Azure WORM is enabled. | Required for Azure mirror when required. | WORM readiness check. |
| [ ] | `AUDIT_OBJECT_MIRROR_AZURE_PREFIX` | Approved prefix when Azure WORM is enabled. | Required for Azure mirror when required. | WORM readiness check. |
| [ ] | `AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE` | `managed_identity` or `workload_identity`. | Unsafe inline credential modes block production. | WORM readiness check. |
| [ ] | `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO` | `false` until approved live validation window. | Real I/O requires SDK and safe identity. | Confirm live tests are not enabled by default. |
| [ ] | `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS` | unset/false until approved. | Operational live-test control. | Confirm no live Azure tests in normal validation. |

## Key Vault Signing Settings

| Status | Setting | Expected production-safe value | Security gate relevance | Validation check |
| --- | --- | --- | --- | --- |
| [ ] | `AUDIT_MANIFEST_SIGNING_REQUIRED` | `false` for first launch unless approved. | If true, signing mode, algorithm, and key ref are required. | Production gate check. |
| [ ] | `AUDIT_MANIFEST_SIGNING_MODE` | `disabled` until approved; `azure_key_vault` when approved. | Placeholder/disabled mode cannot satisfy required signing. | Key Vault readiness check. |
| [ ] | `AUDIT_MANIFEST_SIGNING_ALGORITHM` | `rsa-pss-sha256` or approved non-deprecated algorithm. | Unsafe algorithm blocks required signing. | Key Vault readiness check. |
| [ ] | `AUDIT_MANIFEST_SIGNING_KEY_REF` | Approved key reference, not key material. | Required for external/KMS signing. | Key Vault readiness check. |
| [ ] | `AUDIT_MANIFEST_AZURE_KEY_VAULT_URL` | Approved Key Vault URL when signing is enabled. | Required for Azure Key Vault signing. | `scripts/check_azure_key_vault_signing_readiness.py --json`, no live I/O unless approved. |
| [ ] | `AUDIT_MANIFEST_AZURE_KEY_NAME` | Approved key name when signing is enabled. | Required for Azure Key Vault signing. | Key Vault readiness check. |
| [ ] | `AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE` | `managed_identity` or `workload_identity`. | Unsafe credential modes block production. | Key Vault readiness check. |
| [ ] | `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO` | `false` until approved live validation window. | Real I/O requires SDK and safe identity. | Confirm no live Azure tests in normal validation. |
| [ ] | `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS` | unset/false until approved. | Operational live-test control. | Confirm no live Azure tests in normal validation. |

## Optional Settings To Review

- Email provider settings if outbound notification delivery is approved.
- Data producer and ADLS settings if scheduled exports are approved.
- Session/password policy settings if Security requires hosted overrides.
- Monitoring connection settings if Application Insights or an equivalent telemetry provider is enabled.
