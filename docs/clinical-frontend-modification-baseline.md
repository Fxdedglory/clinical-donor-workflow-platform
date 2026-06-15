# Clinical Frontend Modification Baseline

Task: `CLINICAL-FRONTEND-MOD-00`

Date: `2026-06-15`

Decision: planning and baseline only. No deployment, DNS change, `clinical.teemails.com` launch activation, backend workflow change, database schema change, or site-wide/HR/ERP repo change was performed.

## Source-Control Baseline

| Check | Result |
| --- | --- |
| Initial `git status --short` | One dirty tracked file: `backend/app/cli.py` |
| Initial untracked files | None |
| Protected dirty file | `backend/app/cli.py` |
| Protected file decision | Preserve exactly; do not modify, format, stage, or commit |
| Package files | Not changed by this task |

The `backend/app/cli.py` diff contains pre-existing demo/seed data timestamp and donor eligibility data changes. It is unrelated to this frontend planning task and remains protected.

## Frontend Stack

| Area | Current implementation |
| --- | --- |
| Framework | React `19.2.1` with Vite `8.0.16` |
| Build package | `frontend/package.json` |
| Entry point | `frontend/src/main.jsx` |
| Main app | `frontend/src/App.jsx` |
| Routing model | Manual history routing with `window.history.pushState`, `browserRoute`, `routeToSection`, and `clinicalPatientId`; no React Router |
| Styling | Single CSS file at `frontend/src/styles.css` with Swiss-theme clinical token layer and responsive rules |
| Icons | `lucide-react` |
| API base | `VITE_API_BASE_URL`, falling back to the resolved public base |
| Build command | `cd frontend; npm run build` |
| Local dev command | `cd frontend; npm run dev` |
| Preview command | `cd frontend; npm run preview` |
| Frontend check/lint script | Not available in `frontend/package.json` |

## Route Inventory

### Public/Auth Routes

| Route | Purpose | Component path |
| --- | --- | --- |
| `/` and `/home` | Public home when unauthenticated; dashboard redirect when authenticated | `PublicHome`, `App` |
| `/login` | Demo and credential login | `LoginPage` |
| `/forgot-password` | Password reset request | `ForgotPasswordPage` |
| `/reset-password` | Password reset completion | `ResetPasswordPage` |
| `/request-access` | External/internal access request | `RequestAccessPage` |
| `/logout` | Logout flow | `LogoutPage` |
| `/profile` | User profile settings | `ProfilePage` |
| `/preferences` | Notification preferences | `PreferencesPage` |

### Clinical Workspace Routes

| Route | Current page state | Primary workflows visible |
| --- | --- | --- |
| `/clinical/dashboard` | Foundation shell placeholder | Operational overview, workflow operation activity |
| `/clinical/patients` | Implemented | Create patient/donor, edit demographics, contacts, insurance, consents |
| `/clinical/patients/:id` | Implemented resilient detail route | Patient/donor profile, contacts, insurance, consents, activity, downstream handoffs |
| `/clinical/scheduling` | Implemented | Book, reschedule, cancel, check in, no-show |
| `/clinical/screening` | Implemented | Start screening, questionnaire, vitals, eligibility/result, supervisor override |
| `/clinical/encounters` | Implemented | Create encounter, draft note, sign, amend, diagnosis/problem, allergy, medication |
| `/clinical/orders` | Implemented | Create order, receive/correct result, acknowledge critical result, cancel order |
| `/clinical/care-plans` | Implemented | Create care plan, goal, intervention, task, progress, close plan |
| `/clinical/billing` | Implemented | Verify insurance, capture charge, claim draft, post payment, denial |
| `/clinical/quality` | Implemented | Quality event, adverse event, investigation, CAPA link, closure, audit evidence export |
| `/clinical/reports` | Implemented | Aggregates, module reports, audit activity, analytics export preview/commit |
| `/clinical/admin` | Implemented | Appointment types, schedules, screening templates/rules, note templates, order catalog, billing codes, quality categories, approval paths, notifications, RBAC |

Clinical route metadata lives in `frontend/src/pages/clinical/clinicalRoutes.jsx`. Unimplemented or route-shell-only workflows are marked with `Foundation pending` or `Planned workflow` rather than hidden.

### Legacy Donor/QMS Routes

The authenticated shell also preserves legacy donor/QMS routes in `frontend/src/App.jsx`:

| Route | Purpose |
| --- | --- |
| `/dashboard` | Donor/QMS operations dashboard |
| `/referrals` | Donor referrals |
| `/screening` | Legacy screening queue metrics |
| `/clinical-review` | Clinical review metrics |
| `/eligibility` | Eligibility metrics |
| `/recovery-cases` | Recovery cases |
| `/partner-portal` | Partner portal metrics |
| `/qms` | QMS deviations |
| `/capa` | CAPA aging |
| `/vendor-sla` | Vendor SLA |
| `/documents` | Documents |
| `/audit` | Audit events |
| `/data-producer` | Producer controls |
| `/health` | System health |

