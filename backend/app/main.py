from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import (
    admin,
    ai_governance,
    audit_logs,
    auth,
    change_control,
    dashboard,
    donors,
    enterprise_dashboard,
    escalations,
    functional_routes,
    notifications,
    reviews,
    risk_analysis,
    training,
    vendors,
    workflow_tasks,
    workspaces,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Simulated regulated healthcare workflow platform for donor intake, "
        "AI-assisted screening, audit trails, QMS change control, and vendor SLA monitoring."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(donors.router)
app.include_router(reviews.router)
app.include_router(risk_analysis.router)
app.include_router(audit_logs.router)
app.include_router(change_control.router)
app.include_router(vendors.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(ai_governance.router)
app.include_router(admin.router)
app.include_router(workflow_tasks.router)
app.include_router(notifications.router)
app.include_router(escalations.router)
app.include_router(training.router)
app.include_router(enterprise_dashboard.router)
app.include_router(workspaces.router)
app.include_router(functional_routes.router)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {
        "message": "Clinical Donor Screening & Quality Workflow Platform API",
        "docs": "/docs",
    }

