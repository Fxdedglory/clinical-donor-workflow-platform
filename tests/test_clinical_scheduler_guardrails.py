from __future__ import annotations

import pytest

from app.services.clinical_scheduler_guardrails import (
    DESTRUCTIVE_CONFIRMATION_PHRASE,
    build_accepted_refresh_manifest,
    build_monitor_payloads,
    run_clinical_scheduler_refresh,
    validate_backup_evidence,
)


def _backup_evidence() -> dict[str, object]:
    return {
        "server_name": "psql-teemails-clinical-dev-wcus",
        "database_name": "clinical_donor_workflow",
        "observed_at": "2026-06-04T12:00:00Z",
        "backup_retention_days": 7,
        "earliest_restore_time": "2026-05-29T14:53:42Z",
        "restore_scope": "Azure PostgreSQL flexible server point-in-time restore",
    }


def test_dry_run_does_not_execute_refresh_functions() -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("dry-run must not execute refresh, validate, or export functions")

    result = run_clinical_scheduler_refresh(
        refresh_mode="incremental_demo_refresh",
        batch_id="clinical_guardrail_dry_run",
        dry_run=True,
        incremental_fn=fail_if_called,
        validate_fn=fail_if_called,
        export_fn=fail_if_called,
    )

    assert result["status"] == "dry_run"
    assert result["executed"] is False
    assert result["plan"]["allowed_to_execute"] is True
    assert result["plan"]["destructive"] is False


def test_destructive_refresh_requires_backup_force_and_confirmation() -> None:
    result = run_clinical_scheduler_refresh(
        refresh_mode="full_reseed",
        batch_id="clinical_guardrail_reseed",
        dry_run=True,
    )

    issues = result["plan"]["guardrail_issues"]
    assert result["plan"]["allowed_to_execute"] is False
    assert any("backup_evidence" in issue for issue in issues)
    assert any("force=true" in issue for issue in issues)
    assert any(DESTRUCTIVE_CONFIRMATION_PHRASE in issue for issue in issues)


def test_destructive_refresh_allows_execution_only_with_full_guardrails() -> None:
    issues = validate_backup_evidence(_backup_evidence())
    assert issues == []

    result = run_clinical_scheduler_refresh(
        refresh_mode="full_reseed",
        batch_id="clinical_guardrail_reseed",
        dry_run=True,
        force=True,
        confirm=DESTRUCTIVE_CONFIRMATION_PHRASE,
        backup_evidence=_backup_evidence(),
    )

    assert result["plan"]["allowed_to_execute"] is True
    assert result["plan"]["backup_evidence_present"] is True


def test_accepted_manifest_requires_passing_validation_and_rows() -> None:
    manifest = build_accepted_refresh_manifest(
        batch_id="clinical_batch_1",
        refresh_mode="incremental_demo_refresh",
        refresh_started_at="2026-06-04T12:00:00Z",
        refresh_completed_at="2026-06-04T12:01:00Z",
        validation={"status": "passed"},
        export_manifest={
            "extraction_batch_id": "clinical_batch_1",
            "export_path": "data/exports/clinical_batch_1",
            "files": [{"table": "dim_donor", "row_count": 2}],
        },
        backup_evidence={"server_name": "safe", "connection_string": "not exported"},
    )

    assert manifest["quality_status"] == "passed"
    assert manifest["accepted_at"]
    assert manifest["row_count_total"] == 2
    assert manifest["file_count_total"] == 1
    assert "connection_string" not in manifest["backup_evidence"]


def test_monitor_payload_contract_is_sanitized() -> None:
    payloads = build_monitor_payloads(
        run_id="clinical-run-1",
        batch_id="clinical_batch_1",
        refresh_mode="incremental_demo_refresh",
        status="completed",
        started_at="2026-06-04T12:00:00Z",
        ended_at="2026-06-04T12:01:00Z",
        row_count=10,
        file_count=3,
        validation_status="passed",
        backup_evidence_present=False,
    )

    assert set(payloads) == {"job_run", "status_event", "active_edge"}
    assert payloads["job_run"]["source_system"] == "clinical"
    assert payloads["job_run"]["job_type"] == "scheduled_postgresql_refresh_export"
    assert payloads["active_edge"]["source_node_id"] == "clinical-postgresql"
    for payload in payloads.values():
        metadata = payload["metadata_json"]
        assert metadata["scheduler"] == "azure_container_apps_job"
        assert "token" not in str(metadata).lower()
        assert "password" not in str(metadata).lower()


def test_invalid_refresh_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        run_clinical_scheduler_refresh(refresh_mode="startup_scheduler")
