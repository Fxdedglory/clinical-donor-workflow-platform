# Clinical RBAC Matrix

RC0 inventory date: 2026-06-12

RC1 enforcement review date: 2026-06-13

Post-RC-02 hardening update date: 2026-06-13

Post-RC-04 route drift and suppression update date: 2026-06-13

Post-RC-05 UI masking update date: 2026-06-13

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
| Generic Workflow Foundation | `/api/clinical/workflows/preview` remains foundation preview only. | `/api/clinical/workflows/commit` now requires `clinical_admin.manage` or `system.admin`. | Confirmation header plus internal authenticated admin context. | External partner/supplier users rejected; module-specific commit endpoints are preferred for real clinical workflows. |

## Route Permission Drift Categories

The route-permission drift tests use these category tokens to compare registered FastAPI routes against the documented RBAC model:

| Category | Expected guard pattern |
| --- | --- |
| `public_or_health` | Foundation status, module inventory, or generic preview surface. |
| `internal_read` | Internal authenticated read access through module read guards. |
| `internal_mutation` | Internal authenticated mutation access through module mutation guards and `X-Confirm-Generation: true` where durable. |
| `clinical_admin` | `clinical_admin.read`, `clinical_admin.manage`, or `system.admin`; external users denied. |
| `compliance_export` | `quality.export`, `audit.review`, `qms.manage`, or `system.admin`; external users denied. |
| `analytics_export` | `reports.export`, `quality.export`, `audit.review`, `clinical_admin.manage`, or `system.admin`; external users denied. |
| `audit_evidence` | Audit activity/evidence route requiring audit-aware review during least-privilege changes. |
| `external_partner_denied` | Partner/supplier external accounts rejected by the backend guard. |
| `generic_foundation_restricted` | Generic workflow commit restricted to internal clinical admin/system authority. |

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

## RC1 Route-Level Enforcement Review

| Route area | Current enforcement | RC1 assessment |
| --- | --- | --- |
| `/api/clinical/status`, `/api/clinical/modules`, `/api/clinical/workflows/preview` | Foundation routes are unauthenticated. | Acceptable for local foundation status only if not internet-exposed. RC2 should decide whether foundation routes require authentication in production. |
| `/api/clinical/workflows/commit` | Requires `X-Confirm-Generation: true`, internal authenticated user, and `clinical_admin.manage` or `system.admin`. | Post-RC-02 hardened. Module-specific commit endpoints remain the preferred mutation path. |
| Patients, scheduling, screening, encounters, orders, care plans, billing | Module-specific guards use `get_current_user`, permission sets, and explicit external-user rejection. | Consistent internal-only pattern. Mutation routes also require confirmation header. |
| Quality | `require_quality_read`, `require_quality_mutation`, `require_quality_close`, and `require_quality_export` separate read, mutation, closure, and export access. | Strongest module-level separation in the current clinical namespace. |
| Reports | `require_reports_read` for dashboards/report reads and `require_reports_export` for analytics export preview/commit. | Export guard is appropriate. Audit activity under report-read should be reviewed for least privilege. |
| Clinical admin | `require_admin_read` and `require_admin_mutation`; external users rejected. | Appropriate for RC1. Admin mutation routes also require confirmation header. |
| Frontend `/clinical/...` routes | Visible and navigable shell routes. Backend remains source of authorization. | Frontend route visibility is not an authorization boundary. Route guards should remain backend-enforced. |

## Post-RC-05 Frontend Display Masking

The clinical frontend now uses the existing authenticated user/profile context to choose a display mode:

| UI display mode | Trigger | Behavior |
| --- | --- | --- |
| External safe display | Partner/supplier/external role markers. | Sensitive identifiers and free text render as `Redacted` with `PHI protected`. |
| Internal operational detail | Internal clinical, QA, operations, admin, audit, or export-capable roles. | Operational detail may render when backend access already allowed the page or workflow. |
| Safe display | Missing or incomplete role context. | Sensitive fields default to masked display. |

This display layer does not grant access and does not replace backend route guards. Internal clinical routes continue to reject partner/supplier external users. See `docs/clinical-ui-phi-masking.md`.

## RC1 Mutation / Export / Admin Endpoint Review

