# Clinical Swiss-Theme Frontend Implementation

Implementation date: 2026-06-13 America/New_York

Baseline inputs:

- `docs/clinical-frontend-visual-audit.md`
- `docs/clinical-figma-design-context.md`
- `docs/design/clinical_swiss_theme_design_board.svg`
- `metadata/visual_audit/clinical/current/`

## What Changed

Implemented the first Swiss-theme frontend foundation pass for the Clinical Platform. This sprint keeps existing backend workflows and frontend routes intact while improving shell structure, responsive behavior, dense module layout safety, patient-detail resilience, and clinical error messaging.

Key changes:

- Added a Swiss-inspired token layer in `frontend/src/styles.css` using white, slate, navy, cool blue, thin borders, subtle shadows, and restrained status colors.
- Refined the authenticated app shell with a clinical-first navigation group, separated legacy Donor/QMS operations navigation, compact portfolio navigation, a route-aware top header, and a role/status route context line.
- Added desktop sidebar collapse and mobile drawer behavior so mobile content is visible immediately.
- Prevented clinical route-level dashboard refresh from producing duplicate global errors on API-backed clinical modules.
- Added shared diagnostic API failure copy for network and backend/database failures.
- Added a reusable clinical alert banner in the frontend shell layer.
- Reworked `/clinical/patients/:id` so failed data loading still renders a protected patient-detail shell with retry action, demographic/contact/insurance/consent/audit placeholders, and downstream workflow actions.
- Refined filter bars, tables, cards, status chips, privacy/export badges, and section panels to reduce clipped controls and page-level horizontal overflow.

## Routes Affected

Visual foundation applies to all authenticated routes through the shared app shell and CSS primitives.

Route-specific verification focused on:

- `/clinical/dashboard`
- `/clinical/patients`
- `/clinical/patients/:id`
- `/clinical/scheduling`
- `/clinical/screening`
- `/clinical/encounters`
- `/clinical/orders`
- `/clinical/care-plans`
- `/clinical/billing`
- `/clinical/quality`
- `/clinical/reports`
- `/clinical/admin`

Dense overflow verification focused on:

- `/clinical/orders`
- `/clinical/billing`
- `/clinical/quality`
- `/clinical/reports`
- `/clinical/admin`

## Browser Evidence

Fresh FE-01 screenshots were captured locally and intentionally ignored by git:

`metadata/visual_audit/clinical/fe01/`

Captured evidence includes:

- desktop screenshots for core clinical routes;
- mobile screenshots for dashboard and patients;
- a mobile drawer screenshot;
- a rendered PNG of the SVG design board for local comparison.

Automated Chrome DevTools measurements reported no full-page horizontal overflow for the checked clinical routes at 1440px and no mobile page-level overflow at 390px.

## Manual Screenshots To Retake

For design review, retake screenshots after connecting to a seeded database so the UI can be reviewed with real data:

- `/clinical/dashboard` at 1440px and 390px
- `/clinical/patients` at 1440px and 390px
- `/clinical/patients/:id` with a real patient
- `/clinical/patients/:id` with backend/database unavailable
- `/clinical/orders`
- `/clinical/billing`
- `/clinical/quality`
- `/clinical/reports`
- `/clinical/admin`
- mobile drawer open and closed

## Remaining Gaps

- Workflow modals still use the existing interaction structure; they are visually improved by shared CSS but have not received a dedicated preview -> commit modal redesign.
- Real data-state review remains blocked in this host shell because local `DATABASE_URL` resolves host `db`, which is unavailable from PowerShell.
- Dense tables are overflow-safe, but column-priority design should be refined with real seeded records.
- Legacy Donor/QMS routes are preserved, but their internal route UIs were not redesigned in this sprint.
- Browser plugin and project Playwright are unavailable, so rendered QA used installed Chrome headless through DevTools protocol.

## Recommended CLINICAL-FE-02 Scope

1. Redesign the preview -> commit workflow modal anatomy across patient, scheduling, screening, encounters, orders, care plans, billing, quality, reports, and admin workflows.
2. Add route-level worklist/detail panel patterns for real seeded records, including column priority and row selection behavior.
3. Add explicit empty, loading, warning, and backend-unavailable component variants under `frontend/src/pages/clinical/`.
4. Add focused frontend tests for shell navigation state, mobile drawer behavior, patient-detail fallback, and API diagnostic messaging.
5. Re-run visual QA with a reachable seeded database and update the visual audit with data-rich screenshots.

