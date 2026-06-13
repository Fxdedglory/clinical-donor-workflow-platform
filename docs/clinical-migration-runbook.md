# Clinical Migration Runbook

RC0 inventory date: 2026-06-12

RC2 verification date: 2026-06-13

Scope: clinical platform migrations introduced from Sprint 2 through Sprint 11. Sprint 1 was shell/API foundation only and did not add a broad clinical migration.

## Expected Migration Order

Apply migrations in revision order:

| Sprint | Revision | File | Purpose |
| --- | --- | --- | --- |
| Sprint 2 | `202606120001` | `202606120001_clinical_patient_registration.py` | Patients, contacts, insurance, consents. |
| Sprint 3 | `202606120002` | `202606120002_clinical_scheduling.py` | Providers, rooms, equipment, appointment types, appointments, resources, status history. |
| Sprint 4 | `202606120003` | `202606120003_clinical_screening.py` | Screening sessions, answers, vitals, outcomes, deferrals, screening status history. |
| Sprint 5 | `202606120004` | `202606120004_clinical_encounters.py` | Encounters, notes, note templates, diagnoses, allergies, medications, encounter status history. |
| Sprint 6 | `202606120005` | `202606120005_clinical_orders.py` | Order catalog, orders, results, acknowledgements, order status history. |
| Sprint 7 | `202606120006` | `202606120006_clinical_care_plans.py` | Care plans, goals, interventions, tasks, progress notes, team members, care plan status history. |
| Sprint 8 | `202606120007` | `202606120007_clinical_billing.py` | Billing accounts, insurance verification, charges, claims, lines, payments, denials, billing status history. |
| Sprint 9 | `202606120008` | `202606120008_clinical_quality.py` | Quality events, adverse events, investigations, approvals, links, compliance exports, quality status history. |
| Sprint 10 | `202606120009` | `202606120009_clinical_admin.py` | Clinical admin config versions, approval paths, templates, rule versions, catalogs, quality categories, status history. |
| Sprint 11 | `202606120010` | `202606120010_clinical_reports.py` | Report exports, export items, report status history, report RBAC grants. |

## Local Validation Commands

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest
```

If the local database is already at head, `alembic upgrade head` should be idempotent.

## Deployment Checklist

1. Confirm application release commit and database backup point.
2. Confirm the target database is reachable from the migration execution environment.
3. Confirm current revision:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic current
   ```

4. Confirm the migration graph has the expected head:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic heads
   ```

5. Apply migrations:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   ```

6. Run smoke validation:
   - `GET /api/health`
   - `GET /api/clinical/status`
   - `GET /api/clinical/modules`
   - Authenticate as an internal demo/admin user.
   - Load `/clinical/patients`, `/clinical/scheduling`, `/clinical/screening`, `/clinical/encounters`, `/clinical/orders`, `/clinical/care-plans`, `/clinical/billing`, `/clinical/quality`, `/clinical/admin`, and `/clinical/reports`.

7. Run release candidate QA checklist in `docs/clinical-rc-qa-checklist.md`.

## Rollback Notes

- Each sprint migration includes a downgrade path, but clinical downgrades are destructive for newly created sprint tables and role-permission grants.
- In production, prefer backup restore or point-in-time recovery over downgrade after data has been written.
- If a migration fails before data writes, fix-forward is preferred when the failure is metadata/index/permission related and the database remains consistent.
- Do not downgrade after real clinical workflow commits without explicit data-retention approval.
- Downgrading Sprint 11 removes clinical report export tables and `reports.read` / `reports.export` grants.

## Known Migration Risks

- Role-permission grants depend on expected seeded role names in `operational.dim_role`.
- JSON fields in clinical tables are PostgreSQL JSON columns; downstream BI extracts should validate shape before production use.
- Workflow operation audit remains filesystem-backed in RC2 and is not migrated into database tables yet.
- Large production data volumes may require index review before reporting exports are used heavily.
