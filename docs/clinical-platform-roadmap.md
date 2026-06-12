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
| Patient / Donor Management | Donor master and donor review records exist. | Add canonical patient/donor registration, contacts, insurance, consent, duplicate review, and merge workflows. |
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

## Future Sprint Sequence

1. Patient / Donor Registration: profiles, contacts, insurance, consent, duplicate review, and profile audit.
2. Scheduling: appointment booking, resource conflict checks, reschedule, cancellation, check-in, no-show, and audit.
3. Donor Screening / Eligibility: questionnaire sessions, vitals, eligibility preview, deferrals, supervisor overrides, and audit.
4. EMR / Encounters: encounter creation, note templates, draft notes, signing, locking, amendments, and version history.
5. Orders / Results: order catalog, order lifecycle, result entry, critical flags, acknowledgement, and cancellation.
6. Care Plans: care plan creation, goals, interventions, tasks, care team assignment, progress updates, and closure.
7. Billing / Insurance: charges, coding, claim draft/review/commit, payments, denials, and rework queues.
8. Quality / Compliance: quality events, adverse events, CAPA lifecycle, audit viewer, compliance export, and closure approval.
9. Clinical Administration: versioned templates, rules, catalogs, approval paths, and admin preview/commit.
10. Reporting / Analytics: operational reports, filters, exports, and analytics-ready views.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```
