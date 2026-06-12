import json
from pathlib import Path

from app.main import app
from app.schemas.clinical import WorkflowOperation
from app.services import clinical_workflows
from app.services.clinical_workflows import append_workflow_operation
from fastapi.testclient import TestClient


def _commit_payload() -> dict[str, object]:
    return {
        "workflow": "clinical.foundation.commit",
        "entity_type": "clinical_shell",
        "entity_id": "CLINICAL-0100",
        "actor": "sprint1@example.org",
        "preview_hash": "sha256-test-preview",
        "status_before": "draft",
        "status_after": "foundation_ready",
        "reason": "Sprint 1 foundation validation",
        "changes": {"clinical_router": "added"},
    }


def test_missing_confirmation_header_rejected(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)

    response = TestClient(app).post("/api/clinical/workflows/commit", json=_commit_payload())

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"
    assert not audit_path.exists()


def test_invalid_confirmation_header_rejected(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)

    response = TestClient(app).post(
        "/api/clinical/workflows/commit",
        headers={"X-Confirm-Generation": "false"},
        json=_commit_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"
    assert not audit_path.exists()


def test_valid_confirmation_header_accepted(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "metadata" / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)

    response = TestClient(app).post(
        "/api/clinical/workflows/commit",
        headers={"X-Confirm-Generation": "true"},
        json=_commit_payload(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "committed"
    assert payload["operation"]["commit_confirmed"] is True
    assert payload["operation"]["preview_hash"] == "sha256-test-preview"
    assert audit_path.exists()


def test_workflow_audit_file_created_if_missing(tmp_path: Path) -> None:
    audit_path = tmp_path / "metadata" / "workflow_operations.json"
    operation = WorkflowOperation(
        workflow="clinical.foundation.preview",
        entity_type="clinical_shell",
        entity_id="CLINICAL-0100",
        actor="tester@example.org",
        preview_hash="sha256-created",
        status_before="draft",
        status_after="previewed",
        reason="Create missing audit file",
        changes={"file": "created"},
    )

    append_workflow_operation(operation, path=audit_path)

    assert audit_path.exists()
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert len(entries) == 1
    assert entries[0]["workflow"] == "clinical.foundation.preview"


def test_workflow_audit_entry_appended_without_destroying_existing_entries(tmp_path: Path) -> None:
    audit_path = tmp_path / "metadata" / "workflow_operations.json"
    audit_path.parent.mkdir(parents=True)
    existing = {
        "operation_id": "existing-operation",
        "workflow": "clinical.existing",
        "entity_type": "clinical_shell",
        "entity_id": "EXISTING",
        "actor": "existing@example.org",
        "timestamp": "2026-06-12T00:00:00Z",
        "preview_hash": "sha256-existing",
        "commit_confirmed": True,
        "status_before": "draft",
        "status_after": "committed",
        "reason": "Existing operation",
        "changes": {"existing": True},
    }
    audit_path.write_text(json.dumps([existing], indent=2) + "\n", encoding="utf-8")
    operation = WorkflowOperation(
        workflow="clinical.appended",
        entity_type="clinical_shell",
        entity_id="APPENDED",
        actor="tester@example.org",
        preview_hash="sha256-appended",
        status_before="previewed",
        status_after="committed",
        reason="Append audit entry",
        changes={"appended": True},
    )

    append_workflow_operation(operation, path=audit_path)

    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert len(entries) == 2
    assert entries[0] == existing
    assert entries[1]["workflow"] == "clinical.appended"
