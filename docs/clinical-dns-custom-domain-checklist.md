# Clinical DNS And Custom Domain Checklist

Task: `CLINICAL-DEPLOY-02`

Recommended host: `clinical.teemails.com`

Preferred hosting: single App Service-style app serving FastAPI plus built React frontend.

This checklist is a planning and execution handoff. DEPLOY-02 does not create DNS records, bind domains, or issue certificates.

## DNS Record Options

| Status | Option | Use when | Required records | Notes |
| --- | --- | --- | --- | --- |
| [ ] | CNAME to App Service default hostname | Preferred for subdomain routing. | `clinical` CNAME to `<app-name>.azurewebsites.net` plus App Service validation record if required. | Easiest rollback and aligns with `clinical.teemails.com`. |
| [ ] | A record with TXT validation | Required only if apex-like or platform-specific mapping needs IP-based record. | A record to App Service IP plus TXT validation record. | Higher operational care because IP changes must be tracked. |
| [ ] | Gateway/front-door CNAME | Use only if site-wide routing layer fronts the app. | CNAME to approved gateway endpoint. | Requires extra header, path, TLS, and health checks. |

## App Service Custom Domain Steps

1. Confirm final Web App name and default hostname.
2. In App Service, start custom domain add flow for `clinical.teemails.com`.
3. Capture required validation record values from the portal or approved IaC output.
4. Ask DNS owner to create validation records.
5. Wait for DNS propagation.
6. Complete App Service custom domain validation.
7. Bind `clinical.teemails.com` to the Web App.
8. Enable HTTPS-only.
9. Bind App Service managed certificate or approved certificate.
10. Record certificate owner and expiration/renewal evidence outside Git.

## TLS And Cookie Checks

- `APP_BASE_URL=https://clinical.teemails.com`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax` or approved `strict`
- `CORS_ORIGINS` includes exact approved origins only.
- Browser smoke should confirm login/session cookies are secure and scoped to the approved host.

## Health Checks After DNS

Run after DNS propagation and certificate binding:

```powershell
Invoke-RestMethod https://clinical.teemails.com/api/health
Invoke-WebRequest https://clinical.teemails.com/clinical/dashboard
Invoke-RestMethod https://clinical.teemails.com/api/monitoring/health
```

Expected:

- `/api/health` returns `status=ok`.
- `/clinical/dashboard` returns the React SPA.
- `/api/monitoring/health` reports database connectivity after migrations and app settings are complete.

## Rollback DNS Notes

- Keep previous DNS values and TTLs in the external change ticket.
- Lower TTL before cutover if allowed by DNS policy.
- Roll back DNS only with Operations approval because cached clients may see mixed routing during TTL windows.
- App rollback should be attempted before DNS rollback when the DNS route is healthy but the new artifact is faulty.

## Site-Wide App Launcher Relationship

- The site-wide app launcher can link to `https://clinical.teemails.com` after Product Owner and site-wide owner approval.
- The Clinical backend remains the authorization boundary.
- Do not touch the teemails repository in DEPLOY-02.
- `docs/clinical-site-integration-manifest.json` is the handoff contract for SITE-WIDE-00 planning.

## Path Routing Alternative

Alternative host/path: `https://teemails.com/clinical`

Use this only if the site-wide platform explicitly rejects the subdomain model. Path-prefix routing has added risks:

- SPA asset URLs under `/assets/...` may require rewrite rules or a Vite base path change.
- API routes under `/api/...` may collide with site-wide APIs unless gateway routing is precise.
- Cookies need careful path/domain scoping.
- Browser refresh on nested routes such as `/clinical/dashboard` must fall back to the React index.
- CORS and same-origin assumptions change if the API is split from the frontend.
- Rollback needs gateway and app coordination, not just App Service artifact rollback.
