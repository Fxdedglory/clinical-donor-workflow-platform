# Clinical Frontend Manual Browser QA

Task: `CLINICAL-FRONTEND-QA-00`

Date: `2026-06-15`

Purpose: provide repeatable manual QA coverage for the Clinical frontend shell and current route set after FE-04 and FE-05 route/mobile polish. This task did not deploy, activate production launch links, change DNS, alter backend workflow semantics, or modify database schema.

## Guardrails

| Guardrail | Status |
| --- | --- |
| `AGENTS.md` followed | Passed |
| Protected dirty file reported | Passed: `backend/app/cli.py` only |
| Protected dirty file preserved | Passed |
| New clinical modules | Not added |
| Production launch links | Not activated |
| Real Azure credentials/tests | Not used |

## Browser QA Setup

| Step | Command or value |
| --- | --- |
| Start local database | Existing local PostgreSQL demo data on `127.0.0.1:55432` |
| Apply migrations | `.\.venv\Scripts\python.exe -m alembic upgrade head` |
| Seed demo data | `.\.venv\Scripts\python.exe scripts\seed_clinical_demo_data.py` |
| Start backend | `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012` from `backend/` |
| Start frontend | `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5183 --strictPort` from `frontend/` |
| Local CORS | `CORS_ORIGINS=["http://127.0.0.1:5183","http://localhost:5183"]` |
| Login user | `clinical_demo` with local demo MFA |

Browser plugin support was unavailable, and no Playwright dependency exists in the repo. The evidence run used installed Chrome through the Chrome DevTools Protocol without adding dependencies.

## Manual Checklist

| Area | Check | Result |
| --- | --- | --- |
| Authentication | Demo user can establish an authenticated browser session | Passed |
| `/` | Authenticated root lands on dashboard content and is not blank | Passed |
| Clinical navigation | All required clinical routes are visible and navigable | Passed |
| Desktop shell | Sidebar, topbar, route title, refresh/profile/sign-out controls render | Passed |
| Mobile shell | Drawer opens and closes; route content remains reachable | Passed |
| Tablet layout | Clinical routes render without page-level horizontal overflow | Passed |
| PHI indicators | Protected clinical routes show PHI/privacy cues | Passed |
| Export indicators | Quality and reports show export profile cues | Passed |
| Suppression indicators | Reports show small-cell suppression cues where applicable | Passed |
| Planned workflows | Foundation-pending/planned states remain visible instead of hidden | Passed |
| Console health | No console errors or warnings captured during route sweep | Passed |
| Framework overlays | No Vite/framework error overlay captured | Passed |

## Route Checklist

| Route | Manual QA focus | Result |
| --- | --- | --- |
| `/clinical/dashboard` | Foundation shell, route status, operational next-step messaging | Passed |
| `/clinical/patients` | Patient/donor list, filters, PHI cue, create action | Passed |
| `/clinical/patients/PT-DEMO-001` | Demo patient detail, identifiers, detail tables, audit/handoff context | Passed |
| `/clinical/scheduling` | Appointment list, filters, book action, selected appointment detail | Passed |
| `/clinical/screening` | Screening queue, eligibility/result actions, planned states | Passed |
| `/clinical/encounters` | Encounter queue, note/signature actions, detail sections | Passed |
| `/clinical/orders` | Orders/results queue, result flags, result modal entry point | Passed |
| `/clinical/care-plans` | Care plan queue, task/progress hierarchy, responsive rows | Passed |
| `/clinical/billing` | Billing account/claim queue, payer context, dense tables | Passed |
| `/clinical/quality` | Quality events, CAPA/evidence workflow cues, export profile | Passed |
| `/clinical/reports` | Reports, analytics export modal, suppression/export indicators | Passed |
| `/clinical/admin` | Configuration lists, approval paths, RBAC/admin context | Passed |

## Workflow Modal Checklist

| Modal | Route | Manual QA focus | Result |
| --- | --- | --- | --- |
| Create Patient / Donor | `/clinical/patients` | Draft to validation state, validation summary, action footer | Passed |
| Book Appointment | `/clinical/scheduling` | Form structure, validation step, footer containment | Passed |
| Enter Result | `/clinical/orders` | Result form visibility, preview/commit path entry, modal fit | Passed |
| Generate Analytics Export | `/clinical/reports` | Export preview, suppression/export messaging, modal fit | Passed |

## Responsive Checklist

| Viewport | Size | Result |
| --- | --- | --- |
| Desktop | `1440x1000` | Passed |
| Tablet | `820x1180` | Passed |
| Mobile | `390x844` | Passed |

No route showed page-level horizontal overflow in the captured route sweep. Dense tables remained contained and mobile-card/labeled table treatment stayed readable.

## Remaining Manual QA Gaps

| Gap | Classification | Reason |
| --- | --- | --- |
| Cross-browser manual QA | `defer` | Only installed Chrome/CDP was used in this evidence package. |
| Keyboard-only modal traversal | `needs_design_decision` | Focus trapping and complete keyboard order need a dedicated accessibility pass. |
| Screen-reader pass | `needs_design_decision` | Requires assistive-tech QA beyond the current visual/browser smoke. |
| Production host QA | `needs_auth_or_deployment_approval` | `clinical.teemails.com` is not deployed or approved for activation. |
| Full commit workflow mutation QA | `needs_backend_contract` | This QA package focused route visibility and modal entry points, not durable workflow commits. |

## Result

Manual browser QA passed for the approved local route and screenshot evidence scope. The next frontend QA step should be a dedicated accessibility and keyboard pass, or a Product-approved committed visual smoke harness.