| Endpoint family | Required access today | Confirmation guard | External user handling | Notes |
| --- | --- | --- | --- | --- |
| Clinical mutations across patients/scheduling/screening/encounters/orders/care/billing/quality/admin | Module-specific manage/close/sign/acknowledge/admin permissions or `system.admin`. | Required on durable commit endpoints. | Rejected by module guards. | Preview endpoints validate without durable mutation and do not require confirmation. |
| `/api/clinical/reports/analytics-exports/preview` and `/api/clinical/reports/analytics-exports` | `reports.export`, `quality.export`, `audit.review`, `clinical_admin.manage`, or `system.admin`. | Required on commit. | Rejected. | Export commit writes `reports.analytics_export` workflow audit. |
| `/api/clinical/quality/audit-evidence` | `quality.export`, `audit.review`, `qms.manage`, or `system.admin`. | Not applicable; read-only evidence query. | Rejected. | Evidence can include workflow operation change payloads. |
| `/api/clinical/quality/compliance-exports/preview` and `/api/clinical/quality/compliance-exports` | `quality.export`, `audit.review`, `qms.manage`, or `system.admin`. | Required on commit. | Rejected. | Export commit writes `quality.compliance_export` workflow audit. |
| `/api/clinical/admin/rbac` | `clinical_admin.read`, `clinical_admin.manage`, or `system.admin`. | Not applicable; read-only. | Rejected. | Treat as sensitive admin metadata even though it is not an export endpoint. |
| `/api/clinical/workflows/commit` | `clinical_admin.manage` or `system.admin`. | Required. | Rejected. | Generic foundation commit endpoint is locked down; use module-specific commit routes for clinical mutation behavior. |

## Post-RC-02 Export Profile Access

| Export profile | Intended use | Permission expectation |
| --- | --- | --- |
| `aggregate_safe` | Default analytics/report export preview and commit; avoids direct identifiers. | Existing report/quality export route permission. |
| `external_safe` | Strict safe-share redaction profile for export-like audit/report responses. | Existing route permission; external users remain rejected by current internal clinical guards. |
| `audit_metadata` | Default audit evidence profile; avoids raw clinical narratives and sensitive free text in audit change payloads. | `quality.export`, `audit.review`, `qms.manage`, or `system.admin` for quality evidence; report guard for report audit activity. |
| `internal_detail` | Internal operational detail when necessary. | `system.admin`, `reports.export`, `quality.export`, `audit.review`, or `clinical_admin.manage`. |
| `compliance_evidence` | Compliance evidence package with sensitive details. | `system.admin`, `quality.export`, `audit.review`, `qms.manage`, or `clinical_admin.manage`. |

Post-RC-04 adds small-cell suppression for `aggregate_safe` and `external_safe` report aggregates and analytics export row counts. Nonzero counts below 5 are replaced with suppression metadata; `internal_detail` keeps visible small counts for authorized internal users only.

## RC1 External Partner / Supplier Restrictions

External users are identified through `is_external`, `external_user_flag`, `account_type`, `user_type`, and role names such as "Partner External User" and "Supplier External User". Internal clinical module guards reject these users before permission checks.

Allowed external access remains limited to partner/supplier portal permissions such as `partner.portal`, `supplier.portal`, document workflows, assigned tasks, notifications, and signatures. External users should not receive direct `patients.*`, `scheduling.*`, `screening.*`, `encounters.*`, `orders.*`, `care_plans.*`, `billing.*`, `quality.*`, `clinical_admin.*`, `reports.*`, or `audit.review` permissions for internal clinical routes.

## RC2 Remediation Items

1. Keep the generated route-permission drift test aligned with FastAPI route metadata, this matrix, and `ROLE_DEFINITIONS`.
2. Split report audit activity from broad `reports.read` if compliance owners classify audit operation payloads as audit-only.
3. Decide whether analytics export list metadata should require export permission rather than report read permission.
4. Expand frontend route-visibility and masking tests if partner-facing clinical pages are approved.
5. Resolve the "QA Specialist" display label versus "Quality Assurance Specialist" role-name mismatch.
6. Review `system.admin` use for least-privilege production operations.
7. Obtain compliance signoff for `internal_detail`, `compliance_evidence`, and the small-cell suppression threshold before production analytics sharing.
