# Clinical Production Environment Template

Task: `CLINICAL-DEPLOY-01`

Release baseline: `8e41b07 Add clinical deployment integration inventory`

Purpose: placeholder-only production configuration for the preferred single-host deployment where FastAPI serves the built React frontend from `frontend/dist`. This file is documentation only. Do not paste local `.env` values, demo secrets, account keys, connection strings, or real credentials into Git.

## Environment Template

```dotenv
# Environment identity
APP_ENV=prod
ENVIRONMENT=prod
CLINICAL_ENV=prod
APP_BASE_URL=https://clinical.teemails.com
PORT=<platform-assigned-port>
STARTUP_MODE=fastapi_react
DEBUG=false

# Single-host frontend serving
SERVE_FRONTEND=true
FRONTEND_DIST_DIR=frontend/dist
VITE_API_BASE_URL=

# Database: production must use TLS-enabled PostgreSQL.
# SQLite, local file databases, localhost, and loopback hosts are blocked by production gates.
DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@<postgres_host>:5432/clinical_donor_workflow?sslmode=require

# Application secrets: generate outside Git and store in approved app settings or secret store.
SECRET_KEY=<generated-secret-at-least-32-chars>
ENCRYPTION_KEY=<generated-encryption-key-at-least-32-chars>
BACKUP_ENCRYPTION_KEY=<generated-backup-encryption-key-when-backups-enabled>
MFA_DEV_BYPASS_CODE=<non-demo-non-predictable-mfa-code-or-provider-disabled>

# Cookies and sessions
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Same-origin deployment still allows explicit production origins for browser/API checks.
CORS_ORIGINS=["https://clinical.teemails.com","https://teemails.com","https://www.teemails.com"]

# Authentication and workflow commit safety
AUTHENTICATION_ENABLED=true
AUTH_DISABLED=false
ALLOW_DEMO_AUTH_BYPASS=false
TEST_AUTH_BYPASS_ENABLED=false
DEMO_USERS_ENABLED=false
ALLOW_GENERIC_FOUNDATION_COMMIT=false
GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY=true

# PHI/ePHI and export safety
PHI_REDACTION_ENABLED=true
PHI_REDACTION_DISABLED=false
DEFAULT_ANALYTICS_EXPORT_PROFILE=aggregate_safe
DEFAULT_COMPLIANCE_EXPORT_PROFILE=compliance_evidence
DEFAULT_AUDIT_EXPORT_PROFILE=audit_metadata

# Workflow audit durability
WORKFLOW_AUDIT_STORAGE=db_with_json_mirror
WORKFLOW_AUDIT_DB_REQUIRED=true
WORKFLOW_AUDIT_PATH=metadata/workflow_operations.json

# WORM/object mirror readiness.
# Keep real I/O disabled until Product Owner, Security/Compliance, and Operations approve live validation.
AUDIT_OBJECT_MIRROR_REQUIRED=false
AUDIT_OBJECT_MIRROR_MODE=disabled
AUDIT_OBJECT_MIRROR_PROVIDER=
AUDIT_OBJECT_MIRROR_CONTAINER=
AUDIT_OBJECT_MIRROR_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_RETENTION_POLICY=
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED=false
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE=
AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=false

# Azure Blob WORM placeholders. Use managed identity or approved workload identity when enabled.
AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL=https://<storage-account>.blob.core.windows.net
AUDIT_OBJECT_MIRROR_AZURE_CONTAINER=<worm-container>
AUDIT_OBJECT_MIRROR_AZURE_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE=managed_identity
AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=false
AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED=false
AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED=false
AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED=false

# Manifest signing / Azure Key Vault placeholders.
AUDIT_MANIFEST_SIGNING_REQUIRED=false
AUDIT_MANIFEST_SIGNING_MODE=disabled
AUDIT_MANIFEST_SIGNING_ALGORITHM=rsa-pss-sha256
AUDIT_MANIFEST_SIGNING_KEY_REF=keyvault://<vault-name>/keys/<key-name>
AUDIT_MANIFEST_AZURE_KEY_VAULT_URL=https://<vault-name>.vault.azure.net/
AUDIT_MANIFEST_AZURE_KEY_NAME=<manifest-signing-key>
AUDIT_MANIFEST_AZURE_KEY_VERSION=
AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE=managed_identity
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_REQUIRE_HSM=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS=0
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME=
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION=
AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF=
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF=
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF=

# Live validation flags: keep false until the approved live validation window.
AZURE_WORM_ENABLE_LIVE_IO=false
AZURE_KEY_VAULT_SIGNING_ENABLE_LIVE_IO=false

# Notification provider placeholders
EMAIL_PROVIDER=disabled
EMAIL_FROM=no-reply@clinical.teemails.com
EMAIL_FROM_NAME=Clinical Platform
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=<configured-outside-git-if-smtp-enabled>
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SENDGRID_API_KEY=<configured-outside-git-if-sendgrid-enabled>
MAILGUN_API_KEY=<configured-outside-git-if-mailgun-enabled>
MAILGUN_DOMAIN=

# Data producer and lake exports remain disabled unless approved for the target environment.
ENABLE_DATA_PRODUCER_API=false
DATA_PRODUCER_METADATA_ROOT=data/generated
DATA_PRODUCER_EXPORT_ROOT=data/exports
DATA_LAKE_ACCOUNT_NAME=
DATA_LAKE_CONTAINER=
DATA_LAKE_AUTH_MODE=managed_identity
DATA_LAKE_BASE_PATH=clinical

# Demo/local-only controls
CLINICAL_DEMO_SEED_ENABLED=false
ENABLE_DEMO_USERS=false
```

## Production Gate Requirements

- `DATABASE_URL` must be PostgreSQL with a non-local host and TLS; SQLite and local file databases are blocked.
- `SECRET_KEY`, `ENCRYPTION_KEY`, backup keys, MFA bypass material, email provider keys, and database credentials must be generated and stored outside Git.
- `COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax` or `strict`, no wildcard CORS, no localhost or loopback CORS origins.
- `AUTHENTICATION_ENABLED=true`; demo/test bypass flags must remain false.
- `WORKFLOW_AUDIT_STORAGE=db_with_json_mirror` and `WORKFLOW_AUDIT_DB_REQUIRED=true`; JSON-only audit storage is not production safe.
- `PHI_REDACTION_ENABLED=true`; export defaults must remain `aggregate_safe`, `compliance_evidence`, and `audit_metadata`.
- WORM and Key Vault real I/O flags remain false until live provider validation is approved; when enabled, use managed identity/workload identity, not inline secrets.
- `SERVE_FRONTEND=true` and `FRONTEND_DIST_DIR=frontend/dist` are required for the preferred single App Service-style deployment.

## Values Explicitly Not Allowed

- Local `.env` values, demo credentials, generated screenshots/evidence paths, SQLite paths, localhost database URLs, wildcard CORS origins, inline Azure account keys, inline connection strings, or real provider credentials.
- Demo seed execution in production. `scripts/seed_clinical_demo_data.py` is local/non-prod only.
