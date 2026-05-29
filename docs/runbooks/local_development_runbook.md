# Local Development Runbook

## Current Python Finding

As of 2026-05-29 in this shell:

- `py` is not installed or not on PATH.
- `where python` returns `C:\Users\gamer\AppData\Local\Microsoft\WindowsApps\python.exe`.
- `python --version` opens the Microsoft Store alias message.
- No Python executable was found under `AppData\Local\Programs\Python`.
- No Conda executable was found by `where conda`.

Recommended fix:

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

## Setup Without uv

```powershell
cd E:\Clinical_Donor_Screening_Quality_Workflow_Platform
python -m venv .venv
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

Run migrations:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m alembic upgrade head
```

Seed data:

```powershell
.\.venv\Scripts\python -m app.cli seed --records 1200 --seed 42
```

## Run Locally

Terminal 1:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
$env:API_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\python -m streamlit run frontend\app.py
```

URLs:

- API: `http://127.0.0.1:8000`
- API health: `http://127.0.0.1:8000/api/health`
- Streamlit: `http://localhost:8501`

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
