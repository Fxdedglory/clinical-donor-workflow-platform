"""Publish sanitized Clinical operational job status into Monitor."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from typing import Any

import requests


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    blocked = ("password", "secret", "token", "key", "credential", "connection", "mfa", "session")
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if any(part in str(key).lower() for part in blocked):
            continue
        if any(part in str(value).lower() for part in ("begin rsa", "private key", "password=")):
            continue
        safe[str(key)] = value
    return safe


class MonitorPublisher:
    def __init__(self) -> None:
        self.base_url = os.getenv("MONITOR_BASE_URL", "https://teemails.com/Monitor").rstrip("/")
        self.token = os.getenv("MONITOR_API_TOKEN", "")
        self.timeout_seconds = float(os.getenv("MONITOR_TIMEOUT_SECONDS", "20"))
        self.enabled = os.getenv("MONITOR_PUBLISH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.token)

    def post(self, path: str, payload: dict[str, Any]) -> None:
        if not self.configured:
            return
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

    def publish_cycle(self, *, run: dict[str, Any], manifest: dict[str, Any] | None, status: str, error: str | None = None) -> None:
        started_at = str(run.get("started_at") or _now())
        ended_at = str(run.get("finished_at") or _now())
        job_run_id = f"clinical-scheduled-{run.get('run_id') or hashlib.sha256(ended_at.encode()).hexdigest()[:16]}"
        row_counts = run.get("row_counts") if isinstance(run.get("row_counts"), dict) else {}
        rows = int(sum(int(value or 0) for value in row_counts.values()) or run.get("rows_affected") or 0)
        files = len((manifest or {}).get("files") or [])
        metadata = _safe_metadata(
            {
                "run_id": run.get("run_id"),
                "run_type": run.get("run_type"),
                "validation_status": run.get("validation_status"),
                "export_batch_id": (manifest or {}).get("extraction_batch_id") or (manifest or {}).get("batch_id"),
                "scheduler": "clinical_app_service_background",
            }
        )
        self.post(
            "/api/platform/job-runs",
            {
                "job_run_id": job_run_id,
                "source_system": "clinical",
                "job_type": "scheduled_postgresql_refresh_export",
                "external_run_id": str(run.get("run_id") or ""),
                "status": status,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_seconds": float(run.get("duration_seconds") or 0),
                "rows_processed": rows,
                "files_processed": files,
                "error_count": 1 if error else 0,
                "error_message": error,
                "metadata_json": metadata,
            },
        )
        self.post(
            "/api/platform/status-events",
            {
                "event_id": f"{job_run_id}-event",
                "event_type": "scheduled_postgresql_refresh_export",
                "source_system": "clinical",
                "status": "healthy" if not error else "failed",
                "severity": "info" if not error else "error",
                "message": "Clinical scheduled PostgreSQL refresh/export completed." if not error else "Clinical scheduled PostgreSQL refresh/export failed.",
                "related_resource_id": "azure://app-service/app-teemails-clinical-dev",
                "related_job_run_id": job_run_id,
                "event_time": ended_at,
                "metadata_json": metadata,
            },
        )
        self.post(
            "/api/infrastructure/active-edges",
            {
                "active_edge_id": f"{job_run_id}-edge",
                "edge_id": "clinical.postgresql.publishes_to.monitor",
                "source_node_id": "clinical",
                "target_node_id": "monitor",
                "job_run_id": job_run_id,
                "state": "completed" if not error else "failed",
                "started_at": started_at,
                "ended_at": ended_at,
                "rows_processed": rows,
                "files_processed": files,
                "error_count": 1 if error else 0,
                "metadata_json": metadata,
            },
        )
