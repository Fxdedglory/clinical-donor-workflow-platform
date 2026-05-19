# Clinical Donor Screening & Quality Workflow Platform

Simulated regulated healthcare operations platform for donor intake review, AI-assisted screening, audit trails, QMS change control, vendor SLA monitoring, and executive workflow dashboards.

Repository: `github.com/Fxdedglory/clinical-donor-workflow-platform`

## Project Overview

This project is designed as a portfolio-grade healthcare systems analysis demo. It models a donor services workflow where records enter an intake queue, a rule-based AI screening engine evaluates clinical risk, reviewers approve/defer/reject cases, and every meaningful action is captured in an audit log. It also includes QMS/change control and vendor SLA workflows to reflect regulated healthcare operations rather than a generic AI application.

Resume themes demonstrated:

- Healthcare technology and clinical systems
- Business systems analysis and workflow automation
- QMS, SOP versioning, change control, non-conformance/CAPA concepts
- AI-assisted decision support with transparent risk rules
- Auditability, compliance traceability, and operational dashboards
- Vendor/system monitoring and SLA reporting

## Architecture

```text
Streamlit dashboard  ->  FastAPI REST API  ->  SQLAlchemy ORM  ->  PostgreSQL 16
                              |
                              +-> Rule-based risk engine
                              +-> Audit logging service
                              +-> Dashboard aggregation service
```

Schemas:

- `staging`: reserved for raw imports
- `operational`: application fact/dimension tables
- `marts`: analytics views

Core tables:

- `operational.dim_user`
- `operational.dim_vendor`
- `operational.dim_sop`
- `operational.dim_risk_category`
- `operational.fact_donor_review`
- `operational.fact_audit_log`
- `operational.fact_change_control`
- `operational.fact_vendor_incident`

## Features

- Donor intake queue with status, reviewer, clinical notes, risk flags, and queue prioritization
- Donor review decision workflow with approval, rejection, and deferral tracking
- Rule-based AI screening engine for risk score, recommended action, flagged conditions, and review priority
- Immutable-style audit log entries for create/update/decision actions with before/after payloads
- QMS change control workflow for SOP changes, risk level, approvals, investigation notes, and CAPA flags
- Vendor SLA monitoring for systems, incidents, uptime, ticket aging, breach flags, and resolution time
- Executive dashboard with KPIs, risk distribution, daily trends, priority queue, vendor health, and audit activity
- Faker-powered demo data generator for 500-5000 donor records

## Screenshots

Design concept used for the dashboard visual direction:

![Dashboard concept](docs/screenshots/concept-dashboard.png)

Rendered app screenshot:

![Rendered dashboard](docs/screenshots/rendered-dashboard.png)

## Setup Instructions

### Run with Docker Compose

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Streamlit dashboard: `http://localhost:8501`
- PostgreSQL: `localhost:5432`

The backend container runs Alembic migrations and seeds demo data on startup.

### Run Locally with uv

Start PostgreSQL first, then from the repository root:

```powershell
uv venv
uv pip install -r requirements.txt
$env:PYTHONPATH="backend"
$env:DATABASE_URL="postgresql+psycopg://clinical_admin:clinical_demo_password@localhost:5432/clinical_donor_workflow"
uv run alembic upgrade head
uv run python -m app.cli seed --records 1200
uv run uvicorn app.main:app --reload --app-dir backend
```

In a second terminal:

```powershell
$env:API_URL="http://localhost:8000"
uv run streamlit run frontend/app.py
```

## Demo Workflow

1. Open the dashboard and review pending donor reviews, approval rate, SLA compliance, and open investigations.
2. Go to Donor Queue and filter for `High` or `Critical` risk records.
3. Open Donor Review, choose an active case, review flags and clinical notes, then record a decision.
4. Open Audit Logs and confirm the decision produced a traceable audit event.
5. Open AI Risk Analysis and test how age, infectious history, missing fields, travel risk, and notes change the recommendation.
6. Open Change Control and create a QMS request tied to an SOP.
7. Open Vendor SLA and review open incidents, breach counts, uptime, and mean resolution time.

## Healthcare/QMS Concepts

This platform intentionally reflects regulated healthcare operations:

- **Clinical screening:** Donor review combines structured intake data, clinical notes, risk flags, and reviewer decisions.
- **Decision support:** The risk engine is transparent and auditable. It recommends actions without pretending to replace clinical judgment.
- **Audit trail:** Actions store who changed what, when it changed, and before/after values.
- **QMS workflow:** Change requests include SOP linkage, risk level, approval state, CAPA requirement, due dates, and investigation notes.
- **Vendor governance:** Vendor incidents track criticality, uptime, ticket aging, SLA breach status, and operational impact.
- **Analytics marts:** Dashboard views separate operational transactions from reporting concerns.

## API Endpoints

- `GET /api/donors`
- `GET /api/donors/{review_id}`
- `POST /api/donors`
- `PATCH /api/donors/{review_id}`
- `POST /api/donors/{review_id}/decision`
- `GET /api/reviews`
- `POST /api/risk-analysis`
- `GET /api/risk-analysis/{review_id}`
- `GET /api/audit-logs`
- `GET /api/change-control`
- `POST /api/change-control`
- `PATCH /api/change-control/{change_id}`
- `GET /api/vendors`
- `GET /api/vendors/incidents`
- `POST /api/vendors/incidents`
- `PATCH /api/vendors/incidents/{incident_id}`
- `GET /api/dashboard`

## Future Enhancements

- OCR/PDF ingestion for donor document packets
- Local LLM or OpenAI abstraction layer for clinical note summarization
- Role-based access control and reviewer assignment rules
- Power BI or analytics export integration
- Azure deployment path
- SharePoint document-control integration
- Email/Teams notification workflow
- Non-conformance and CAPA lifecycle expansion

