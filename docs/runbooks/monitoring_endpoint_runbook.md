# Monitoring Endpoint Runbook

Use these checks after local startup or Azure deployment.

## Local Checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/monitoring/health
Invoke-RestMethod http://127.0.0.1:8000/api/monitoring/source-freshness
Invoke-RestMethod http://127.0.0.1:8000/api/monitoring/validation
Invoke-RestMethod http://127.0.0.1:8000/api/monitoring/export-manifest
Invoke-RestMethod http://127.0.0.1:8000/api/monitoring/run-history
Invoke-RestMethod http://127.0.0.1:8000/api/monitoring/security-events
Invoke-RestMethod http://127.0.0.1:8000/api/monitoring/user-access
```

## Production Route Checks

```powershell
Invoke-RestMethod https://teemails.com/Clinical/api/monitoring/health
Invoke-RestMethod https://teemails.com/Clinical/api/monitoring/source-freshness
Invoke-RestMethod https://teemails.com/Clinical/api/monitoring/validation
Invoke-RestMethod https://teemails.com/Clinical/api/monitoring/export-manifest
Invoke-RestMethod https://teemails.com/Clinical/api/monitoring/run-history
Invoke-RestMethod https://teemails.com/Clinical/api/monitoring/security-events
Invoke-RestMethod https://teemails.com/Clinical/api/monitoring/user-access
```

## Expected Results

- Every endpoint returns HTTP 200.
- `health.status` should be `ok` when PostgreSQL connectivity is healthy, otherwise `degraded`.
- `source-freshness.freshness_status` should be `ok` after producer data exists and the database is reachable.
- `validation.latest_validation_status` should be `passed` after validation.
- `export-manifest.export_status` should be `ok` after an export batch exists.
- Security and user access endpoints may return empty arrays in a fresh database, but the schema fields should always be present.

## Safety

Do not put database URLs, storage connection strings, secrets, tokens, passwords, session cookies, or MFA codes in monitoring responses. Raw IP addresses should stay masked or omitted for broad monitoring views.
