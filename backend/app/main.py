from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.routes import (
    admin,
    ai_governance,
    audit_logs,
    auth,
    change_control,
    dashboard,
    documents,
    donors,
    eligibility,
    enterprise_dashboard,
    escalations,
    functional_routes,
    generation,
    notifications,
    partners,
    reviews,
    risk_analysis,
    suppliers,
    training,
    vendors,
    workflow_tasks,
    workspaces,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
        )
        if settings.cookie_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

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
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(donors.router)
app.include_router(reviews.router)
app.include_router(risk_analysis.router)
app.include_router(audit_logs.router)
app.include_router(change_control.router)
app.include_router(vendors.router)
app.include_router(dashboard.router)
app.include_router(documents.router)
app.include_router(eligibility.router)
app.include_router(auth.router)
app.include_router(ai_governance.router)
app.include_router(admin.router)
app.include_router(workflow_tasks.router)
app.include_router(notifications.router)
app.include_router(partners.router)
app.include_router(escalations.router)
app.include_router(training.router)
app.include_router(enterprise_dashboard.router)
app.include_router(workspaces.router)
app.include_router(functional_routes.router)
app.include_router(suppliers.router)
app.include_router(generation.router)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.get("/api/health", tags=["System"])
def api_health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "startup_mode": settings.startup_mode,
    }


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {
        "message": "Clinical Donor Screening & Quality Workflow Platform API",
        "docs": "/docs",
    }

