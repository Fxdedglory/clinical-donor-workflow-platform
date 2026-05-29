# Observability Contract

This Clinical Donor Platform exposes a standard read-only monitoring surface for the future teemails Monitoring App. The endpoints summarize application, database, producer, validation, export, and audit state without exposing secrets, raw connection strings, tokens, passwords, session cookies, MFA codes, or local `.env` values.

## Standard Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/monitoring/health` | App, environment, build, PostgreSQL status, and uptime status. |
| `GET /api/monitoring/source-freshness` | Latest producer generation, validation, export, and clinical source watermark status. |
| `GET /api/monitoring/validation` | Latest validation status, error/warning counts, and summarized checks. |
| `GET /api/monitoring/export-manifest` | Latest clinical source export batch id, generated timestamp, file count, and row count. |
| `GET /api/monitoring/run-history` | Recent seed, incremental, validation, and export run summaries. |
| `GET /api/monitoring/security-events` | Recent app-level security audit events with hashed IP values. |
| `GET /api/monitoring/user-access` | Recent session/login-compatible events with hashed IP values. |

## Contract Notes

- `app_name` is `clinical-donor-platform`.
- `source_systems` contains `CLINICAL_DONOR_PLATFORM`.
- `storage_backend` is `postgresql`.
- `stale_threshold_minutes` defaults to 1440 minutes for portfolio monitoring.
- Security and user access endpoints avoid raw IP output by returning `hashed_ip` and `ip_address: null`.
- Monitoring endpoints are read-only. Data producer write actions remain guarded by authentication, permissions, and explicit confirmation.

## Monitoring App Expectations

The Monitoring App should poll these endpoints as operational telemetry. Low-privilege monitoring views should mask user identifiers and should not display raw security/audit detail broadly.
