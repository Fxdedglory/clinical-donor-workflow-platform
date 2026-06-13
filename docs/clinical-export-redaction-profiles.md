# Clinical Export Redaction Profiles

Post-RC-02 update date: 2026-06-13

Scope: PHI/ePHI hardening for export-like clinical report, audit evidence, and compliance evidence routes. This is a deterministic foundation, not a full policy engine.

## Sensitivity Registry

The registry lives in `backend/app/services/clinical_phi.py` and classifies fields with these levels:

- `public`
- `internal`
- `phi`
- `ephi`
- `financial`
- `compliance_sensitive`
- `audit_sensitive`

Covered modules are patients, contacts, insurance, scheduling, screening, encounters, orders, care plans, billing, quality, audit, reports, and admin.

## Profiles

| Profile | Default surface | Behavior | Permission notes |
| --- | --- | --- | --- |
| `aggregate_safe` | Reports analytics preview/commit. | Redacts direct identifiers and sensitive audit-change details while preserving aggregate counts and profile metadata. | Requires the existing route export permission. |
| `external_safe` | Safe-share audit/report response profile. | Redacts internal, PHI/ePHI, financial, compliance-sensitive, and audit-sensitive fields. | External users remain rejected by current internal clinical route guards. |
| `audit_metadata` | Quality audit evidence default. | Keeps operational audit shape while avoiding raw narratives, note bodies, detailed claim data, and sensitive free text in changes. | Requires the existing quality export/audit route permission. |
| `internal_detail` | Internal operational detail. | Allows more detail but still routes workflow audit change storage through the conservative audit redactor. | Requires `system.admin`, `reports.export`, `quality.export`, `audit.review`, or `clinical_admin.manage`. |
| `compliance_evidence` | Compliance evidence preview/commit. | Allows sensitive evidence only for internal compliance/audit/QMS/admin use; stored audit changes remain redacted. | Requires `system.admin`, `quality.export`, `audit.review`, `qms.manage`, or `clinical_admin.manage`. |

## Hardened Endpoints

- `POST /api/clinical/reports/analytics-exports/preview`
- `POST /api/clinical/reports/analytics-exports`
- `POST /api/clinical/quality/compliance-exports/preview`
- `POST /api/clinical/quality/compliance-exports`
- `GET /api/clinical/quality/audit-evidence`
- `GET /api/clinical/reports/audit-activity`

## Audit Payload Behavior

Workflow commit audit entries continue to include operation id, workflow, entity type/id, actor, timestamp, preview hash, confirmation status, status transition, reason, and changes.

Post-RC-02 redacts the `changes` payload before DB persistence and JSON mirror/fallback writes. This preserves append-only evidence while avoiding raw PHI/ePHI payload storage where practical.

## Remaining Gaps

- Small-cell suppression is not implemented.
- Full role-aware UI field masking is not implemented.
- Free-text clinical narrative review is still required for production detailed exports.
- External warehouse, FHIR/HL7, Power BI, clearinghouse, and object export delivery remain out of scope.
- Object-storage/WORM mirroring for immutable audit/export evidence remains planned.
