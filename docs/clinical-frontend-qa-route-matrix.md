# Clinical Frontend QA Route Matrix

Task: `CLINICAL-FRONTEND-QA-00`

Date: `2026-06-15`

Decision: manual browser QA and screenshot evidence package only. No deployment, DNS change, `clinical.teemails.com` activation, backend workflow change, database schema change, or cross-repo change was performed.

## Source-Control Baseline

| Check | Result |
| --- | --- |
| Initial `git status --short` | One dirty tracked file: `backend/app/cli.py` |
| Protected dirty file | `backend/app/cli.py` |
| Protected decision | Preserved; not modified, formatted, staged, or committed |
| Generated evidence | `metadata/visual_audit/clinical/frontend_qa/current/` ignored by `.gitignore` |

The protected `backend/app/cli.py` diff remains unrelated demo/seed timestamp and donor eligibility data work.

## QA Environment

| Area | Value |
| --- | --- |
| Browser path | Chrome headless through local Chrome DevTools Protocol |
| Browser plugin | Not available in this session |
| Playwright | Not installed in the repo; no dependency was added |
| Backend | FastAPI on `http://127.0.0.1:8012` with local demo PostgreSQL on port `55432` |
| Frontend | Vite dev server on `http://127.0.0.1:5183` |
| Demo user | `clinical_demo` |
| Evidence manifest | `metadata/visual_audit/clinical/frontend_qa/current/manifest.json` |
| Screenshot count | 43 PNG screenshots |
| Route viewport checks | 39 checks: desktop, tablet, and mobile for 13 routes |
| Console events | 0 errors or warnings captured |

## Route Matrix

| Route | Expected surface | Desktop | Tablet | Mobile | QA result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `/` | Authenticated landing redirects to donor/QMS dashboard | Captured | Captured | Captured | Passed | Included for route smoke; it is not expected to render the clinical shell. |
| `/clinical/dashboard` | Clinical dashboard foundation shell | Captured | Captured | Captured | Passed | Shows `Foundation pending` operational shell without hidden navigation. |
| `/clinical/patients` | Patients / donors work queue | Captured | Captured | Captured | Passed | PHI indicator present; create patient/donor workflow visible. |
| `/clinical/patients/PT-DEMO-001` | Patient / donor detail | Captured | Captured | Captured | Passed | Demo patient resolves; compact detail tables have no page-level horizontal overflow. |
| `/clinical/scheduling` | Scheduling work queue | Captured | Captured | Captured | Passed | Book appointment workflow visible and navigable. |
| `/clinical/screening` | Donor screening workflow queue | Captured | Captured | Captured | Passed | Eligibility/result workflows visible; unavailable workflow states remain explicit. |
| `/clinical/encounters` | Encounters and clinical note workflow | Captured | Captured | Captured | Passed | Encounter workflows visible with responsive state treatment. |
| `/clinical/orders` | Orders / results worklist | Captured | Captured | Captured | Passed | Dense tables render without page-level overflow; result entry workflow visible. |
| `/clinical/care-plans` | Care plan work queue | Captured | Captured | Captured | Passed | Care plan context and task/progress states remain visible. |
| `/clinical/billing` | Billing and revenue-cycle work queue | Captured | Captured | Captured | Passed | Dense billing tables render without page-level overflow. |
| `/clinical/quality` | Quality, adverse event, CAPA, evidence workflows | Captured | Captured | Captured | Passed | PHI and export-profile indicators present. |
| `/clinical/reports` | Reporting and analytics export workspace | Captured | Captured | Captured | Passed | PHI, export profile, and small-cell suppression indicators present. |
| `/clinical/admin` | Clinical administration configuration workspace | Captured | Captured | Captured | Passed | Admin configuration routes and approval path workflows visible. |

## Interaction Matrix

| Interaction | Route | Result | Evidence |
| --- | --- | --- | --- |
| Desktop sidebar collapse/expand | `/clinical/dashboard` | Passed | Manifest `navigation_checks.sidebarCollapse.toggled=true` |
| Mobile drawer open/close | `/clinical/dashboard` | Passed | Manifest `navigation_checks.mobileDrawer.opened=true`, `closed=true` |
| Create Patient / Donor validation modal | `/clinical/patients` | Passed | `modal-create-patient-validation-desktop.png` |
| Book Appointment modal | `/clinical/scheduling` | Passed | `modal-book-appointment-form-desktop.png` |
| Enter Result modal | `/clinical/orders` | Passed | `modal-enter-order-result-form-desktop.png` |
| Generate Analytics Export preview modal | `/clinical/reports` | Passed | `modal-reports-export-preview-desktop.png` |

## Dense Route Checks

| Route | Dense tables | Page overflow | PHI indicator | Export indicator | Suppression indicator |
| --- | ---: | --- | --- | --- | --- |
| `/clinical/patients/PT-DEMO-001` | 5 | No | Yes | No | No |
| `/clinical/orders` | 7 | No | Yes | No | No |
| `/clinical/billing` | 5 | No | Yes | No | No |
| `/clinical/quality` | 6 | No | Yes | Yes | No |
| `/clinical/reports` | 10 | No | Yes | Yes | Yes |

## Result

Clinical frontend manual browser QA evidence passed for required route visibility, desktop/tablet/mobile rendering, sidebar/mobile navigation, representative workflow modals, PHI/export/suppression indicators, and console health.
