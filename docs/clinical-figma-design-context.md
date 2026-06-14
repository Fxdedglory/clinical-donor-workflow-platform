# Clinical Figma Design Context

Purpose: prepare the next Figma design pass for the clinical platform without implementing a redesign in code yet.

Accepted baseline: `7fd6dfb Add production evidence bundle readiness`

Screenshot evidence location: `metadata/visual_audit/clinical/current/` (local, ignored by git)

## Product Frame

This is an operational clinical donor screening and quality workflow platform. It is not a marketing site and not a generic CRUD admin console. The interface must help clinical, quality, scheduling, billing, and operations users move regulated work through preview -> commit workflows with clear auditability, PHI protection, and role-aware actions.

Project OS reminders for the design pass:

- Product intent and roadmap decisions are the source of truth; the repository is implementation evidence, not the source of truth.
- Preserve the Preview -> Commit pattern for durable workflow changes.
- Durable commit actions must communicate the `X-Confirm-Generation: true` requirement.
- Do not hide workflows just because backend support is partial. Mark unavailable work as `Foundation pending` or `Planned workflow`.
- Protect dirty files during implementation; `backend/app/cli.py` must not be modified unless explicitly required.

## Primary Users

| User | Primary needs |
| --- | --- |
| Donor intake coordinator | Register patients/donors, resolve missing identity/contact/consent details, route ready records. |
| Scheduler | Book, reschedule, cancel, check in, and no-show appointments while seeing patient/resource context. |
| Clinical reviewer | Run screening, review questionnaire/vitals, preview eligibility, commit outcomes, and escalate exceptions. |
| Clinician/documentation user | Create encounters, draft/sign/amend notes, record diagnoses, allergies, and medications. |
| Orders/results user | Place orders, enter/correct results, acknowledge critical results, and cancel orders. |
| Care coordinator | Create care plans, manage goals/interventions/tasks, and track progress/closure. |
| Billing user | Verify insurance, capture charges, create claims, post payments, and manage denials. |
| Quality/compliance user | Create quality/adverse events, investigate, link CAPA, close events, and export audit evidence. |
| Clinical administrator | Manage templates, rules, catalogs, approval paths, notification templates, and RBAC overview. |
| Product Owner/Security/Operations reviewer | Verify readiness, evidence, auditability, security gates, and production blockers. |

## Current Route Surface

| Route | Current user-facing purpose |
| --- | --- |
| `/clinical/dashboard` | Clinical shell overview and workflow operation activity foundation. |
| `/clinical/patients` | Patient/donor registration list, filters, create flow entry, PHI indicator. |
| `/clinical/patients/:id` | Patient/donor detail, contacts, insurance, consents, audit activity. |
| `/clinical/scheduling` | Appointment work queue, resource filters, book/reschedule/cancel/check-in/no-show actions. |
| `/clinical/screening` | Screening queue, questionnaire/vitals/eligibility/override workflow entry points. |
| `/clinical/encounters` | Encounter worklist, documentation workflows, note/sign/amend/diagnosis/allergy/medication actions. |
| `/clinical/orders` | Orders/results worklist, order placement, result, acknowledgement, and cancellation actions. |
| `/clinical/care-plans` | Care plan worklist, goals, interventions, tasks, progress, closure. |
| `/clinical/billing` | Billing account and revenue cycle workspace. |
| `/clinical/quality` | Quality event, adverse event, investigation, CAPA, closure, evidence export. |
| `/clinical/reports` | Aggregate reporting, audit activity, PHI/ePHI suppression, analytics export. |
| `/clinical/admin` | Versioned clinical configuration and governance. |

## Backend Functionality Context

The clinical backend is organized under `/api/clinical` with module routers for foundation, patients, scheduling, screening, encounters, orders, care plans, billing, quality, reports, and admin. `docs/clinical-api-inventory.md` is the detailed endpoint reference.

Design implications:

