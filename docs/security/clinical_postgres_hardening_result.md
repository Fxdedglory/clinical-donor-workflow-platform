# Clinical PostgreSQL Hardening Result

Date: 2026-05-29

## Scope

This pass hardened only the Clinical Donor Platform PostgreSQL runtime path. ERP, HR, Monitor, Data Platform, Cloudflare routing, and Azure topology were not modified.

## Current PostgreSQL Inventory

| Area | Result |
|---|---|
| Server | `psql-teemails-clinical-dev-wcus` |
| Resource group | `rg-teemails-portfolio-dev-wcus` |
| Region | West Central US |
| PostgreSQL version | 16 |
| SKU | `Standard_B1ms`, Burstable |
| Database | `clinical_donor_workflow` |
| SSL transport | `require_secure_transport=on`; live SQL connection reported SSL `on` |
| Backup retention | 7 days |
| Public network access | Enabled |
| App runtime role | `clinical_runtime` |
| Admin role retained | `clinical_admin` |

## Role Changes

Created `clinical_runtime` as an application runtime role:

- Login enabled.
- No superuser.
- No createdb.
- No createrole.
- No replication.
- No bypassrls.
- No schema ownership granted.

Granted application-only access across current app schemas:

- Schemas: `marts`, `operational`, `public`, `staging`
- Schema usage.
- Existing table CRUD: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
- Sequence usage/select.
- Default privileges for future objects created by `clinical_admin` in those schemas.

`clinical_admin` remains available for migrations and administrative work only.

## Application Cutover

Azure App Service `app-teemails-clinical-dev` now uses `clinical_runtime` in `DATABASE_URL`.

The connection string includes `sslmode=require`. Secret values are stored only in Azure App Settings and were not committed.

## Validation Results

Runtime validation was performed with `clinical_runtime`:

- Producer status: succeeded.
- Incremental producer: succeeded.
- Validation: passed.
- Export batch: `clinical_runtime_hardening_20260529`.
- Runtime row count after incremental: 12,107 rows across exported tables.
- Tests: `pytest` passed.
- Preflight: passed.
- Startup helper: passed.
- Frontend build: passed.

## Monitoring Integration

`/api/monitoring/health` now exposes:

- `database_status`
- `database_role`
- `database_ssl_status`

These values are intended for the Monitoring Platform and do not expose credentials.

## Backup Status

Attempted Azure on-demand backup:

- Backup name: `clinical-hardening-20260529`
- Result: failed because Azure does not allow customer on-demand backups on Burstable Flexible Server SKUs.
- Azure error: `CustomerOnDemandBackupCannotBePerformedOnBurstableServer`

Created local logical backup instead:

- Path: `data/backups/clinical_logical_backup_20260529.zip`
- Type: logical CSV ZIP
- Files: 78 table CSV files plus `manifest.json`
- Row count: 12,107
- Role used: `clinical_runtime`
- SSL mode: `require`

The backup artifact is generated runtime data and ignored by Git.

## Restore Verification Checklist

Use this checklist before relying on a backup for recovery:

1. Confirm the ZIP contains `manifest.json`.
2. Confirm table count matches the manifest.
3. Confirm row counts match the manifest.
4. Restore to a temporary PostgreSQL database, not the production Clinical database.
5. Run Alembic migration status against the restored database.
6. Run producer validation against the restored database.
7. Run sample API read checks against the restored database.
8. Destroy the temporary restore database/server after explicit approval.

No Azure restore server was created during this pass because that would provision an additional resource and may create cost.

## Firewall Review

Current rules:

| Rule | Purpose | Recommendation |
|---|---|---|
| `allow-current-dev-ip` | Local admin/developer access | Keep only while direct admin access is needed. Remove later if not needed. |
| `AllowAllAzureServicesAndResourcesWithinAzureIps_2026-5-29_10-47-30` | Allows Azure service access from App Service | Convenient but broad. Tighten only after validating App Service outbound IP allowlisting. |

Recommended next firewall path:

1. Inventory `app-teemails-clinical-dev` current and possible outbound IPs.
2. Add explicit firewall rules for possible outbound IPs.
3. Restart and validate Clinical.
4. Remove broad Azure-services access only after validation.
5. Consider private networking later if cost/complexity is acceptable.

## Remaining Risks

- `clinical_admin` still has administrative permissions and must be protected/rotated separately.
- Burstable PostgreSQL SKU cannot create customer on-demand Azure backups.
- Public network access remains enabled.
- Broad Azure-services firewall rule remains enabled.
- A full restore test was documented but not provisioned.
