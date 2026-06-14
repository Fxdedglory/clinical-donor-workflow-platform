# Clinical Local Demo Setup

This runbook makes the Clinical Platform locally verifiable with synthetic backend data. It is for local demo/readiness work only. Do not use real PHI, production credentials, Docker, or live Azure services.

## Current Local Finding

The application expects PostgreSQL, not SQLite. The ORM models use the `operational` schema, Alembic migrations create PostgreSQL schema objects, and clinical routes read from migrated PostgreSQL tables.

The current ignored `.env` on this workstation points `DATABASE_URL` at Docker-style host `db`:

```powershell
DATABASE_URL=postgresql+psycopg://clinical_admin:<password>@db:5432/clinical_donor_workflow
```

That host is not resolvable in local Windows development without Docker. Use a localhost PostgreSQL URL instead.

## Required Local Services

- Python virtual environment from `.venv`
- Node/npm for the Vite frontend
- PostgreSQL 16 or compatible PostgreSQL service
- No Docker is required or introduced

The existing Windows PostgreSQL 16 service may require elevated permissions to start. If it cannot be started from a normal shell, use an already-running local PostgreSQL instance or a user-owned throwaway cluster created with the installed PostgreSQL binaries.

## Recommended DATABASE_URL

For the documented local PostgreSQL service:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://clinical_admin@localhost:5433/clinical_donor_workflow"
```

For a user-owned throwaway cluster on an alternate port:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow"
```

Do not commit `.env` changes.

## Migration Command

```powershell
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Demo Data Command

Seed deterministic synthetic clinical demo data without touching `backend/app/cli.py`:

```powershell
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow"
.\.venv\Scripts\python.exe scripts\seed_clinical_demo_data.py
```

Optional local password override:

```powershell
$env:CLINICAL_DEMO_PASSWORD = "<local-only-password>"
.\.venv\Scripts\python.exe scripts\seed_clinical_demo_data.py
```

Default local-only demo login:

```text
username: clinical_demo
password: ClinicalDemo!2026
```

The script is idempotent for its deterministic demo records and uses `example.test` addresses and synthetic names only.

## Backend Launch

If the frontend uses a Vite port other than `5173`, include that origin in `CORS_ORIGINS` as a JSON array:

```powershell
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow"
$env:CORS_ORIGINS = '["http://127.0.0.1:5182","http://localhost:5182","http://127.0.0.1:5173","http://localhost:5173","http://127.0.0.1:8000","http://localhost:8000"]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012
```

## Frontend Launch

```powershell
cd frontend
$env:VITE_API_BASE_URL = "http://127.0.0.1:8012"
npm run dev -- --host 127.0.0.1 --port 5173
```

If Vite auto-increments the port because `5173` is occupied, add the actual port to backend `CORS_ORIGINS` and restart the backend.

## Verification

Clinical status:

```powershell
Invoke-RestMethod http://127.0.0.1:8012/api/clinical/status
```

Patient list:

```powershell
$login = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8012/api/auth/login" -ContentType "application/x-www-form-urlencoded" -Body "username=clinical_demo&password=ClinicalDemo!2026"
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri "http://127.0.0.1:8012/api/clinical/patients" -Headers $headers
```

Frontend routes to verify:

```text
/clinical/dashboard
/clinical/patients
/clinical/patients/PT-DEMO-001
/clinical/scheduling
/clinical/screening
/clinical/encounters
/clinical/orders
/clinical/care-plans
/clinical/billing
/clinical/quality
/clinical/admin
/clinical/reports
```

## Troubleshooting

If the backend logs show unresolved host `db`, replace the ignored local `.env` value or override `DATABASE_URL` in the shell with a localhost PostgreSQL URL.

If the frontend shows `Data unavailable` while API curl checks succeed, confirm `VITE_API_BASE_URL` points at the backend and that backend `CORS_ORIGINS` includes the actual Vite origin.

If ports are occupied, use alternates such as backend `8012` and frontend `5182`, then keep `VITE_API_BASE_URL` and `CORS_ORIGINS` aligned.

