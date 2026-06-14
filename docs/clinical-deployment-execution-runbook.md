# Clinical Deployment Execution Runbook

Task: `CLINICAL-DEPLOY-02`

Baseline package commit: `48d804b Add clinical deployment packaging dry run`

Target URL: `https://clinical.teemails.com`

Preferred hosting: single Azure App Service-style app serving FastAPI plus the built React frontend from `frontend/dist`.

This runbook is human-executable after Product Owner, Security/Compliance, and Operations approval. DEPLOY-02 does not execute these steps, create cloud resources, create DNS records, deploy, or use real secrets.

## Phase 1: Preflight

1. Confirm approved deployment commit.
2. Confirm `backend/app/cli.py` local dirty changes are excluded from the release package unless separately approved.
3. Confirm Product Owner, Security/Compliance, and Operations have approved the deployment window.
4. Confirm production PostgreSQL target, app settings, DNS plan, TLS plan, and rollback owner are documented.
5. Run local validation:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
cd ..
```

## Phase 2: Build Frontend

```powershell
cd frontend
npm ci
npm run build
cd ..
```

Expected:

- `frontend/dist/index.html` exists.
- `frontend/dist/assets/` contains hashed Vite assets.
- `frontend/dist` is included in the deployment artifact but not committed unless explicitly approved.

## Phase 3: Package App

1. Include runtime paths listed in `docs/clinical-deployment-package-manifest.md`.
2. Exclude `.env`, `.venv`, `node_modules`, generated metadata, logs, screenshots, local DB files, and demo seed outputs.
3. Include `frontend/dist` as a build artifact.
4. Preserve `scripts/start_app_service.py` as the startup entry point.
5. Record package checksum and storage location in the external release ticket.

## Phase 4: Provision Database

1. Use `docs/clinical-production-postgres-checklist.md`.
2. Provision PostgreSQL 16-compatible target or approved managed PostgreSQL.
3. Require TLS.
4. Configure private access or approved firewall allowlist.
5. Enable backup/retention and monitoring.
6. Store `DATABASE_URL` in approved app settings or secret store.
7. Do not run `scripts/seed_clinical_demo_data.py` in production.

## Phase 5: Apply Migrations

Before migration:

```powershell
.\.venv\Scripts\python.exe -m alembic heads
```

Expected head:

```text
202606130003 (head)
```

Apply only in approved deployment window with production `DATABASE_URL` loaded:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

After migration:

- Record current revision.
- Confirm no migration errors.
- Keep backup/restore marker available.

## Phase 6: Configure App Settings

1. Use `docs/clinical-app-service-settings-checklist.md`.
2. Configure non-secret settings directly in App Service settings.
3. Configure secret settings from approved secret store or protected app settings.
4. Confirm:
   - `APP_ENV=prod`
   - `CLINICAL_ENV=prod`
   - `SERVE_FRONTEND=true`
   - `FRONTEND_DIST_DIR=frontend/dist`
   - `DATABASE_URL` uses PostgreSQL with TLS
   - `COOKIE_SECURE=true`
   - `AUTHENTICATION_ENABLED=true`
   - `PHI_REDACTION_ENABLED=true`
   - `WORKFLOW_AUDIT_STORAGE=db_with_json_mirror`

## Phase 7: Deploy App

1. Deploy the approved package to the Web App by the approved release process.
2. Do not change Docker or Kubernetes settings.
3. Set startup command:

```text
python scripts/start_app_service.py
```

4. Restart the Web App after settings and package are in place.
5. Record deployment artifact version and operator.

## Phase 8: Run Startup Check

Run in the target environment shell or equivalent controlled deployment shell:

```powershell
python scripts/start_app_service.py --check
```

Expected:

- `startup_mode=fastapi_react`
- `serve_frontend=True`
- `frontend_dist_dir=frontend/dist`
- `production_security_gate=passed`
- `status=ok`

## Phase 9: Verify Health Endpoints

```powershell
Invoke-RestMethod https://clinical.teemails.com/api/health
Invoke-RestMethod https://clinical.teemails.com/api/monitoring/health
```

Expected:

- `/api/health` returns `status=ok`.
- `/api/monitoring/health` confirms database connectivity.

## Phase 10: Verify SPA Routes

Open or request:

- `https://clinical.teemails.com/`
- `https://clinical.teemails.com/clinical/dashboard`
- `https://clinical.teemails.com/clinical/patients`
- `https://clinical.teemails.com/clinical/reports`

