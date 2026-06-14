# Clinical Backend-Connected Visual Verification

Task: `CLINICAL-DEMO-01`

Baseline commits:

- UX audit: `c7edcc4 Add clinical frontend visual audit context`
- Swiss frontend foundation: `0613c60 Implement clinical Swiss frontend foundation`

## Database Setup Used

The ignored `.env` still points to Docker-style host `db`, which is not resolvable from local Windows development in this repo. The documented localhost PostgreSQL service was installed but stopped, and this non-elevated shell could not start the Windows service.

For verification, a user-owned PostgreSQL 16 cluster was initialized under ignored path:

```text
data/generated/local_pg/pgdata
```

Runtime database URL used:

```powershell
postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow
```

Migration status:

```text
202606130003 (head)
```

## Commands Used

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts\seed_clinical_demo_data.py
.\.venv\Scripts\python.exe scripts\seed_clinical_demo_data.py
```

Seed results:

```text
first run: created 118, updated 0
second run: created 0, updated 77
```

Backend launch:

```powershell
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow"
$env:CORS_ORIGINS = '["http://127.0.0.1:5182","http://localhost:5182","http://127.0.0.1:5173","http://localhost:5173","http://127.0.0.1:8000","http://localhost:8000"]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012
```

Frontend launch:

```powershell
cd frontend
$env:VITE_API_BASE_URL = "http://127.0.0.1:8012"
npm run dev -- --host 127.0.0.1 --port 5177
```

Vite auto-incremented to:

```text
http://127.0.0.1:5182
```

## API Endpoint Status

All endpoints below were verified with the seeded local demo user and returned HTTP `200`.

| Endpoint | Status |
| --- | --- |
| `/api/clinical/status` | 200 |
| `/api/clinical/patients` | 200 |
| `/api/clinical/scheduling/appointments` | 200 |
| `/api/clinical/screening/sessions` | 200 |
| `/api/clinical/encounters` | 200 |
| `/api/clinical/orders` | 200 |
| `/api/clinical/care-plans` | 200 |
| `/api/clinical/billing/work-queue` | 200 |
| `/api/clinical/quality/dashboard` | 200 |
| `/api/clinical/reports/dashboard` | 200 |
| `/api/clinical/admin/dashboard` | 200 |

## Screenshot Inventory

Screenshots were generated under ignored path:

```text
metadata/visual_audit/clinical/fe01_backend_connected/
```

Manifest:

```text
metadata/visual_audit/clinical/fe01_backend_connected/manifest.json
```

Captured routes:

| Route | Screenshot | Backend data | Horizontal overflow |
| --- | --- | --- | --- |
| `/clinical/dashboard` | `clinical-dashboard-desktop.png` | Authenticated foundation shell | No |
| `/clinical/patients` | `clinical-patients-desktop.png` | Patients visible | No |
| `/clinical/patients/PT-DEMO-001` | `clinical-patient-detail-desktop.png` | Detail, contacts, insurance, consent visible | No |
| `/clinical/scheduling` | `clinical-scheduling-desktop.png` | Appointments/resources visible | No |
| `/clinical/screening` | `clinical-screening-desktop.png` | Screening session/deferral visible | No |
| `/clinical/encounters` | `clinical-encounters-desktop.png` | Encounter/note context visible | No |
| `/clinical/orders` | `clinical-orders-desktop.png` | Critical result visible | No |
| `/clinical/care-plans` | `clinical-care-plans-desktop.png` | Critical follow-up care plan visible | No |
| `/clinical/billing` | `clinical-billing-desktop.png` | Charge, claim, payment, denial visible | No |
| `/clinical/quality` | `clinical-quality-desktop.png` | Quality event/adverse event visible | No |
| `/clinical/admin` | `clinical-admin-desktop.png` | Admin config/catalog data visible | No |
| `/clinical/reports` | `clinical-reports-desktop.png` | Aggregate reports/export visible | No |
| `/clinical/patients` mobile | `clinical-patients-mobile.png` | Patients visible | No |

## Updated Visual Defects From Real Data

1. Dense secondary tables no longer create page-level horizontal overflow, but they can become too narrow and split identifiers or words vertically. This is most visible in Orders, Billing, and Quality lower panels.
2. Billing work queue subpanels need route-specific column priority or card layouts for claims, payments, denials, and insurance verification.
3. Orders and Quality linked-context tables need more deliberate widths for identifiers such as `ORD-DEMO-001`, `CP-DEMO-001`, and `CLM-DEMO-001`.
4. Patient detail works with real data, but contact/email cells wrap awkwardly in constrained two-column panels.
5. `/clinical/dashboard` remains a visible foundation route rather than a backend aggregate dashboard.
6. Local demo CORS must be kept aligned with the actual Vite port when Vite auto-increments.

## FE-02 Recommendation

Proceed with `CLINICAL-FE-02` route-specific polish before deployment prep:

- Replace narrow repeated tables in secondary panels with key-value cards or priority columns.
- Add module-specific responsive layouts for Orders, Billing, Quality, and Reports.
- Keep the no-horizontal-overflow rule, but improve readability for long identifiers and timestamps.
- Consider a small local demo launch helper that starts the user-owned PostgreSQL cluster and prints the required backend/frontend env vars.

