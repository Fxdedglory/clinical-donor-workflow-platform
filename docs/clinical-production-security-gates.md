# Clinical Production Security Gates

Post-RC-03 update date: 2026-06-13

Post-RC-06 WORM mirror gate update date: 2026-06-13

Post-RC-07 manifest/signature gate update date: 2026-06-13

Post-RC-08 Azure provider readiness gate update date: 2026-06-13

Post-RC-09 Azure real-I/O gate update date: 2026-06-13

Post-RC-10 Azure live harness note date: 2026-06-13

Post-RC-11 Azure evidence package note date: 2026-06-13

Post-RC-12 manifest signing gate update date: 2026-06-13

Scope: fail-closed startup validation for production-like environments. The gate is deterministic, uses local configuration only, and does not call a network service or require an external secret manager.

## Runtime Behavior

The startup gate lives in `backend/app/services/production_security_gates.py`.

Production-like environments are detected from:

- `APP_ENV`
- `ENVIRONMENT`
- `CLINICAL_ENV`

The values `prod`, `production`, `stage`, and `staging` are treated as production-like. Local values such as `dev`, `development`, `local`, `test`, `testing`, and `demo` do not hard fail. In local/dev mode, the gate returns warnings so developers can see which defaults would block production.

`backend/app/main.py` calls the gate during application import. If a production-like environment has critical failures, the application raises `RuntimeError` and refuses to start.

## Required Production Settings

- `APP_ENV=prod` or another approved production-like environment value.
- `SECRET_KEY` must be generated outside Git and must not be a demo/default placeholder.
- `ENCRYPTION_KEY` must be generated outside Git so encryption helpers do not fall back to `SECRET_KEY`.
- `COOKIE_SECURE=true`.
- `COOKIE_SAMESITE=lax` or `strict`.
- `CORS_ORIGINS` must contain only approved production origins.
- `DATABASE_URL` must point at PostgreSQL, not SQLite or localhost.
- `WORKFLOW_AUDIT_STORAGE=db_with_json_mirror`.
- `WORKFLOW_AUDIT_DB_REQUIRED=true`.
- `AUDIT_OBJECT_MIRROR_REQUIRED=false` unless compliance policy requires object/WORM mirroring.
- If `AUDIT_OBJECT_MIRROR_REQUIRED=true`, configure `AUDIT_OBJECT_MIRROR_MODE`, `AUDIT_OBJECT_MIRROR_PROVIDER`, `AUDIT_OBJECT_MIRROR_CONTAINER`, and `AUDIT_OBJECT_MIRROR_PREFIX`.
- If manifest/signature policy is required, configure `AUDIT_OBJECT_MIRROR_RETENTION_POLICY`, `AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED`, `AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED`, `AUDIT_OBJECT_MIRROR_SIGNATURE_ALGORITHM`, and `AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF`.
- For new signed manifest configuration, prefer `AUDIT_MANIFEST_SIGNING_REQUIRED`, `AUDIT_MANIFEST_SIGNING_MODE`, `AUDIT_MANIFEST_SIGNING_ALGORITHM`, and `AUDIT_MANIFEST_SIGNING_KEY_REF`.
- If Azure Key Vault placeholder signing is selected, configure `AUDIT_MANIFEST_AZURE_KEY_VAULT_URL` and `AUDIT_MANIFEST_AZURE_KEY_NAME`.
- If legal hold is required, configure `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED=true` and `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE`.
- If `AUDIT_OBJECT_MIRROR_PROVIDER=azure_blob` or `azure_blob_immutability`, configure `AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL`, `AUDIT_OBJECT_MIRROR_AZURE_CONTAINER`, `AUDIT_OBJECT_MIRROR_AZURE_PREFIX`, and `AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE`.
- Set `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true` only after Azure Blob writes are approved for the environment and required SDK dependencies are installed.
- Live validation flags such as `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS` and `AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX` are operational test controls, not startup gate bypasses.
- If Azure immutability, legal hold, or checksum validation is required, configure the matching `AUDIT_OBJECT_MIRROR_AZURE_*_REQUIRED` flags plus retention/legal-hold references.
- `DEFAULT_ANALYTICS_EXPORT_PROFILE=aggregate_safe`.
- `DEFAULT_COMPLIANCE_EXPORT_PROFILE=compliance_evidence` or `audit_metadata`.
- `DEFAULT_AUDIT_EXPORT_PROFILE=audit_metadata`.
- `PHI_REDACTION_ENABLED=true`.
- `ALLOW_GENERIC_FOUNDATION_COMMIT=false`.
- `GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY=true`.
- `AUTHENTICATION_ENABLED=true`.
- `MFA_DEV_BYPASS_CODE` must not be the predictable local demo default.

