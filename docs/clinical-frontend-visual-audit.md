# Clinical Frontend Visual Audit

Audit date: 2026-06-13 America/New_York

Accepted baseline: `7fd6dfb Add production evidence bundle readiness`

Scope: frontend visual verification and screenshot audit for the clinical route shell. This audit does not redesign, refactor, deploy, add backend features, or modify `backend/app/cli.py`.

## Launch Summary

| Check | Result |
| --- | --- |
| `git status --short` before work | Only `backend/app/cli.py` was dirty. |
| `git diff -- backend/app/cli.py` before work | Existing seed-data timestamp/referral changes only; preserved and not modified. |
| Existing port `8000` | Occupied by a different local app returning `hr-workforce-simulator`. |
| Existing port `5173` | Occupied by an existing Node/Vite process. |
| Audit backend launch | Started this repo on `http://127.0.0.1:8011`; stopped after capture. |
| Audit frontend launch | Started this repo on `http://127.0.0.1:5174`; stopped after capture. |
| Backend health | `GET /api/health` returned this app: `Clinical Donor Screening & Quality Workflow Platform`. |
| Clinical foundation API | `GET /api/clinical/status` returned `foundation_ready`. |
| Authenticated data state | Demo login failed because local `DATABASE_URL` resolves host `db`, which is not available from this host shell. |
| Screenshot method | Browser plugin unavailable; project Playwright unavailable; used installed Chrome headless through DevTools protocol. |

The screenshots use a temporary localStorage visual-audit session so route shells can render without changing source code. API-backed data calls show `Failed to fetch` because the local database was unavailable. Treat the screenshots as route-shell and layout evidence, not full happy-path data evidence.

Generated screenshots are local audit artifacts and intentionally ignored by git:

`metadata/visual_audit/clinical/current/`

## Screenshot Inventory

| Route | Viewport | Screenshot |
| --- | --- | --- |
| `/clinical/dashboard` | 1440x1100 | `clinical-dashboard-desktop.png` |
| `/clinical/patients` | 1440x1100 | `clinical-patients-desktop.png` |
| `/clinical/patients/PT-000001` | 1440x1100 | `clinical-patient-detail-desktop.png` |
| `/clinical/scheduling` | 1440x1100 | `clinical-scheduling-desktop.png` |
| `/clinical/screening` | 1440x1100 | `clinical-screening-desktop.png` |
| `/clinical/encounters` | 1440x1100 | `clinical-encounters-desktop.png` |
| `/clinical/orders` | 1440x1100 | `clinical-orders-desktop.png` |
| `/clinical/care-plans` | 1440x1100 | `clinical-care-plans-desktop.png` |
| `/clinical/billing` | 1440x1100 | `clinical-billing-desktop.png` |
| `/clinical/quality` | 1440x1100 | `clinical-quality-desktop.png` |
| `/clinical/reports` | 1440x1100 | `clinical-reports-desktop.png` |
| `/clinical/admin` | 1440x1100 | `clinical-admin-desktop.png` |
| `/clinical/dashboard` | 390x844 | `clinical-dashboard-mobile.png` |
| `/clinical/patients` | 390x844 | `clinical-patients-mobile.png` |

## Route Verification

| Route | Visible and navigable | Visual result | Notes |
| --- | --- | --- | --- |
| `/clinical/dashboard` | Yes | Pass with data blocker | Clinical shell placeholder renders with planned workflows and foundation contract. Global error banner appears because authenticated dashboard refresh cannot reach the DB. |
| `/clinical/patients` | Yes | Pass with data blocker | Registration workspace, filters, PHI badge, create action, empty state, and refresh action render. Data load shows `Failed to fetch`. |
| `/clinical/patients/:id` | Partial | Defect | Only page title and error banners render when patient fetch fails. The detail page needs resilient fallback content, back navigation, and planned-workflow context. |
| `/clinical/scheduling` | Yes | Pass with data blocker | Appointment workspace renders with filters and actions. Empty state appears because API data is unavailable. |
| `/clinical/screening` | Yes | Pass with data blocker | Screening queue renders with start screening, refresh, handoff action, filters, rules, and deferrals. |
| `/clinical/encounters` | Yes | Pass with data blocker | Encounter workspace route renders and remains navigable; data state blocked by unavailable DB. |
| `/clinical/orders` | Yes | Defect | Worklist renders, but dense action and filter rows clip horizontally at 1440px. |
| `/clinical/care-plans` | Yes | Pass with data blocker | Care-plan workspace route renders and remains navigable; data state blocked by unavailable DB. |
| `/clinical/billing` | Yes | Defect | Revenue cycle route renders, but action buttons and filters overflow horizontally at 1440px. |
| `/clinical/quality` | Yes | Defect | Quality route renders, but action buttons and filters overflow horizontally at 1440px. |
| `/clinical/reports` | Yes | Defect | Reporting cards render, but the route produces horizontal overflow and clipped controls at 1440px. |
| `/clinical/admin` | Yes | Pass with data blocker | Admin route renders configuration controls, KPI cards, and configure actions; data state blocked by unavailable DB. |

