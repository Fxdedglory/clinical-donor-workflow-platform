# Clinical RC QA Checklist

RC0 checklist date: 2026-06-12

Use this checklist after migrations and before promoting a release candidate.

## Setup

- [ ] Confirm latest expected release commit is deployed.
- [ ] Confirm `GET /api/health` returns healthy status.
- [ ] Confirm `GET /api/clinical/status` returns `foundation_ready`.
- [ ] Confirm `GET /api/clinical/modules` includes dashboard, patients, scheduling, screening, encounters, orders, care plans, billing, quality, reports, and admin.
- [ ] Confirm internal demo users can authenticate.
- [ ] Confirm external partner/supplier demo users can authenticate but cannot access internal clinical mutation workflows.

## Frontend Navigation

- [ ] Open `/clinical/dashboard`.
- [ ] Open `/clinical/patients`.
- [ ] Open `/clinical/patients/PT-000001` or another seeded patient detail route.
- [ ] Open `/clinical/scheduling`.
- [ ] Open `/clinical/screening`.
- [ ] Open `/clinical/encounters`.
- [ ] Open `/clinical/orders`.
- [ ] Open `/clinical/care-plans`.
- [ ] Open `/clinical/billing`.
- [ ] Open `/clinical/quality`.
- [ ] Open `/clinical/reports`.
- [ ] Open `/clinical/admin`.
- [ ] Confirm sidebar clinical links route without blank pages or console errors.
- [ ] Confirm planned/foundation-pending workflows remain visible and are not hidden.

## Patient / Donor Registration

- [ ] Search patient list by name/status.
- [ ] Create patient/donor preview and confirm duplicate warnings are visible when applicable.
- [ ] Commit create with `X-Confirm-Generation: true`.
- [ ] Edit demographics preview and commit.
- [ ] Add contact preview and commit.
- [ ] Add insurance preview and commit.
- [ ] Capture consent preview and commit.
- [ ] Confirm patient detail shows demographics, contacts, insurance, consents, and recent workflow activity.
- [ ] Confirm external users cannot mutate patient records.

## Scheduling

- [ ] Load appointment list and resources.
- [ ] Book appointment preview and commit.
- [ ] Verify provider, room, patient, and equipment conflict warnings/blockers.
- [ ] Reschedule appointment preview and commit.
- [ ] Cancel appointment preview and commit with reason.
- [ ] Check in appointment preview and commit.
- [ ] Mark no-show preview and commit.
- [ ] Confirm status history and workflow audit entries are visible.

## Screening / Eligibility

- [ ] Start screening session from a patient.
- [ ] Commit questionnaire answers after preview.
- [ ] Commit vitals after preview.
- [ ] Generate eligibility preview.
- [ ] Commit screening result.
- [ ] Confirm temporary/permanent deferral behavior when selected.
- [ ] Execute supervisor override with authorized user.
- [ ] Confirm missing questionnaire/vitals blocks result commit.
- [ ] Confirm external users cannot mutate screening workflows.

## Encounters

- [ ] Create encounter preview and commit from patient/appointment/screening context.
- [ ] Save draft note preview and commit.
- [ ] Sign note preview and commit.
- [ ] Confirm signed note cannot be directly edited.
- [ ] Amend signed note preview and commit.
- [ ] Add diagnosis/problem preview and commit.
- [ ] Add allergy preview and commit.
- [ ] Add medication preview and commit.
- [ ] Confirm encounter status history and downstream Orders/Care Plans handoffs.

## Orders / Results

- [ ] Load order catalog.
- [ ] Create order preview and commit.
- [ ] Enter normal result preview and commit.
- [ ] Enter abnormal or critical result preview and commit.
- [ ] Confirm critical result acknowledgement is required and visible.
- [ ] Acknowledge critical result preview and commit.
- [ ] Correct result preview and commit.
- [ ] Cancel order preview and commit with reason.
- [ ] Confirm cancelled order blocks new result entry.

## Care Plans

