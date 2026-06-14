# Clinical Deployment Environment Variables

Task: `CLINICAL-DEPLOY-00`

Release baseline: `f7d186f Finalize clinical frontend QA polish`

Do not store real secret values in Git. Examples below are placeholders or local-only shapes.

## Runtime and Hosting

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `APP_ENV` | Yes | `dev` | `prod`, `production`, `stage`, or `staging` for production-like gate behavior | No | Production-like detector | `ENVIRONMENT` and `CLINICAL_ENV` are also recognized by the gate as environment indicators. |
| `ENVIRONMENT` | Optional | `dev` | Align with `APP_ENV` if set | No | Production-like detector | Useful when hosting platform standardizes on `ENVIRONMENT`. |
| `CLINICAL_ENV` | Optional | `dev` | Align with `APP_ENV` if set | No | Production-like detector | Clinical-specific override if needed. |
| `DEBUG` | Optional | `false` | `false` | No | Fails if true in production | Do not use reload/dev-server mode in production. |
| `PORT` | Yes | `8000` | Injected by App Service or managed host | No | Startup behavior | `scripts/start_app_service.py` reads this value. |
| `STARTUP_MODE` | Yes | `fastapi_react` | `fastapi_react` | No | Blocks dev/reload values | Current no-Docker target. |
| `SERVE_FRONTEND` | Yes for single-host | `true` | `true` for FastAPI serving built React; `false` only for split hosting | No | Empty CORS fails when false | `backend/app/main.py` serves `frontend/dist` when true. |
| `FRONTEND_DIST_DIR` | Yes for single-host | `frontend/dist` | Built React dist directory | No | Startup check reports value | Must exist after `npm run build`. |
| `APP_BASE_URL` | Yes | `http://localhost:8000` | `https://clinical.teemails.com` or approved path URL | No | Indirect | Used by app links and email flows. |

## Database and Migrations

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | Yes | `postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow` | TLS-enabled PostgreSQL URL with production credentials | Yes | Required; blocks SQLite, non-PostgreSQL, localhost, loopback, and missing host in production | PostgreSQL is required. SQLite is disallowed in production. |

Migration command:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Head check:

```powershell
.\.venv\Scripts\python.exe -m alembic heads
```

## Auth, JWT, Cookie, and Session

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `SECRET_KEY` | Yes | `change-me-for-production-demo-only` | Strong generated value of at least 32 chars outside Git | Yes | Required; placeholder blocks production startup | Signs JWT/session material. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `30` | Approved access token lifetime | No | No direct gate | Default is 30. |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Optional | `20160` | Approved refresh lifetime | No | No direct gate | Default is 14 days. |
| `JWT_ALGORITHM` | Optional | `HS256` | Approved algorithm if exposed as environment | No | No direct gate | Config field exists without explicit env alias; keep default unless reviewed. |
| `COOKIE_SECURE` | Yes | `false` | `true` behind HTTPS | No | Required true in production | Blocks insecure hosted cookie settings. |
| `COOKIE_SAMESITE` | Yes | `lax` | `lax` or `strict` unless reviewed | No | Blocks unsafe SameSite | Review if cross-site auth redirects are introduced. |
| `SESSION_TIMEOUT_MINUTES` | Optional | `30` | Approved session timeout | No | No direct gate | Current default is 30. |
| `MAX_FAILED_LOGIN_ATTEMPTS` | Optional | `5` | Approved lockout threshold | No | No direct gate | Existing auth lockout setting. |
| `ACCOUNT_LOCKOUT_MINUTES` | Optional | `15` | Approved lockout duration | No | No direct gate | Existing auth lockout setting. |
| `PASSWORD_MIN_LENGTH` | Optional | `12` | Approved password policy | No | No direct gate | Existing password policy setting. |
| `PASSWORD_EXPIRATION_DAYS` | Optional | `180` | Approved password expiration policy | No | No direct gate | Existing password policy setting. |
| `MFA_DEV_BYPASS_CODE` | Yes until MFA provider changes | `000000` | Strong non-predictable value or replaced by approved MFA provider flow | Yes | Predictable value blocks production | Do not use the local demo default. |
| `AUTHENTICATION_ENABLED` | Yes | `true` | `true` | No | Must remain true in production | Disabling auth blocks production startup. |
| `ALLOW_DEMO_AUTH_BYPASS` | Yes | `false` | `false` | No | Must remain false in production | Demo/test bypass is blocked. |