## Fail-Closed Conditions

Startup fails in production when any of these are detected:

- missing or placeholder `SECRET_KEY`;
- missing or placeholder `ENCRYPTION_KEY`;
- insecure cookies or unsafe SameSite policy;
- wildcard, localhost, loopback, or local-only production CORS origins;
- `DEBUG=true`;
- reload/dev server mode enabled;
- missing `DATABASE_URL`;
- SQLite, non-PostgreSQL, localhost, or loopback database URL;
- JSON-only or disabled workflow audit storage;
- DB-backed workflow audit not required;
- required object/WORM audit mirror disabled;
- required object/WORM provider, container, or prefix missing;
- required local filesystem mirror without `AUDIT_OBJECT_MIRROR_ALLOW_LOCAL_PRODUCTION_SIMULATION=true`;
- required manifest policy without retention policy reference;
- legal hold required without legal hold reference;
- signature required without manifest required;
- signed manifests required without signature algorithm or key reference;
- required manifest signing disabled or set to `checksum_placeholder`;
- local HMAC manifest signing in production without explicit allowance;
- external/KMS or Azure Key Vault manifest signing without key reference;
- Azure Key Vault placeholder signing without vault URL or key name;
- missing or unsafe manifest signing algorithm;
- required Azure Blob mirror without account URL, container, prefix, or safe credential mode;
- required Azure Blob real I/O enabled without `azure-storage-blob`;
- required Azure Blob real I/O enabled with identity credential mode but without `azure-identity`;
- required Azure Blob immutability without retention policy reference;
- required Azure Blob legal hold without legal hold reference;
- required Azure Blob checksum validation without safe credential mode;
- unsafe default analytics, compliance, or audit export profile;
- PHI/ePHI redaction disabled;
- generic foundation commit broadly enabled or not admin-only;
- authentication disabled;
- demo/test auth bypass enabled;
- demo user mode enabled;
- predictable local MFA bypass code.

## Preflight And Startup Checks

Local preflight now includes a warning inventory:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
```

When run with local/dev settings, this command reports the number of production-hardening warnings but does not fail because production secrets are intentionally absent.

For App Service startup checks:

```powershell
.\.venv\Scripts\python.exe scripts\start_app_service.py --check
```

In production-like environments, both startup paths refuse unsafe settings before the app opens traffic.

The production gate remains local-only. It does not run live Azure pytest checks, upload objects, call Azure APIs, or call a signing provider. Use `scripts/check_azure_worm_readiness.py --json --evidence-out <approved-evidence-path>\azure-worm-validation-evidence.json` for sanitized dry-run Azure WORM readiness evidence and `docs/clinical-azure-worm-live-validation.md` for the opt-in live process.

## Failure Example

If `APP_ENV=prod` and `SECRET_KEY=change-me-for-production-demo-only`, startup fails with:

```text
Production security gate failed. Refusing to start with unsafe production configuration.
- secret_key_unsafe: SECRET_KEY must be a generated non-placeholder value of at least 32 characters.
```

## Known Limitations

- The gate validates configuration shape and known flags; it does not prove database migrations have already run.
- It does not contact PostgreSQL, object storage, Entra ID, or a secret manager.
- MFA provider integration remains future work; the gate only blocks predictable local bypass values and unsafe auth bypass flags.
- Object-storage/WORM audit mirroring has a local/provider-placeholder foundation, Azure Blob readiness checks, guarded Azure SDK operation paths, skipped-by-default live harnesses, sanitized evidence artifacts, deterministic local HMAC manifest signing, provider-placeholder signing metadata, and recovery drill helpers; Azure resource provisioning, retention policy creation, legal hold automation, and real cloud KMS/Key Vault signing remain planned.
- Small-cell suppression and lightweight role-aware UI masking are implemented; centralized field policy remains future work.
