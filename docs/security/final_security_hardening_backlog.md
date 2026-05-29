# Final Security Hardening Backlog

## Before Public Hosting

- Replace all local placeholder secrets.
- Set `COOKIE_SECURE=true`.
- Use strong `SECRET_KEY`.
- Configure production `ENCRYPTION_KEY`.
- Review CSP for React static assets and API routes.
- Confirm partner org scoping on every partner-facing endpoint.
- Disable demo MFA bypass in production.
- Confirm password policy values.
- Confirm session timeout and refresh-token rotation.
- Run dependency vulnerability checks.
- Enable App Service HTTPS-only.
- Store secrets in App Service settings or Key Vault later.

## Before External Partner Access

- Review partner role permissions.
- Test cross-organization access attempts.
- Add explicit partner access tests.
- Add audit events for partner submission/document reads.
- Add document retention and deletion policy.
- Add incident response contact path.

## Before Regulated Demo Review

- Add validation evidence for deployment build and data producer behavior.
- Add database backup/restore runbook for Azure PostgreSQL.
- Add immutable audit/event retention plan.
- Add clinical disclaimer that data is synthetic and not patient data.
- Add dependency patch cadence.
- Add security logging retention plan.

## Later Enhancements

- Microsoft Entra ID for internal staff.
- External partner identity decision.
- Key Vault integration.
- Managed identity for database if feasible.
- Application Insights traces with PII-safe telemetry rules.
- Rate limiting and bot protection at the edge.
