# Clinical Production Security Gates

Post-RC-03 update date: 2026-06-13

Post-RC-06 WORM mirror gate update date: 2026-06-13

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
- Object-storage/WORM audit mirroring has a local/provider-placeholder foundation; real provider SDK integration, retention policy creation, and legal hold automation remain planned.
- Small-cell suppression and lightweight role-aware UI masking are implemented; centralized field policy remains future work.