## CORS and Frontend API Base

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `CORS_ORIGINS` | Yes | `["http://127.0.0.1:5173","http://localhost:5173"]` | Exact approved origins only, for example `https://clinical.teemails.com` and approved teemails origins | No | Blocks wildcard, localhost, loopback, and empty split-host CORS in production | JSON array or comma-separated values are accepted. |
| `VITE_API_BASE_URL` | Required only for split hosting or local Vite | `http://127.0.0.1:8012` | Backend API origin when frontend is separately hosted | No | Frontend build-time setting | Not needed for single-host FastAPI serving React and API same-origin. |

## PHI, Export Profiles, and Clinical Commit Controls

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `DEFAULT_ANALYTICS_EXPORT_PROFILE` | Yes | `aggregate_safe` | `aggregate_safe` or approved safe profile | No | Unsafe value blocks production | Preserves small-cell suppression and safe report defaults. |
| `DEFAULT_COMPLIANCE_EXPORT_PROFILE` | Yes | `compliance_evidence` | `compliance_evidence` or `audit_metadata` | No | Unsafe value blocks production | Compliance exports require approved profile. |
| `DEFAULT_AUDIT_EXPORT_PROFILE` | Yes | `audit_metadata` | `audit_metadata`, `aggregate_safe`, or `external_safe` as approved | No | Unsafe value blocks production | Audit evidence defaults. |
| `PHI_REDACTION_ENABLED` | Yes | `true` | `true` | No | Must remain true | Production startup blocks if disabled. |
| `ALLOW_GENERIC_FOUNDATION_COMMIT` | Yes | `false` | `false` | No | Must remain false | Generic foundation commits must not be broadly enabled. |
| `GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY` | Yes | `true` | `true` | No | Must remain true | Generic foundation commit remains admin-only. |

