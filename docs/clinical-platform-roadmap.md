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
| Donor Screening / Eligibility | Sprint 4 adds patient-linked screening sessions, questionnaire/vitals capture, eligibility preview, result commit, deferrals, supervisor override, UI workflow, RBAC, and audit while reusing the existing donor eligibility engine. | Add richer screening templates, infectious disease result entry, deferral expiration workflows, medical director queues, and deeper donor-to-patient identity reconciliation. |
| EMR / Encounters | Sprint 5 adds encounter creation, note templates, draft notes, signing/locking, amendments, diagnoses/problems, allergies, medications, status history, RBAC, audit, and an operational UI. | Add richer clinician assignment, encounter closure/cancellation policies, problem reconciliation, medication/allergy reconciliation, and deeper downstream decision support. |
| Orders / Results | Sprint 6 adds generic clinical order catalog, order placement, result entry/correction, abnormal/critical flags, acknowledgement, cancellation, status history, RBAC, audit, and an operational UI. | Add specimen accessioning, laboratory interface ingestion, reference-range engines, richer correction policy, infectious disease fact reconciliation, and downstream Billing handoff. |
| Care Plans | Sprint 7 adds patient-linked care plans, goals, interventions, tasks, team assignment, progress timeline, closure, RBAC, audit, and an operational UI. | Add richer task lifecycle updates, cross-plan case load balancing, referral automation, and downstream Billing/Quality handoff. |
| Billing / Insurance | Sprint 8 adds billing accounts, insurance verification, charge capture, claim drafts/lines, payment posting, denial/rework, RBAC, audit, and an operational UI. | Add real clearinghouse submission, EDI 837/835, prior authorization, coding master data ingestion, appeals, and payer integrations. |
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

## Sprint 4 Implemented Scope

Sprint 4 implements Donor Screening / Eligibility as an operational clinical module linked to canonical Patient / Donor Registration and Scheduling.

Existing assets reused:

- Existing `dim_donor` bridge by patient `donor_reference` when present.
- Existing donor eligibility engine in `app.services.eligibility_engine`.
- Existing eligibility rules in `operational.dim_eligibility_rule`.
- Existing donor screening facts in `operational.fact_donor_screening`.
- Existing infectious disease, medical/social history, recovery suitability, QMS deviation, CAPA, and release context consumed by the existing engine.
- Existing clinical workflow commit guard and append-only workflow audit writer.

Implemented screening foundation:

- Persistent clinical screening entities:
  - `operational.clinical_screening_sessions`
  - `operational.clinical_screening_answers`
  - `operational.clinical_screening_vitals`
  - `operational.clinical_screening_outcomes`
  - `operational.clinical_deferrals`
  - `operational.clinical_screening_status_history`
- Alembic migration `202606120003_clinical_screening`.
- Screening RBAC permissions:
  - `screening.read`
  - `screening.manage`
  - `screening.override`
- Backend `/api/clinical/screening` endpoints:
  - `GET /api/clinical/screening/sessions`
  - `GET /api/clinical/screening/sessions/{session_id}`
  - `POST /api/clinical/screening/sessions/preview`
  - `POST /api/clinical/screening/sessions`
  - `POST /api/clinical/screening/sessions/{session_id}/questionnaire/preview`
  - `POST /api/clinical/screening/sessions/{session_id}/questionnaire`
  - `POST /api/clinical/screening/sessions/{session_id}/vitals/preview`
  - `POST /api/clinical/screening/sessions/{session_id}/vitals`
  - `POST /api/clinical/screening/sessions/{session_id}/eligibility/preview`
  - `POST /api/clinical/screening/sessions/{session_id}/result`
  - `POST /api/clinical/screening/sessions/{session_id}/override/preview`
  - `POST /api/clinical/screening/sessions/{session_id}/override`
  - `GET /api/clinical/screening/deferrals`
  - `GET /api/clinical/screening/templates`
  - `GET /api/clinical/screening/rules`
- Minimal donor screening questionnaire template with required identity, authorization, infectious symptom, transmissible disease, IV drug use, incarceration, travel exposure, and high-risk behavior questions.
- Vitals capture for height, weight, temperature, blood pressure, pulse, respiration rate, oxygen saturation, and notes.
- Eligibility preview returns proposed outcome, blocking issues, warnings, rules evaluated, missing answers, missing vitals, deferral recommendation, supervisor review flag, and existing engine outcome when linked donor context is available.
- Result commits reject missing required questionnaire/vitals data.
- Temporary and permanent deferrals create `clinical_deferrals` records and append deferral audit events.
- Supervisor override requires elevated/internal permission, reason, original outcome, override outcome, and audit.
- Successful commits append workflow operations for:
  - `screening.session_create`
  - `screening.questionnaire_commit`
  - `screening.vitals_commit`
  - `screening.result_commit`
  - `screening.override_commit`
  - `screening.deferral_create`
