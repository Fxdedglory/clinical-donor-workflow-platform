# Clinical Authentication Audit

Date: 2026-05-29

Scope: Clinical Donor Platform only. This audit did not implement Microsoft Entra ID for Clinical, did not change Azure topology, did not change Cloudflare routes, and did not print or document secret values.

## Executive Summary

Clinical already has a native FastAPI authentication and RBAC layer with seeded internal and external demo users, role-to-permission mappings, session records, MFA policy flags, and protected API routes. The backend auth model is more complete than the current React login UI.

The main confirmed login defect was path-prefix sensitivity. Under `https://teemails.com/Clinical`, root `/api/...` requests do not route to Clinical, while `/Clinical/api/...` does. The React frontend previously defaulted to an empty API base and relied on Cloudflare Worker JavaScript rewriting. A small safe fix was applied so the frontend infers `/Clinical` when served under the Cloudflare path prefix.

The next material auth gap is not database seeding; users and roles exist in Azure PostgreSQL. The larger gaps are UI and hardening:

- MFA-required demo roles cannot complete MFA in the React UI yet.
- Logout clears only browser local storage and does not revoke the backend session.
- Demo credentials are still hard-coded in source for convenience and should be removed before wider sharing.
- Azure App Settings do not currently include explicit cookie/security settings such as `SECRET_KEY`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, or `COOKIE_PATH`.
- Clinical native auth should remain temporary until the planned Microsoft Entra ID model is implemented.

## Current Auth Architecture

Backend:

- FastAPI auth router: `backend/app/routes/auth.py`
- Dependency enforcement: `backend/app/auth/dependencies.py`
- Password/JWT helpers: `backend/app/auth/security.py`
- Role and permission seed definitions: `backend/app/services/access_control.py`
- Auth-related models: `backend/app/models/entities.py`
- Seed/bootstrap workflow: `backend/app/cli.py`

Frontend:

- React/Vite operational UI: `frontend/src/App.jsx`
- Token payload stored in `localStorage` under `clinical_token_payload`
- API calls use a Bearer access token after login
- React MFA flow is not implemented yet

Database:

- Azure PostgreSQL database: `clinical_donor_workflow`
- Runtime database role observed: `clinical_runtime`
- Operational schema: `operational`

## Login Flow

Current backend flow:

1. `POST /api/auth/login` accepts OAuth2 password form fields.
2. User is looked up by username or email.
3. Password hash is verified with Passlib.
4. If role/user policy requires MFA, the response returns an MFA challenge rather than access tokens.
5. If MFA is not required, backend creates a session record, returns tokens, and sets access/refresh cookies.
6. `GET /api/auth/me` resolves the current user from Bearer token or cookie.

Current frontend flow:

1. Login panel posts username/password.
2. If tokens are returned, the payload is stored in browser local storage.
3. Subsequent calls send `Authorization: Bearer <access_token>`.
4. If `mfa_required=true`, the UI shows an error and cannot complete MFA.
5. Sign out removes local storage only.

## Route Prefix Finding

Safe route checks showed:

| URL | Result | Meaning |
|---|---:|---|
| `https://teemails.com/api/auth/me` | 404 | Root `/api` is not routed to Clinical. |
| `https://teemails.com/Clinical/api/auth/me` | 401 | Request reaches Clinical and is unauthenticated, as expected. |
| `https://teemails.com/Clinical/api/monitoring/health` | 200 | Clinical prefixed API routing works. |

Fix applied:

- `frontend/src/App.jsx` now resolves the API base to `/Clinical` when `window.location.pathname` starts with `/Clinical`.
- Local development and direct Azure hostname behavior still use an empty API base unless `VITE_API_BASE_URL` is configured.

## Seeded Users And Roles

Azure PostgreSQL contains seeded users, roles, auth identities, MFA configuration, and partner organizations. This audit verified password hashes against the seed default without printing the password value.

Observed counts:

| Entity | Count |
|---|---:|
| Users | 11 |
| Active users | 11 |
| Roles | 9 |
| Role permissions | 111 |
| Auth identities | 11 |
| MFA configurations | 11 |
| User sessions | 1 |
| Non-internal partner organizations | 3 |

Observed roles:

| Role | User count | Permission count | MFA posture |
|---|---:|---:|---|
| System Administrator | 1 | 27 | MFA required |
| Donor Intake Coordinator | 1 | 8 | MFA not required |
| Clinical Reviewer | 1 | 9 | MFA policy currently not required |
| Quality Assurance Specialist | 1 | 14 | MFA required |
| Vendor Operations Analyst | 1 | 9 | MFA not required |
| Operations Manager | 1 | 16 | MFA required |
| Business Technology Analyst | 1 | 12 | MFA required |
| Partner External User | 4 | 8 | MFA required |
| Supplier External User | 0 | 8 | compatibility role |

