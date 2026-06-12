# Clinical Platform Roadmap

## Sprint 0 Discovery Summary

The repository is a FastAPI, SQLAlchemy, PostgreSQL, and React/Vite application focused on donor referral intake, donor eligibility, workflow orchestration, QMS/CAPA, audit, partner portal, AI governance, data generation, and export readiness.

`AGENTS.md` was absent during discovery. The existing implementation already contains donor/QMS workflow depth, RBAC, audit logging, workflow tasks, transition history, security audit, and data export foundations. It does not yet expose the broader clinical platform shell and API contract described by the clinical implementation roadmap.

Important repository state from Sprint 0:

- Frontend is a single React app in `frontend/src/App.jsx` with custom browser routing.
- Backend routers are registered in `backend/app/main.py`.
- Existing API namespaces include `/api/donors`, `/api/eligibility`, `/api/workflow-tasks`, `/api/audit-logs`, `/api/change-control`, `/api/vendors`, `/api/workspaces`, and `/api/routes`.
- Existing data model strongly covers donor eligibility, QMS/CAPA, audit, workflow orchestration, RBAC, partner portal, documents, and exports.
- Existing tests cover runtime smoke, monitoring, auth shell routes, ADLS/parquet export, scheduler guardrails, and scheduled jobs.

## Current Gap Matrix

| Module | Current State | Remaining Gap |
| --- | --- | --- |
| Patient / Donor Management | Sprint 2 adds canonical patient/donor registration, contacts, insurance, consents, duplicate warnings, preview/commit APIs, UI workflows, and workflow operation audit. | Add merge/review queue, richer identity conflict review, patient/donor linkage to downstream modules, and production duplicate-resolution policy. |
| Scheduling | No clinical appointment module. | Add appointments, provider/resource calendars, rooms, equipment, conflict checks, cancellation, check-in, and no-show transitions. |
| Donor Screening / Eligibility | Donor eligibility engine and staged outcomes exist. | Add first-class screening sessions, questionnaire templates, vitals capture, preview/commit result flow, and deferral registry. |
| EMR / Encounters | No generic encounter documentation module. | Add encounters, notes, diagnoses, allergies, medications, signing, locking, and amendments. |
| Orders / Results | Infectious disease results exist for donor eligibility. | Add generic order catalog, lab/test orders, result entry, abnormal/critical flags, acknowledgement, and cancellation. |
| Care Plans | No care plan module. | Add care plans, goals, interventions, tasks, care team assignment, progress updates, and closure. |
| Billing / Insurance | No billing workflow module. | Add insurance profile, charges, codes, authorizations, claims, payments, denials, and rework queues. |
| Quality / Compliance | Deviation, CAPA, audit, and QMS concepts exist. | Add `/clinical/quality` workflows, adverse events, audit evidence export, severity classification, and closure approval. |
| Reporting / Analytics | Dashboards, monitoring, and export metadata exist. | Add clinical module reports with date/status/entity filters and export surfaces. |
| Clinical Administration | System admin and RBAC exist. | Add versioned clinical templates, appointment types, screening rules, note templates, order catalogs, billing code lists, quality categories, and approval paths. |
| Audit / Workflow Operations | Database audit and transition history exist. | Add roadmap-level preview/commit audit records in `metadata/workflow_operations.json`. |

## Sprint 1 Implemented Scope

Sprint 1 adds the clinical shell and shared workflow foundation without implementing full module workflows.

Implemented foundation:

- Project OS documentation in `AGENTS.md`.
- Frontend clinical route shell:
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
- Backend `/api/clinical` router foundation:
  - `GET /api/clinical/status`
  - `GET /api/clinical/modules`
  - `POST /api/clinical/workflows/preview`
  - `POST /api/clinical/workflows/commit`
- Reusable clinical workflow schemas for module inventory, preview, commit, validation issues, and operation audit records.
- Reusable `X-Confirm-Generation: true` commit guard.
- Append-only JSON workflow audit writer targeting `metadata/workflow_operations.json`.
- Focused tests for commit confirmation and audit append behavior.

## Sprint 2 Implemented Scope

Sprint 2 implements canonical Patient / Donor Registration as the first real clinical module on top of the Sprint 1 shell.

Implemented patient registration:

- Persistent clinical registration entities:
  - `operational.patients`
  - `operational.patient_contacts`
  - `operational.patient_insurance`
  - `operational.patient_consents`
- Alembic migration `202606120001_clinical_patient_registration`.
- Backend `/api/clinical/patients` endpoints:
  - `GET /api/clinical/patients`
  - `POST /api/clinical/patients/preview`
  - `POST /api/clinical/patients`
  - `GET /api/clinical/patients/{patient_id}`
  - `POST /api/clinical/patients/{patient_id}/edit/preview`
  - `PATCH /api/clinical/patients/{patient_id}`
  - `POST /api/clinical/patients/{patient_id}/contacts/preview`
  - `POST /api/clinical/patients/{patient_id}/contacts`
  - `POST /api/clinical/patients/{patient_id}/insurance/preview`
  - `POST /api/clinical/patients/{patient_id}/insurance`
  - `POST /api/clinical/patients/{patient_id}/consents/preview`
  - `POST /api/clinical/patients/{patient_id}/consents`
- Mutation endpoints require authenticated internal users and `X-Confirm-Generation: true`.
- External partner/supplier users are rejected from patient registration mutation.
- Preview duplicate-risk warnings are based on name/date of birth, phone, and email.
- Successful commits append workflow operations for:
  - `patient.create`
  - `patient.update_demographics`
  - `patient.add_contact`
  - `patient.add_insurance`
  - `patient.capture_consent`
- Frontend `/clinical/patients` is now a searchable patient/donor list with status chips, loading/error/empty states, create action, and row detail navigation.
- Frontend `/clinical/patients/:id` is now a patient detail page with demographics, contacts, insurance, consents, recent workflow activity, and planned downstream workflow actions.
- Modal workflows now follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success for create, edit, contact, insurance, and consent capture.
- Focused tests cover confirmation header enforcement, duplicate warnings, create/update/consent audit events, and external partner mutation rejection.

## Future Sprint Sequence

1. Scheduling: appointment booking, resource conflict checks, reschedule, cancellation, check-in, no-show, and audit.
2. Donor Screening / Eligibility: questionnaire sessions, vitals, eligibility preview, deferrals, supervisor overrides, and audit.
3. EMR / Encounters: encounter creation, note templates, draft notes, signing, locking, amendments, and version history.
4. Orders / Results: order catalog, order lifecycle, result entry, critical flags, acknowledgement, and cancellation.
5. Care Plans: care plan creation, goals, interventions, tasks, care team assignment, progress updates, and closure.
6. Billing / Insurance: charges, coding, claim draft/review/commit, payments, denials, and rework queues.
7. Quality / Compliance: quality events, adverse events, CAPA lifecycle, audit viewer, compliance export, and closure approval.
8. Clinical Administration: versioned templates, rules, catalogs, approval paths, and admin preview/commit.
9. Reporting / Analytics: operational reports, filters, exports, and analytics-ready views.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```
