# Clinical Analytics Small-Cell Suppression

Post-RC-04 update date: 2026-06-13

## Purpose

Clinical aggregate reports and analytics export row-count contracts can expose re-identification risk when a nonzero cohort is very small. Post-RC-04 adds deterministic small-cell suppression for safe report/export profiles.

## Behavior

The reusable helper lives in `backend/app/services/clinical_reporting_privacy.py`.

Suppression applies when:

- `export_profile=aggregate_safe`
- `export_profile=external_safe`
- an integer count is nonzero and below `5`

Suppression does not apply when:

- the count is `0`
- the count is `5` or greater
- the profile is `internal_detail`, `audit_metadata`, or `compliance_evidence`

Suppressed cells use this shape:

```json
{
  "value": null,
  "suppressed": true,
  "suppression_reason": "small_cell",
  "threshold": 5
}
```

## Covered Surfaces

- Report metric card values.
- Report count dictionaries such as status, outcome, priority, workflow, actor, module, and row counts.
- Selected scalar count fields such as duplicate warnings, supervisor review, overrides, and total operations.
- Report series count values.
- Provider utilization appointment counts and related scheduled minutes.
- Dashboard module counts.
- Analytics export preview and commit row counts.

Analytics export commits persist suppression metadata in export payload metadata and workflow audit changes. Suppressed export item row counts are stored as `0` to prevent downstream readers from treating hidden cohorts as visible rows.

## Validation

Focused coverage lives in:

- `tests/test_clinical_reports.py`
- `tests/test_clinical_route_permission_drift.py`

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_clinical_reports.py tests\test_clinical_route_permission_drift.py tests\test_clinical_phi_redaction.py
```