## Layout And Component Inventory

| Area | Current implementation |
| --- | --- |
| App shell | `app-shell` grid with persistent sidebar and topbar |
| Portfolio navigation | External/internal portfolio links for Home, ERP, HR, Clinical, Monitor, Analytics |
| Clinical navigation | Dedicated `Clinical Workspace` sidebar group from `clinicalSections` |
| Legacy navigation | Separate `Donor/QMS Ops` sidebar group |
| Account navigation | Profile and preferences links |
| Mobile navigation | Drawer/backdrop pattern with `mobile-nav-toggle` and `mobile-nav-open` state |
| Desktop navigation | Collapsible sidebar with `PanelLeftClose` and `PanelLeftOpen` controls |
| Header/topbar | Route-aware title, route context, refresh, profile, and sign-out actions |
| Status badges | `StatusPill`, `PriorityChip`, `QualitySeverityChip`, `ResultFlagPill` |
| Metrics/cards | `MetricCard`, content grids, split panels |
| Tables | Shared `Table` and `TableCellValue` with compact clinical table classes, sensitive column handling, horizontal scroll containment |
| Clinical identifiers | `ClinicalIdentifier`, `clinicalCellKind`, monospace/truncated identifier display |
| PHI/privacy | `ClinicalPrivacyIndicator`, `ClinicalRedactedValue`, `clinicalPrivacyDisplay.js` |
| Reports/export | `ExportProfileIndicator`, `ClinicalSuppressedMetric`, small-cell suppression indicators |
| Alerts/errors | `ClinicalAlertBanner`, `notice-state`, `error-state`, `empty-state` |
| Modals | Separate workflow modal implementations for patient, scheduling, screening, encounters, orders, care plans, billing, quality, reports, and admin |

## Visual Evidence Inventory

Existing evidence was not refreshed in this planning task because current screenshot tooling is local CDP-based and this task did not require new visual capture.

| Evidence | Location | Notes |
| --- | --- | --- |
| Initial visual audit | `docs/clinical-frontend-visual-audit.md` | Documents original route shell, mobile, overflow, and failure-state findings |
| Swiss theme implementation | `docs/clinical-swiss-theme-frontend-implementation.md` | Records app shell, responsive navigation, and Swiss-theme foundation |
| FE-02 route polish | `docs/clinical-fe02-route-polish.md` | Records compact table and dense route improvements |
| FE-03 final QA | `docs/clinical-fe03-final-frontend-qa.md` | Latest frontend QA evidence |
| FE-03 manifest | `metadata/visual_audit/clinical/fe03_final_frontend_qa/manifest.json` | 17 route checks, 21 screenshots, 0 route failures, 0 modal failures, 0 console events |
| FE-03 screenshots | `metadata/visual_audit/clinical/fe03_final_frontend_qa/` | Desktop/mobile route and representative modal captures |

## Frontend Health Validation

Validation was run from the current repository checkout. No live Azure tests, deployment, DNS changes, or real Clinical launch activation were performed.

