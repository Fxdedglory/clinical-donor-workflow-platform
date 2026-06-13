# Clinical Route Permission Drift Tests

Post-RC-04 update date: 2026-06-13

## Purpose

`tests/test_clinical_route_permission_drift.py` enumerates registered FastAPI routes under `/api/clinical` and checks that sensitive routes stay documented in `docs/clinical-api-inventory.md` and classified in `docs/clinical-rbac-matrix.md`.

This test is meant to catch quiet permission drift when new mutation, admin, audit, or export routes are added.

## Category Vocabulary

| Category | Meaning |
| --- | --- |
| `public_or_health` | Foundation status, module inventory, or generic preview surface. |
| `internal_read` | Internal authenticated clinical read route. |
| `internal_mutation` | Internal authenticated clinical mutation route. |
| `clinical_admin` | Clinical administration route. |
| `compliance_export` | Quality/compliance export or evidence route. |
| `analytics_export` | Reports analytics export preview or commit route. |
| `audit_evidence` | Audit activity or audit evidence route. |
| `external_partner_denied` | Route must reject partner/supplier external users. |
| `generic_foundation_restricted` | Generic workflow commit restricted to internal admin/system authority. |

## Maintenance Rule

When adding a new `/api/clinical` route:

1. Add it to `docs/clinical-api-inventory.md`.
2. Confirm its route guard matches `docs/clinical-rbac-matrix.md`.
3. Extend the drift test classifier only when the new route introduces a new route family or permission category.
4. Keep external partner/supplier denial explicit for internal mutation, export, audit, and admin surfaces.
