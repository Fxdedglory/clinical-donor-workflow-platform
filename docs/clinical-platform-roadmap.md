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
| Quality / Compliance | Sprint 9 adds patient-linked quality events, adverse events, investigations, CAPA/deviation linkage, closure approval, audit evidence, compliance export, RBAC, tests, and an operational UI. Sprint 10 adds admin-managed quality categories and approval paths. | Add investigation templates, external response routing, and report-ready compliance packages. |
| Reporting / Analytics | Sprint 11 adds clinical module reports, aggregate dashboard metrics, date/status/entity/audit filters, analytics export preview/commit, RBAC, tests, and an operational UI. | Add external warehouse delivery, analytics marts/views, BI semantic models, FHIR/HL7 extracts, signed report packages, and retention policy automation. |
| Clinical Administration | Sprint 10 adds versioned clinical templates, appointment types, provider schedule templates, screening and deferral rules, note templates, order catalogs, billing code lists, quality categories, approval paths, notification templates, RBAC overview, tests, and an operational UI. | Add advanced approval execution, notification delivery, recurring schedule engines, and production policy review workflows. |
| Audit / Workflow Operations | Database audit, transition history, and append-only workflow operation audit exist across clinical modules. | Add retention policy, export signing, and report packaging controls. |

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

## Sprint 9 Implemented Scope

Sprint 9 implements Quality / Compliance as the clinical quality foundation while preserving the existing donor QMS, deviation, and CAPA assets.

Implemented quality/compliance foundation:

- Existing QMS/CAPA/deviation assets reused:
  - `operational.fact_deviation`
  - `operational.fact_capa`
  - existing audit and workflow operation helpers
- Persistent quality entities:
  - `operational.clinical_quality_events`
  - `operational.clinical_adverse_events`
  - `operational.clinical_quality_event_links`
  - `operational.clinical_quality_investigations`
  - `operational.clinical_quality_approvals`
  - `operational.clinical_compliance_exports`
  - `operational.clinical_quality_status_history`
- Alembic migration `202606120008_clinical_quality`.
- Quality RBAC permissions:
  - `quality.read`
  - `quality.manage`
  - `quality.close`
  - `quality.export`
- Backend `/api/clinical/quality` endpoints:
  - `GET /api/clinical/quality/events`
  - `GET /api/clinical/quality/events/{event_id}`
  - `POST /api/clinical/quality/events/preview`
  - `POST /api/clinical/quality/events`
  - `POST /api/clinical/quality/events/{event_id}/investigation/preview`
  - `POST /api/clinical/quality/events/{event_id}/investigation`
  - `POST /api/clinical/quality/events/{event_id}/capa/preview`
  - `POST /api/clinical/quality/events/{event_id}/capa`
  - `POST /api/clinical/quality/events/{event_id}/close/preview`
  - `POST /api/clinical/quality/events/{event_id}/close`
  - `GET /api/clinical/quality/adverse-events`
  - `POST /api/clinical/quality/adverse-events/preview`
  - `POST /api/clinical/quality/adverse-events`
  - `GET /api/clinical/quality/audit-evidence`
  - `GET /api/clinical/quality/compliance-exports`
  - `POST /api/clinical/quality/compliance-exports/preview`
  - `POST /api/clinical/quality/compliance-exports`
  - `GET /api/clinical/quality/dashboard`
- Quality events capture category, severity, status, owner, due date, source module, description, and linked clinical context across patient, appointment, screening, encounter, order/result, care plan, charge, claim, payment, denial, deviation, and CAPA.
- Adverse events link to a patient and may link to screening, encounter, order/result, care plan, and quality event context; severe and critical events produce investigation/supervisor review warnings.
- Investigation commits append notes/evidence and status history without overwriting prior investigation records.
- CAPA workflow can link an existing `fact_capa` record or create a planned CAPA link without redesigning the existing QMS CAPA model.
- Closure requires resolution summary and closure reason, records approval, moves the event to `closed`, and blocks further investigation/CAPA/closure mutations.
- Compliance export preview summarizes workflow operation evidence and quality status history; commit persists an export record without external regulator submission.
- Successful commits append workflow operations for:
  - `quality.event_create`
  - `quality.adverse_event_create`
  - `quality.investigation_add`
  - `quality.capa_link`
  - `quality.event_close`
  - `quality.compliance_export`