## Workflow Audit Durability

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `WORKFLOW_AUDIT_STORAGE` | Yes | `db_with_json_mirror` | `db_with_json_mirror` | No | JSON-only blocks production | DB-backed audit is production source of truth. |
| `WORKFLOW_AUDIT_DB_REQUIRED` | Yes | `true` | `true` | No | Must remain true | Production must not silently fall back to JSON-only audit. |
| `AUDIT_OBJECT_MIRROR_MODE` | Conditional | `disabled` | `disabled` until WORM object mirror is approved; otherwise approved object-storage mode | No | Required if mirror is required | Do not enable object mirroring without provider approval. |
| `AUDIT_OBJECT_MIRROR_REQUIRED` | Conditional | `false` | `false` until compliance requires WORM mirror | No | If true, mirror config must be complete | Keep false until external approvals exist. |
| `AUDIT_OBJECT_MIRROR_LOCAL_ROOT` | Optional | `metadata/audit_worm_mirror` | Not a production WORM target unless explicitly simulation-only | No | Local mirror cannot satisfy production WORM unless allowed | Local/generated metadata remains ignored. |
| `AUDIT_OBJECT_MIRROR_URI_PREFIX` | Optional | `local-worm://clinical-audit` | Approved provider URI prefix | No | Provider consistency | Used in mirror metadata. |
| `AUDIT_OBJECT_MIRROR_PROVIDER` | Conditional | blank | `azure_blob` or approved provider when required | No | Required when WORM mirror required | Provider placeholder is not production evidence by itself. |
| `AUDIT_OBJECT_MIRROR_CONTAINER` | Conditional | blank | Approved immutable container when required | No | Required when mirror required | Use Azure-specific var if Azure provider is selected. |
| `AUDIT_OBJECT_MIRROR_PREFIX` | Conditional | `workflow-audit` | Approved object prefix | No | Required when mirror required | Keep per-environment prefix isolated. |
| `AUDIT_OBJECT_MIRROR_RETENTION_POLICY` | Conditional | blank | Approved retention reference when manifests/immutability are required | No | Required for manifest/legal-hold policy | Do not invent retention values. |
| `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, reference required | Requires external evidence. |
| `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE` | Conditional | blank | Approved legal hold evidence reference | No | Required when legal hold true | Store reference, not secret. |
| `AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED` | Conditional | `false` | `true` only after manifest policy approval | No | Drives signing requirements | Must align with signing policy. |
| `AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED` | Conditional | `false` | `true` only after signature policy approval | No | Requires algorithm/key ref | Legacy manifest signature controls remain supported. |
| `AUDIT_OBJECT_MIRROR_SIGNATURE_ALGORITHM` | Conditional | `sha256-placeholder` | Approved non-deprecated algorithm when required | No | Placeholder blocks required production signing | Prefer newer `AUDIT_MANIFEST_*` controls. |
| `AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF` | Conditional | blank | Approved key reference when required | No | Required when signature required | No key material in Git. |

## Azure Blob WORM Mirror Settings

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL` | Conditional | blank | Approved Azure Storage account URL | No | Required for Azure mirror when required | No network calls in this planning sprint. |
| `AUDIT_OBJECT_MIRROR_AZURE_CONTAINER` | Conditional | blank | Approved immutable container | No | Required for Azure mirror when required | Container creation is out of scope here. |
| `AUDIT_OBJECT_MIRROR_AZURE_PREFIX` | Conditional | blank | Approved prefix | No | Required for Azure mirror when required | Use isolated validation prefix for live tests. |
| `AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE` | Conditional | blank | `managed_identity`, `workload_identity`, or approved non-secret mode | No | Unsafe modes block production | Inline account keys/connection strings are not allowed. |
| `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO` | Conditional | `false` | `true` only after Azure Blob live validation approval | No | Requires SDK dependencies and safe identity | Keep false for dry-run readiness. |
| `AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, retention reference required | Requires provider-side evidence. |
| `AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, legal hold reference required | Requires provider-side evidence. |
| `AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED` | Conditional | `false` | Approved compliance value | No | Requires safe credential mode | Used for provider verification. |
| `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS` | Optional live validation flag | unset | `true` only during approved live validation window | No | Operational control, not startup bypass | Do not enable in normal validation. |
| `AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX` | Optional live validation flag | blank | Dedicated non-production prefix | No | Operational control | Keep separate from production evidence prefix. |