- Mutating clinical workflows follow form -> validation -> preview -> commit confirmation -> success.
- Durable commits require `X-Confirm-Generation: true`.
- Clinical audit entries and workflow operations are append-only evidence, not incidental logs.
- Read surfaces and mutation surfaces are role-aware.
- External partner/supplier users must not get internal clinical mutation affordances.
- PHI/ePHI redaction and small-cell suppression need visible but quiet status indicators.
- Empty states and planned workflows must keep users oriented without pretending data exists.

## Current Visual Baseline

Observed from screenshots and `frontend/src/styles.css`:

- Frame: fixed dark teal left rail, topbar, main content region.
- Main palette: dark teal/navy rail, teal primary buttons, pale blue-gray canvas, white cards, red/yellow/green state colors.
- Typography: heavy weights, many uppercase section labels, compact operational text.
- Components: cards, metric tiles, status pills, filter grids, tables, action buttons, modal workflow forms.
- Radius: mostly 7-8px, consistent with project guidance.
- Density: medium-dense, but card and toolbar behavior breaks in dense modules.

## Current UX Gaps To Solve In Figma

1. Create a mobile navigation pattern that gets users to active clinical content immediately.
2. Replace horizontal overflow in orders, billing, quality, and reports with responsive action grouping and filter layouts.
3. Make patient detail resilient when data fails: stable header, back link, record identifier, local error state, and planned workflow actions.
4. Separate global portfolio navigation from clinical operations navigation.
5. Reduce repeated `Failed to fetch` banners into a scoped, actionable error pattern.
6. Establish a calmer clinical visual hierarchy: fewer emphatic pills, fewer repeated cards, stronger tables and detail panes.
7. Create consistent preview/commit modal anatomy that exposes validation issues, preview hash/evidence, confirmation requirement, and audit outcome.

## Swiss-Inspired Direction

Use a Swiss clinical operations theme, not a decorative Swiss travel theme.

Recommended direction:

- Grid-first layouts with clear left alignment, predictable column rhythm, and disciplined spacing.
- Neutral clinical canvas with restrained teal/green accents for primary action and clinical identity.
- Use color sparingly for status, risk, PHI, validation, and destructive actions.
- Prefer table/worklist + detail-panel patterns over card-heavy dashboards for repeated operational use.
- Use compact icon buttons with tooltips where action meaning is familiar; use text labels for irreversible or regulated commits.
- Keep badges small and semantic: PHI protected, Active, Planned workflow, Append only, Suppressed, Commit guarded.
- Avoid one-note teal dominance by adding neutral grays, white space, black text hierarchy, and restrained secondary accent colors.

## Figma Deliverables Requested Next

Recommended next Figma pass:

1. Desktop clinical app frame at 1440px.
2. Mobile clinical app frame at 390px.
3. Route-level design for:
   - Clinical dashboard
   - Patients list
   - Patient detail
   - Scheduling
   - Screening
   - Orders/results
   - Billing
   - Quality
   - Reports
   - Admin
4. Reusable component set:
   - clinical shell navigation
   - module header/action bar
   - filter bar
   - worklist table
   - split detail panel
   - empty/loading/error state
   - PHI/redaction badge
   - status pill
   - preview/commit modal
   - audit timeline/event row
   - evidence/export summary
5. Responsive rules for action overflow, filter wrapping, and route navigation.

## Prompt Seed For Figma

Create a Swiss-inspired clinical operations design system and route mockups for a regulated Clinical Donor Screening and Quality Workflow Platform. Use the existing screenshots in `metadata/visual_audit/clinical/current/` and this design context as implementation evidence. Preserve the product workflows and route inventory. Do not remove planned workflows; show them as `Foundation pending` or `Planned workflow`. Prioritize desktop 1440px and mobile 390px. Fix the observed issues: mobile sidebar consumes the viewport, dense desktop routes overflow horizontally, patient detail has poor error resilience, legacy portfolio navigation competes with clinical navigation, and repeated fetch errors are noisy. Keep the interface calm, grid-based, table-first, PHI-aware, audit-aware, and optimized for repeated clinical work.

