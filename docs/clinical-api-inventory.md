# Clinical API Inventory

RC0 inventory date: 2026-06-12

Scope: clinical platform routes registered under `/api/clinical`. Donor/QMS legacy routes outside this namespace remain in their existing docs and tests.

## Summary

| Module | Namespace | Router File | Notes |
| --- | --- | --- | --- |
| Clinical Foundation | `/api/clinical` | `backend/app/routes/clinical.py` | Module inventory and generic preview/commit audit foundation. |
| Patients / Donors | `/api/clinical/patients` | `backend/app/routes/clinical_patients.py` | Registration, demographics, contacts, insurance, consent. |
| Scheduling | `/api/clinical/scheduling` | `backend/app/routes/clinical_scheduling.py` | Appointment lifecycle and resources. |
| Screening / Eligibility | `/api/clinical/screening` | `backend/app/routes/clinical_screening.py` | Screening sessions, questionnaire, vitals, result, override, deferrals. |
| Encounters | `/api/clinical/encounters` and `/api/clinical/patients/...` | `backend/app/routes/clinical_encounters.py` | Router prefix is `/api/clinical`; endpoints include encounter and patient allergy/medication paths. |
| Orders / Results | `/api/clinical/orders` | `backend/app/routes/clinical_orders.py` | Orders, result entry/correction, acknowledgement, cancellation. |
| Care Plans | `/api/clinical/care-plans` | `backend/app/routes/clinical_care_plans.py` | Care plans, goals, interventions, tasks, progress, closure. |
| Billing / Insurance | `/api/clinical/billing` | `backend/app/routes/clinical_billing.py` | Accounts, charges, claims, payments, denials, insurance verification. |
| Quality / Compliance | `/api/clinical/quality` | `backend/app/routes/clinical_quality.py` | Quality events, adverse events, investigation, CAPA, closure, audit evidence, compliance exports. |
| Reports | `/api/clinical/reports` | `backend/app/routes/clinical_reports.py` | Aggregate reports and analytics export preview/commit. |
| Clinical Admin | `/api/clinical/admin` | `backend/app/routes/clinical_admin.py` | Versioned configuration, RBAC overview, templates, catalogs, approval paths, notifications. |

## Inventory Rules

- `Preview required` means the workflow has an explicit preview endpoint or expected preview step.
- `Commit guarded` means durable mutation requires `X-Confirm-Generation: true`.
- Read-only `GET` endpoints do not require preview or the confirmation header.
- Audit workflow event names are recorded in `metadata/workflow_operations.json` on successful commit.

## Foundation

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/status` | No | No | None |
| GET | `/api/clinical/modules` | No | No | None |
| POST | `/api/clinical/workflows/preview` | Yes | No | None |
| POST | `/api/clinical/workflows/commit` | Yes | Yes | Caller-supplied workflow |

## Patients / Donors

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/patients` | No | No | None |
| POST | `/api/clinical/patients/preview` | Yes | No | None |
| POST | `/api/clinical/patients` | Yes | Yes | `patient.create` |
| GET | `/api/clinical/patients/{patient_id}` | No | No | None |
| POST | `/api/clinical/patients/{patient_id}/edit/preview` | Yes | No | None |
| PATCH | `/api/clinical/patients/{patient_id}` | Yes | Yes | `patient.update_demographics` |
| POST | `/api/clinical/patients/{patient_id}/contacts/preview` | Yes | No | None |
| POST | `/api/clinical/patients/{patient_id}/contacts` | Yes | Yes | `patient.add_contact` |
| POST | `/api/clinical/patients/{patient_id}/insurance/preview` | Yes | No | None |
| POST | `/api/clinical/patients/{patient_id}/insurance` | Yes | Yes | `patient.add_insurance` |
| POST | `/api/clinical/patients/{patient_id}/consents/preview` | Yes | No | None |
| POST | `/api/clinical/patients/{patient_id}/consents` | Yes | Yes | `patient.capture_consent` |