## Findings

1. Mobile layout is not usable as a clinical workspace.
   At 390x844, the first viewport is consumed by the full left navigation. Clinical content is pushed below the long sidebar, so users do not reach the active route without substantial scrolling. The redesign should use a collapsible mobile navigation, skip-to-content behavior, or a top/bottom clinical module switcher.

2. Dense desktop modules overflow horizontally.
   Orders, billing, quality, and reports show right-edge clipping and a horizontal scrollbar at 1440px. Action clusters and filter grids need wrapping rules, priority menus, or responsive column reduction.

3. Patient detail has poor failure-state resilience.
   `/clinical/patients/PT-000001` renders mostly blank when the patient API fails. The detail route should keep a stable shell with record identifier, back link, planned workflow actions, and a clearly scoped error panel.

4. Error messaging is too repetitive and not diagnostic.
   Global and local `Failed to fetch` banners appear together. The UI should distinguish database unavailable, authorization failure, empty result, and network failure without flooding the page.

5. The clinical shell still feels mixed with the legacy donor/QMS portfolio.
   The left rail includes legacy donor/QMS routes and clinical platform routes in one long list. For clinical production UX, Figma should evaluate a focused clinical app frame with global portfolio navigation separated from clinical operations navigation.

6. Action labels are often too long for dense toolbars.
   Buttons such as `Encounters Planned`, `Capture Denial`, `Close Event`, and report export controls compete with primary page content. Consider icon-first compact actions with tooltips, overflow menus, or a workflow action drawer.

## Swiss-Theme Gaps

The current UI is operational and readable, but it is not yet a Swiss-style clinical system:

- Layout relies on repeated cards and panels instead of a stricter grid, typographic scale, and table-first hierarchy.
- The palette is dominated by dark teal and teal action buttons, with limited neutral contrast and limited secondary accent discipline.
- Many labels use all caps, heavy font weights, and pill badges; a calmer clinical interface should reserve emphasis for risk, status, and required action.
- Dense modules need stronger alignment rules, consistent column systems, and less visual padding variability.
- Mobile needs a designed navigation model rather than stacking the full desktop sidebar above content.

## Screenshot Evidence Limits

The evidence confirms route visibility, shell layout, navigation, responsive behavior, and failure states. It does not confirm:

- seeded patient, appointment, order, billing, quality, or report data rendering;
- real login and MFA flow in this local session;
- preview/commit modal interaction success;
- browser console health, because Browser plugin and project Playwright were unavailable.

The local blocker is external to the frontend code under audit: `DATABASE_URL` points to host `db`, and this host shell cannot resolve that name.

## Validation Results

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe scripts\preflight_check.py` | Passed. |
| `.\.venv\Scripts\python.exe -m pytest` | Passed: 290 passed, 7 skipped, 1 warning. |
| `npm run build` from `frontend` | Passed. |
| `.\.venv\Scripts\python.exe -m pip check` | Passed: no broken requirements. |
| `npm audit --audit-level=high` from `frontend` | Passed: 0 vulnerabilities. |
| `.\.venv\Scripts\python.exe scripts\start_app_service.py --check` | Passed with 5 expected local production-hardening warnings. |
| `git diff --check` | Passed; Git reported line-ending normalization warnings only. |

## Commands Used For Visual Capture

- Started backend on `PORT=8011` with `.\.venv\Scripts\python.exe scripts\start_app_service.py`.
- Started frontend on `127.0.0.1:5174` with `npm run dev -- --host 127.0.0.1 --port 5174 --strictPort`.
- Verified `GET http://127.0.0.1:8011/api/health`.
- Verified `GET http://127.0.0.1:8011/api/clinical/status`.
- Captured screenshots with installed Chrome headless through DevTools protocol on temporary port `9222`.
- Stopped the backend and frontend processes started for this audit.
