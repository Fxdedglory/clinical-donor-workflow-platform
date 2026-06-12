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
| Scheduling | Sprint 3 adds appointment booking, resources, appointment types, conflict previews, status transitions, UI workflows, RBAC, and audit. | Add full calendar visualization, recurring availability templates, capacity rules, waitlists, reminders, and completed-appointment handoff into encounters. |
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

## Sprint 3 Implemented Scope

Sprint 3 implements Clinical Scheduling linked to the canonical Patient / Donor Registration foundation.

Implemented scheduling foundation:

- Persistent scheduling entities:
  - `operational.clinical_providers`
  - `operational.clinical_rooms`
  - `operational.clinical_equipment`
  - `operational.appointment_types`
  - `operational.appointments`
  - `operational.appointment_resources`
  - `operational.appointment_status_history`
- Alembic migration `202606120002_clinical_scheduling`.
- Scheduling RBAC permissions:
  - `scheduling.read`
  - `scheduling.manage`
- Backend `/api/clinical/scheduling` endpoints:
  - `GET /api/clinical/scheduling/appointments`
  - `GET /api/clinical/scheduling/appointments/{appointment_id}`
  - `POST /api/clinical/scheduling/appointments/preview`
  - `POST /api/clinical/scheduling/appointments`
  - `POST /api/clinical/scheduling/{appointment_id}/reschedule/preview`
  - `POST /api/clinical/scheduling/{appointment_id}/reschedule`
  - `POST /api/clinical/scheduling/{appointment_id}/cancel/preview`
  - `POST /api/clinical/scheduling/{appointment_id}/cancel`
  - `POST /api/clinical/scheduling/{appointment_id}/check-in/preview`
  - `POST /api/clinical/scheduling/{appointment_id}/check-in`
  - `POST /api/clinical/scheduling/{appointment_id}/no-show/preview`
  - `POST /api/clinical/scheduling/{appointment_id}/no-show`
  - `GET /api/clinical/scheduling/resources`
  - `GET /api/clinical/scheduling/appointment-types`
- Preview conflict detection covers:
  - Provider overlap
  - Room overlap
  - Equipment/resource overlap
  - Patient overlap
  - Invalid scheduled start/end
  - Missing required room
  - Unknown patient/provider/room/equipment/type references
- Preview warnings cover appointment type duration mismatch and outside-normal-hours scheduling.
- Commit endpoints require authenticated internal users, scheduling mutation permission, and `X-Confirm-Generation: true`.
- External partner/supplier users are rejected from scheduling mutation.
- Successful commits append workflow operations for:
  - `appointment.book`
  - `appointment.reschedule`
  - `appointment.cancel`
  - `appointment.check_in`
  - `appointment.no_show`
- Frontend `/clinical/scheduling` is now an operational appointment workspace with filters, appointment table, detail panel, status chips, resource/type/patient loading, and actions for book, reschedule, cancel, check-in, and no-show.
- Scheduling modal workflows follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success.
- Focused tests cover confirmation guard behavior, audit creation and append preservation, overlap conflicts, status history, audit events, invalid transitions, cancellation reason validation, check-in/no-show transitions, and external partner rejection.

## Future Sprint Sequence

1. Donor Screening / Eligibility: questionnaire sessions, vitals, eligibility preview, deferrals, supervisor overrides, and audit.
2. EMR / Encounters: encounter creation, note templates, draft notes, signing, locking, amendments, and version history.
3. Orders / Results: order catalog, order lifecycle, result entry, critical flags, acknowledgement, and cancellation.
4. Care Plans: care plan creation, goals, interventions, tasks, care team assignment, progress updates, and closure.
5. Billing / Insurance: charges, coding, claim draft/review/commit, payments, denials, and rework queues.
6. Quality / Compliance: quality events, adverse events, CAPA lifecycle, audit viewer, compliance export, and closure approval.
7. Clinical Administration: versioned templates, rules, catalogs, approval paths, and admin preview/commit.
8. Reporting / Analytics: operational reports, filters, exports, and analytics-ready views.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```
