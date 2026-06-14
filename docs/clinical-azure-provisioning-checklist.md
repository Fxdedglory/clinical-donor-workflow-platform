# Clinical Azure Provisioning Checklist

Task: `CLINICAL-DEPLOY-02`

Baseline package commit: `48d804b Add clinical deployment packaging dry run`

Target URL: `https://clinical.teemails.com`

Preferred hosting option: single Azure App Service-style app serving FastAPI plus the built React frontend from `frontend/dist`.

This checklist is for external environment provisioning. DEPLOY-02 does not create resources, deploy code, create DNS records, use real secrets, add Docker, or add Kubernetes.

## Provisioning Rules

- No Docker or Kubernetes for the first clinical deployment package.
- Use placeholder names until Product Owner, Security/Compliance, and Operations approve final resource names.
- Store secrets in approved app settings or secret store, never in Git.
- Production `DATABASE_URL` must target PostgreSQL. SQLite is blocked by production gates.
- WORM storage and Key Vault signing remain future/live-validation dependencies unless explicitly approved for first launch.
- Record actual resource ids and evidence outside the repository.

## Resource Checklist

| Status | Resource | Purpose | Required setting | Recommended placeholder | Security note | Owner / action |
| --- | --- | --- | --- | --- | --- | --- |
| [ ] | Resource group | Deployment boundary for clinical web app resources. | Region, tags, owner, cost center. | `rg-clinical-prod-<region>` | Restrict contributor access to approved deployment operators. | Operations: create or identify approved group. |
| [ ] | App Service Plan | Hosts the Python web app. | Linux/Python-capable plan, production SKU, scaling policy. | `asp-clinical-prod-<region>` | Use production SKU with TLS and monitoring support; no Docker required. | Operations: size plan and document scaling owner. |
| [ ] | Web App / App Service | Runs FastAPI and serves built React assets. | Python 3.12 runtime or approved equivalent, startup command, `$PORT`, HTTPS only. | `app-clinical-prod` | Enable managed identity if database, storage, or Key Vault integration requires it. | Operations: provision shell; release operator deploys package after approval. |
| [ ] | PostgreSQL Flexible Server or approved managed PostgreSQL | Production clinical application database. | PostgreSQL 16-compatible target, TLS required, backup policy, access policy. | `psql-clinical-prod-<region>` / `clinical_donor_workflow` | No SQLite, local database, or public broad firewall access. | DBA/Ops: provision and provide secret-store connection material. |
| [ ] | Application Insights or monitoring equivalent | Runtime telemetry, failures, latency, availability, and health checks. | Instrumentation/connection setting, retention policy, alert routing. | `appi-clinical-prod` | Avoid PHI/ePHI in logs; configure sampling and access controls. | Operations/Security: approve telemetry scope and alert recipients. |
| [ ] | Key Vault or approved secret store | Stores app secrets and optional manifest signing key references. | RBAC/access policy, soft delete, purge protection, managed identity access. | `kv-clinical-prod` | Store generated secrets only; do not store secrets in docs or Git. | Security/Ops: approve access and rotation owner. |
| [ ] | DNS/custom domain configuration | Routes `clinical.teemails.com` to the Web App. | CNAME or A/TXT validation records per App Service instructions. | `clinical.teemails.com` | Coordinate with site-wide team; do not create records before cutover approval. | DNS owner: validate and apply approved records. |
| [ ] | TLS certificate configuration | Provides HTTPS for the custom domain. | App Service managed certificate or approved certificate binding. | App Service managed certificate for `clinical.teemails.com` | Enforce HTTPS only; verify cookie secure behavior after binding. | Operations/Security: bind cert and record expiration owner. |
| [ ] | Azure Blob WORM storage, if approved | Future immutable audit object mirror and live validation target. | Immutable container, retention, legal hold, checksum validation policy. | `stclinicalauditprod` / `clinical-audit-worm` | Not required for first app launch unless Compliance approves; use managed identity only. | Security/Compliance/Ops: provision only after live-validation approval. |
| [ ] | Azure Key Vault signing key, if approved | Future audit manifest signing validation target. | RSA key, approved algorithm, logging, lifecycle/rotation policy. | `clinical-audit-manifest-key` | No live signing tests until approved; key material never leaves Key Vault. | Security/Compliance: approve key policy and access logs. |

## Required App Service Runtime Shape

- Startup command: `python scripts/start_app_service.py`
- Startup check: `python scripts/start_app_service.py --check`
- Frontend build artifact: `frontend/dist`
- Static serving: `SERVE_FRONTEND=true`
- API health: `/api/health`
- Monitoring health: `/api/monitoring/health`
- SPA route smoke: `/clinical/dashboard`

## Evidence To Capture Outside Git

- Resource names and ids.
- App Service runtime version and startup command screenshot/export.
- Database server, database name, TLS mode, backup policy, and access mode.
- DNS validation and custom domain binding evidence.
- TLS certificate binding and expiration owner.
- Monitoring alert routing and dashboard links.
- Secret storage owner and rotation policy.
