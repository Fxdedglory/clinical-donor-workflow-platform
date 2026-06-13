# Clinical Export Permission Review

RC1 review date: 2026-06-13

Scope: clinical export, reporting, audit evidence, and export-like endpoints under `/api/clinical`. This review does not cover legacy donor/QMS exports outside the clinical namespace.

## Enforcement Summary

- Clinical report exports use `require_reports_export`, which rejects external users and accepts users with one of `system.admin`, `reports.export`, `quality.export`, `audit.review`, or `clinical_admin.manage`.
- Clinical quality audit evidence and compliance exports use `require_quality_export`, which rejects external users and accepts users with one of `system.admin`, `quality.export`, `audit.review`, or `qms.manage`.
- Commit endpoints also require `X-Confirm-Generation: true`.
- Current analytics export implementation stores export metadata, row counts, filters, status history, and audit operations. It does not perform external warehouse delivery in RC1.

## Endpoint Review

| Endpoint | Data sensitivity | Expected permission | Current enforcement | Gaps / follow-ups |
| --- | --- | --- | --- | --- |
| `GET /api/clinical/reports/analytics-exports` | Moderate to high. Export metadata can reveal selected modules, filters, row counts, generator, and timing. | `reports.read` for operational visibility; consider `reports.export` for minimum-necessary access. | `require_reports_read`; rejects external users. | RC2: confirm whether export metadata should require export permission instead of report read. |
| `POST /api/clinical/reports/analytics-exports/preview` | High. Preview row counts span patient throughput, scheduling, screening, deferrals, encounters, orders/results, care plans, billing, quality, and audit activity. | `reports.export` or equivalent approved export/audit role. | `require_reports_export`; rejects external users. | No code gap found in RC1. |
| `POST /api/clinical/reports/analytics-exports` | High. Durable export metadata record plus workflow audit entry. | `reports.export`; confirmation header required. | `require_reports_export`; `require_generation_confirmation`; audit append to `metadata/workflow_operations.json`. | Audit storage durability remains RC2. |
| `GET /api/clinical/reports/audit-activity` | High. Returns workflow operation audit summaries and recent operation payloads. | Prefer `audit.review` or dedicated audit reporting permission. | `require_reports_read`; rejects external users. | RC2: split audit activity from broad `reports.read`. |
| `GET /api/clinical/quality/audit-evidence` | High. Evidence can include actor, workflow, entity id/type, status transitions, reason, and change payloads. | `quality.export`, `audit.review`, `qms.manage`, or `system.admin`. | `require_quality_export`; rejects external users. | No code gap found in RC1; durability and masking remain follow-ups. |
| `GET /api/clinical/quality/compliance-exports` | High. Lists compliance export metadata and evidence summaries. | `quality.export`, `audit.review`, `qms.manage`, or `system.admin`. | `require_quality_export`; rejects external users. | No code gap found in RC1. |
| `POST /api/clinical/quality/compliance-exports/preview` | High. Builds evidence summary from quality and workflow audit data. | `quality.export`, `audit.review`, `qms.manage`, or `system.admin`. | `require_quality_export`; rejects external users. | No code gap found in RC1. |
| `POST /api/clinical/quality/compliance-exports` | High. Durable compliance export metadata plus workflow audit entry. | `quality.export`; confirmation header required. | `require_quality_export`; `require_generation_confirmation`; audit append to `metadata/workflow_operations.json`. | Audit storage durability remains RC2. |
| `GET /api/clinical/reports/billing-work-queue` | High. Aggregate billing status and balances. | `reports.read` or billing/reporting role approved by compliance. | `require_reports_read`; rejects external users. | RC2: confirm whether financial aggregates require a distinct billing report permission. |
| `GET /api/clinical/reports/orders-results` | High. Aggregate order/result status and critical-result counts. | `reports.read`; consider clinical report segmentation. | `require_reports_read`; rejects external users. | RC2: confirm whether result reporting needs extra clinical reviewer/QA scope. |
| `GET /api/clinical/admin/rbac` | High administrative metadata. Role permissions can expose internal access model. | `clinical_admin.read` or `system.admin`; no external access. | `require_admin_read`; rejects external users. | No code gap found in RC1. |

## Billing, Quality, And Admin Export-Like Endpoints

No additional billing export endpoint was found under `/api/clinical/billing`; billing export exposure is currently through report aggregates and report analytics export metadata.

Quality export-like exposure is concentrated in:

- `/api/clinical/quality/audit-evidence`
- `/api/clinical/quality/compliance-exports`
- `/api/clinical/reports/quality-trends`
- `/api/clinical/reports/audit-activity`
- `/api/clinical/reports/analytics-exports`

Clinical administration has no export commit endpoint, but `/api/clinical/admin/rbac` is export-like from a security perspective because it discloses role and permission configuration.

## Existing Tests

Current tests already cover low-risk enforcement smoke checks for the highest-risk export paths:

- `tests/test_clinical_reports.py` verifies analytics export preview, confirmation guard, audit file creation, audit append preservation, and external partner rejection.
- `tests/test_clinical_quality.py` verifies compliance export preview/commit, audit evidence filtering, quality audit append behavior, and external partner mutation rejection.

## RC2 Recommendations

1. Add a generated route-permission inventory test from FastAPI OpenAPI and route dependency metadata.
2. Split audit activity report access from broad `reports.read` if compliance owners classify workflow operations as audit-only evidence.
3. Decide whether export metadata list endpoints require export permission instead of read permission.
4. Add PHI-aware masking/redaction before any detailed export or external delivery capability.
5. Move workflow operation audit from filesystem JSON to append-only database storage before compliance evidence packages are production authoritative.