- Frontend `/clinical/screening` is now an operational screening workspace with queue filters, patient identity summary, appointment context, questionnaire, vitals, eligibility preview, deferrals, override history, recent audit activity, templates/rules, and modal workflows.
- Focused tests cover session preview/commit guard, questionnaire validation/audit, vitals validation/audit, explainable eligibility preview, result commit blocking behavior, eligible result commit, temporary/permanent deferrals, supervisor override, and external partner rejection.

## Sprint 5 Implemented Scope

Sprint 5 implements EMR / Encounters as the clinical documentation foundation linked to Patient / Donor Registration, Scheduling, and Screening.

Implemented encounter foundation:

- Persistent encounter entities:
  - `operational.clinical_encounters`
  - `operational.clinical_encounter_notes`
  - `operational.clinical_note_templates`
  - `operational.clinical_encounter_diagnoses`
  - `operational.clinical_patient_allergies`
  - `operational.clinical_patient_medications`
  - `operational.clinical_encounter_status_history`
- Alembic migration `202606120004_clinical_encounters`.
- Encounter RBAC permissions:
  - `encounters.read`
  - `encounters.manage`
  - `encounters.sign`
- Backend `/api/clinical/encounters` endpoints:
  - `GET /api/clinical/encounters`
  - `GET /api/clinical/encounters/{encounter_id}`
  - `POST /api/clinical/encounters/preview`
  - `POST /api/clinical/encounters`
  - `POST /api/clinical/encounters/{encounter_id}/notes/preview`
  - `POST /api/clinical/encounters/{encounter_id}/notes`
  - `POST /api/clinical/encounters/{encounter_id}/sign/preview`
  - `POST /api/clinical/encounters/{encounter_id}/sign`
  - `POST /api/clinical/encounters/{encounter_id}/amend/preview`
  - `POST /api/clinical/encounters/{encounter_id}/amend`
  - `POST /api/clinical/encounters/{encounter_id}/diagnoses/preview`
  - `POST /api/clinical/encounters/{encounter_id}/diagnoses`
  - `POST /api/clinical/patients/{patient_id}/allergies/preview`
  - `POST /api/clinical/patients/{patient_id}/allergies`
  - `POST /api/clinical/patients/{patient_id}/medications/preview`
  - `POST /api/clinical/patients/{patient_id}/medications`
  - `GET /api/clinical/encounters/templates`
- Encounter creation validates patient context, checked-in appointment context, and optional screening-session linkage before commit.
- Draft notes can be created or updated until signed.
- Signed notes are locked from direct edit.
- Amendments create signed addendum note versions and move the encounter to `amended`.
- Diagnoses/problems, allergies, and medications are append-only operational additions in this sprint.
- Successful commits append workflow operations for:
  - `encounter.create`
  - `encounter.note_save`
  - `encounter.sign`
  - `encounter.amend`
  - `encounter.diagnosis_add`
  - `patient.allergy_add`
  - `patient.medication_add`
- Frontend `/clinical/encounters` is now an operational EMR workspace with worklist filters, patient identity, appointment/screening context, clinical summary, draft note/template workflow, signed-note read-only state, amendment history, diagnoses/problems, allergies, medications, recent status history, and planned downstream Orders/Care Plans/Billing actions.
- Modal workflows follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success.
- Focused tests cover checked-in appointment validation, confirmation header rejection/acceptance, audit creation/append preservation, draft note saving, signing/locking, amendment addenda, diagnosis/allergy/medication commits, and external partner rejection.

## Sprint 6 Implemented Scope

Sprint 6 implements Orders / Results as the first downstream operational module after encounters while preserving the existing donor infectious disease result implementation.

Existing assets reused:

- Existing infectious disease catalog/result facts remain in place:
  - `operational.dim_infectious_disease_test`
  - `operational.fact_infectious_disease_result`
- Infectious disease order catalog entries reference those existing donor eligibility assets and do not replace or rewrite donor eligibility logic.
- Existing clinical workflow commit guard and append-only workflow audit writer are reused.

Implemented orders/results foundation:

- Persistent orders/results entities:
  - `operational.clinical_order_catalog_items`
  - `operational.clinical_orders`
  - `operational.clinical_order_results`
  - `operational.clinical_order_result_acknowledgements`
  - `operational.clinical_order_status_history`
- Alembic migration `202606120005_clinical_orders`.
- Orders RBAC permissions:
  - `orders.read`
  - `orders.manage`
  - `orders.acknowledge`
- Backend `/api/clinical/orders` endpoints:
  - `GET /api/clinical/orders`
  - `GET /api/clinical/orders/{order_id}`
  - `GET /api/clinical/orders/catalog`
  - `POST /api/clinical/orders/preview`
  - `POST /api/clinical/orders`
  - `POST /api/clinical/orders/{order_id}/results/preview`
  - `POST /api/clinical/orders/{order_id}/results`
  - `POST /api/clinical/orders/{order_id}/acknowledge/preview`
  - `POST /api/clinical/orders/{order_id}/acknowledge`
  - `POST /api/clinical/orders/{order_id}/cancel/preview`
  - `POST /api/clinical/orders/{order_id}/cancel`
- Supported order statuses:
  - `draft`
  - `ordered`
  - `in_progress`
  - `resulted`
  - `cancelled`
- Order creation links to patient/donor, optional appointment, screening session, and encounter context.
- Result entry supports normal, abnormal, critical, corrected, and cancelled statuses.
- Critical results remain visibly unacknowledged until acknowledgement is committed.
- Cancelled orders reject new result entry and preserve cancellation reason/status history.
- Successful commits append workflow operations for:
  - `order.create`
  - `order.result_add`
  - `order.result_correct`
  - `order.acknowledge`
  - `order.cancel`
- Frontend `/clinical/orders` is now an operational orders/results workspace with worklist filters, patient identity, encounter/screening/appointment context, catalog selector, result entry, correction history, critical/abnormal indicators, acknowledgement state, cancellation workflow, recent status/audit activity, and planned downstream Care Plans/Billing actions.
- Modal workflows follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success.
- Focused tests cover catalog access, patient/encounter linkage validation, missing/invalid/valid confirmation headers, audit creation and append preservation, cancelled-order result blocking, critical result acknowledgement, cancellation reason/audit behavior, and external partner mutation rejection.

## Sprint 7 Implemented Scope

Sprint 7 implements Care Plans / Case Management as the operational coordination layer linked to Patient / Donor Registration, Screening, Encounters, and Orders / Results.

Implemented care plan foundation:

- Persistent care plan entities:
  - `operational.clinical_care_plans`
  - `operational.clinical_care_plan_goals`
  - `operational.clinical_care_plan_interventions`
  - `operational.clinical_care_plan_tasks`
  - `operational.clinical_care_plan_progress_notes`
  - `operational.clinical_care_plan_team_members`
  - `operational.clinical_care_plan_status_history`
- Alembic migration `202606120006_clinical_care_plans`.
- Care Plans RBAC permissions:
  - `care_plans.read`
  - `care_plans.manage`
  - `care_plans.close`
- Backend `/api/clinical/care-plans` endpoints:
  - `GET /api/clinical/care-plans`
  - `GET /api/clinical/care-plans/{care_plan_id}`
  - `POST /api/clinical/care-plans/preview`
  - `POST /api/clinical/care-plans`
  - `POST /api/clinical/care-plans/{care_plan_id}/goals/preview`
  - `POST /api/clinical/care-plans/{care_plan_id}/goals`
  - `POST /api/clinical/care-plans/{care_plan_id}/interventions/preview`
  - `POST /api/clinical/care-plans/{care_plan_id}/interventions`
  - `POST /api/clinical/care-plans/{care_plan_id}/tasks/preview`
  - `POST /api/clinical/care-plans/{care_plan_id}/tasks`
  - `POST /api/clinical/care-plans/{care_plan_id}/progress/preview`
  - `POST /api/clinical/care-plans/{care_plan_id}/progress`
  - `POST /api/clinical/care-plans/{care_plan_id}/close/preview`
  - `POST /api/clinical/care-plans/{care_plan_id}/close`
- Supported care plan statuses:
  - `draft`
  - `active`
  - `on_hold`
  - `completed`
  - `cancelled`
  - `closed`