- Frontend `/clinical/quality` is now an operational quality workspace with dashboard cards, quality event worklist, adverse event worklist, filters, linked context, investigation timeline, status history, CAPA/deviation links, audit evidence, compliance exports, and Administration/Reports handoffs.
- Modal workflows follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success.
- Focused tests cover link validation, missing/invalid/valid confirmation headers, audit file creation, audit append preservation, adverse event warnings/commit, investigation append, closed mutation block, CAPA reuse, closure approval, compliance export preview/commit/audit evidence, and external partner mutation rejection.

## Sprint 10 Implemented Scope

Sprint 10 implements Clinical Administration as the configuration-management foundation for clinical workflows while preserving existing donor, QMS, CAPA, deviation, scheduling, encounter, orders, billing, and quality modules.

Implemented administration foundation:

- Existing clinical configuration reused:
  - `operational.appointment_types`
  - `operational.clinical_providers`
  - `operational.clinical_note_templates`
  - `operational.clinical_order_catalog_items`
  - existing RBAC roles and permissions
  - existing QMS/CAPA/deviation records
- Persistent administration entities:
  - `operational.clinical_admin_config_versions`
  - `operational.clinical_admin_approval_paths`
  - `operational.clinical_admin_approval_steps`
  - `operational.clinical_notification_templates`
  - `operational.clinical_provider_schedule_templates`
  - `operational.clinical_screening_template_versions`
  - `operational.clinical_eligibility_rule_versions`
  - `operational.clinical_deferral_rule_versions`
  - `operational.clinical_billing_code_catalog`
  - `operational.clinical_quality_categories`
  - `operational.clinical_quality_severity_matrix`
  - `operational.clinical_admin_status_history`
- Alembic migration `202606120009_clinical_admin`.
- Clinical Administration RBAC permissions:
  - `clinical_admin.read`
  - `clinical_admin.manage`
- Backend `/api/clinical/admin` endpoints:
  - `GET /api/clinical/admin/dashboard`
  - `GET /api/clinical/admin/config-versions`
  - `GET /api/clinical/admin/appointment-types`
  - `POST /api/clinical/admin/appointment-types/preview`
  - `POST /api/clinical/admin/appointment-types`
  - `GET /api/clinical/admin/provider-schedules`
  - `POST /api/clinical/admin/provider-schedules/preview`
  - `POST /api/clinical/admin/provider-schedules`
  - `GET /api/clinical/admin/screening-templates`
  - `POST /api/clinical/admin/screening-templates/preview`
  - `POST /api/clinical/admin/screening-templates`
  - `GET /api/clinical/admin/eligibility-rules`
  - `POST /api/clinical/admin/eligibility-rules/preview`
  - `POST /api/clinical/admin/eligibility-rules`
  - `GET /api/clinical/admin/deferral-rules`
  - `POST /api/clinical/admin/deferral-rules/preview`
  - `POST /api/clinical/admin/deferral-rules`
  - `GET /api/clinical/admin/note-templates`
  - `POST /api/clinical/admin/note-templates/preview`
  - `POST /api/clinical/admin/note-templates`
  - `GET /api/clinical/admin/order-catalog`
  - `POST /api/clinical/admin/order-catalog/preview`
  - `POST /api/clinical/admin/order-catalog`
  - `GET /api/clinical/admin/billing-codes`
  - `POST /api/clinical/admin/billing-codes/preview`
  - `POST /api/clinical/admin/billing-codes`
  - `GET /api/clinical/admin/quality-categories`
  - `POST /api/clinical/admin/quality-categories/preview`
  - `POST /api/clinical/admin/quality-categories`
  - `GET /api/clinical/admin/approval-paths`
  - `POST /api/clinical/admin/approval-paths/preview`
  - `POST /api/clinical/admin/approval-paths`
  - `GET /api/clinical/admin/notification-templates`
  - `POST /api/clinical/admin/notification-templates/preview`
  - `POST /api/clinical/admin/notification-templates`
  - `GET /api/clinical/admin/rbac`
- Every mutating endpoint requires authenticated internal administration permissions and `X-Confirm-Generation: true`.
- External partner and supplier users are rejected from Clinical Administration mutation.
- Preview responses compare current and proposed configuration, list changed fields, warnings, blocking issues, affected downstream modules, and the commit guard.
- Commit responses create version history records, append administration status history when status changes, and write workflow operation audit entries for:
  - `admin.appointment_type_upsert`
  - `admin.provider_schedule_upsert`
  - `admin.screening_template_version`
  - `admin.eligibility_rule_version`
  - `admin.deferral_rule_version`
  - `admin.note_template_upsert`
  - `admin.order_catalog_upsert`
  - `admin.billing_code_upsert`
  - `admin.quality_category_upsert`
  - `admin.approval_path_upsert`
  - `admin.notification_template_upsert`
