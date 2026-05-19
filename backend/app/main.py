from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import (
    audit_logs,
    change_control,
    dashboard,
    donors,
    reviews,
    risk_analysis,
    vendors,
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


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {
        "message": "Clinical Donor Screening & Quality Workflow Platform API",
        "docs": "/docs",
    }

