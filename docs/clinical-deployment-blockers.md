# Clinical Deployment Blockers

Task: `CLINICAL-DEPLOY-00`

Release baseline: `f7d186f Finalize clinical frontend QA polish`

This list separates repository blockers from environment, approval, and optional hardening items. It is a deployment planning artifact only.

## Summary

The repository is ready for deployment packaging and environment provisioning planning. The remaining blockers are mostly environment and approval items, not missing Clinical workflow implementation.

## Repo Blockers

| Blocker | Status | Required action |
| --- | --- | --- |
| Path-based hosting under `teemails.com/clinical` not fully proven | Open only if path routing is selected | Prefer `clinical.teemails.com` for first release, or run a dedicated path-prefix test pass before cutover. |
| Production secrets absent from repo | Expected and correct | Configure secrets in the hosting platform or approved secret store only. |
| Production DB migration not run against target DB | Open until environment exists | Run `python -m alembic upgrade head` after target PostgreSQL is provisioned and backed up. |
| Full production evidence bundle must be regenerated for final deployment commit | Open until packaging sprint | Run `scripts/build_clinical_production_evidence_bundle.py` after final deployment packaging. |
| `backend/app/cli.py` has pre-existing local dirty changes | Not a deployment blocker if kept out of release scope | Preserve or resolve separately by Product Owner direction; do not include in deployment planning commit. |

## Environment Blockers

| Blocker | Status | Required action |
| --- | --- | --- |
| Production PostgreSQL database not provisioned | Open | Provision approved PostgreSQL 16-compatible managed database. |
| Production `DATABASE_URL` not configured | Open | Store TLS-enabled PostgreSQL URL in hosted app settings or secret store. |
| `SECRET_KEY` not configured | Open | Generate a strong unique value outside Git. |
| `ENCRYPTION_KEY` not configured | Open | Generate a strong unique value outside Git so sensitive-field encryption does not fall back to `SECRET_KEY`. |
| `COOKIE_SECURE=true` not configured for hosted HTTPS | Open | Set in production app settings. |
| Production `CORS_ORIGINS` not finalized | Open | Use only approved production origins; no wildcard, localhost, or loopback. |
| Public URL and DNS routing not selected | Open | Decide between `clinical.teemails.com` and path routing. |
| Hosting target not selected | Open | Choose single App Service-style host or split frontend/backend host. |
| Monitoring target not configured | Open | Decide App Service logs only vs Application Insights or equivalent. |
| Email provider not configured | Open if notification delivery is in production scope | Configure SMTP, SendGrid, SES, or Mailgun outside Git. |

## External Approval Blockers

| Blocker | Status | Required approval |
| --- | --- | --- |
| Product Owner go-live approval | Pending | Product Owner signs `docs/clinical-production-go-live-signoff.md`. |
| Security/Compliance approval | Pending | Security/Compliance accepts production gate settings, PHI/export policy, and WORM/Key Vault posture. |
| Operations deployment window and rollback owner | Pending | Operations signs deployment window, rollback owner, and smoke test plan. |
| Live Azure WORM validation | Pending | Requires approved storage account/container, identity, retention/legal hold, logging, and validation window. |
| Live Azure Key Vault signing validation | Pending | Requires approved vault/key/version, identity, logging, lifecycle references, and validation window. |
| DNS ownership approval | Pending | Domain owner approves `clinical.teemails.com` or path routing. |
| Data retention and backup approval | Pending | Database backup, evidence retention, WORM policy, and rollback plan accepted. |

## Optional Future Hardening

| Item | Why it matters | Timing |
| --- | --- | --- |
| Entra-backed SSO/MFA | Replaces platform-native internal auth with enterprise identity. | Future security sprint. |
| Application Insights or equivalent APM | Better request/error visibility after launch. | Deployment packaging or operations sprint. |
| Azure Blob WORM real I/O | Moves audit mirror from readiness foundation to approved cloud object storage. | After compliance approval. |
| Azure Key Vault real signing | Moves manifest signing from readiness foundation to approved cloud KMS. | After compliance approval. |
| Automated backup/restore drill | Proves operational recovery. | Before production with real data. |
| CI vulnerability scan lane | Adds dependency/security visibility. | Future CI hardening. |
| Full path-prefix certification | Needed only if `teemails.com/clinical` is selected. | Before path-based cutover. |
| Unified teemails app launcher | Improves site-wide navigation across Clinical, HR, ERP, and Analytics. | SITE-WIDE planning sprint. |

## Not Blockers

- Docker is not required and should not be introduced for this target.
- Kubernetes is not required and should not be introduced for this target.
- Live Azure tests are not required for this inventory sprint.
- Real Azure credentials are not required for this inventory sprint.
- Clinical backend workflow logic is complete for the deployment planning baseline.
