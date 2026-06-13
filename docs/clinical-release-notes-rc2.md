# Clinical Release Notes RC2

Release candidate: RC2 Signoff / Final Hardening

Review date: 2026-06-13

## Accepted Commit Sequence

- `ee40f42` - Hardening pass for clinical release candidate.
- `9ad2b06` - Document RC1 clinical security readiness.
- RC2 signoff commit - final dependency remediation, signoff docs, and release guard tests in this change set.

## Completed Platform Modules

- Patient / Donor Registration
- Scheduling
- Screening / Eligibility
- EMR / Encounters
- Orders / Results
- Care Plans
- Billing / Insurance
- Quality / Compliance
- Clinical Administration
- Reporting / Analytics Readiness
- RBAC/export review
- Workflow operation audit foundation
- Release-candidate security and production-readiness documentation

## RC2 Changes

- Resolved the RC1 Vite/esbuild advisory by upgrading `vite` to `^8.0.16` and `@vitejs/plugin-react` to `^6.0.2`.
- Added `docs/clinical-release-exceptions.md` with the dependency decision and remaining production-readiness limitations.
- Added `docs/clinical-rc2-signoff.md` with automated evidence, manual Product Owner signoff items, route smoke inventory, and known limitations.
- Added RC2 documentation guards for route inventory, migration chain inventory, dependency remediation, and release note coverage.
- Updated security, production readiness, migration, and RC1 release docs to reflect the RC2 dependency result.

## Validation Status

RC2 validation commands:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
npm audit --audit-level=high
```

Actual RC2 outcome:

- preflight passed;
- pytest passed: 141 tests, 1 existing Starlette `TestClient` deprecation warning;
- frontend build passed with Vite `8.0.16`;
- npm audit reported `found 0 vulnerabilities`;
- `pip check` passed with no broken requirements.

## Security / Dependency Exceptions

No Vite/esbuild release exception remains open. The dependency advisory was remediated with a bounded frontend toolchain upgrade.

Remaining release-candidate exceptions are production-readiness limitations:

- filesystem-backed workflow operation audit;
- missing PHI/ePHI masking and redaction framework;
- missing production startup fail-closed checks for unsafe default settings;
- generic foundation workflow commit endpoint is not authenticated;
- least-privilege review remains for report audit activity and export metadata.

## Audit Durability Status

Workflow commits still append to `metadata/workflow_operations.json`. RC2 keeps the database-backed audit migration out of scope and relies on `docs/clinical-audit-durability-implementation-plan.md` for the post-RC implementation path.

## Production Readiness Status

RC2 is suitable for release-candidate signoff once Product Owner manual QA is complete. It is not full production go-live approval until the post-RC backlog items below are closed or formally accepted.

## Recommended Post-RC Backlog

1. Implement database-backed append-only workflow operation audit with backfill and database-first readers.
2. Add production startup validation for unsafe defaults and missing security settings.
3. Add PHI/ePHI masking, export profiles, and small-cell suppression.
4. Add generated route-permission drift tests from FastAPI route metadata.
5. Split audit activity/export metadata permissions if compliance requires stricter least privilege.
6. Complete external identity/MFA production design.
7. Add approved Python vulnerability scanning to CI.
8. Complete manual Product Owner QA evidence and archive signoff artifacts.
