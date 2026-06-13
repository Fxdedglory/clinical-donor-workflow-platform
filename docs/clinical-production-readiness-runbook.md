# Clinical Production Readiness Runbook

RC1 review date: 2026-06-13

RC2 update date: 2026-06-13

This runbook prepares the clinical platform for production signoff. It does not replace environment-specific deployment documentation in `docs/azure/`.

## Environment Variables

Required production settings:

- `APP_ENV=prod`
- `DATABASE_URL` with production database credentials and TLS
- `SECRET_KEY` generated outside Git
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax` unless partner redirect testing requires another approved value
- `CORS_ORIGINS` restricted to approved production domains
- `ENCRYPTION_KEY` before field-level sensitive-data encryption is enabled
- `BACKUP_ENCRYPTION_KEY` before hosted backup automation is enabled
- `EMAIL_PROVIDER` and provider credentials if notification delivery is enabled
- `VITE_API_BASE_URL` only when frontend and backend are hosted separately

Disallowed production values:

- demo `SECRET_KEY`
- predictable `MFA_DEV_BYPASS_CODE`
- demo/shared passwords
- local database credentials
- local `.env` values copied into hosted settings without review

## Migration Sequence

1. Confirm target database backup and rollback point.
2. Confirm Alembic configuration points at the target database.
3. Run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

4. Confirm the Sprint 2 through Sprint 11 clinical migrations from `docs/clinical-migration-runbook.md` are applied.
5. Run application smoke tests before opening user traffic.

## Validation Commands

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
```

Run from the frontend directory:

```powershell
npm run build
```

RC1 and RC2 also used these readiness checks:

```powershell
.\.venv\Scripts\python.exe -m pip check
cd frontend
npm audit --audit-level=high
```

RC2 upgraded Vite and the React plugin to resolve the RC1 Vite/esbuild advisories. `npm audit --audit-level=high` now reports zero vulnerabilities in the frontend package set.

## Manual QA Checklist Reference

Use `docs/clinical-rc-qa-checklist.md` for manual module QA. RC1 production signoff should include at least:

- patient/donor registration preview and commit;
- scheduling appointment lifecycle;
- screening questionnaire, vitals, result, and override;
- encounter note, sign, amendment, diagnosis, allergy, medication;
- order, result, correction, acknowledgement, cancellation;
- care plan goals, interventions, tasks, progress, closure;
- billing charge, claim, payment, denial, insurance verification;
- quality event, adverse event, investigation, CAPA, closure;
- reporting dashboard and analytics export preview/commit;
- clinical admin configuration preview/commit;
- audit evidence filtering.

## Smoke Test Checklist

1. Login succeeds with an approved internal user.
2. External partner user cannot access internal clinical modules.
3. `/clinical/dashboard` and all `/clinical/...` routes render.
4. `/api/clinical/status` and `/api/clinical/modules` return expected module inventory.
5. A representative commit endpoint rejects missing `X-Confirm-Generation`.
6. The same endpoint accepts `X-Confirm-Generation: true`.
7. A workflow operation audit entry is written.
8. Reports analytics export preview and commit work for an authorized export role.
9. Quality audit evidence works for an authorized QA/audit role.
10. Clinical admin mutation requires admin mutation permission and confirmation.

## Audit And Export Review Checklist

- Confirm `metadata/workflow_operations.json` is not the production source of truth.
- Confirm production audit migration plan is scheduled before signoff.
- Confirm export metadata retention and access are approved.
- Confirm report audit activity is scoped to approved roles.
- Confirm no external delivery is enabled for analytics/compliance exports.
- Confirm PHI/ePHI masking requirements are documented before detailed exports.

## Rollback Notes

- Keep a database backup before migration.
- Roll back application deployment first if validation fails after deployment.
- Use Alembic downgrade only when the migration explicitly supports safe downgrade and clinical data loss has been reviewed.
- Do not delete workflow audit evidence as part of rollback.
- Preserve generated export/audit metadata for incident review.

## Known Limitations

- Workflow operation audit remains filesystem-backed in RC2.
- No full PHI masking/redaction framework exists yet.
- Vite/esbuild audit advisories were resolved in RC2 with the bounded Vite 8 upgrade.
- Production startup does not yet fail closed on unsafe default secrets/cookie settings.
- Analytics/compliance exports are metadata/evidence contracts only; external warehouse, FHIR/HL7, Power BI, clearinghouse, and notification delivery integrations remain out of scope.