## Scheduling

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/scheduling/appointments` | No | No | None |
| GET | `/api/clinical/scheduling/appointments/{appointment_id}` | No | No | None |
| POST | `/api/clinical/scheduling/appointments/preview` | Yes | No | None |
| POST | `/api/clinical/scheduling/appointments` | Yes | Yes | `appointment.book` |
| POST | `/api/clinical/scheduling/{appointment_id}/reschedule/preview` | Yes | No | None |
| POST | `/api/clinical/scheduling/{appointment_id}/reschedule` | Yes | Yes | `appointment.reschedule` |
| POST | `/api/clinical/scheduling/{appointment_id}/cancel/preview` | Yes | No | None |
| POST | `/api/clinical/scheduling/{appointment_id}/cancel` | Yes | Yes | `appointment.cancel` |
| POST | `/api/clinical/scheduling/{appointment_id}/check-in/preview` | Yes | No | None |
| POST | `/api/clinical/scheduling/{appointment_id}/check-in` | Yes | Yes | `appointment.check_in` |
| POST | `/api/clinical/scheduling/{appointment_id}/no-show/preview` | Yes | No | None |
| POST | `/api/clinical/scheduling/{appointment_id}/no-show` | Yes | Yes | `appointment.no_show` |
| GET | `/api/clinical/scheduling/resources` | No | No | None |
| GET | `/api/clinical/scheduling/appointment-types` | No | No | None |

## Screening / Eligibility

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/screening/sessions` | No | No | None |
| GET | `/api/clinical/screening/sessions/{session_id}` | No | No | None |
| POST | `/api/clinical/screening/sessions/preview` | Yes | No | None |
| POST | `/api/clinical/screening/sessions` | Yes | Yes | `screening.session_create` |
| POST | `/api/clinical/screening/sessions/{session_id}/questionnaire/preview` | Yes | No | None |
| POST | `/api/clinical/screening/sessions/{session_id}/questionnaire` | Yes | Yes | `screening.questionnaire_commit` |
| POST | `/api/clinical/screening/sessions/{session_id}/vitals/preview` | Yes | No | None |
| POST | `/api/clinical/screening/sessions/{session_id}/vitals` | Yes | Yes | `screening.vitals_commit` |
| POST | `/api/clinical/screening/sessions/{session_id}/eligibility/preview` | Yes | No | None |
| POST | `/api/clinical/screening/sessions/{session_id}/result` | Yes | Yes | `screening.result_commit`; `screening.deferral_create` when applicable |
| POST | `/api/clinical/screening/sessions/{session_id}/override/preview` | Yes | No | None |
| POST | `/api/clinical/screening/sessions/{session_id}/override` | Yes | Yes | `screening.override_commit`; `screening.deferral_create` when applicable |
| GET | `/api/clinical/screening/deferrals` | No | No | None |
| GET | `/api/clinical/screening/templates` | No | No | None |
| GET | `/api/clinical/screening/rules` | No | No | None |

## Encounters

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/encounters` | No | No | None |
| GET | `/api/clinical/encounters/templates` | No | No | None |
| GET | `/api/clinical/encounters/{encounter_id}` | No | No | None |
| POST | `/api/clinical/encounters/preview` | Yes | No | None |
| POST | `/api/clinical/encounters` | Yes | Yes | `encounter.create` |
| POST | `/api/clinical/encounters/{encounter_id}/notes/preview` | Yes | No | None |
| POST | `/api/clinical/encounters/{encounter_id}/notes` | Yes | Yes | `encounter.note_save` |
| POST | `/api/clinical/encounters/{encounter_id}/sign/preview` | Yes | No | None |
| POST | `/api/clinical/encounters/{encounter_id}/sign` | Yes | Yes | `encounter.sign` |
| POST | `/api/clinical/encounters/{encounter_id}/amend/preview` | Yes | No | None |
| POST | `/api/clinical/encounters/{encounter_id}/amend` | Yes | Yes | `encounter.amend` |
| POST | `/api/clinical/encounters/{encounter_id}/diagnoses/preview` | Yes | No | None |
| POST | `/api/clinical/encounters/{encounter_id}/diagnoses` | Yes | Yes | `encounter.diagnosis_add` |
| POST | `/api/clinical/patients/{patient_id}/allergies/preview` | Yes | No | None |
| POST | `/api/clinical/patients/{patient_id}/allergies` | Yes | Yes | `patient.allergy_add` |
| POST | `/api/clinical/patients/{patient_id}/medications/preview` | Yes | No | None |
| POST | `/api/clinical/patients/{patient_id}/medications` | Yes | Yes | `patient.medication_add` |

## Orders / Results

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/orders` | No | No | None |
| GET | `/api/clinical/orders/catalog` | No | No | None |
| GET | `/api/clinical/orders/{order_id}` | No | No | None |
| POST | `/api/clinical/orders/preview` | Yes | No | None |
| POST | `/api/clinical/orders` | Yes | Yes | `order.create` |
| POST | `/api/clinical/orders/{order_id}/results/preview` | Yes | No | None |
| POST | `/api/clinical/orders/{order_id}/results` | Yes | Yes | `order.result_add` or `order.result_correct` |
| POST | `/api/clinical/orders/{order_id}/acknowledge/preview` | Yes | No | None |
| POST | `/api/clinical/orders/{order_id}/acknowledge` | Yes | Yes | `order.acknowledge` |
| POST | `/api/clinical/orders/{order_id}/cancel/preview` | Yes | No | None |
| POST | `/api/clinical/orders/{order_id}/cancel` | Yes | Yes | `order.cancel` |