- Care plan creation validates patient, encounter, screening session, order, and order result linkage before commit.
- Linked abnormal and critical order results remain visible in preview, list filters, and detail context, including unacknowledged critical result warnings.
- Goals, interventions, tasks, progress notes, team members, and status history are stored as reusable case-management records.
- Tasks require owner and due date; tasks committed as completed capture completion timestamp and actor.
- Progress notes append to the timeline and can move care plans between `draft`, `active`, and `on_hold`.
- Closure requires outcome summary and closure reason, moves the plan to `closed`, records closure actor/time, and blocks later goals, interventions, tasks, or progress.
- Successful commits append workflow operations for:
  - `care_plan.create`
  - `care_plan.goal_add`
  - `care_plan.intervention_add`
  - `care_plan.task_add`
  - `care_plan.progress_add`
  - `care_plan.close`
- Frontend `/clinical/care-plans` is now an operational case-management workspace with worklist filters, status and priority chips, patient/encounter/screening/order-result context, critical/abnormal indicators, goals, interventions, tasks, team, progress, closure details, status history, and planned downstream Billing handoff.
- Modal workflows follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success.
- Focused tests cover patient/context validation, missing/invalid/valid confirmation headers, audit file creation and append preservation, goals/interventions/tasks, progress timeline/status update, closure requirements/blocking behavior, and external partner mutation rejection.

## Sprint 8 Implemented Scope

Sprint 8 implements Billing / Insurance as the revenue-cycle foundation linked to Patient / Donor Registration, Encounters, Orders / Results, and Care Plans.

Implemented billing foundation:

- Persistent billing entities:
  - `operational.clinical_billing_accounts`
  - `operational.clinical_insurance_verifications`
  - `operational.clinical_charges`
  - `operational.clinical_claims`
  - `operational.clinical_claim_lines`
  - `operational.clinical_payments`
  - `operational.clinical_denials`
  - `operational.clinical_billing_status_history`
- Alembic migration `202606120007_clinical_billing`.
- Billing RBAC permissions:
  - `billing.read`
  - `billing.manage`
  - `billing.payment_post`
- Backend `/api/clinical/billing` endpoints:
  - `GET /api/clinical/billing/accounts`
  - `GET /api/clinical/billing/accounts/{account_id}`
  - `GET /api/clinical/billing/charges`
  - `POST /api/clinical/billing/charges/preview`
  - `POST /api/clinical/billing/charges`
  - `GET /api/clinical/billing/claims`
  - `GET /api/clinical/billing/claims/{claim_id}`
  - `POST /api/clinical/billing/claims/preview`
  - `POST /api/clinical/billing/claims`
  - `POST /api/clinical/billing/payments/preview`
  - `POST /api/clinical/billing/payments`
  - `POST /api/clinical/billing/denials/preview`
  - `POST /api/clinical/billing/denials`
  - `POST /api/clinical/billing/insurance-verifications/preview`
  - `POST /api/clinical/billing/insurance-verifications`
  - `GET /api/clinical/billing/work-queue`
- Billing accounts link to canonical patient records and are created automatically on first charge when no account exists.
- Patient insurance records from registration are reused for insurance verification and claim payer context.
- Charge capture validates linked encounter, order, order result, care plan, and care plan task context belongs to the same patient before commit.
- Claim preview rejects voided/cancelled charges, returns payer/patient/line item totals, and claim commit generates claim lines from selected charges.
- Payment posting updates claim paid amount, adjustment amount, balance, status, and account totals.
- Partial payments leave claims `partially_paid`; full payments mark claims `paid` and record closure fields.
- Denial capture records open rework items, can link to claim lines, moves claims to `denied`, and surfaces denials in the billing work queue.
- Successful commits append workflow operations for:
  - `billing.insurance_verify`
  - `billing.charge_capture`
  - `billing.claim_create`
  - `billing.payment_post`
  - `billing.denial_capture`
- Frontend `/clinical/billing` is now an operational billing workspace with work queue filters, account summary, charges, claims, payments, denial/rework, insurance verification, status chips, balance cards, modal workflows, and planned Quality/Reporting handoffs.
- Modal workflows follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success.
- Focused tests cover insurance verification validation/commit/audit, charge context validation and account creation/reuse, claim totals and claim lines, payment balance/status behavior, denial capture/work queue behavior, and external partner mutation rejection.

## Future Sprint Sequence

1. Quality / Compliance: quality events, adverse events, CAPA lifecycle, audit viewer, compliance export, and closure approval.
2. Clinical Administration: versioned templates, rules, catalogs, approval paths, and admin preview/commit.
3. Reporting / Analytics: operational reports, filters, exports, and analytics-ready views.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```
