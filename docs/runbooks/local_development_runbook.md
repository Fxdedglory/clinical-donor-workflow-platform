# Local Development Runbook

## Current Runtime Finding

As of 2026-05-29 in this shell:

- `py` is not installed or not on PATH.
- `where python` returns `C:\Users\gamer\AppData\Local\Microsoft\WindowsApps\python.exe`.
- `python --version` opens the Microsoft Store alias message.
- A usable Python executable was found at `C:\Users\gamer\OneDrive\Documents\Python\python.exe`.
- That interpreter reports Python `3.13.7` and can create `.venv` for this repo.
- No Python executable was found under `AppData\Local\Programs\Python`.
- No Conda executable was found by `where conda`.
- PostgreSQL 13 and 16 services are installed but stopped.
- `psql.exe` exists under `C:\Program Files\PostgreSQL\16\bin`.
- Starting `postgresql-x64-16` from a non-elevated PowerShell failed with service permission errors.
- `localhost:5432` did not accept TCP connections.

Recommended Python fix if you want a standard install:

1. Install Python 3.12.x from python.org.
2. Select `Add python.exe to PATH`.
3. Disable Windows Store Python aliases if needed:
   - Settings
   - Apps
   - Advanced app settings
   - App execution aliases
   - Turn off `python.exe` and `python3.exe`
4. Open a new PowerShell terminal.
5. Confirm:

```powershell
python --version
where python
```

Current usable interpreter command:

```powershell
& "C:\Users\gamer\OneDrive\Documents\Python\python.exe" --version
& "C:\Users\gamer\OneDrive\Documents\Python\python.exe" -m venv .venv
```

## Setup Without uv

```powershell
cd E:\Clinical_Donor_Screening_Quality_Workflow_Platform
& "C:\Users\gamer\OneDrive\Documents\Python\python.exe" -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Database

The app expects PostgreSQL. Configure:

```powershell
copy .env.example .env
notepad .env
```

Set `DATABASE_URL` for the local PostgreSQL database.

For local development, use a localhost database URL. If an older ignored `.env` still points to Docker host `db`, replace it before running migrations:

```powershell
DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/clinical_donor_workflow
```

Start PostgreSQL 16 from an elevated PowerShell window if the service is stopped:

```powershell
Start-Service postgresql-x64-16
& "C:\Program Files\PostgreSQL\16\bin\pg_isready.exe" -h localhost -p 5432
```

Run migrations:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m alembic upgrade head
```

Seed data:

```powershell
.\.venv\Scripts\python -m app.cli seed --records 1200 --seed 42
```

If the role or database does not exist, create them using your local PostgreSQL administrator account. Do not commit the resulting `.env` file.

## Run Locally

Terminal 1:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If port `8000` is already in use by another portfolio app, use an alternate local port such as `8010`.

Terminal 2:

```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

URLs:

- API: `http://127.0.0.1:8000`
- API health: `http://127.0.0.1:8000/api/health`
- React dev frontend: `http://127.0.0.1:5173`

## App Service-Style Local Run

```powershell
cd frontend
npm install
npm run build
cd ..
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python scripts\start_app_service.py
```

URL:

- App: `http://127.0.0.1:8000`

## App Service Startup Check

```powershell
.\.venv\Scripts\python scripts\start_app_service.py --check
```

## Git Hygiene

Do not commit:

- `.env`
- `.venv`
- generated data
- exports
- logs
- secrets
- local database dumps