## Manifest Signing and Key Vault

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `AUDIT_MANIFEST_SIGNING_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, mode/algorithm/key ref required | Keep false until signing policy approved. |
| `AUDIT_MANIFEST_SIGNING_MODE` | Conditional | blank | Approved mode such as `azure_key_vault` | No | Required if signing required | Placeholder modes cannot satisfy production. |
| `AUDIT_MANIFEST_SIGNING_ALGORITHM` | Conditional | blank | Approved non-deprecated algorithm such as RSA-PSS-SHA256 | No | Required if signing required | Must match provider. |
| `AUDIT_MANIFEST_SIGNING_KEY_REF` | Conditional | blank | Approved key reference | No | Required if external/KMS signing configured | No key material. |
| `AUDIT_MANIFEST_LOCAL_HMAC_KEY` | Conditional | blank | Avoid in production unless explicitly approved | Yes | Required if local HMAC mode enabled | Store outside Git only. |
| `AUDIT_MANIFEST_ALLOW_LOCAL_SIGNING_IN_PRODUCTION` | Conditional | `false` | `false` unless explicitly approved | No | Local signing blocks production unless allowed | Prefer Key Vault for production. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_URL` | Conditional | blank | Approved Key Vault URL | No | Required for Azure Key Vault signing | No live calls in this sprint. |
| `AUDIT_MANIFEST_AZURE_KEY_NAME` | Conditional | blank | Approved key name | No | Required for Azure Key Vault signing | Use dedicated key. |
| `AUDIT_MANIFEST_AZURE_KEY_VERSION` | Conditional | blank | Approved key version | No | Lifecycle evidence | Required when policy mandates pinned key. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE` | Conditional | blank | `managed_identity`, `workload_identity`, or approved non-secret mode | No | Unsafe modes block production | No client secrets in app settings. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO` | Conditional | `false` | `true` only after live validation approval | No | Requires SDK dependencies and safe identity | Keep false for dry-run readiness. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_REQUIRE_HSM` | Conditional | `false` | Approved compliance value | No | Lifecycle readiness | Requires Key Vault SKU/policy decision. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, interval and next key metadata required | Requires lifecycle owner. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS` | Conditional | `0` | Positive approved rotation interval when required | No | Required when rotation required | No default for production policy. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME` | Conditional | blank | Approved next key name when rotation required | No | Required when rotation required | No key material. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION` | Conditional | blank | Approved next key version when rotation required | No | Required when rotation required | No key material. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, reference required | Requires evidence reference. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF` | Conditional | blank | Approved retirement policy reference | No | Required when retirement policy required | Reference only. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, reference required | Requires operations evidence. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF` | Conditional | blank | Approved access-log review reference | No | Required when access-log review required | Reference only. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED` | Conditional | `false` | Approved compliance value | No | If true, reference required | Requires tabletop or recovery evidence. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF` | Conditional | blank | Approved incident recovery reference | No | Required when incident recovery required | Reference only. |
| `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS` | Optional live validation flag | unset | `true` only during approved live validation window | No | Operational control, not startup bypass | Do not enable in normal validation. |
| `AUDIT_MANIFEST_AZURE_KEY_VAULT_LIVE_ALLOW_PRODUCTION_KEY` | Optional live validation flag | unset | `true` only with explicit approval | No | Operational control | Avoid production keys for validation unless approved. |

## Email and Notification Delivery

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `EMAIL_PROVIDER` | Optional | `console` | Approved provider if outbound delivery is enabled | No | No direct gate | Keep `console` for non-delivery environments. |
| `EMAIL_FROM` | Optional | `no-reply@teemails.com` | Approved sender | No | No direct gate | Domain alignment needed before delivery. |
| `EMAIL_FROM_NAME` | Optional | `Clinical Donor Workflow` | Approved display name | No | No direct gate |  |
| `SENDGRID_API_KEY` | Conditional | blank | Provider secret in secret store | Yes | Preflight scans for accidental tracked secrets | Do not commit. |
| `SES_REGION` | Conditional | blank | Approved AWS SES region if selected | No | No direct gate |  |
| `MAILGUN_API_KEY` | Conditional | blank | Provider secret in secret store | Yes | Preflight scans for accidental tracked secrets | Do not commit. |
| `MAILGUN_DOMAIN` | Conditional | blank | Approved Mailgun domain if selected | No | No direct gate |  |
| `SMTP_HOST` | Conditional | blank | Approved SMTP host if selected | No | No direct gate |  |
| `SMTP_PORT` | Conditional | `587` | Approved SMTP port | No | No direct gate |  |
| `SMTP_USERNAME` | Conditional | blank | Provider username in secret store | Yes | No direct gate | Do not commit. |
| `SMTP_PASSWORD` | Conditional | blank | Provider password in secret store | Yes | No direct gate | Do not commit. |
| `SMTP_USE_TLS` | Conditional | `true` | Approved value | No | No direct gate |  |
| `SMTP_USE_SSL` | Conditional | `false` | Approved value | No | No direct gate |  |

