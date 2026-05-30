# Clinical Authentication Fix Plan

Date: 2026-05-29

## Fix Applied In This Pass

### Path-Prefix API Base

Problem:

- Clinical is served publicly at `https://teemails.com/Clinical`.
- The frontend previously defaulted to an empty API base.
- If a browser request goes to root `/api/...`, Cloudflare does not route it to the Clinical origin.

Change:

- `frontend/src/App.jsx` now resolves `API_BASE` to `/Clinical` when the current browser path starts with `/Clinical`.
- Direct Azure hostname and local dev still use an empty API base unless `VITE_API_BASE_URL` is configured.

Why this is safe:

- It is frontend-only.
- It does not change backend auth semantics.
- It preserves local development.
- It reduces reliance on Worker text rewriting.

Validation:

- `ruff check .` passed.
- `pytest` passed.
- `npm run build` passed.

## Immediate Follow-Up Fixes

1. Add React MFA flow.

   Current behavior: MFA-required users receive a challenge, but the UI cannot submit `/api/auth/mfa/verify`.

   Required behavior:

   - Show an MFA challenge form after login response.
   - Submit challenge ID and verification code.
   - Store returned session payload only after MFA succeeds.
   - Log failure/success outcomes through existing backend audit logic.

2. Change default demo login selection.

   Current behavior: the login panel defaults to an administrator-style account that requires MFA.

   Safer demo behavior:

   - Default to a non-MFA demo role for local portfolio review.
   - Add a role selector or "demo account" selector without exposing passwords.
   - Keep administrator accounts MFA-required.

3. Remove hard-coded demo password defaults from the frontend.

   Current behavior: source code includes a demo password default for convenience.

   Target behavior:

   - Keep demo credentials in a local-only runbook section, never in production UI source.
   - Use an empty password field by default.
   - If demo autofill is needed locally, gate it behind `VITE_ENABLE_DEMO_LOGIN_HINTS=true`.

4. Call backend logout.

   Current behavior: logout only clears browser local storage.

   Target behavior:

   - `POST /api/auth/logout` or equivalent should revoke the active session.
   - Then clear local storage.
   - Handle expired tokens gracefully.

5. Add explicit Azure auth/cookie settings.

   Recommended settings for native auth until Entra replaces it:

   - `SECRET_KEY`: generated secret, not default source value.
   - `COOKIE_SECURE=true`
   - `COOKIE_SAMESITE=lax`
   - `COOKIE_PATH=/Clinical` if cookies remain app-scoped.
   - Token lifetimes reviewed for public portfolio use.

6. Tighten runtime role permissions.

   Observed `clinical_runtime` is not admin and owns no operational objects, but it has broad CRUD on auth tables. Review whether it needs delete privileges on role/user tables after backend session and admin flows are finalized.

## Future Entra ID Direction

Clinical should eventually move from native username/password auth to Microsoft Entra ID for internal users. Native partner portal auth may remain separate or move to Entra External ID/B2B depending on partner onboarding requirements.

Recommended sequence:

1. Stabilize native auth UI enough for demo and admin recovery.
2. Implement Entra ID for internal Clinical routes.
3. Keep partner portal access organization-scoped and least-privilege.
4. Add Monitoring integration for login success/failure, access denied, role resolution, MFA events, and partner activity.
5. Retire or restrict native internal username/password accounts.

## Deployment Plan For The Applied Fix

This pass changed source only. To deploy later:

1. Build frontend locally.
2. Run tests.
3. Commit source changes and docs.
4. Deploy Clinical app package to Azure App Service.
5. Verify:
   - `https://teemails.com/Clinical`
   - `https://teemails.com/Clinical/api/monitoring/health`
   - Login with a non-MFA demo user.
   - MFA-required user shows the expected MFA-needed message until UI support is added.

## Rollback Plan

If the API base inference causes a regression:

1. Revert the `resolveApiBase()` change in `frontend/src/App.jsx`.
2. Rebuild and redeploy Clinical.
3. Confirm Worker text rewriting still handles `/api` references in built JavaScript.

Rollback should not require database, Cloudflare, or Azure topology changes.