## Care Plans

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/care-plans` | No | No | None |
| GET | `/api/clinical/care-plans/{care_plan_id}` | No | No | None |
| POST | `/api/clinical/care-plans/preview` | Yes | No | None |
| POST | `/api/clinical/care-plans` | Yes | Yes | `care_plan.create` |
| POST | `/api/clinical/care-plans/{care_plan_id}/goals/preview` | Yes | No | None |
| POST | `/api/clinical/care-plans/{care_plan_id}/goals` | Yes | Yes | `care_plan.goal_add` |
| POST | `/api/clinical/care-plans/{care_plan_id}/interventions/preview` | Yes | No | None |
| POST | `/api/clinical/care-plans/{care_plan_id}/interventions` | Yes | Yes | `care_plan.intervention_add` |
| POST | `/api/clinical/care-plans/{care_plan_id}/tasks/preview` | Yes | No | None |
| POST | `/api/clinical/care-plans/{care_plan_id}/tasks` | Yes | Yes | `care_plan.task_add` |
| POST | `/api/clinical/care-plans/{care_plan_id}/progress/preview` | Yes | No | None |
| POST | `/api/clinical/care-plans/{care_plan_id}/progress` | Yes | Yes | `care_plan.progress_add` |
| POST | `/api/clinical/care-plans/{care_plan_id}/close/preview` | Yes | No | None |
| POST | `/api/clinical/care-plans/{care_plan_id}/close` | Yes | Yes | `care_plan.close` |

## Billing / Insurance

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/billing/accounts` | No | No | None |
| GET | `/api/clinical/billing/accounts/{account_id}` | No | No | None |
| GET | `/api/clinical/billing/charges` | No | No | None |
| POST | `/api/clinical/billing/charges/preview` | Yes | No | None |
| POST | `/api/clinical/billing/charges` | Yes | Yes | `billing.charge_capture` |
| GET | `/api/clinical/billing/claims` | No | No | None |
| GET | `/api/clinical/billing/claims/{claim_id}` | No | No | None |
| POST | `/api/clinical/billing/claims/preview` | Yes | No | None |
| POST | `/api/clinical/billing/claims` | Yes | Yes | `billing.claim_create` |
| POST | `/api/clinical/billing/payments/preview` | Yes | No | None |
| POST | `/api/clinical/billing/payments` | Yes | Yes | `billing.payment_post` |
| POST | `/api/clinical/billing/denials/preview` | Yes | No | None |
| POST | `/api/clinical/billing/denials` | Yes | Yes | `billing.denial_capture` |
| POST | `/api/clinical/billing/insurance-verifications/preview` | Yes | No | None |
| POST | `/api/clinical/billing/insurance-verifications` | Yes | Yes | `billing.insurance_verify` |
| GET | `/api/clinical/billing/work-queue` | No | No | None |

## Quality / Compliance

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/quality/events` | No | No | None |
| GET | `/api/clinical/quality/events/{event_id}` | No | No | None |
| POST | `/api/clinical/quality/events/preview` | Yes | No | None |
| POST | `/api/clinical/quality/events` | Yes | Yes | `quality.event_create` |
| POST | `/api/clinical/quality/events/{event_id}/investigation/preview` | Yes | No | None |
| POST | `/api/clinical/quality/events/{event_id}/investigation` | Yes | Yes | `quality.investigation_add` |
| POST | `/api/clinical/quality/events/{event_id}/capa/preview` | Yes | No | None |
| POST | `/api/clinical/quality/events/{event_id}/capa` | Yes | Yes | `quality.capa_link` |
| POST | `/api/clinical/quality/events/{event_id}/close/preview` | Yes | No | None |
| POST | `/api/clinical/quality/events/{event_id}/close` | Yes | Yes | `quality.event_close` |
| GET | `/api/clinical/quality/adverse-events` | No | No | None |
| POST | `/api/clinical/quality/adverse-events/preview` | Yes | No | None |
| POST | `/api/clinical/quality/adverse-events` | Yes | Yes | `quality.adverse_event_create` |
| GET | `/api/clinical/quality/audit-evidence` | No | No | None |
| GET | `/api/clinical/quality/compliance-exports` | No | No | None |
| POST | `/api/clinical/quality/compliance-exports/preview` | Yes | No | None |
| POST | `/api/clinical/quality/compliance-exports` | Yes | Yes | `quality.compliance_export` |
| GET | `/api/clinical/quality/dashboard` | No | No | None |

## Reports

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/reports/dashboard` | No | No | None |
| GET | `/api/clinical/reports/patient-throughput` | No | No | None |
| GET | `/api/clinical/reports/scheduling-utilization` | No | No | None |
| GET | `/api/clinical/reports/screening-outcomes` | No | No | None |
| GET | `/api/clinical/reports/deferrals` | No | No | None |
| GET | `/api/clinical/reports/encounter-volume` | No | No | None |
| GET | `/api/clinical/reports/orders-results` | No | No | None |
| GET | `/api/clinical/reports/care-plan-aging` | No | No | None |
| GET | `/api/clinical/reports/billing-work-queue` | No | No | None |
| GET | `/api/clinical/reports/quality-trends` | No | No | None |
| GET | `/api/clinical/reports/audit-activity` | No | No | None |
| GET | `/api/clinical/reports/analytics-exports` | No | No | None |
| POST | `/api/clinical/reports/analytics-exports/preview` | Yes | No | None |
| POST | `/api/clinical/reports/analytics-exports` | Yes | Yes | `reports.analytics_export` |