## Data Producer, ADLS, and Scheduled Export Settings

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ENABLE_DATA_PRODUCER_API` | Optional | `true` | Disable if admin producer controls are not approved | No | No direct gate | Review before production. |
| `DATA_PRODUCER_METADATA_ROOT` | Optional | `data/generated` | Approved writable location | No | Preflight ensures generated paths ignored | Local generated metadata is ignored by Git. |
| `DATA_PRODUCER_EXPORT_ROOT` | Optional | `data/exports` | Approved writable/export location | No | Preflight ensures generated paths ignored | Local generated exports are ignored by Git. |
| `DATA_PRODUCER_STOP_FILE` | Optional | `data/generated/STOP_CONTINUOUS` | Approved writable stop-file path | No | No direct gate |  |
| `DATA_PRODUCER_MIN_INTERVAL_SECONDS` | Optional | `1` | Raised for hosted environments if continuous producer is enabled | No | No direct gate |  |
| `DATA_PRODUCER_MAX_CYCLES` | Optional | `1000` | Approved guardrail | No | No direct gate |  |
| `DATA_PRODUCER_ALLOW_INFINITE` | Optional | `false` | `false` unless explicitly approved | No | No direct gate |  |
| `DATA_LAKE_ACCOUNT_NAME` | Conditional | blank | Required for ADLS scheduled jobs/uploads | No | Runtime validation | No live ADLS calls in deployment inventory. |
| `DATA_LAKE_CONTAINER` | Conditional | `datalake` | Approved container | No | Runtime validation |  |
| `DATA_LAKE_AUTH_MODE` | Conditional | `managed_identity` | `managed_identity` | No | Runtime validation rejects other modes | Storage keys intentionally unsupported. |
| `DATA_LAKE_BASE_PATH` | Conditional | `bronze` | Approved path | No | Runtime validation |  |
| `DATA_LAKE_LOCAL_ROOT` | Optional | blank | Local fallback only | No | No direct gate | Not a production storage target. |

## Backup and Document Links

| Variable | Required | Local example | Production expectation | Sensitive | Gate relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `BACKUP_ENCRYPTION_KEY` | Required before hosted backup automation | blank | Strong generated value outside Git | Yes | No direct gate today | Listed in readiness runbook as required before automated backups. |
| `DOCUMENT_SIGNED_URL_MINUTES` | Optional | `10` | Approved signed URL lifetime | No | No direct gate | Used by secure document access flow. |

## Minimal Single-App Production Shape

For the recommended first release on `clinical.teemails.com`:

```text
APP_ENV=prod
APP_BASE_URL=https://clinical.teemails.com
STARTUP_MODE=fastapi_react
SERVE_FRONTEND=true
FRONTEND_DIST_DIR=frontend/dist
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
CORS_ORIGINS=https://clinical.teemails.com,https://teemails.com,https://www.teemails.com
WORKFLOW_AUDIT_STORAGE=db_with_json_mirror
WORKFLOW_AUDIT_DB_REQUIRED=true
DEFAULT_ANALYTICS_EXPORT_PROFILE=aggregate_safe
DEFAULT_COMPLIANCE_EXPORT_PROFILE=compliance_evidence
DEFAULT_AUDIT_EXPORT_PROFILE=audit_metadata
PHI_REDACTION_ENABLED=true
ALLOW_GENERIC_FOUNDATION_COMMIT=false
GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY=true
AUTHENTICATION_ENABLED=true
```

Secrets required outside Git:

```text
DATABASE_URL=<TLS PostgreSQL URL>
SECRET_KEY=<generated secret>
ENCRYPTION_KEY=<generated secret>
MFA_DEV_BYPASS_CODE=<non-predictable approved value or replaced MFA mechanism>
```
