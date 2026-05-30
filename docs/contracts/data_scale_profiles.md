# Clinical Data Scale Profiles

The Clinical Donor Platform uses database-backed producer profiles for historical donor, partner portal, QMS, vendor SLA, workflow, audit, and security-event data.

| Profile | Date range | Seed donors | Incremental scale | Expected rows | Azure suitability |
|---|---:|---:|---:|---|---|
| `demo` | 2026-01-01 to 2026-05-29 | 500 | 1 | ~5K-15K clinical rows | Safe for current Azure PostgreSQL/App Service footprint |
| `small` | 2025-07-01 to 2026-05-29 | 1,200 | 3 | ~20K-60K rows | Feasible with monitoring |
| `medium` | 2024-01-01 to 2026-05-29 | 5,000 | 10 | ~100K-300K rows | Dry-run locally before Azure |
| `large` | 2021-01-01 to 2026-05-29 | 20,000 | 25 | Path toward 1M+ workflow events | Requires storage/cost plan |
| `enterprise` | 2019-01-01 to 2026-05-29 | 50,000 | 25 | Target: 50K+ referrals, 100K+ screenings, 1M+ workflow events, 2M+ audit events | Requires PostgreSQL capacity review and external export storage |

## Generation Modes

Historical baseline generation seeds the regulated clinical workflow database with donor review, screening, partner portal, QMS, CAPA, vendor SLA, workflow, audit, notification, and training records over the configured date range. Incremental generation requires an existing seeded database and adds new donor cases, partner activity, QMS/vendor events, task mutations, audit events, and producer run history after the current state.

## EDW Metadata

Source exports include:

- `source_system`
- `source_table`
- `source_record_id`
- `source_created_at`
- `source_updated_at`
- `ingestion_batch_id`
- `extraction_batch_id`
- `generated_at`
- `extracted_at`

Clinical generation must preserve partner organization relationships, reviewer/user relationships, role/audit relationships, and `clinical_runtime` compatibility. Auth/MFA tables are not synthetic scale targets except for deliberate audit/security event workflows.