| Command/check | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe scripts\preflight_check.py` | Passed |
| `.\.venv\Scripts\python.exe -m pytest` | Passed: `303 passed, 7 skipped, 1 warning` |
| `cd frontend; npm run build` | Passed; Vite built production assets |
| `cd frontend; npm audit --audit-level=high` | Passed: `found 0 vulnerabilities` |
| `.\.venv\Scripts\python.exe scripts\start_app_service.py --check` | Passed with 5 expected local production-hardening warnings |
| `git diff --check` | Passed; Git reported line-ending normalization warning for protected `backend/app/cli.py` |
| `cd frontend; npm run check` | Not available; no `check` script exists |
| Vite preview route smoke | Passed HTTP 200 for `/`, all listed `/clinical/*` routes, and `/clinical/patients/PT-DEMO-001` |

The startup check warnings remain local hardening warnings: placeholder `SECRET_KEY`, missing `ENCRYPTION_KEY`, insecure cookies for local mode, localhost CORS origins, and demo MFA bypass configuration. These are deployment-readiness concerns, not frontend implementation blockers for this planning task.

## UX Inventory

| Area | Current assessment |
| --- | --- |
| Navigation clarity | Improved by Swiss-theme shell, separate Clinical Workspace group, mobile drawer, and sidebar collapse. Still visually dense because legacy Donor/QMS routes share the same shell. |
| Route density | FE-02/FE-03 reduced page-level overflow and identifier fragmentation. Orders, billing, quality, reports, and patient detail remain the highest-density routes and should be tuned at route level. |
| Responsive/mobile | FE-03 mobile route checks passed for dashboard, patients, orders, billing, and reports. Some dense tables still rely on contained horizontal scroll rather than a fully mobile-native pattern. |
| Dashboard clarity | `/clinical/dashboard` remains a foundation shell placeholder. It needs real module status, workflow activity, and operational next-action cards once backend dashboard contract is approved. |
| Patient/donor forms | Registration/edit/contact/insurance/consent flows exist, but the modal structure is not yet standardized across workflow types. |
| Preview -> Commit clarity | Backend guard and confirmation pattern are present. UI modals vary: reports export uses a clear preview/commit state, while several workflow modals still use local step/action patterns. |
| Eligibility/status badges | Shared status pills and chips exist; next pass should normalize status vocabulary across patient, screening, orders, care plan, billing, quality, and reports. |
| Tables and filters | Shared table path supports compact clinical density. Route-specific filter bars and action clusters remain inconsistent in priority, wrapping, and empty-state placement. |
| Report/export gating | Reports show export profile and suppression indicators. Export gating copy should be made more explicit for external-safe, aggregate-safe, audit-metadata, and internal-detail contexts. |
| PHI/masking | Privacy helpers and redaction/suppression indicators are in place. External/limited-role messaging should be reviewed with Security/Product before production launch. |
| Empty/loading/error states | States exist, including diagnostic API failure copy. They are implemented route-by-route and should be consolidated into reusable clinical state components. |
| Accessibility/contrast | Swiss-theme colors are restrained and route QA passed visual smoke. Future pass should verify keyboard order, focus visibility, modal focus trapping, and screen-reader naming. |
| Copy clarity | Operational copy is generally clear but long action labels compete in dense modules. Button labels and status text should be shortened where icons/tooltips can carry context. |
| Deployment readiness messaging | `clinical.teemails.com` remains a recommended future URL only. The frontend should not display or link it as active until hosting, DNS, TLS, health checks, and approvals complete. |
| Swiss enterprise alignment | Good foundation: neutral palette, compact tables, restrained borders. Further route-level polish should reduce repeated panels and strengthen grid alignment. |

## Safe Change Themes

- Standardize route headers, filter bars, and action clusters without changing backend contracts.
- Extract reusable empty, loading, backend-unavailable, and permission-denied clinical state components.
- Normalize status badge vocabulary and severity mapping in the frontend display layer.
- Refine mobile treatment for dense tables using progressive row summaries and detail expansion.
- Standardize Preview -> Commit modal anatomy while preserving existing endpoints and `X-Confirm-Generation: true`.
- Add frontend-only route smoke documentation around existing FE-03 screenshot evidence.

## CLINICAL-FE-04 Implementation Addendum

Task `CLINICAL-FE-04` implemented the safe route-level polish recommended by this baseline.

| Area | Result |
| --- | --- |
| Shared route header | Implemented `ClinicalPageHeader` for implemented clinical routes and aligned the dashboard shell placeholder. |
| Shared route state | Implemented `ClinicalStateMessage` and applied consistent loading, empty, select-row, and retry/error patterns to clinical work queues. |
| Status badges | Normalized frontend status labels and tone mapping for active, planned, pending, completed, blocked, failed, and related statuses. |
| Workflow modals | Added reusable workflow modal header, step indicator, and validation summary components for Draft -> Validate -> Preview -> Commit presentation. |
| Preview -> Commit copy | Replaced remaining generic confirmation labels with commit-specific labels in billing and reports/export flows. |
| Validation | Passed preflight, pytest, frontend build, npm audit, app-service startup check, and Vite preview route smoke. |
| Evidence doc | `docs/clinical-fe04-route-polish-summary.md` |

FE-04 preserved the protected dirty `backend/app/cli.py` file and did not change backend workflow semantics, database schema, deployment, DNS, or launch links.

## Risky Or Blocked Themes

- Any change that alters clinical workflow commit semantics or backend audit behavior requires backend contract review.
- Any live `https://clinical.teemails.com` link or launch action requires hosting, DNS, TLS, health checks, and Product/Security/Ops approval.
- Any auth/SSO or role-personalized navigation change requires security and deployment review.
- Any database-backed dashboard redesign needs an approved API/data contract.
- Any dependency remediation or new UI library requires explicit scope.
- The protected dirty `backend/app/cli.py` must remain excluded from frontend docs commits.

## Recommended Next Sprint

Recommended next implementation sprint:

`CLINICAL-FE-05 - Mobile Dense-Route Interaction`

Suggested scope:

- Product/design review of mobile row summaries for dense clinical tables.
- Detail expansion patterns for orders, billing, quality, reports, and patient detail.
- Mobile keyboard/focus review for dense route workflows.
- Keep backend workflow logic, database schema, deployment, DNS, and launch links unchanged.
- Preserve FE-04 route headers, state messages, status badges, and Preview -> Commit semantics.
- Reuse the current React/Vite/CSS stack and existing components.