- Screening template, eligibility rule, deferral rule, and approval path commits create new versions while preserving prior records.
- Appointment types, note templates, order catalog items, billing codes, quality categories, provider schedule templates, and notification templates retain historical snapshots through `clinical_admin_config_versions`.
- Frontend `/clinical/admin` is now an operational workspace with dashboard cards, config version history, appointment types, provider schedules, screening templates, eligibility rules, deferral rules, note templates, order catalog, billing codes, quality categories, approval paths, notification templates, RBAC overview, filters, loading/error/empty states, and modal workflows.
- Modal workflows follow Form -> Validation Summary -> Preview -> Commit Confirmation -> Success.
- Focused tests cover missing/invalid/valid confirmation headers, audit file creation, audit append preservation, every admin preview/commit/audit workflow, version preservation, config history/dashboard/RBAC, and external partner mutation rejection.

## Sprint 11 Implemented Scope

Sprint 11 implements Reporting / Analytics Readiness as an aggregate clinical reporting foundation across Patient / Donor Registration, Scheduling, Screening, Encounters, Orders / Results, Care Plans, Billing, Quality, Administration, and workflow audit activity.

Implemented reporting foundation:

- Persistent reporting entities:
  - `operational.clinical_report_exports`
  - `operational.clinical_report_export_items`
  - `operational.clinical_report_status_history`
- Alembic migration `202606120010_clinical_reports`.
- Reporting RBAC permissions:
  - `reports.read`
  - `reports.export`
- Backend `/api/clinical/reports` endpoints:
  - `GET /api/clinical/reports/dashboard`
  - `GET /api/clinical/reports/patient-throughput`
  - `GET /api/clinical/reports/scheduling-utilization`
  - `GET /api/clinical/reports/screening-outcomes`
  - `GET /api/clinical/reports/deferrals`
  - `GET /api/clinical/reports/encounter-volume`
  - `GET /api/clinical/reports/orders-results`
  - `GET /api/clinical/reports/care-plan-aging`
  - `GET /api/clinical/reports/billing-work-queue`
  - `GET /api/clinical/reports/quality-trends`
  - `GET /api/clinical/reports/audit-activity`
  - `GET /api/clinical/reports/analytics-exports`
  - `POST /api/clinical/reports/analytics-exports/preview`
  - `POST /api/clinical/reports/analytics-exports`
- Report filters support date range, status, audit module, workflow, actor, entity type, and entity ID where applicable.
- Report responses use reusable metric cards, warnings, series points, row counts, and blocking issue schemas.
- Analytics export preview returns module row counts, preview hash, warnings, blocking issues, and the required `X-Confirm-Generation: true` commit guard.
- Analytics export commit persists export metadata, export items, status history, and workflow audit entries for `reports.analytics_export`.
- External partner and supplier users are rejected from analytics export generation.
- Frontend `/clinical/reports` is now an operational reporting workspace with aggregate cards, filters, report panels for each module, recent audit activity, analytics export history, export preview/commit modal, and planned BI/FHIR/retention handoffs.
- The clinical module inventory now marks Reports as active and lists the Sprint 11 reporting workflows.
- Focused tests cover report endpoint loading, export preview row counts, missing/invalid/valid confirmation headers, audit file creation, audit append preservation, persisted export metadata, and external partner export rejection.

Post-RC-04 hardening:

- Added route-permission drift tests that enumerate live `/api/clinical` FastAPI routes and require sensitive routes to remain documented and classified.
- Added small-cell suppression for aggregate report count cells and analytics export row counts under safe export profiles.
- Added suppression metadata to report/export responses and analytics export workflow audit changes.

## Future Sprint Sequence

1. Advanced workflow execution: approval execution, notification delivery, recurrence engines, escalation actions, and production policy review queues.
2. Analytics delivery hardening: warehouse delivery, materialized marts/views, BI semantic models, FHIR/HL7 extracts, governed external analytics packaging, and compliance signoff for suppression thresholds.
3. External compliance packages: retention policy automation, export signing, external response routing, and regulator-ready submission workflows.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```