## Clinical Administration

| Method | Endpoint | Preview Required | Commit Guarded | Audit Workflow |
| --- | --- | --- | --- | --- |
| GET | `/api/clinical/admin/dashboard` | No | No | None |
| GET | `/api/clinical/admin/config-versions` | No | No | None |
| GET | `/api/clinical/admin/appointment-types` | No | No | None |
| POST | `/api/clinical/admin/appointment-types/preview` | Yes | No | None |
| POST | `/api/clinical/admin/appointment-types` | Yes | Yes | `admin.appointment_type_upsert` |
| GET | `/api/clinical/admin/provider-schedules` | No | No | None |
| POST | `/api/clinical/admin/provider-schedules/preview` | Yes | No | None |
| POST | `/api/clinical/admin/provider-schedules` | Yes | Yes | `admin.provider_schedule_upsert` |
| GET | `/api/clinical/admin/screening-templates` | No | No | None |
| POST | `/api/clinical/admin/screening-templates/preview` | Yes | No | None |
| POST | `/api/clinical/admin/screening-templates` | Yes | Yes | `admin.screening_template_version` |
| GET | `/api/clinical/admin/eligibility-rules` | No | No | None |
| POST | `/api/clinical/admin/eligibility-rules/preview` | Yes | No | None |
| POST | `/api/clinical/admin/eligibility-rules` | Yes | Yes | `admin.eligibility_rule_version` |
| GET | `/api/clinical/admin/deferral-rules` | No | No | None |
| POST | `/api/clinical/admin/deferral-rules/preview` | Yes | No | None |
| POST | `/api/clinical/admin/deferral-rules` | Yes | Yes | `admin.deferral_rule_version` |
| GET | `/api/clinical/admin/note-templates` | No | No | None |
| POST | `/api/clinical/admin/note-templates/preview` | Yes | No | None |
| POST | `/api/clinical/admin/note-templates` | Yes | Yes | `admin.note_template_upsert` |
| GET | `/api/clinical/admin/order-catalog` | No | No | None |
| POST | `/api/clinical/admin/order-catalog/preview` | Yes | No | None |
| POST | `/api/clinical/admin/order-catalog` | Yes | Yes | `admin.order_catalog_upsert` |
| GET | `/api/clinical/admin/billing-codes` | No | No | None |
| POST | `/api/clinical/admin/billing-codes/preview` | Yes | No | None |
| POST | `/api/clinical/admin/billing-codes` | Yes | Yes | `admin.billing_code_upsert` |
| GET | `/api/clinical/admin/quality-categories` | No | No | None |
| POST | `/api/clinical/admin/quality-categories/preview` | Yes | No | None |
| POST | `/api/clinical/admin/quality-categories` | Yes | Yes | `admin.quality_category_upsert` |
| GET | `/api/clinical/admin/approval-paths` | No | No | None |
| POST | `/api/clinical/admin/approval-paths/preview` | Yes | No | None |
| POST | `/api/clinical/admin/approval-paths` | Yes | Yes | `admin.approval_path_upsert` |
| GET | `/api/clinical/admin/notification-templates` | No | No | None |
| POST | `/api/clinical/admin/notification-templates/preview` | Yes | No | None |
| POST | `/api/clinical/admin/notification-templates` | Yes | Yes | `admin.notification_template_upsert` |
| GET | `/api/clinical/admin/rbac` | No | No | None |

## RC0 Route Notes

- Frontend `/clinical/...` route metadata now lives in `frontend/src/pages/clinical/clinicalRoutes.jsx`.
- The backend clinical module inventory in `GET /api/clinical/modules` and the frontend clinical route list both include dashboard, patients, scheduling, screening, encounters, orders, care plans, billing, quality, reports, and admin.
- No obvious stale clinical frontend route paths were found during RC0 inventory.
- Production API documentation should eventually be generated from OpenAPI to reduce drift between this Markdown inventory and router decorators.
