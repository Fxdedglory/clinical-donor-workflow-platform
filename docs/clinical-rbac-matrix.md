# Clinical RBAC Matrix

RC0 inventory date: 2026-06-12

Source reviewed: `backend/app/services/access_control.py` plus module-level route dependencies.

## Permission Families

| Permission Family | Purpose |
| --- | --- |
| `patients.*` | Patient/donor registration read, create, and demographic/contact/insurance/consent management. |
| `scheduling.*` | Appointment reads and lifecycle mutation. |
| `screening.*` | Screening read, questionnaire/vitals/result mutation, supervisor override. |
| `encounters.*` | Encounter read, documentation mutation, signing. |
| `orders.*` | Order/result read and mutation, critical result acknowledgement. |
| `care_plans.*` | Care plan read, mutation, and closure. |
| `billing.*` | Billing read, charge/claim/denial mutation, payment posting. |
| `quality.*` | Quality read, mutation, closure, and compliance export. |
| `clinical_admin.*` | Clinical configuration read and mutation. |
| `reports.*` | Clinical reporting read and analytics export generation. |
| `audit.review` | Audit evidence and cross-module evidence review. |
| `dashboard.view` | Dashboard and operational overview access. |
| `system.admin` | Superuser-style administrative access. |
| `partner.portal` / `supplier.portal` | Bounded external portal access; not internal clinical mutation. |

## Role Capability Matrix

| Role | Clinical Read | Clinical Write | Export / Audit | Admin / Config | External Restrictions |
| --- | --- | --- | --- | --- | --- |
| System Administrator | All clinical modules | All clinical modules | `quality.export`, `reports.export`, `audit.review` | `clinical_admin.manage`, `workflow.configure`, users/roles/security | Internal role; unrestricted within current clinical routers. |
| Donor Intake Coordinator | Patients, scheduling, screening, encounters, orders, care plans, billing, quality, reports | Patients create, scheduling manage, screening manage, encounters manage, orders manage, care plans manage, billing manage | Reports read only; no quality/report export | No clinical admin manage | Internal role. |
| Clinical Reviewer | Patients, scheduling, screening, encounters, orders, care plans, billing, quality, clinical admin, reports | Patients manage, scheduling manage, screening manage/override, encounters manage/sign, orders manage/acknowledge, care plans manage/close, billing manage, quality manage, clinical admin manage | Reports read only | Clinical admin read/manage | Internal role; broad clinical reviewer capability. |
| Quality Assurance Specialist | Patients, scheduling, screening, encounters, orders, care plans, billing, quality, clinical admin, reports | Screening manage/override, encounters manage/sign, orders manage/acknowledge, care plans manage/close, billing manage/payment, quality manage/close, clinical admin manage | `quality.export`, `reports.export`, `audit.review` | Clinical admin read/manage; documents/training/change control | Internal role. |
| Operations Manager | Patients, scheduling, screening, encounters, orders, care plans, billing, quality, clinical admin, reports | Scheduling manage, screening manage/override, encounters manage/sign, orders manage/acknowledge, care plans manage/close, billing manage/payment, quality manage, clinical admin manage | `quality.export`, `reports.export`, `audit.review` | Clinical admin read/manage; escalations/training/partners/suppliers | Internal role. |
| Business Technology Analyst | Quality read, clinical admin read, reports, audit, background jobs | Risk rules and eligibility configuration; no direct patient/scheduling/order mutation in the current role definition | `quality.export`, `reports.export`, `audit.review`, `security.audit` | Workflow analytics, risk rules, AI governance | Internal role focused on governance and analytics. |
| Vendor Operations Analyst | Vendor, task, notification, document, dashboard | Vendor/task operations only | None for clinical exports | No clinical admin | Internal role; no direct clinical module permissions. |
| Partner External User | Partner/supplier portal, tasks, notifications, documents, signatures | External portal submissions/documents/tasks/signatures only | No clinical exports | No clinical admin | Clinical patient/scheduling/screening/encounter/order/care/billing/quality/admin/report mutation is rejected by module guards. |
| Supplier External User | Partner/supplier portal compatibility, tasks, notifications, documents, signatures | External portal tasks/documents/signatures only | No clinical exports | No clinical admin | Same external restrictions as Partner External User. |

## Module Permission Detail

| Module | Read Permissions | Write / Commit Permissions | Export / Close / Special Permissions | External User Handling |
| --- | --- | --- | --- | --- |
| Patients / Donors | `patients.read`, `patients.manage`, `patients.create`, `system.admin` | `patients.create`, `patients.manage`, `system.admin` | None | External users rejected from mutation. |
| Scheduling | `scheduling.read`, `scheduling.manage`, `system.admin` | `scheduling.manage`, `system.admin` | None | External users rejected from mutation. |
| Screening | `screening.read`, `screening.manage`, `screening.override`, `system.admin` | `screening.manage`, `system.admin` | `screening.override` for override workflows | External users rejected from mutation. |
| Encounters | `encounters.read`, `encounters.manage`, `encounters.sign`, `system.admin` | `encounters.manage`, `system.admin` | `encounters.sign` for signing workflows | External users rejected from mutation. |
| Orders / Results | `orders.read`, `orders.manage`, `orders.acknowledge`, `system.admin` | `orders.manage`, `system.admin` | `orders.acknowledge` for critical acknowledgement | External users rejected from mutation. |
| Care Plans | `care_plans.read`, `care_plans.manage`, `care_plans.close`, `system.admin` | `care_plans.manage`, `system.admin` | `care_plans.close` for closure | External users rejected from mutation. |
| Billing / Insurance | `billing.read`, `billing.manage`, `billing.payment_post`, `system.admin` | `billing.manage`, `system.admin` | `billing.payment_post` for payment posting | External users rejected from mutation. |
| Quality / Compliance | `quality.read`, `quality.manage`, `quality.close`, `quality.export`, `qms.manage`, `audit.review`, `system.admin` | `quality.manage`, `qms.manage`, `system.admin` | `quality.close`, `quality.export`, `audit.review` | External users rejected from quality operations and export. |
| Reports | `reports.read`, `reports.export`, `dashboard.view`, `audit.review`, `quality.export`, `clinical_admin.read`, `system.admin` | None for aggregate reads | `reports.export`, `quality.export`, `audit.review`, `clinical_admin.manage`, `system.admin` for analytics export | External users rejected from report access/export in current route guards. |
| Clinical Admin | `clinical_admin.read`, `clinical_admin.manage`, `system.admin` | `clinical_admin.manage`, `system.admin` | Configuration versioning and approval path management | External users rejected from admin read/mutation. |

## Commit Guard Expectations

All durable clinical mutation endpoints require:

```text
X-Confirm-Generation: true
```

Preview endpoints do not mutate durable clinical state and do not require this header.

## Known Gaps / RC1 Review Items

- RBAC policy is currently encoded in Python route/service constants and role seed definitions. RC1 should consider a generated permission matrix test that compares route guards to `ROLE_DEFINITIONS`.
- External user behavior is intentionally restrictive for internal clinical modules. Future partner-facing clinical views should use organization-scoped endpoints rather than relaxing internal clinical routes.
- Role names include both "Quality Assurance Specialist" and an `INTERNAL_ADMIN_ASSIGNED_ROLES` frontend label of "QA Specialist"; RC1 should review whether this label mismatch is only display copy or affects access request routing.
- `system.admin` remains broad. Production readiness should include least-privilege review before go-live.
- Audit/export permissions should be reviewed with compliance owners before enabling production exports.