Notes:

- The seed default password is present in source as a constant and in the frontend demo defaults. The value is intentionally not documented here.
- Password hash verification succeeded for the observed seeded demo accounts.
- MFA-required roles cannot complete the full login flow from the React UI yet.

## Protected API Surface

Clinical has meaningful route-level permission checks:

| Area | Route prefix | Representative permissions |
|---|---|---|
| Admin | `/api/admin` | `users.manage`, `system.admin` |
| Donors | `/api/donors` | `donors.read`, `donors.create`, `donors.review` |
| Eligibility | `/api/eligibility` | `eligibility.read`, `eligibility.review` |
| Partner portal | `/api/partners` | `partner.portal`, `partners.read`, `partners.manage` |
| Supplier compatibility | `/api/suppliers` | `supplier.portal`, `suppliers.read`, `suppliers.manage` |
| QMS | `/api/change-control`, `/api/training` | `qms.manage`, `training.manage` |
| Vendor SLA | `/api/vendors` | `vendors.read`, `vendors.manage` |
| Audit logs | `/api/audit-logs` | `audit.review`, `security.audit` |
| Data producer | `/api/generation/*` | `system.admin` |
| Workspaces | `/api/workspaces` | current user plus `workflow.configure` for admin changes |

## Runtime Database Role

The Azure app is using `clinical_runtime`.

Observed database posture:

- Current user: `clinical_runtime`
- PostgreSQL SSL: enabled, TLS 1.3 observed
- Superuser: no
- Create database: no
- Create role: no
- Bypass RLS: no
- Schema create on `operational`: no
- Owned operational objects: 0

The runtime role has CRUD privileges on the checked auth tables, including `dim_user`, `dim_role`, `bridge_role_permission`, `dim_auth_identity`, `dim_mfa_configuration`, `dim_user_session`, and `fact_security_audit`. This is not blocking auth, but it is broader than ideal for long-term least-privilege design.

## Cookie And Session Findings

Backend cookies:

- Access cookie: `cdwp_access_token`
- Refresh cookie: `cdwp_refresh_token`
- Default cookie path in source: `/`
- Default `COOKIE_SECURE`: false unless configured
- Default `COOKIE_SAMESITE`: `lax`

Cloudflare Worker behavior:

- Worker rewrites `Set-Cookie` paths to the app prefix when proxying prefixed routes.
- Worker sends `X-Forwarded-Host`, `X-Forwarded-Proto`, and `X-Forwarded-Prefix`.

Frontend behavior:

- The UI primarily uses localStorage plus Bearer token headers.
- Logout does not call backend logout, so server-side sessions may remain until expiration.

Recommended next hardening:

- Configure `COOKIE_SECURE=true`.
- Use an explicit Clinical cookie path policy when native auth remains enabled.
- Revoke backend sessions during logout.
- Remove localStorage token persistence or replace it with a safer session-cookie pattern during Entra migration.

## Azure App Settings Observed

The Clinical Azure Web App has the expected serving and database settings, including `DATABASE_URL`, frontend serving settings, Oryx build settings, and producer roots.

Security-related gaps:

- No explicit `SECRET_KEY` app setting was observed.
- No explicit `COOKIE_SECURE`, `COOKIE_SAMESITE`, or `COOKIE_PATH` app settings were observed.
- No explicit MFA dev-bypass app setting was observed.

Do not print or commit actual App Setting values. Add security settings only through Azure App Settings or Key Vault-backed references in a future approved hardening pass.

## Root Causes For Current Role Usability Issues

1. The React UI could route API calls incorrectly under `/Clinical` unless Worker text rewriting caught the built JavaScript. This was fixed at source.
2. The default login panel points at an MFA-required administrator account, but the React UI cannot complete MFA.
3. Several realistic roles exist but are not exposed as a role-aware login selector or guided demo flow.
4. Backend role permissions exist, but the current UI is still a compact operations dashboard rather than a full role-scoped portal.
5. Logout is client-side only.

## Checks Run

- Clinical route checks through Cloudflare for root `/api`, prefixed auth, and prefixed monitoring health.
- Azure App Settings inventory with values redacted.
- Azure PostgreSQL read-only auth inventory using the `clinical_runtime` connection.
- Password hash verification against seeded demo accounts without printing password values.
- `ruff check .`
- `pytest`
- `npm run build`

## Non-Goals

This pass did not:

- Implement Entra ID for Clinical.
- Change Cloudflare production routes.
- Change Azure topology.
- Rotate secrets.
- Modify database roles or grants.
- Run login POSTs against production.
- Generate bulk data.