- [ ] Create care plan preview and commit.
- [ ] Add goal preview and commit.
- [ ] Add intervention preview and commit.
- [ ] Add task preview and commit.
- [ ] Add progress note preview and commit.
- [ ] Close care plan preview and commit with closure reason.
- [ ] Confirm closed care plan blocks additional plan mutation.
- [ ] Confirm abnormal/critical linked result warnings remain visible.

## Billing / Insurance

- [ ] Verify insurance preview and commit.
- [ ] Capture charge preview and commit.
- [ ] Create claim preview and commit.
- [ ] Post partial payment preview and commit.
- [ ] Post full payment preview and commit.
- [ ] Capture denial preview and commit.
- [ ] Confirm billing work queue updates account balance, claims, payments, and denials.
- [ ] Confirm payment posting requires payment-post permission.

## Quality / Compliance

- [ ] Create quality event preview and commit.
- [ ] Create adverse event preview and commit.
- [ ] Add investigation preview and commit.
- [ ] Link existing CAPA or planned CAPA preview and commit.
- [ ] Close quality event preview and commit.
- [ ] Confirm closed quality event blocks additional investigation/CAPA/closure mutation.
- [ ] Generate audit evidence with workflow/entity filters.
- [ ] Preview and commit compliance export.
- [ ] Confirm quality export requires export/audit permission.

## Clinical Administration

- [ ] Load admin dashboard, config versions, and RBAC overview.
- [ ] Preview and commit appointment type configuration.
- [ ] Preview and commit provider schedule template.
- [ ] Preview and commit screening template version.
- [ ] Preview and commit eligibility rule version.
- [ ] Preview and commit deferral rule version.
- [ ] Preview and commit note template.
- [ ] Preview and commit order catalog item.
- [ ] Preview and commit billing code.
- [ ] Preview and commit quality category.
- [ ] Preview and commit approval path.
- [ ] Preview and commit notification template.
- [ ] Confirm prior versions are preserved where versioning applies.
- [ ] Confirm external users cannot access or mutate clinical admin.

## Reports / Analytics

- [ ] Load reports dashboard.
- [ ] Apply date/status/workflow/actor filters.
- [ ] Review patient throughput report.
- [ ] Review scheduling utilization report.
- [ ] Review screening outcomes report.
- [ ] Review deferral report.
- [ ] Review encounter volume report.
- [ ] Review orders/results report.
- [ ] Review care plan aging report.
- [ ] Review billing work queue report.
- [ ] Review quality trends report.
- [ ] Review audit activity report.
- [ ] Preview analytics export with selected modules.
- [ ] Commit analytics export with `X-Confirm-Generation: true`.
- [ ] Confirm external users cannot generate exports.

## RBAC / Export Behavior

- [ ] Confirm missing `X-Confirm-Generation` rejects commit endpoints.
- [ ] Confirm invalid `X-Confirm-Generation` rejects commit endpoints.
- [ ] Confirm valid `X-Confirm-Generation: true` accepts authorized commits.
- [ ] Confirm read-only routes do not require the confirmation header.
- [ ] Confirm users without export permissions cannot generate quality/report exports.
- [ ] Confirm partner/supplier users remain limited to portal workflows.

## Audit Evidence

- [ ] Confirm each committed workflow appends to `metadata/workflow_operations.json`.
- [ ] Confirm existing audit entries are preserved after new commits.
- [ ] Confirm quality audit evidence can filter by workflow, actor, entity type, and entity ID.
- [ ] Confirm report audit activity reflects recent workflow operation entries.
- [ ] Confirm production audit durability remains a known RC1 follow-up.

## Migration Readiness

- [ ] Confirm database backup or restore point exists.
- [ ] Confirm `alembic current` matches expected pre-deploy revision.
- [ ] Confirm `alembic heads` reports the expected head.
- [ ] Run `alembic upgrade head`.
- [ ] Confirm Sprint 2 through Sprint 11 tables exist.
- [ ] Confirm role-permission grants exist for patient, scheduling, screening, encounter, order, care plan, billing, quality, admin, and reports permissions.
- [ ] Run full automated validation after migration.

## Automated Validation

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```
