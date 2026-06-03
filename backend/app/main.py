import logging
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth.dependencies import require_permission
from app.core.config import settings
from app.database import engine
from app.models import User
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
from app.services.adls_historical import (
    HISTORICAL_CONFIRMATION_PHRASE,
    run_clinical_historical_adls_upload,
)
from app.services.adls_smoke import CONFIRMATION_PHRASE, run_adls_smoke_upload

APP_NAME = "clinical-donor-platform"
APP_STARTED_MONOTONIC = time.monotonic()
PERFORMANCE_LOGGER = logging.getLogger("clinical.performance")


class AdlsSmokeUploadRequest(BaseModel):
    confirm: str = Field(default="")


class HistoricalAdlsUploadRequest(BaseModel):
    confirm: str = Field(default="")
    batch_id: str | None = Field(default=None)


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


@app.middleware("http")
async def add_timing_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        PERFORMANCE_LOGGER.exception(
            "request_timing_failed method=%s path=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            duration_ms,
            request_id,
        )
        raise
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
    response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"
    PERFORMANCE_LOGGER.info(
        "request_timing method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


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
app.include_router(auth.router, prefix="/Clinical")
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


def _frontend_index() -> Path | None:
    index_path = Path(settings.frontend_dist_dir) / "index.html"
    return index_path if settings.serve_frontend and index_path.exists() else None


assets_path = Path(settings.frontend_dist_dir) / "assets"
if settings.serve_frontend and assets_path.exists():
    app.mount("/assets", StaticFiles(directory=assets_path), name="frontend-assets")


@app.get("/health", tags=["System"], response_model=None)
def health(request: Request) -> FileResponse | dict[str, str]:
    if "text/html" in request.headers.get("accept", ""):
        index_path = _frontend_index()
        if index_path:
            return FileResponse(index_path)
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


@app.get("/api/monitoring/health", tags=["Monitoring"])
def monitoring_health() -> dict[str, str | float | None]:
    database_status = "unknown"
    database_role = None
    database_ssl_status = None
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    select
                        current_user as database_role,
                        coalesce(
                            (
                                select case when ssl then 'on' else 'off' end
                                from pg_stat_ssl
                                where pid = pg_backend_pid()
                            ),
                            'unknown'
                        ) as database_ssl_status
                    """
                )
            ).mappings().one()
            database_role = row["database_role"]
            database_ssl_status = row["database_ssl_status"]
        database_status = "ok"
    except Exception:
        database_status = "unavailable"
    return {
        "app_name": APP_NAME,
        "environment": settings.app_env,
        "status": "ok" if database_status == "ok" else "degraded",
        "version": settings.app_version,
        "build_sha": "unknown",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "storage_backend": "postgresql",
        "database_status": database_status,
        "database_role": database_role,
        "database_ssl_status": database_ssl_status,
        "uptime_seconds": round(time.monotonic() - APP_STARTED_MONOTONIC, 3),
    }


@app.post("/api/operations/adls-smoke-upload", tags=["Operations"], response_model=None)
def adls_smoke_upload(payload: AdlsSmokeUploadRequest) -> object:
    if payload.confirm != CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "confirmation_required",
                "message": f'Send {{"confirm":"{CONFIRMATION_PHRASE}"}} to upload the tiny ADLS smoke batch.',
            },
        )
    try:
        return run_adls_smoke_upload(source_system="clinical")
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "source_system": "clinical",
                "status": "failed",
                "file_count": 0,
                "row_count": 0,
                "uploaded_paths": [],
                "batch_id": None,
                "auth_mode": os.getenv("DATA_LAKE_AUTH_MODE", "managed_identity"),
                "account_name": os.getenv("DATA_LAKE_ACCOUNT_NAME", ""),
                "container": os.getenv("DATA_LAKE_CONTAINER", "datalake"),
                "error": str(exc),
            },
        )


@app.post("/api/operations/clinical-historical-adls-upload", tags=["Operations"], response_model=None)
def clinical_historical_adls_upload(
    payload: HistoricalAdlsUploadRequest,
    _: User = Depends(require_permission("system.admin")),
) -> object:
    if payload.confirm != HISTORICAL_CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "confirmation_required",
                "message": f'Send {{"confirm":"{HISTORICAL_CONFIRMATION_PHRASE}"}} to upload the Clinical historical ADLS batch.',
            },
        )
    try:
        return run_clinical_historical_adls_upload(batch_id=payload.batch_id)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "source_system": "clinical",
                "status": "failed",
                "batch_id": payload.batch_id,
                "file_count": 0,
                "row_count": 0,
                "uploaded_paths": [],
                "auth_mode": os.getenv("DATA_LAKE_AUTH_MODE", "managed_identity"),
                "account_name": os.getenv("DATA_LAKE_ACCOUNT_NAME", ""),
                "container": os.getenv("DATA_LAKE_CONTAINER", "datalake"),
                "error": str(exc),
            },
        )


@app.get("/", tags=["System"], response_model=None)
def root() -> FileResponse | dict[str, str]:
    index_path = _frontend_index()
    if index_path:
        return FileResponse(index_path)
    return {
        "message": "Clinical Donor Screening & Quality Workflow Platform API",
        "docs": "/docs",
    }


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def serve_frontend(full_path: str) -> FileResponse:
    if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
        raise HTTPException(status_code=404, detail="Not found")
    index_path = _frontend_index()
    if not index_path:
        raise HTTPException(status_code=404, detail="Frontend build is not available")
    return FileResponse(index_path)

