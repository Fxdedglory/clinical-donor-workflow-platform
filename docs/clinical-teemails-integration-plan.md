# Clinical teemails Integration Plan

Task: `CLINICAL-DEPLOY-00`

Release baseline: `f7d186f Finalize clinical frontend QA polish`

This is a planning and handoff document only. It does not deploy the Clinical app, create DNS records, create cloud resources, or wire the Clinical app into the teemails site-wide repository.

## Recommendation

Recommended public URL for first hosted release:

```text
https://clinical.teemails.com
```

Rationale:

- It avoids path-prefix ambiguity between the portfolio site and the Clinical app's internal `/clinical/...` routes.
- It keeps `/api/...`, `/assets/...`, `/health`, `/api/health`, and `/api/monitoring/health` simple.
- It reduces risk around browser cookies, static assets, and SPA fallback routing.
- It can still be linked from the main teemails navigation and future unified app launcher.

Secondary option:

```text
https://teemails.com/clinical
```

This is viable later, but it requires a portfolio gateway, Azure Front Door, Cloudflare Worker, or equivalent edge routing layer that is explicitly tested with the React/Vite app, FastAPI fallback routes, static assets, and API paths. Existing historical docs reference `/Clinical`; a lowercase `/clinical` portfolio path should be tested deliberately before cutover.

## Subdomain vs Path Routing

| Area | `clinical.teemails.com` | `teemails.com/clinical` |
| --- | --- | --- |
| Operational fit | Best first release fit. Clinical is a full app with many routes and APIs. | Works if a gateway owns path rewriting and SPA fallback behavior. |
| Static assets | Simple `/assets/...` serving from the Clinical app. | Requires asset path strategy so `/assets/...` does not collide with the main site. |
| API routing | Simple `/api/...` origin on the same Clinical host. | Must decide whether `/clinical/api/...` rewrites to `/api/...` or whether API remains on a separate backend host. |
| Cookies | Dedicated host reduces collision with teemails main-site cookies. | Shared parent domain/path needs careful cookie path, SameSite, and session testing. |
| CORS | Can run same-origin if FastAPI serves React. | Path-based same-origin is possible, but split API or gateway rewrites can reintroduce CORS. |
| Rollback | DNS or gateway route can be rolled back independently. | Main-site route changes and Clinical app rollback may be coupled. |
| User mental model | Clean "Clinical" app destination. | Feels integrated into the main site navigation. |

## CORS Implications

Single-host App Service serving React and API:

- `SERVE_FRONTEND=true`
- `APP_BASE_URL=https://clinical.teemails.com`
- `CORS_ORIGINS` may include `https://clinical.teemails.com`, `https://teemails.com`, and `https://www.teemails.com` if the main site links or embeds API-aware surfaces.
- No wildcard origins in production.
- No localhost or loopback origins in production.

Separate frontend/backend hosts:

- Frontend host, for example `https://clinical.teemails.com`, must be listed in backend `CORS_ORIGINS`.
- If backend is `https://clinical-api.teemails.com`, do not use wildcard CORS.
- Cookies and Authorization headers require `allow_credentials` and exact origins.

Path routing:

- If the main site serves the frontend and the backend remains separate, CORS must include the main site origin.
- If a gateway rewrites `/clinical/api/*` to backend `/api/*`, test preflight behavior and preserve auth headers.

## Cookie and Session Implications

Production settings should include:

- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax` unless a reviewed cross-site redirect flow requires another approved value
- `SESSION_TIMEOUT_MINUTES=30` or an approved production timeout
- Generated `SECRET_KEY` and `ENCRYPTION_KEY` outside Git

Subdomain deployment can isolate Clinical cookies by host. Path deployment may need explicit cookie path review so Clinical sessions do not collide with teemails main-site sessions.

## Auth Implications

Current auth is platform-native JWT/RBAC with MFA foundation. Entra integration is planned but not required for the deployment inventory sprint.

Integration expectations:

- Main teemails site should link users to Clinical; it should not impersonate users or inject Clinical tokens.
- Clinical retains backend authorization as the source of truth.
- External partner users remain blocked from internal Clinical modules by backend permissions.
- Future unified SSO/app launcher should be planned as a separate security sprint.

## Static Asset Routing Implications

Current app behavior:

- Vite build command: `cd frontend; npm run build`
- FastAPI serves `frontend/dist` when `SERVE_FRONTEND=true`.
- FastAPI mounts `/assets` from `frontend/dist/assets` when the directory exists.
- FastAPI returns `index.html` for non-API app routes through its fallback route.

Subdomain routing keeps this straightforward. Path routing must verify:

- SPA fallback under the chosen path.
- Static asset URLs.
- Browser refresh on `/clinical/dashboard` and other nested routes.
- Existing route logic that treats `/Clinical` as a public base does not conflict with lowercase portfolio routing.

## API Routing Implications

Important health and API endpoints:

- `GET /health`
- `GET /api/health`
- `GET /api/monitoring/health`
- `GET /api/clinical/status`
- `GET /api/clinical/modules`

For subdomain single-host deployment, API and frontend are same-origin:

```text
https://clinical.teemails.com/api/health
https://clinical.teemails.com/clinical/dashboard
```

For separate backend deployment, the frontend must be built with:

```text
VITE_API_BASE_URL=https://<clinical-api-host>
```

For path routing, the site-wide gateway must define whether APIs are:

```text
https://teemails.com/clinical/api/...
```

or:

```text
https://clinical-api.teemails.com/api/...
```

## Health Check URL

Recommended production health checks:

- App availability: `https://clinical.teemails.com/api/health`
- Database-aware monitoring: `https://clinical.teemails.com/api/monitoring/health`
- Frontend route smoke: `https://clinical.teemails.com/clinical/dashboard`

Use `/api/monitoring/health` for operations readiness because it reports database reachability and storage backend metadata.

## Navigation Links Needed From teemails Main Site

Recommended top-level navigation entry:

- Label: `Clinical`
- URL: `https://clinical.teemails.com/clinical/dashboard`
- Status badge: `Production prep`
- Audience: internal clinical, operations, quality, billing, reporting, and admin users

Recommended deep links:

- `Patients / Donors` -> `/clinical/patients`
- `Scheduling` -> `/clinical/scheduling`
- `Screening` -> `/clinical/screening`
- `Orders / Results` -> `/clinical/orders`
- `Billing` -> `/clinical/billing`
- `Quality` -> `/clinical/quality`
- `Reports` -> `/clinical/reports`
- `Clinical Admin` -> `/clinical/admin`

## Cross-Links to HR and ERP Platforms

Planned portfolio cross-links:

- HR platform -> Clinical role/access request status and training readiness.
- ERP platform -> Billing, claims, cost center, and financial operations handoff.
- Clinical platform -> HR for user role lifecycle and SOP/training ownership.
- Clinical platform -> ERP for billing/cash posting, procurement/vendor, and accounting workflows.

No cross-repo wiring is included in this sprint.

## Future Unified App Launcher Concept

A future teemails app launcher can display:

- Clinical
- HR
- ERP
- Analytics
- Admin / Identity

Launcher metadata should come from a site-wide manifest. The Clinical handoff manifest in `docs/clinical-site-integration-manifest.json` provides the first draft for that downstream integration.

## Site-Wide Integration Readiness

Ready for site-wide planning:

- Route inventory is complete.
- Frontend QA evidence exists under `metadata/visual_audit/clinical/fe03_final_frontend_qa/`.
- Local demo setup is documented in `docs/clinical-local-demo-setup.md`.
- Production readiness docs exist.
- Deployment blockers are documented in `docs/clinical-deployment-blockers.md`.

Not ready without environment provisioning:

- DNS decision and record creation.
- Hosting target selection.
- Production PostgreSQL provisioning.
- Production secrets.
- Live Azure WORM and Key Vault validation approval.
