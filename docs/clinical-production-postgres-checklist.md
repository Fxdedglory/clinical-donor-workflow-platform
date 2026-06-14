# Clinical Production PostgreSQL Checklist

Task: `CLINICAL-DEPLOY-02`

Production database requirement: PostgreSQL is mandatory. SQLite and local file databases are blocked by production gates.

This checklist is for provisioning and validating the production database target. It does not create the database, run live migrations, or contain real credentials.

## Provisioning Fields

| Status | Item | Required decision | Recommended placeholder | Owner / action |
| --- | --- | --- | --- | --- |
| [ ] | Server name | Approved production PostgreSQL server name. | `psql-clinical-prod-<region>` | DBA/Ops: reserve final name. |
| [ ] | Database name | Clinical application database name. | `clinical_donor_workflow` | DBA/Ops: create database after approval. |
| [ ] | Region | Azure region or approved managed PostgreSQL region. | `<approved-primary-region>` | Product/Ops: confirm residency and latency. |
| [ ] | Version | PostgreSQL 16-compatible engine unless approved otherwise. | `PostgreSQL 16` | DBA/Ops: confirm version compatibility. |
| [ ] | Admin/auth model | Choose admin account, managed identity, or approved operational model. | `<approved-db-admin-or-managed-identity>` | Security/DBA: approve least-privilege access. |
| [ ] | Application role | Least-privilege runtime principal. | `clinical_app` | DBA/Security: grant only needed runtime permissions. |
| [ ] | SSL/TLS | Require encrypted connections. | `sslmode=require` or stricter approved mode | DBA/Ops: verify enforcement. |
| [ ] | Network access | Firewall allowlist, private endpoint, or VNet integration decision. | `<private-access-or-app-service-egress-allowlist>` | Security/Ops: approve access model. |
| [ ] | Backup retention | PITR and retention window. | `<approved-retention-days>` | DBA/Ops: document restore owner and RPO/RTO. |
| [ ] | Maintenance window | Approved patching window. | `<approved-window>` | Ops: coordinate with deployment calendar. |
| [ ] | Monitoring | DB metrics, connection saturation, storage, errors, backup status. | `<monitoring-workspace-or-appinsights-link>` | Ops: configure alerts. |

## Connection String Shape

Use this placeholder shape only:

```text
DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@<postgres_host>:5432/clinical_donor_workflow?sslmode=require
```

Production expectations:

- Scheme starts with `postgresql` or `postgres`.
- Host is not `localhost`, loopback, or a local container name.
- TLS is required.
- Credentials are generated and stored outside Git.
- Application runtime uses least-privilege credentials or approved managed identity integration.

## Migration Plan

Pre-migration checks:

```powershell
.\.venv\Scripts\python.exe -m alembic heads
```

Expected head:

```text
202606130003 (head)
```

Production migration command, run only in the approved deployment window with production app settings loaded:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Post-migration checks:

- Confirm Alembic current revision is at the expected head.
- Confirm `/api/monitoring/health` reports database connectivity after app deployment.
- Confirm workflow audit DB tables are available before clinical writes are enabled.

## Backup And Rollback

- [ ] Confirm PITR is enabled before migration.
- [ ] Capture a named restore point or approved backup marker before migration.
- [ ] Record rollback owner and contact path.
- [ ] Define app rollback artifact and database restore decision gate.
- [ ] Prefer app rollback first; database restore requires DBA and Product Owner approval after real clinical writes.
- [ ] Do not rely on Alembic downgrade as the primary rollback for production clinical data.

## Production Warning

`scripts/seed_clinical_demo_data.py` is non-production only. Do not run demo seed scripts, demo user creation, or synthetic-data population against the production database.