Expected: the React app loads and route refresh works without 404.

## Phase 11: Verify Clinical Route Smoke

Smoke the operational shell routes:

- `/clinical/dashboard`
- `/clinical/patients`
- `/clinical/patients/:id`
- `/clinical/scheduling`
- `/clinical/screening`
- `/clinical/encounters`
- `/clinical/orders`
- `/clinical/care-plans`
- `/clinical/billing`
- `/clinical/quality`
- `/clinical/reports`
- `/clinical/admin`

Expected: visible route content, no blank screen, no unauthorized data leakage, unavailable workflows labeled as planned/foundation-pending where applicable.

## Phase 12: Verify Production Security Gates

1. Confirm startup check reports `production_security_gate=passed`.
2. Confirm production settings do not include:
   - SQLite
   - localhost/loopback database host
   - wildcard CORS
   - insecure cookies
   - demo auth bypass
   - JSON-only audit mode
   - unsafe export profiles
3. Confirm no live Azure tests are enabled unless the approved live-validation window is active.

## Phase 13: Verify Audit DB Table Availability

1. Confirm workflow audit storage is DB-backed.
2. Confirm `metadata/workflow_operations.json` is only a compatibility mirror.
3. Run an approved non-destructive audit availability check or controlled preview/commit smoke if Product Owner authorizes it.
4. Confirm append-only operation records are queryable from the database-backed audit store.

## Phase 14: Verify Reports/Exports Are Gated

1. Confirm export routes require appropriate permissions.
2. Confirm default profiles:
   - `DEFAULT_ANALYTICS_EXPORT_PROFILE=aggregate_safe`
   - `DEFAULT_COMPLIANCE_EXPORT_PROFILE=compliance_evidence`
   - `DEFAULT_AUDIT_EXPORT_PROFILE=audit_metadata`
3. Confirm PHI redaction remains enabled.
4. Confirm external/partner users cannot access internal clinical modules or high-risk export paths.

## Phase 15: Verify No Demo Seed In Production

1. Confirm `scripts/seed_clinical_demo_data.py` was not run.
2. Confirm demo users and demo auth bypass are disabled.
3. Confirm no synthetic/demo seed outputs are included in the production package.

## Phase 16: DNS Cutover

1. Use `docs/clinical-dns-custom-domain-checklist.md`.
2. Apply DNS records only after approval.
3. Complete App Service custom domain validation.
4. Bind TLS certificate.
5. Verify `https://clinical.teemails.com/api/health`.
6. Verify `https://clinical.teemails.com/clinical/dashboard`.

## Phase 17: Post-Deploy Monitoring

1. Monitor App Service startup, latency, 4xx/5xx rates, memory, CPU, and restarts.
2. Monitor PostgreSQL connections, CPU, storage, backup status, and error logs.
3. Monitor authentication failures and export attempts.
4. Keep deployment bridge open through the approved observation window.
5. Record Product Owner, Security/Compliance, and Operations acceptance or exceptions.

## Phase 18: Rollback

1. If startup fails before traffic cutover, stop and redeploy the last approved artifact.
2. If traffic cutover succeeds but app health fails, roll back app artifact first.
3. Roll back DNS only when Operations approves and artifact rollback is not sufficient.
4. Database restore requires DBA, Product Owner, and Security/Compliance approval after real clinical writes.
5. Record incident timeline, operator, decision owner, and follow-up ticket.
