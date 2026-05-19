# Demo Data

The seed command generates a healthcare operations dataset with:

- 500-5000 donor intake records
- AI-style risk scoring results
- audit log history
- SOP/change control records
- vendor incidents and SLA breach flags

Run from the repository root:

```bash
uv run --env-file .env python -m app.cli seed --records 1200
```

When running outside Docker, set:

```bash
$env:PYTHONPATH="backend"
$env:DATABASE_URL="postgresql+psycopg://clinical_admin:clinical_demo_password@localhost:5432/clinical_donor_workflow"
```

