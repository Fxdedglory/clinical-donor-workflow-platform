# Clinical RC2 Signoff

RC2 signoff date: 2026-06-13

Scope: final release-candidate signoff and hardening. RC2 does not add clinical modules or redesign existing screens.

## Automated Evidence

| Area | Evidence | Status |
| --- | --- | --- |
| Worktree protection | `git status --short`; `git diff -- backend/app/cli.py` | `backend/app/cli.py` is the only pre-existing dirty file and remains protected. |
| Dependency advisory | Vite 8 and React plugin 6 bounded upgrade; `npm audit --audit-level=high` | Resolved; zero vulnerabilities reported after upgrade. |
| Frontend build | `cd frontend; npm run build` | Passed with Vite `8.0.16`. |
| Route inventory | `frontend/src/pages/clinical/clinicalRoutes.jsx`; RC2 documentation guard test | All required `/clinical/...` routes are present, including `/clinical/patients/:id`. |
| Migration readiness | `docs/clinical-migration-runbook.md`; RC2 migration guard test | Sprint 2 through Sprint 11 migration chain documented in order. |
| Backend validation | `.\.venv\Scripts\python.exe -m pytest` | Passed: 141 tests, 1 existing Starlette `TestClient` deprecation warning. |
| Preflight validation | `.\.venv\Scripts\python.exe scripts\preflight_check.py` | Passed. |
| Python dependency consistency | `.\.venv\Scripts\python.exe -m pip check` | Passed: no broken requirements found. |

## Manual QA Signoff Matrix

Codex cannot complete full browser/manual Product Owner QA inside this environment. The items below are ready for Product Owner signoff using `docs/clinical-rc-qa-checklist.md`.

| Module / Area | RC2 evidence | Product Owner signoff item |
| --- | --- | --- |
| Patient / Donor Registration | Routes, API inventory, workflow audit, and tests exist for patient create/update/contact/insurance/consent. | Exercise registration preview/commit, patient detail, contacts, insurance, consents, duplicate-warning behavior, and audit evidence. |
| Scheduling | Scheduling routes and tests cover appointment booking, reschedule, cancel, check-in, and no-show. | Exercise appointment lifecycle in browser and verify resource/type context. |
| Screening / Eligibility | Screening routes and tests cover sessions, questionnaire, vitals, result, override, deferrals, and audit append. | Exercise questionnaire/vitals/result/override flows and verify eligibility warnings/blockers. |
| EMR / Encounters | Encounter routes and tests cover encounter creation, notes, sign/amend, diagnoses, allergies, and medications. | Exercise note lifecycle, signed-note lock behavior, amendment history, and patient clinical summary. |
| Orders / Results | Orders routes and tests cover order creation, result add/correction, critical acknowledgement, and cancellation. | Exercise order/result workflow and critical-result acknowledgement UX. |
| Care Plans | Care plan routes and tests cover plan create, goals, interventions, tasks, progress, and closure. | Exercise care plan lifecycle and linked order/result context. |
| Billing / Insurance | Billing routes and tests cover charges, claims, payments, denials, insurance verification, and work queue. | Exercise billing work queue and each preview/commit path. |
| Quality / Compliance | Quality tests cover quality events, adverse events, investigations, CAPA links, closures, compliance export, and audit evidence. | Exercise quality workspace, compliance export, and audit evidence filters. |
| Clinical Administration | Admin tests cover configuration preview/commit and external-user rejection. | Exercise config versioning, templates, catalogs, approval paths, notification templates, and RBAC overview. |
| Reporting / Analytics | Reports tests cover dashboard/report endpoints, analytics export preview/commit, audit append, and external-user rejection. | Exercise report filters, analytics export modal, export history, and audit activity. |
| RBAC/export behavior | RBAC matrix and export permission review document current enforcement; tests cover high-risk external rejection paths. | Confirm least-privilege expectations with compliance/product owners. |
| Audit evidence | Workflow operation audit append is covered by module tests and docs. | Confirm evidence package format and filters; accept JSON audit as RC-only limitation. |
| Migration readiness | Sprint 2-11 migrations documented and tested for chain order. | Confirm deployment database backup, Alembic current/head, and migration execution window. |

## Browser Route Smoke Inventory

Required clinical routes for RC2:

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
- `/clinical/admin`
- `/clinical/reports`

RC2 does not add a browser automation framework. Route presence is verified through the existing frontend route metadata and documentation guard tests; Product Owner browser smoke remains manual.

## Known Limitations

- Workflow operation audit remains filesystem-backed and must move to database-backed append-only storage before production go-live.
- PHI/ePHI masking and redaction are documented but not implemented.
- Production startup does not yet reject unsafe default secrets/cookie/MFA/encryption settings.
- Generic foundation workflow commit endpoint is confirmation-guarded but not authenticated.
- Report audit activity and export metadata may need stricter least-privilege separation.
- External integrations remain out of scope: Snowflake, dbt, Power BI, FHIR/HL7, clearinghouse submission, notification delivery, and approval execution.
