# Clinical UI PHI Masking

Post-RC-05 update date: 2026-06-13

## Purpose

Post-RC-05 adds a frontend display foundation for role-aware PHI/ePHI masking, export profile indicators, and small-cell suppression labels. It does not create a new authorization system. Backend route guards, export profile enforcement, and workflow commit checks remain the source of access control.

## Frontend Helpers

The reusable UI helpers live in:

- `frontend/src/pages/clinical/clinicalPrivacyDisplay.js`
- `frontend/src/pages/clinical/ClinicalRedactedValue.jsx`
- `frontend/src/pages/clinical/ClinicalSuppressedMetric.jsx`

Display labels are standardized as:

- `Redacted`
- `PHI protected`
- `Suppressed`
- `Small-cell suppression`

The redacted and suppressed components avoid placing raw PHI/ePHI values in tooltip text, `aria-label` text, or hidden labels.

## Role Behavior

The frontend uses the existing authenticated user/profile shape when available.

| Role context | UI display behavior |
| --- | --- |
| External partner/supplier role flags or role names | Sensitive clinical identifiers and free text render as `Redacted` with `PHI protected`. |
| Internal clinical, QA, operations, admin, audit, or export-capable roles | Operational detail may render when backend access already allowed it. |
| Missing or incomplete role context | UI defaults to safer masked display. |

The recognized external role markers are `Partner External User`, `Supplier External User`, `is_external`, `external_user_flag`, and `account_type` or `user_type` values such as `partner`, `supplier`, or `external`.

## Covered UI Areas

The display helpers are applied to high-risk clinical surfaces:

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

Masked fields include direct patient identifiers, names, date of birth, contact data, payer/member identifiers, clinical reasons, notes, result values, care plan narratives, billing denial reasons, audit entity identifiers, and quality/adverse event free text.

## Export Profile UX

Reports and quality export workflows now show the selected export profile and whether PHI/ePHI redaction and small-cell suppression are active.

| Profile | UI signal |
| --- | --- |
| `aggregate_safe` | Redaction active, small-cell suppression active, details intentionally omitted. |
| `external_safe` | Redaction active, small-cell suppression active, internal and sensitive fields omitted. |
| `audit_metadata` | Redaction active, small-cell suppression inactive, audit narratives avoided. |
| `internal_detail` | Detail visibility restricted to approved internal roles. |
| `compliance_evidence` | Sensitive evidence warning for approved compliance/audit access. |

When report APIs return suppression metadata, the UI displays the threshold and suppressed-cell count.

## Small-Cell Display

Suppressed aggregate values render as:

```text
Suppressed
Small-cell suppression < 5
```

The component does not display the hidden raw count. Analytics export preview and report metric tables use the same suppressed-cell helper when API values carry `suppressed: true`.

## Limitations

- The frontend is not an authorization boundary. Backend RBAC and export profiles remain authoritative.
- Some form controls still submit internal identifiers as select values because backend workflow APIs require stable IDs. The visible labels use masking where practical.
- Existing internal clinical routes continue to reject external users at the backend. Partner-facing clinical views should use separate scoped APIs if approved later.
- Free-text clinical narrative review remains a production governance requirement for detailed exports.
- Object-storage/WORM audit mirroring remains planned and is not implemented by this UI masking update.

## Validation

Focused coverage lives in `tests/test_clinical_ui_privacy_helpers.py`.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_clinical_ui_privacy_helpers.py tests\test_clinical_route_permission_drift.py tests\test_clinical_reports.py
cd frontend
npm run build
```
